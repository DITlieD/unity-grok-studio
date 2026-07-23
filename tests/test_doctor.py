"""Drive real scripts/doctor.sh --json (no reimplementation of component logic)."""
import json
import os
import pathlib
import stat
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run_doctor(env=None, timeout=60):
    r = subprocess.run(
        ['bash', str(ROOT / 'scripts' / 'doctor.sh'), '--json'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    # doctor prints a single JSON object
    text = r.stdout.strip()
    data = json.loads(text)
    return data, r


def test_doctor_json():
    data, _ = _run_doctor()
    assert 'components' in data
    assert 'python' in data['components']


def test_doctor_has_unity_cli_component_and_missing_cli_does_not_fail_overall():
    """unity_cli is present; missing CLI must not flip top-level ok when python is healthy."""
    data, _ = _run_doctor()
    comps = data['components']
    assert 'unity_cli' in comps, sorted(comps)
    assert comps['unity_cli']['status'] in ('ok', 'warn', 'missing')
    # Overall ok is python-gated only (same as lia/blender optional pattern)
    if comps.get('python', {}).get('status') == 'ok':
        assert data['ok'] is True
    # If CLI not installed, status is missing or warn — still overall ok
    if comps['unity_cli']['status'] in ('missing', 'warn'):
        assert data['ok'] is True
        fix = comps['unity_cli'].get('fix') or ''
        assert 'UNITY_CLI' in fix or 'unity-cli' in fix or 'install' in fix.lower()


def test_doctor_unity_cli_ok_with_path_shim():
    """PATH shim that succeeds on unity --version → unity_cli ok (drives real doctor.sh)."""
    with tempfile.TemporaryDirectory() as td:
        shim_dir = pathlib.Path(td)
        shim = shim_dir / 'unity'
        shim.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "${1:-}" == "--version" ]]; then echo "Unity CLI 1.0.0-test-shim"; exit 0; fi\n'
            'echo "shim help"; exit 0\n',
            encoding='utf-8',
        )
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        env = os.environ.copy()
        env['PATH'] = f'{shim_dir}{os.pathsep}{env.get("PATH", "")}'
        data, _ = _run_doctor(env=env)
        uc = data['components']['unity_cli']
        assert uc['status'] == 'ok', uc
        assert 'shim' in (uc.get('detail') or '').lower() or '1.0.0' in (uc.get('detail') or '')
        assert data['ok'] is True


def test_doctor_optional_components_do_not_gate_ok():
    data, _ = _run_doctor()
    # Contract: top-level ok follows python only
    assert data['ok'] == (data['components']['python']['status'] == 'ok')
    for name in ('lia', 'blender', 'unity_cli', 'unity_editor'):
        assert name in data['components'], name
