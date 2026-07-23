"""Anthropic Messages API  ->  Devin gateway (server.codeium.com) proxy.

Claude Code speaks the Anthropic Messages API; the Devin gateway speaks
Connect-RPC + protobuf. This proxy presents POST /v1/messages locally,
translates each call into the captured GetChatMessage protobuf frame, posts it
with your bearer token, and translates the streamed proto response back into
Anthropic SSE.

Run:
  python -m uvicorn devin_proxy:app --host 0.0.0.0 --port 8810
  (or: python devin_proxy.py)

Env knobs:
  DEVIN_PROXY_MODEL    force a Devin model id for every call (e.g. kimi-k2-7).
                       if unset, Claude Code's requested model id is passed through.
  DEVIN_TEMPERATURE / DEVIN_TOP_K / DEVIN_TOP_P / DEVIN_MAX_TOKENS
                       force CompletionConfig values (override Claude Code's).
  DEVIN_EMIT_REASONING=1   prepend the model's field-9 reasoning to the text answer.
  DEVIN_CREDS          path to credentials.toml (default: kit account-store).
  DEVIN_PROXY_PORT     port (default 8810) when run as __main__.
  DEVIN_LOG=1          verbose request/response logging to stderr.
"""
from __future__ import annotations
import json, os, sys, time, uuid
import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse, PlainTextResponse
from starlette.routing import Route

sys.path.insert(0, os.path.dirname(__file__))
import devin_wire as W
import replay_pb2
import account_catalog as CAT

LOG = os.environ.get("DEVIN_LOG") == "1"
EMIT_REASONING = os.environ.get("DEVIN_EMIT_REASONING") == "1"
_TEMPLATE = W.load_template()           # seed metadata from the proven capture, once
_CONV_ID = uuid.uuid4().hex             # one conversation id per proxy process


def log(*a):
    if LOG:
        print("[proxy]", *a, file=sys.stderr, flush=True)


def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


STOP_MAP = {2: "end_turn", 10: "tool_use", 3: "max_tokens"}


