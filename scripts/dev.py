#!/usr/bin/env python3
"""Owner: Dev 1. The project commands without make: python scripts/dev.py <command>.

Works on Windows, macOS and Linux with only Python 3.11+. The Makefile calls this file,
so `make <command>` and `python scripts/dev.py <command>` do the same thing.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def venv_python(root: Path = ROOT, windows: bool | None = None) -> Path:
    win = (os.name == "nt") if windows is None else windows
    return root / ".venv" / ("Scripts" if win else "bin") / ("python.exe" if win else "python")


def python_for(root: Path = ROOT) -> str:
    p = venv_python(root)
    return str(p) if p.exists() else sys.executable


def run(*args: str) -> int:
    return subprocess.call([python_for(), *args], cwd=ROOT)


def setup() -> int:
    print("Checking tools")
    missing = False
    print("  ok    git" if shutil.which("git") else "  MISSING git")
    missing |= not shutil.which("git")
    if sys.version_info >= (3, 11):
        print(f"  ok    python {platform.python_version()}")
    else:
        print("  MISSING python >= 3.11")
        missing = True
    print("  ok    claude (Claude Code)" if shutil.which("claude") else "  note  claude CLI not found; install Claude Code before building")
    print("  ok    node (optional)" if shutil.which("node") else "  note  node not found; only needed for the chart test")
    if missing:
        print("Install the missing tools and run setup again.")
        return 1
    print("Python environment")
    if not venv_python().exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(ROOT / ".venv")], cwd=ROOT)
    py = str(venv_python())
    subprocess.check_call([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], cwd=ROOT)
    subprocess.check_call([py, "-m", "pip", "install", "--quiet", "-r", "requirements.txt", "-r", "requirements-dev.txt"], cwd=ROOT)
    print("  ok    .venv with requirements.txt and requirements-dev.txt")
    print("Local config")
    env = ROOT / ".env"
    if env.exists():
        print("  ok    .env exists (not overwritten)")
    else:
        shutil.copy(ROOT / ".env.example", env)
        print("  ok    .env created from .env.example")
    if any(l.startswith("ANTHROPIC_API_KEY=") and len(l.strip()) > len("ANTHROPIC_API_KEY=") for l in env.read_text().splitlines()):
        print("  ok    ANTHROPIC_API_KEY is set in .env")
    else:
        print("  note  ANTHROPIC_API_KEY is empty in .env; ask the lead. The offline profile still works")
    (ROOT / "artifacts").mkdir(exist_ok=True)
    print("\nSetup complete. Next: python scripts/dev.py check, then open docs/index.html")
    return 0


def check() -> int:
    return run("scripts/verify.py")


def test() -> int:
    rc = run("-m", "pytest")
    if rc == 5:
        print("\nNOT IMPLEMENTED: no tests collected.")
        print("  Needed: tests under mcp/*/tests/, harness/, evals/ or tests/ (owner: Dev 2, plus each component owner).")
        return 1
    if rc != 0 and subprocess.call([python_for(), "-c", "import pytest"], cwd=ROOT, stderr=subprocess.DEVNULL) != 0:
        print("pytest not available. Run: python scripts/dev.py setup")
    return rc


def run_server() -> int:
    return run("tools/kpi-lab/server.py")


def docs() -> int:
    return run("scripts/build_docs.py")


def demo_smoke() -> int:
    if not (ROOT / "scripts" / "demo-smoke.sh").exists():
        print("NOT IMPLEMENTED: scripts/demo-smoke.sh does not exist yet (Dev 3).")
        return 1
    bash = shutil.which("bash")
    if not bash:
        print("demo-smoke needs bash (Git Bash or WSL on Windows).")
        return 1
    return subprocess.call([bash, "scripts/demo-smoke.sh"], cwd=ROOT)


def verify() -> int:
    steps = [("check", check), ("test", test), ("demo-smoke", demo_smoke)]
    results = []
    for name, fn in steps:
        print(f"== {name} ==")
        results.append((name, fn() == 0))
        print()
    print("== summary ==")
    for name, ok in results:
        print(f"  {name:<10} {'PASS' if ok else 'FAIL'}")
    return 0 if all(ok for _, ok in results) else 1


COMMANDS = {"setup": setup, "check": check, "test": test, "run": run_server, "docs": docs, "verify": verify, "demo-smoke": demo_smoke}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in COMMANDS:
        print("Usage: python scripts/dev.py <" + "|".join(COMMANDS) + ">")
        return 2
    return COMMANDS[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
