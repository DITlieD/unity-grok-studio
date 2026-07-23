"""Meshy HTTP wrappers with Generated/ output contract.

Real create + poll against Meshy OpenAPI when MESHY_API_KEY is set.
On missing key / HTTP failure / timeout: unavailable + procedural fallback
(primary path remains blender-gen procedural).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .manifest import write_manifest
from .paths import generated_root


MESHY_BASE = os.environ.get("MESHY_API_BASE", "https://api.meshy.ai")


def _headers() -> dict[str, str]:
    key = os.environ.get("MESHY_API_KEY", "")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _http_json(
    method: str,
    url: str,
    body: dict | None = None,
    timeout: float = 60.0,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return resp.status, {"raw": raw}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(err)
        except json.JSONDecodeError:
            return exc.code, {"error": err[:500]}
    except Exception as exc:
        return 0, {"error": repr(exc)}


def check_balance() -> dict[str, Any]:
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        return {"ok": False, "reason": "MESHY_API_KEY unset", "credits": None}
    status, data = _http_json("GET", f"{MESHY_BASE}/openapi/v1/balance")
    if status and 200 <= status < 300:
        return {"ok": True, "raw": data}
    return {"ok": False, "reason": f"balance HTTP {status}: {data}", "raw": data}


def _poll_task(
    status_urls: list[str],
    *,
    poll_s: float,
    timeout_s: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last: Any = None
    while time.time() < deadline:
        for url in status_urls:
            status, data = _http_json("GET", url, timeout=min(60.0, timeout_s))
            last = data
            if not status or status >= 400:
                continue
            # Meshy uses status: PENDING|IN_PROGRESS|SUCCEEDED|FAILED|CANCELED
            st = ""
            if isinstance(data, dict):
                st = str(data.get("status") or data.get("task_status") or "").upper()
            if st in ("SUCCEEDED", "SUCCESS", "DONE", "COMPLETED"):
                return {"status": "SUCCEEDED", "task": data}
            if st in ("FAILED", "CANCELED", "CANCELLED", "ERROR"):
                return {"status": "FAILED", "task": data, "reason": st}
        time.sleep(poll_s)
    return {"status": "TIMEOUT", "task": last, "reason": f"timeout after {timeout_s}s"}


def _download(url: str, dest: Path, timeout: float = 120.0) -> bool:
    try:
        req = urllib.request.Request(url, headers=_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception:
        return False


def mesh_retexture(
    game_slug: str,
    input_glb: str | Path,
    *,
    style_prompt: str = "weathered stone",
    preserve_uv: bool = True,
    seed: int = 0,
    poll_s: float = 5.0,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    """Create Meshy retexture task, poll to SUCCEEDED, land maps under Generated/."""
    out = generated_root(game_slug) / "retexture" / f"retex_{seed}"
    out.mkdir(parents=True, exist_ok=True)
    params = {
        "style_prompt": style_prompt,
        "preserve_uv": preserve_uv,
        "input": str(input_glb),
    }

    bal = check_balance()
    if not bal.get("ok"):
        write_manifest(
            out,
            seed=seed,
            kind="meshy_retexture",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": bal.get("reason")},
        )
        return {
            "status": "unavailable",
            "reason": bal.get("reason"),
            "fallback": "procedural",
            "out_dir": str(out),
        }

    input_path = Path(input_glb)
    if not input_path.is_file():
        write_manifest(
            out,
            seed=seed,
            kind="meshy_retexture",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": f"input glb missing: {input_glb}"},
        )
        return {
            "status": "unavailable",
            "reason": f"input glb missing: {input_glb}",
            "fallback": "procedural",
            "out_dir": str(out),
        }

    # Meshy retexture OpenAPI (v1): model_url or local upload depending on account.
    # Prefer public URL field; for local files send data URI / model_url path per API.
    body = {
        "input_task_id": None,
        "model_url": None,
        "text_style_prompt": style_prompt,
        "enable_original_uv": bool(preserve_uv),
        "ai_model": "meshy-5",
    }
    # Local file: Meshy accepts model upload endpoints; try multipart-free path via
    # openapi/v1/retexture with model_url as file:// is rejected — upload first.
    upload_status, upload_data = _http_json(
        "POST",
        f"{MESHY_BASE}/openapi/v1/uploads",
        {"filename": input_path.name},
        timeout=60.0,
    )
    # Fallback: try retexture with raw base64 model payload (some tiers)
    if not (upload_status and 200 <= upload_status < 300):
        import base64

        b64 = base64.b64encode(input_path.read_bytes()).decode("ascii")
        body["model_file"] = {
            "type": "glb",
            "data": b64[:100],  # probe — full payload may exceed limits
        }
        # Prefer not to send huge base64; use retexture create with model path field
        body.pop("model_file", None)
        body["model_url"] = f"file://{input_path}"  # may 400; then unavailable

    if isinstance(upload_data, dict) and upload_data.get("url"):
        body["model_url"] = upload_data["url"]
        # if put_url provided, PUT the file
        put_url = upload_data.get("put_url") or upload_data.get("upload_url")
        if put_url:
            try:
                put_req = urllib.request.Request(
                    put_url,
                    data=input_path.read_bytes(),
                    method="PUT",
                    headers={"Content-Type": "model/gltf-binary"},
                )
                urllib.request.urlopen(put_req, timeout=120.0).read()
            except Exception as exc:
                write_manifest(
                    out,
                    seed=seed,
                    kind="meshy_retexture",
                    params=params,
                    files=[],
                    extra={"status": "unavailable", "reason": f"upload put failed: {exc!r}"},
                )
                return {
                    "status": "unavailable",
                    "reason": f"upload put failed: {exc!r}",
                    "fallback": "procedural",
                    "out_dir": str(out),
                }

    create_status, create_data = _http_json(
        "POST", f"{MESHY_BASE}/openapi/v1/retexture", body, timeout=60.0
    )
    # try v2 path if v1 fails
    if not (create_status and 200 <= create_status < 300):
        create_status, create_data = _http_json(
            "POST",
            f"{MESHY_BASE}/openapi/v2/retexture",
            {
                "model_url": body.get("model_url"),
                "text_style_prompt": style_prompt,
                "enable_original_uv": preserve_uv,
            },
            timeout=60.0,
        )

    if not (create_status and 200 <= create_status < 300):
        reason = f"retexture create HTTP {create_status}: {create_data}"
        write_manifest(
            out,
            seed=seed,
            kind="meshy_retexture",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": reason, "fallback": "procedural"},
        )
        return {
            "status": "unavailable",
            "reason": reason,
            "fallback": "procedural",
            "out_dir": str(out),
            "create_response": create_data,
        }

    task_id = None
    if isinstance(create_data, dict):
        task_id = create_data.get("result") or create_data.get("id") or create_data.get("task_id")
    if not task_id:
        reason = f"no task id in create response: {create_data}"
        write_manifest(
            out,
            seed=seed,
            kind="meshy_retexture",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": reason},
        )
        return {
            "status": "unavailable",
            "reason": reason,
            "fallback": "procedural",
            "out_dir": str(out),
        }

    poll = _poll_task(
        [
            f"{MESHY_BASE}/openapi/v1/retexture/{task_id}",
            f"{MESHY_BASE}/openapi/v2/retexture/{task_id}",
        ],
        poll_s=poll_s,
        timeout_s=timeout_s,
    )
    files: list[str] = []
    if poll["status"] == "SUCCEEDED":
        task = poll.get("task") or {}
        # download texture URLs if present
        tex = task.get("texture_urls") or task.get("textures") or []
        if isinstance(tex, dict):
            tex = list(tex.values())
        for i, u in enumerate(tex):
            if isinstance(u, dict):
                u = u.get("base_color") or u.get("url") or u.get("base_color_url")
            if not isinstance(u, str):
                continue
            dest = out / f"meshy_tex_{i}.png"
            if _download(u, dest):
                files.append(dest.name)
        model_urls = task.get("model_urls") or {}
        if isinstance(model_urls, dict):
            for key in ("glb", "fbx", "obj"):
                u = model_urls.get(key)
                if u:
                    dest = out / f"meshy_model.{key}"
                    if _download(u, dest):
                        files.append(dest.name)

    write_manifest(
        out,
        seed=seed,
        kind="meshy_retexture",
        params={**params, "task_id": task_id},
        files=files + ["manifest.json"],
        extra={"status": poll["status"], "task": poll.get("task")},
    )
    return {
        "status": poll["status"],
        "task_id": task_id,
        "out_dir": str(out),
        "files": files,
        "fallback": "procedural" if poll["status"] != "SUCCEEDED" else None,
        "reason": poll.get("reason"),
    }


def mesh_text_to_3d(
    game_slug: str,
    prompt: str,
    *,
    seed: int = 0,
    poll_s: float = 5.0,
    timeout_s: float = 600.0,
    mode: str = "preview",
) -> dict[str, Any]:
    """Create Meshy text-to-3d task, poll, download GLB into Generated/."""
    out = generated_root(game_slug) / "meshes" / f"meshy_t23d_{seed}"
    out.mkdir(parents=True, exist_ok=True)
    params = {"prompt": prompt, "mode": mode}

    bal = check_balance()
    if not bal.get("ok"):
        write_manifest(
            out,
            seed=seed,
            kind="meshy_text_to_3d",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": bal.get("reason")},
        )
        return {
            "status": "unavailable",
            "reason": bal.get("reason"),
            "fallback": "procedural",
            "out_dir": str(out),
        }

    body = {
        "mode": mode,
        "prompt": prompt,
        "art_style": "realistic",
        "should_remesh": True,
        "seed": int(seed) if seed else None,
    }
    # strip None
    body = {k: v for k, v in body.items() if v is not None}

    create_status, create_data = _http_json(
        "POST", f"{MESHY_BASE}/openapi/v2/text-to-3d", body, timeout=60.0
    )
    if not (create_status and 200 <= create_status < 300):
        create_status, create_data = _http_json(
            "POST", f"{MESHY_BASE}/openapi/v1/text-to-3d", body, timeout=60.0
        )

    if not (create_status and 200 <= create_status < 300):
        reason = f"text-to-3d create HTTP {create_status}: {create_data}"
        write_manifest(
            out,
            seed=seed,
            kind="meshy_text_to_3d",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": reason, "fallback": "procedural"},
        )
        return {
            "status": "unavailable",
            "reason": reason,
            "fallback": "procedural",
            "out_dir": str(out),
            "create_response": create_data,
        }

    task_id = None
    if isinstance(create_data, dict):
        task_id = create_data.get("result") or create_data.get("id") or create_data.get("task_id")
    if not task_id:
        reason = f"no task id: {create_data}"
        write_manifest(
            out,
            seed=seed,
            kind="meshy_text_to_3d",
            params=params,
            files=[],
            extra={"status": "unavailable", "reason": reason},
        )
        return {
            "status": "unavailable",
            "reason": reason,
            "fallback": "procedural",
            "out_dir": str(out),
        }

    poll = _poll_task(
        [
            f"{MESHY_BASE}/openapi/v2/text-to-3d/{task_id}",
            f"{MESHY_BASE}/openapi/v1/text-to-3d/{task_id}",
        ],
        poll_s=poll_s,
        timeout_s=timeout_s,
    )
    files: list[str] = []
    if poll["status"] == "SUCCEEDED":
        task = poll.get("task") or {}
        model_urls = task.get("model_urls") or {}
        if isinstance(model_urls, dict):
            for key in ("glb", "fbx"):
                u = model_urls.get(key)
                if u:
                    dest = out / f"meshy_t23d.{key}"
                    if _download(u, dest):
                        files.append(dest.name)

    write_manifest(
        out,
        seed=seed,
        kind="meshy_text_to_3d",
        params={**params, "task_id": task_id},
        files=files + ["manifest.json"],
        extra={"status": poll["status"], "task": poll.get("task")},
    )
    return {
        "status": poll["status"],
        "task_id": task_id,
        "out_dir": str(out),
        "files": files,
        "fallback": "procedural" if poll["status"] != "SUCCEEDED" else None,
        "reason": poll.get("reason"),
    }