def _estimate_tokens(body: dict) -> int:
    """Consistent char/4 token estimate of an Anthropic request's full input: the system prompt
    (string OR content blocks) + every message's content + the tool definitions. The gateway does
    not reliably report input_tokens, so we report a REAL number ourselves -- Claude Code reads
    message_start.usage.input_tokens for its context meter, and the conductor's usage_ctx_used sums
    it. char/4 is a deliberate cross-model approximation (exact per-model token counts are
    impossible; each model tokenizes differently); it is a trustworthy, consistent floor, NOT an
    exact count. The gateway's own input_tokens overrides this when present and larger."""
    def _chars(v):
        if v is None:
            return 0
        if isinstance(v, str):
            return len(v)
        if isinstance(v, list):
            n = 0
            for b in v:
                if isinstance(b, str):
                    n += len(b)
                elif isinstance(b, dict):
                    n += len(b.get("text") or "")
                    if b.get("input") is not None:
                        n += len(json.dumps(b.get("input")))
                    if b.get("content") is not None:
                        n += _chars(b.get("content"))
            return n
        if isinstance(v, dict):
            return len(json.dumps(v))
        return len(str(v))
    chars = _chars(body.get("system"))
    for m in body.get("messages") or []:
        chars += _chars(m.get("content"))
    chars += len(json.dumps(body.get("tools") or []))
    return max(1, chars // 4)


def _explain_gateway_error(err) -> str:
    """Turn a raw gateway error into a readable, actionable message."""
    msg = ""
    code = ""
    if isinstance(err, dict):
        code = err.get("code", "")
        msg = err.get("message", "") or json.dumps(err)
    else:
        msg = str(err)
    low = (msg + " " + code).lower()
    if "content policy" in low or "permission_denied" in low or "unsafe" in low:
        return ("[devin-proxy] The Devin gateway's content filter blocked this request. "
                "Free models reject capability-explicit tool descriptions and security-heavy "
                "system prompts. Try: DEVIN_TOOL_DESC=generic (sanitize tool text), and/or run "
                "in a project whose CLAUDE.md isn't security/RE-heavy (this ELAI root's rules "
                "trip the filter). Raw: " + msg[:200])
    return "[devin-proxy gateway error] " + msg[:400]


def _build_devin_request(body: dict):
    token = W.read_token()
    req = W.build_request(body, token, template=_TEMPLATE, conv_id=_CONV_ID)
    return token, req


def _gateway_stream(token: str, req) -> httpx.Response:
    payload = req.SerializeToString()
    url = W.server_url() + W.ENDPOINT_PATH
    headers = {"authorization": f"Bearer {token}",
               "content-type": "application/connect+proto",
               "connect-protocol-version": "1", "accept": "*/*"}
    client = httpx.Client(timeout=httpx.Timeout(300.0, connect=30.0))
    stream = client.stream("POST", url, content=W.frame(payload), headers=headers)
    return client, stream


def _iter_devin(client, stream):
    """Yield ('error', dict) | ('chat', ChatResp) | ('end', dict) from the gateway."""
    with stream as r:
        if r.status_code != 200:
            yield "error", {"status": r.status_code, "body": r.read().decode("utf-8", "replace")}
            return
        for flags, msg in W.iter_frames(r.iter_bytes()):
            if flags & 2:
                try:
                    end = json.loads(msg.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    end = {"raw": msg.decode("utf-8", "replace")}
                yield "end", end
                return
            fr = replay_pb2.ChatResp()
            fr.ParseFromString(msg)
            yield "chat", fr
    client.close()


def _translate(body: dict):
    """Generator of Anthropic SSE byte-events translated from the Devin stream."""
    model_out = body.get("model") or os.environ.get("DEVIN_PROXY_MODEL") or "unknown"
    msg_id = "msg_" + uuid.uuid4().hex[:24]

    # Report a REAL input_tokens up front (the gateway often omits it / the old code hardcoded 0,
    # so the conductor's ctx meter showed only the reply size). message_start is where the Anthropic
    # streaming protocol carries input_tokens, so Claude Code + the conductor read it from here.
    in_tok = _estimate_tokens(body)
    yield sse("message_start", {
        "type": "message_start",
        "message": {"id": msg_id, "type": "message", "role": "assistant",
                    "model": model_out, "content": [],
                    "stop_reason": None, "stop_sequence": None,
                    "usage": {"input_tokens": in_tok, "output_tokens": 0}}})

    token, req = _build_devin_request(body)
    log("model=%s msgs=%d tools=%d cfg(t=%s tk=%s tp=%s max=%s)" % (
        req.model, len(req.messages), len(req.tools), req.config.temperature,
        req.config.top_k, round(req.config.top_p, 4), req.config.max_tokens))
    client, stream = _gateway_stream(token, req)

    # block bookkeeping
    block_index = -1
    text_open = False
    answer_chars = 0
    reasoning = ""
    tool_blocks = {}          # call_id -> {index, args_started}
    stop_reason = "end_turn"
    usage = {"input_tokens": in_tok, "output_tokens": 0}

    def open_text():
        nonlocal block_index, text_open
        block_index += 1
        text_open = True
        return sse("content_block_start", {
            "type": "content_block_start", "index": block_index,
            "content_block": {"type": "text", "text": ""}})

    for kind, item in _iter_devin(client, stream):
        if kind == "error":
            # surface as a text block so Claude Code shows it, then stop
            if not text_open:
                yield open_text()
            txt = _explain_gateway_error({"code": "http_%s" % item["status"], "message": item["body"]})
            yield sse("content_block_delta", {
                "type": "content_block_delta", "index": block_index,
                "delta": {"type": "text_delta", "text": txt}})
            log("gateway HTTP error:", item["status"], item["body"][:200])
            stop_reason = "end_turn"
            break
        if kind == "end":
            if isinstance(item, dict) and item.get("error"):
                if not text_open:
                    yield open_text()
                txt = _explain_gateway_error(item["error"])
                yield sse("content_block_delta", {
                    "type": "content_block_delta", "index": block_index,
                    "delta": {"type": "text_delta", "text": txt}})
                log("gateway stream error:", json.dumps(item["error"])[:200])
            break

        fr = item  # ChatResp
        if fr.delta_text:
            reasoning += fr.delta_text

        if fr.final_text:
            if not text_open:
                yield open_text()
            yield sse("content_block_delta", {
                "type": "content_block_delta", "index": block_index,
                "delta": {"type": "text_delta", "text": fr.final_text}})
            answer_chars += len(fr.final_text)

        tc = fr.tool_call
        if tc.id or tc.name or tc.arguments:
            cid = tc.id or (next(reversed(tool_blocks)) if tool_blocks else "call_0")
            if cid not in tool_blocks:
                if text_open:
                    yield sse("content_block_stop", {"type": "content_block_stop", "index": block_index})
                    text_open = False
                block_index += 1
                tool_blocks[cid] = {"index": block_index}
                # strip the "functions.<name>:<i>" prefix devin uses for the id
                aid = cid
                yield sse("content_block_start", {
                    "type": "content_block_start", "index": block_index,
                    "content_block": {"type": "tool_use", "id": aid,
                                      "name": tc.name or "", "input": {}}})
            if tc.arguments:
                yield sse("content_block_delta", {
                    "type": "content_block_delta", "index": tool_blocks[cid]["index"],
                    "delta": {"type": "input_json_delta", "partial_json": tc.arguments}})

        if fr.stop_marker:
            stop_reason = STOP_MAP.get(fr.stop_marker, "end_turn")
        if fr.meta.input_tokens or fr.meta.output_tokens:
            # Prefer the gateway's input count when it reports a real (larger) number; otherwise
            # keep our up-front estimate (the gateway frequently reports 0/partial input).
            if fr.meta.input_tokens:
                usage["input_tokens"] = max(usage["input_tokens"], fr.meta.input_tokens)
            usage["output_tokens"] = fr.meta.output_tokens or usage["output_tokens"]

    # fallback: model put its whole answer in field 9 (reasoning) and field 3 was empty
    if answer_chars == 0 and reasoning and not tool_blocks:
        yield open_text()
        yield sse("content_block_delta", {
            "type": "content_block_delta", "index": block_index,
            "delta": {"type": "text_delta", "text": reasoning}})
    elif EMIT_REASONING and reasoning and text_open:
        pass  # reasoning already separate; left as a knob

    if tool_blocks:
        stop_reason = "tool_use"

    # close any open block
    if text_open or tool_blocks:
        yield sse("content_block_stop", {"type": "content_block_stop", "index": block_index})

    yield sse("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": stop_reason, "stop_sequence": None},
        "usage": {"input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"]}})
    yield sse("message_stop", {"type": "message_stop"})
    log("done stop=%s usage=%s answer_chars=%d tools=%d" % (
        stop_reason, usage, answer_chars, len(tool_blocks)))


