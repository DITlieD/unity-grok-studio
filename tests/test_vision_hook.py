import json, os, pathlib, subprocess, textwrap
ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT/'plugin'/'hooks'/'bin'/'vision-predescribe.sh'
def test_hook_noop_without_images():
    env = os.environ.copy()
    env['UNITY_GROK_ROOT'] = str(ROOT)
    env['GROK_PLUGIN_ROOT'] = str(ROOT/'plugin')
    payload = json.dumps({'prompt': 'hello', 'model': 'free-coder', 'attachments': []})
    r = subprocess.run(['bash', str(HOOK)], input=payload, text=True, capture_output=True, env=env, timeout=30)
    assert r.returncode == 0
    # empty or no additionalContext is fine
def test_hook_with_missing_image_path_noopish():
    env = os.environ.copy()
    env['UNITY_GROK_ROOT'] = str(ROOT)
    env['GROK_PLUGIN_ROOT'] = str(ROOT/'plugin')
    payload = json.dumps({'prompt': 'see /no/such/file.png', 'model': 'free-coder'})
    r = subprocess.run(['bash', str(HOOK)], input=payload, text=True, capture_output=True, env=env, timeout=30)
    assert r.returncode == 0
