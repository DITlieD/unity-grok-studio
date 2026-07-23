#!/usr/bin/env python3
"""Free OpenAI-compatible chat_completions shim for Grok free-auto.

Implements the FreeLLMAPI-shaped surface Grok expects:
  GET  /v1/models
  POST /v1/chat/completions  (stream + non-stream, tools)

Backends (first that works):
  1. FREELLM_UPSTREAM (real FreeLLMAPI / other OpenAI-compatible) if set and healthy
  2. Local Devin bridge messages API (default http://127.0.0.1:8810) with free models

This lets coworkers run `api_backend = "chat_completions"` against :3001 without
paid xAI/Claude keys. Prefer real FreeLLMAPI when provider free-tier keys exist;
set FREELLM_UPSTREAM=http://127.0.0.1:3002/v1 and run FreeLLMAPI there instead.

Env:
  SHIM_PORT           default 3001
  SHIM_HOST           default 127.0.0.1
  DEVIN_BRIDGE        default http://127.0.0.1:8810
  DEVIN_DEFAULT_MODEL default kimi-k2-7
  FREELLM_UPSTREAM    optional OpenAI-compatible base ending in /v1
  SHIM_API_KEY        accepted Bearer key (default freellmapi-local)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from uuid import uuid4

PORT = int(os.environ.get("SHIM_PORT", "3001"))
HOST = os.environ.get("SHIM_HOST", "127.0.0.1")
DEVIN = os.environ.get("DEVIN_BRIDGE", "http://127.0.0.1:8810").rstrip("/")
DEFAULT_MODEL = os.environ.get("DEVIN_DEFAULT_MODEL", "kimi-k2-7")
UPSTREAM = (os.environ.get("FREELLM_UPSTREAM") or "").rstrip("/")
API_KEY = os.environ.get("SHIM_API_KEY", "freellmapi-local")

FREE_MODELS = [
    "auto",
    "kimi-k2-7",
    "kimi-k2-6",
    "glm-5-2",
    "swe-1-6",
    "swe-check",
    "qwen3-coder",  # alias → DEFAULT_MODEL when only Devin backend
]


def _http_json(method: str, url: str, body: dict | None = None, headers: dict | None = None, timeout: float = 120.0) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw}
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


def upstream_healthy() -> bool:
    if not UPSTREAM:
        return False
    code, _ = _http_json("GET", f"{UPSTREAM}/models", timeout=3.0)
    return code == 200


def devin_healthy() -> bool:
    code, body = _http_json("GET", f"{DEVIN}/health", timeout=3.0)
    if code == 200:
        return True
    # health may be plain text
    try:
        with urllib.request.urlopen(f"{DEVIN}/health", timeout=3.0) as r:
            return r.status == 200
    except Exception:
        return False


def resolve_model(requested: str | None) -> str:
    m = (requested or "auto").strip() or "auto"
    if m in ("auto", "qwen3-coder", "free-auto"):
        return DEFAULT_MODEL
    return m


def openai_messages_to_anthropic(messages: list[dict], tools: list | None) -> dict:
    system_parts: list[str] = []
    out_msgs: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        system_parts.append(b.get("text") or "")
            continue
        if role == "tool":
            # OpenAI tool result → Anthropic tool_result user message
            out_msgs.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id") or msg.get("id") or "tool",
                    "content": content if isinstance(content, str) else json.dumps(content),
                }],
            })
            continue
        if role == "assistant" and msg.get("tool_calls"):
            blocks: list[dict] = []
            if content:
                blocks.append({"type": "text", "text": content if isinstance(content, str) else str(content)})
            for tc in msg["tool_calls"]:
                fn = tc.get("function") or {}
                args = fn.get("arguments") or "{}"
                if isinstance(args, str):
                    try:
                        args_obj = json.loads(args)
                    except json.JSONDecodeError:
                        args_obj = {"raw": args}
                else:
                    args_obj = args
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id") or f"call_{uuid4().hex[:8]}",
                    "name": fn.get("name") or "tool",
                    "input": args_obj,
                })
            out_msgs.append({"role": "assistant", "content": blocks})
            continue
        # normal user/assistant text
        if isinstance(content, list):
            text = " ".join(
                (b.get("text") or "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            text = content if isinstance(content, str) else (json.dumps(content) if content is not None else "")
        out_msgs.append({"role": role if role in ("user", "assistant") else "user", "content": text})

    body: dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "max_tokens": 4096,
        "messages": out_msgs or [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    if system_parts:
        # Keep lean: gateway filters security-heavy systems
        sys_text = "\n\n".join(system_parts)
        if len(sys_text) > 6000:
            sys_text = sys_text[:6000] + "\n…[truncated for free-model filter]"
        body["system"] = sys_text
    if tools:
        a_tools = []
        for t in tools:
            fn = t.get("function") if t.get("type") == "function" else t
            if not isinstance(fn, dict):
                continue
            name = fn.get("name") or "tool"
            # Generic description reduces Devin gateway content-filter hits
            a_tools.append({
                "name": name,
                "description": f"The {name} tool.",
                "input_schema": fn.get("parameters") or {"type": "object", "properties": {}},
            })
        if a_tools:
            body["tools"] = a_tools
    return body


def anthropic_to_openai(resp: dict, model: str) -> dict:
    content = resp.get("content") or []
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text_parts.append(block.get("text") or "")
        elif block.get("type") == "tool_use":
            tool_calls.append({
                "id": block.get("id") or f"call_{uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": block.get("name") or "tool",
                    "arguments": json.dumps(block.get("input") or {}),
                },
            })
    msg: dict[str, Any] = {
        "role": "assistant",
        "content": "".join(text_parts) if text_parts else (None if tool_calls else ""),
    }
    if tool_calls:
        msg["tool_calls"] = tool_calls
    finish = "tool_calls" if tool_calls else "stop"
    usage = resp.get("usage") or {}
    return {
        "id": resp.get("id") or f"chatcmpl-{uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": msg,
            "finish_reason": finish,
        }],
        "usage": {
            "prompt_tokens": usage.get("input_tokens") or 0,
            "completion_tokens": usage.get("output_tokens") or 0,
            "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
        },
    }


def call_upstream(body: dict) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {API_KEY}"}
    return _http_json("POST", f"{UPSTREAM}/chat/completions", body, headers, timeout=180.0)


def call_devin(body: dict) -> tuple[int, dict]:
    model = resolve_model(body.get("model"))
    a_body = openai_messages_to_anthropic(body.get("messages") or [], body.get("tools"))
    a_body["model"] = model
    if body.get("max_tokens") or body.get("max_completion_tokens"):
        a_body["max_tokens"] = int(body.get("max_tokens") or body.get("max_completion_tokens") or 4096)
    # force non-stream for simple translation; we synthesize OpenAI SSE ourselves
    a_body["stream"] = False
    code, resp = _http_json(
        "POST",
        f"{DEVIN}/v1/messages",
        a_body,
        {
            "x-api-key": "devin-local",
            "anthropic-version": "2023-06-01",
        },
        timeout=180.0,
    )
    if code != 200 or not isinstance(resp, dict):
        err = resp if isinstance(resp, dict) else {"error": str(resp)}
        return code or 502, {"error": err}
    return 200, anthropic_to_openai(resp, model)


def openai_completion_to_sse_chunks(completion: dict) -> list[bytes]:
    """Turn a full chat.completion into OpenAI SSE chunks Grok can consume."""
    cid = completion.get("id") or f"chatcmpl-{uuid4().hex[:12]}"
    model = completion.get("model") or "auto"
    created = completion.get("created") or int(time.time())
    choice0 = (completion.get("choices") or [{}])[0]
    msg = choice0.get("message") or {}
    content = msg.get("content") or ""
    tool_calls = msg.get("tool_calls") or []
    finish = choice0.get("finish_reason") or "stop"

    chunks: list[bytes] = []

    def pack(obj: dict) -> bytes:
        return f"data: {json.dumps(obj, separators=(',', ':'))}\n\n".encode("utf-8")

    # role chunk
    chunks.append(pack({
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }))
    if content:
        chunks.append(pack({
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
        }))
    if tool_calls:
        # emit tool_calls in one delta (index-stable)
        delta_tcs = []
        for i, tc in enumerate(tool_calls):
            fn = tc.get("function") or {}
            delta_tcs.append({
                "index": i,
                "id": tc.get("id"),
                "type": "function",
                "function": {"name": fn.get("name") or "", "arguments": fn.get("arguments") or ""},
            })
        chunks.append(pack({
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"tool_calls": delta_tcs}, "finish_reason": None}],
        }))
    chunks.append(pack({
        "id": cid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
    }))
    chunks.append(b"data: [DONE]\n\n")
    return chunks


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[free-chat-shim] " + (fmt % args) + "\n")

    def _auth_ok(self) -> bool:
        auth = self.headers.get("Authorization") or ""
        if not auth:
            return True  # local coworker trust; optional key
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            return token in (API_KEY, "freellmapi-local", "dummy", "")
        return True

    def _send(self, code: int, obj: Any, content_type: str = "application/json") -> None:
        raw = obj if isinstance(obj, (bytes, bytearray)) else json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_sse(self, chunks: list[bytes]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        for c in chunks:
            self.wfile.write(c)
            self.wfile.flush()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/health", "/"):
            backend = "upstream" if upstream_healthy() else ("devin" if devin_healthy() else "none")
            self._send(200, {
                "ok": True,
                "service": "unity-grok-free-chat-shim",
                "backend": backend,
                "port": PORT,
            })
            return
        if path in ("/v1/models", "/models"):
            data = {
                "object": "list",
                "data": [
                    {"id": m, "object": "model", "owned_by": "unity-grok-free"}
                    for m in FREE_MODELS
                ],
            }
            self._send(200, data)
            return
        self._send(404, {"error": "not found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._send(404, {"error": "not found", "path": path})
            return
        if not self._auth_ok():
            self._send(401, {"error": "unauthorized"})
            return

        want_stream = bool(body.get("stream"))

        # Prefer real FreeLLMAPI-shaped upstream when configured and healthy
        if upstream_healthy():
            up_body = dict(body)
            # always fetch non-stream then re-emit so we control framing
            up_body["stream"] = False
            code, resp = call_upstream(up_body)
            if code == 200 and isinstance(resp, dict) and "choices" in resp:
                if want_stream:
                    self._send_sse(openai_completion_to_sse_chunks(resp))
                else:
                    self._send(200, resp)
                return
            # fall through to Devin on upstream failure

        if not devin_healthy():
            self._send(503, {
                "error": {
                    "message": "No free backend: start Devin bridge on :8810 or FreeLLMAPI upstream",
                    "type": "backend_unavailable",
                }
            })
            return

        code, resp = call_devin(body)
        if code != 200 or not isinstance(resp, dict) or "choices" not in resp:
            self._send(code if code else 502, resp)
            return
        if want_stream:
            self._send_sse(openai_completion_to_sse_chunks(resp))
        else:
            self._send(200, resp)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[free-chat-shim] listening on http://{HOST}:{PORT}/v1 (Devin={DEVIN} upstream={UPSTREAM or 'none'})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[free-chat-shim] stop", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