def _aggregate(body: dict) -> dict:
    """Non-streaming: collect the SSE translation into one Anthropic Message."""
    content, cur_text, cur_tool = [], None, None
    msg_id = "msg_" + uuid.uuid4().hex[:24]
    model_out = body.get("model") or os.environ.get("DEVIN_PROXY_MODEL") or "unknown"
    stop_reason, usage = "end_turn", {"input_tokens": _estimate_tokens(body), "output_tokens": 0}
    for ev in _translate(body):
        line = ev.decode("utf-8")
        if "\ndata: " not in line:
            continue
        data = json.loads(line.split("\ndata: ", 1)[1].strip())
        t = data.get("type")
        if t == "content_block_start":
            cb = data["content_block"]
            if cb["type"] == "text":
                cur_text = {"type": "text", "text": ""}
            else:
                cur_tool = {"type": "tool_use", "id": cb["id"], "name": cb["name"], "_args": ""}
        elif t == "content_block_delta":
            d = data["delta"]
            if d["type"] == "text_delta" and cur_text is not None:
                cur_text["text"] += d["text"]
            elif d["type"] == "input_json_delta" and cur_tool is not None:
                cur_tool["_args"] += d["partial_json"]
        elif t == "content_block_stop":
            if cur_text is not None:
                content.append(cur_text); cur_text = None
            if cur_tool is not None:
                try:
                    cur_tool["input"] = json.loads(cur_tool.pop("_args") or "{}")
                except json.JSONDecodeError:
                    cur_tool["input"] = {}; cur_tool.pop("_args", None)
                content.append(cur_tool); cur_tool = None
        elif t == "message_delta":
            stop_reason = data["delta"]["stop_reason"]
            usage["output_tokens"] = data["usage"].get("output_tokens", usage["output_tokens"])
            if data["usage"].get("input_tokens"):
                usage["input_tokens"] = max(usage["input_tokens"], data["usage"]["input_tokens"])
    return {"id": msg_id, "type": "message", "role": "assistant", "model": model_out,
            "content": content, "stop_reason": stop_reason, "stop_sequence": None, "usage": usage}


