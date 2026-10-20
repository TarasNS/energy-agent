"""Tests for scripts/dev.py, the make-free command runner (owner: Dev 3)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_venv_python_path_per_os():
    assert dev.venv_python(ROOT, windows=True) == ROOT / ".venv" / "Scripts" / "python.exe"
    assert dev.venv_python(ROOT, windows=False) == ROOT / ".venv" / "bin" / "python"


def test_python_falls_back_when_no_venv(tmp_path):
    assert dev.python_for(tmp_path) == sys.executable


def test_all_commands_known():
    assert set(dev.COMMANDS) == {"setup", "check", "test", "run", "docs", "verify", "demo-smoke"}


def test_unknown_command_fails():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dev.py"), "nope"], capture_output=True, text=True)
    assert r.returncode == 2 and "Usage" in r.stdout + r.stderr


def test_check_runs_without_make():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "dev.py"), "check"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "passed" in r.stdout


def test_dev_requirements_include_runtime():
    assert "-r requirements.txt" in (ROOT / "requirements-dev.txt").read_text()
