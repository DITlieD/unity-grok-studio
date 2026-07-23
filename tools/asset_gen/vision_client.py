#!/usr/bin/env python3
"""Python vision second-check client (same contract as vision-check MCP).

Uses Anthropic POST /v1/messages ONLY against the vision bridge / FreeLLMAPI.
Bridge-down => explicit unavailable object (never silent pass).
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BRIDGE_URL = os.environ.get("VISION_BRIDGE_URL", os.environ.get("CLOUDCODE_BRIDGE_URL", os.environ.get("FREELLM_BASE_URL", "http://127.0.0.1:3001")))
DEFAULT_MODEL = os.environ.get("VISION_CHECK_MODEL", "gemini-3.5-flash-low")
ESCALATE_MODEL = os.environ.get("VISION_CHECK_ESCALATE_MODEL", "gemini-3.1-pro-high")

SYSTEM_CHECK = (
    "You are a strict visual QA critic for game assets and UI.\n"
    "Describe what you see FIRST, then judge each checklist item.\n"
    "Return ONLY valid JSON (no markdown fences) of the form:\n"
    '{"items":[{"item":"...","verdict":"pass"|"fail"|"unknown",'
    '"evidence_region":[x0,y0,x1,y1],"note":"..."}]}\n'
    "unknown is treated as fail. Never invent counts from vision alone."
)

DEFAULT_CHECKLIST = [
    "no obvious seams or tiling discontinuities at edges",
    "no baked lighting / shadows that break tiling",
    "scale and texture density look intentional",
    "no large repeated identical blobs / obvious copy-paste",
    "colors look within a coherent material palette",
]


def treat_unknown_as_fail(verdict: str) -> str:
    return "pass" if verdict == "pass" else "fail"


def parse_check_json(raw: str) -> list[dict[str, Any]] | None:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    items = obj.get("items") if isinstance(obj, dict) else None
    if not isinstance(items, list) or not items:
        return None
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        verdict = str(it.get("verdict", "unknown")).lower()
        if verdict not in ("pass", "fail", "unknown"):
            verdict = "unknown"
        region = it.get("evidence_region") or [0, 0, 1, 1]
        if not (isinstance(region, (list, tuple)) and len(region) >= 4):
            region = [0, 0, 1, 1]
        out.append(
            {
                "item": str(it.get("item", "")),
                "verdict": verdict,
                "evidence_region": [float(region[i]) for i in range(4)],
                "note": str(it.get("note", "")),
            }
        )
    return out or None


def bridge_health(bridge_url: str = DEFAULT_BRIDGE_URL, timeout: float = 3.0) -> tuple[bool, str]:
    url = bridge_url.rstrip("/") + "/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (resp.status == 200 and body.startswith("ok "), body)
    except Exception as exc:
        return False, repr(exc)


def _post_messages(bridge_url: str, body: dict, timeout: float = 120.0) -> tuple[bool, Any, str]:
    url = bridge_url.rstrip("/") + "/v1/messages"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": "unused",
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(raw), ""
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        try:
            return False, json.loads(err), f"HTTP {exc.code}: {err[:300]}"
        except json.JSONDecodeError:
            return False, None, f"HTTP {exc.code}: {err[:300]}"
    except Exception as exc:
        return False, None, repr(exc)


def _extract_text(resp: Any) -> str:
    if not isinstance(resp, dict):
        return ""
    content = resp.get("content") or []
    if not isinstance(content, list):
        return ""
    return "\n".join(
        str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("type") == "text"
    )


def image_to_b64(path: str | Path) -> tuple[str, str]:
    p = Path(path)
    data = p.read_bytes()
    ext = p.suffix.lower()
    mt = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")
    return base64.b64encode(data).decode("ascii"), mt


def vision_check(
    image_path: str | Path | None = None,
    *,
    image_b64: str | None = None,
    media_type: str = "image/jpeg",
    context: str = "",
    checklist: list[str] | None = None,
    bridge_url: str = DEFAULT_BRIDGE_URL,
    model: str | None = None,
) -> dict[str, Any]:
    up, health_body = bridge_health(bridge_url)
    model = model or DEFAULT_MODEL
    if not up:
        return {
            "items": [],
            "model": model,
            "raw": "",
            "unavailable": True,
            "reason": f"vision bridge / FreeLLMAPI unavailable at {bridge_url}: {health_body}",
        }
    if image_b64 is None:
        if image_path is None:
            raise ValueError("image_path or image_b64 required")
        image_b64, media_type = image_to_b64(image_path)
    cl = checklist or DEFAULT_CHECKLIST
    text = (
        f"Context: {context}\nChecklist:\n"
        + "\n".join(f"{i+1}. {c}" for i, c in enumerate(cl))
        + "\nDescribe briefly, then return the JSON items array."
    )
    body = {
        "model": model,
        "max_tokens": 2048,
        "system": SYSTEM_CHECK,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                ],
            }
        ],
    }
    ok, resp, err = _post_messages(bridge_url, body)
    raw = _extract_text(resp) if ok else ""
    items = parse_check_json(raw) if raw else None
    if items is None:
        body["model"] = ESCALATE_MODEL
        body["messages"][0]["content"][0]["text"] = (
            text + "\n\nPrevious response was not valid JSON. Return ONLY the JSON object."
        )
        ok2, resp2, err2 = _post_messages(bridge_url, body)
        raw = _extract_text(resp2) if ok2 else raw
        items = parse_check_json(raw) if raw else None
        model = ESCALATE_MODEL
        if not ok2:
            err = err2
    if items is None:
        return {
            "items": [
                {
                    "item": c,
                    "verdict": "unknown",
                    "evidence_region": [0, 0, 1, 1],
                    "note": err or "parse failure after re-ask; unknown(=fail)",
                }
                for c in cl
            ],
            "model": model,
            "raw": raw or err or "",
        }
    return {"items": items, "model": model, "raw": raw}


def vision_describe(
    image_path: str | Path | None = None,
    *,
    image_b64: str | None = None,
    media_type: str = "image/jpeg",
    question: str = "Describe this image.",
    bridge_url: str = DEFAULT_BRIDGE_URL,
    model: str | None = None,
) -> dict[str, Any]:
    up, health_body = bridge_health(bridge_url)
    model = model or DEFAULT_MODEL
    if not up:
        return {
            "description": "",
            "model": model,
            "unavailable": True,
            "reason": f"vision bridge / FreeLLMAPI unavailable at {bridge_url}: {health_body}",
        }
    if image_b64 is None:
        if image_path is None:
            raise ValueError("image_path or image_b64 required")
        image_b64, media_type = image_to_b64(image_path)
    body = {
        "model": model,
        "max_tokens": 2048,
        "system": "Describe the image accurately and answer the question.",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                ],
            }
        ],
    }
    ok, resp, err = _post_messages(bridge_url, body)
    if not ok:
        return {
            "description": "",
            "model": model,
            "unavailable": True,
            "reason": err,
        }
    return {"description": _extract_text(resp), "model": model}
