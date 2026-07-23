import json, os, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugin" / "hooks" / "bin" / "vision-predescribe.sh"
FIXTURE = ROOT / "fixtures" / "ref.png"


def test_hook_noop_without_images():
    env = os.environ.copy()
    env["UNITY_GROK_ROOT"] = str(ROOT)
    env["GROK_PLUGIN_ROOT"] = str(ROOT / "plugin")
    payload = json.dumps({"prompt": "hello", "model": "free-coder", "attachments": []})
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert r.returncode == 0
    # empty or no additionalContext is fine


def test_hook_with_missing_image_path_noopish():
    env = os.environ.copy()
    env["UNITY_GROK_ROOT"] = str(ROOT)
    env["GROK_PLUGIN_ROOT"] = str(ROOT / "plugin")
    payload = json.dumps({"prompt": "see /no/such/file.png", "model": "free-coder"})
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert r.returncode == 0


def test_hook_force_predescribe_with_fixture():
    """UGS_FORCE_PREDESCRIBE=1 + real image → JSON with [vision-predescribe] block.

    FreeLLMAPI may be down: graceful error inside the block is still success.
    If up: description may be non-empty beyond the tags.
    """
    assert FIXTURE.is_file(), "fixtures/ref.png required"
    env = os.environ.copy()
    env["UNITY_GROK_ROOT"] = str(ROOT)
    env["GROK_PLUGIN_ROOT"] = str(ROOT / "plugin")
    env["UGS_FORCE_PREDESCRIBE"] = "1"
    env.setdefault("FREELLM_BASE_URL", "http://127.0.0.1:3001/v1")
    env.setdefault("FREELLM_API_KEY", "freellmapi-local")
    payload = json.dumps(
        {
            "prompt": f"look at {FIXTURE}",
            "model": "free-coder",
            "attachments": [str(FIXTURE)],
        }
    )
    r = subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    out = (r.stdout or "").strip()
    assert out, "expected JSON additionalContext on stdout"
    data = json.loads(out)
    ctx = data.get("additionalContext") or ""
    assert "[vision-predescribe]" in ctx
    assert "[/vision-predescribe]" in ctx
    # Either real description or graceful error string
    assert str(FIXTURE) in ctx or FIXTURE.name in ctx or "vision-describe" in ctx or "error" in ctx.lower()
