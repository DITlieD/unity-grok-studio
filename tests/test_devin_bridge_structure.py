"""Assert portable Devin bridge layout and hygiene."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "tools" / "devin-bridge"


def test_run_sh_exists():
    assert (BRIDGE / "run.sh").is_file()


def test_proxy_files_exist():
    for rel in [
        "proxy/devin_proxy.py",
        "proxy/devin_wire.py",
        "proxy/replay_pb2.py",
        "proxy/account_catalog.py",
        "proxy/claudedevin-system.md",
        "proxy/data/template.bin",
        "cli-config/model_configs_v3.bin",
        "cli-config/team_settings.bin",
        "requirements.txt",
        "README.md",
    ]:
        assert (BRIDGE / rel).exists(), rel


def test_run_sh_no_teikoku_path():
    text = (BRIDGE / "run.sh").read_text(encoding="utf-8", errors="ignore")
    assert "teikoku" not in text.lower()
    assert "/home/lied/teikoku" not in text
    assert "$HOME/teikoku" not in text


def test_run_sh_credentials_discovery_comments():
    text = (BRIDGE / "run.sh").read_text(encoding="utf-8", errors="ignore")
    # Linux / macOS / Windows-WSL discovery documented in script
    assert "credentials.toml" in text
    assert ".local/share/devin" in text or "DEVIN_CREDS" in text
    assert "Application Support" in text or "macOS" in text
    assert "AppData" in text or "WSL" in text or "/mnt/c" in text
    assert "DEVIN_TOOL_DESC" in text
    assert "8810" in text


def test_wire_no_teikoku_branding():
    wire = (BRIDGE / "proxy" / "devin_wire.py").read_text(encoding="utf-8", errors="ignore")
    assert "TEIKOKU" not in wire
    assert "teikoku" not in wire.lower()


def test_docs_devin_bridge_present():
    assert (ROOT / "docs" / "DEVIN-BRIDGE.md").is_file()
