import json, os, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
def test_doctor_json():
    r = subprocess.run(['bash', str(ROOT/'scripts'/'doctor.sh'), '--json'], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout.strip().splitlines()[-1] if r.stdout.strip().startswith('{') else r.stdout)
    # tolerate multi-line; try full stdout
    if 'components' not in data:
        data = json.loads(r.stdout)
    assert 'components' in data
    assert 'python' in data['components'] or any('python' in k for k in data['components'])
