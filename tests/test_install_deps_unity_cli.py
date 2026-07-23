"""Drive real scripts/install-deps.sh flags for Unity CLI (no Editor install)."""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'install-deps.sh'


def test_install_deps_help_mentions_unity_cli():
    r = subprocess.run(
        ['bash', str(SCRIPT), '--help'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout + r.stderr
    assert '--with-unity-cli' in out
    assert 'Editor' in out or 'multi-GB' in out or 'UNITY-CLI' in out


def test_install_deps_with_unity_cli_prints_guidance_without_assume_yes():
    """--with-unity-cli alone must print install guidance and not require network Editor install."""
    # Source-level: never auto editor install
    src = SCRIPT.read_text(encoding='utf-8')
    assert '--with-unity-cli' in src
    # No path that runs editor install as a default action
    assert not re.search(r'unity\s+install\s+\$\{?|unity\s+install\s+lts|unity\s+install\s+6000', src)
    # Flag path mentions print-only / assume-yes gate
    assert 'ASSUME_YES' in src and 'WITH_UNITY_CLI' in src

    # Runtime: run only the unity-cli branch by grepping script structure is not enough —
    # invoke with --with-unity-cli but intercept so bootstrap/doctor noise is ok.
    # We only assert the CLI guidance appears and no unity install <version> is spawned.
    r = subprocess.run(
        ['bash', str(SCRIPT), '--with-unity-cli'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    # install-deps ends with doctor || true; may be 0
    combined = (r.stdout or '') + (r.stderr or '')
    assert 'Unity CLI' in combined or 'unity-cli' in combined.lower() or 'UNITY_CLI_CHANNEL' in combined
    assert 'public-cdn.cloud.unity3d.com' in combined or 'install.sh' in combined
    # Must not claim it ran multi-GB editor install
    assert 'unity install lts' not in combined.lower()
    assert 'unity install 6000' not in combined


def test_install_deps_source_never_auto_editor_install():
    src = SCRIPT.read_text(encoding='utf-8')
    # Allowed to mention the forbidden pattern as a warning string
    forbidden_run = re.findall(r'^\s*unity\s+install\b', src, flags=re.M)
    assert forbidden_run == [], f'script must not execute unity install: {forbidden_run}'