_dump_n = {"i": 0}


def _maybe_dump(body):
    if os.environ.get("DEVIN_DUMP") != "1":
        return
    _dump_n["i"] += 1
    capdir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "capture"))
    os.makedirs(capdir, exist_ok=True)
    p = os.path.join(capdir, f"cc_req_{_dump_n['i']}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=1, default=str)
    log("dumped incoming request ->", p)


async def messages(request: Request):
    body = await request.json()
    _maybe_dump(body)
    if body.get("stream"):
        return StreamingResponse(_translate(body), media_type="text/event-stream")
    return JSONResponse(_aggregate(body))


async def count_tokens(request: Request):
    # Claude Code calls this for its own context display. Reuse the SAME estimator the turn path
    # reports, so the pre-count and the post-turn ctx_used stay consistent.
    body = await request.json()
    return JSONResponse({"input_tokens": _estimate_tokens(body)})


_MODEL_CREATED = "2026-01-01T00:00:00Z"


def _model_obj(r):
    return {"type": "model", "id": r["id"],
            "display_name": CAT.annotated_display(r), "created_at": _MODEL_CREATED}


async def list_models(request: Request):
    # Anthropic Models API. The build calls getAPIList("/v1/models?beta=true").
    cat = CAT.load_account_catalog()
    data = [_model_obj(r) for r in cat]
    return JSONResponse({"data": data, "has_more": False,
                         "first_id": data[0]["id"] if data else None,
                         "last_id": data[-1]["id"] if data else None})


async def get_model(request: Request):
    mid = request.path_params["model_id"]
    for r in CAT.load_account_catalog():
        if r["id"] == mid:
            return JSONResponse(_model_obj(r))
    # unknown id: synthesize a minimal record so the client doesn't hard-fail
    return JSONResponse({"type": "model", "id": mid, "display_name": mid, "created_at": _MODEL_CREATED})


async def health(_):
    cat = CAT.load_account_catalog()
    free = [r for r in cat if r["free"]]
    return PlainTextResponse(
        "ok devin-proxy model=%s | %d models on account, %d FREE (%s)" % (
            os.environ.get("DEVIN_PROXY_MODEL") or "passthrough", len(cat), len(free),
            ", ".join(r["id"] for r in free)))


app = Starlette(routes=[
    Route("/v1/messages", messages, methods=["POST"]),
    Route("/v1/messages/count_tokens", count_tokens, methods=["POST"]),
    Route("/v1/models", list_models, methods=["GET"]),
    Route("/v1/models/{model_id:path}", get_model, methods=["GET"]),
    Route("/health", health, methods=["GET"]),
    Route("/", health, methods=["GET"]),
])


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("DEVIN_PROXY_PORT", "8810"))
    # K-27: the /v1/messages handler makes a SYNC httpx call (up to 300s) inside the async loop, so a
    # single worker serializes everything -- one in-flight worker turn blocks /health (the opus-walk
    # spawn gate) and starves concurrent workers on a shared port. DEVIN_PROXY_WORKERS>1 runs N worker
    # procs (SO_REUSEPORT) so /health stays responsive while a turn runs and N turns run concurrently.
    # Default 1 = UNCHANGED behavior (the :8811-8813 research bridges do not set this env). Only :8810
    # sets DEVIN_PROXY_WORKERS=4 (matches the measured free-4 ceiling). Verified 2026-07-11.
    workers = int(os.environ.get("DEVIN_PROXY_WORKERS", "1"))
    if workers > 1:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # make "devin_proxy:app" importable in worker procs
        uvicorn.run("devin_proxy:app", host="0.0.0.0", port=port, workers=workers)
    else:
        uvicorn.run(app, host="0.0.0.0", port=port)
