"""Drive real scripts/wire-unity-project.sh default vs --with-pipeline."""
import json
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'wire-unity-project.sh'


def test_wire_default_does_not_add_pipeline():
    with tempfile.TemporaryDirectory() as td:
        proj = pathlib.Path(td)
        (proj / 'Packages').mkdir()
        r = subprocess.run(
            ['bash', str(SCRIPT), str(proj)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert r.returncode == 0, (r.stdout, r.stderr)
        data = json.loads((proj / 'Packages' / 'manifest.json').read_text())
        deps = data['dependencies']
        assert 'com.unitygrok.uitools' in deps
        assert 'com.unity.pipeline' not in deps
        assert 'com.unity.pipeline' not in (r.stdout + r.stderr)


def test_wire_with_pipeline_adds_pipeline_opt_in():
    with tempfile.TemporaryDirectory() as td:
        proj = pathlib.Path(td)
        (proj / 'Packages').mkdir()
        r = subprocess.run(
            ['bash', str(SCRIPT), str(proj), '--with-pipeline'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert r.returncode == 0, (r.stdout, r.stderr)
        data = json.loads((proj / 'Packages' / 'manifest.json').read_text())
        deps = data['dependencies']
        assert 'com.unitygrok.uitools' in deps
        assert 'com.unity.pipeline' in deps
        assert 'pipeline' in (r.stdout + r.stderr).lower()


def test_wire_help():
    r = subprocess.run(
        ['bash', str(SCRIPT), '--help'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert r.returncode == 0
    assert '--with-pipeline' in r.stdout
