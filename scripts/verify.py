#!/usr/bin/env python3
"""Repository health check behind `make check` (owner: Dev 1).

Checks: required files, JSON schemas, local links in Markdown and HTML,
developer page sections, secret patterns, and mcp/ package shadowing.
Standard library only, so it runs before `make setup`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
errors: list[str] = []

REQUIRED = """README.md INTENT.md TEAM.md ARCHITECTURE.md
SPEC.md EVALS.md DEMO.md CLAUDE.md Makefile .env.example .gitignore requirements-dev.txt pytest.ini
index.html docs/index.html docs/lead.html .claude/brand-voice-guidelines.md
docs/developer-4.html docs/developer-3.html docs/developer-1.html docs/developer-2.html docs/presentation.html
docs/css/style.css docs/js/app.js scripts/build_docs.py model/README.md requirements.txt
.claude/agents/researcher.md .claude/agents/verifier.md .claude/agents/simplifier.md
.github/PULL_REQUEST_TEMPLATE.md
scripts/setup.sh scripts/verify.sh""".split()

DEV_SECTIONS = ["setup", "loop", "tasks", "done"]

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
]
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
TEXT_EXT = {".md", ".py", ".sh", ".json", ".jsonl", ".yml", ".yaml", ".html", ".css",
            ".js", ".ts", ".tsx", ".txt", ".ini", ".toml", ".env", ""}


def files(pattern: str):
    for p in ROOT.rglob(pattern):
        if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            yield p


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def check_required():
    for f in REQUIRED:
        if not (ROOT / f).exists():
            errors.append(f"missing required file: {f}")


SCHEMA_FILES = ["chat-result", "chart", "proposal", "audit-line"]


def check_schemas():
    try:
        import jsonschema  # installed by make setup; a missing package is a failure, not a skip
    except ImportError:
        errors.append("jsonschema is not installed: run python scripts/dev.py setup")
        return
    for name in SCHEMA_FILES:
        if not (ROOT / "schemas" / f"{name}.schema.json").exists():
            errors.append(f"missing contract schema: schemas/{name}.schema.json")
    for p in sorted((ROOT / "schemas").glob("*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{rel(p)}: invalid JSON ({e})")
            continue
        if jsonschema:
            try:
                jsonschema.Draft202012Validator.check_schema(data)
            except jsonschema.SchemaError as e:
                errors.append(f"{rel(p)}: invalid JSON Schema ({e.message})")


LINK_MD = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
LINK_HTML = re.compile(r"""(?:href|src)=["']([^"']+)["']""")


def check_links():
    # docs/reference/*.md are raw copies of the root documents; their links are meant for the root.
    md = [p for p in files("*.md") if "reference" not in p.relative_to(ROOT).parts[:2]]
    targets = [(p, LINK_MD) for p in md] + [(p, LINK_HTML) for p in files("*.html")]
    for p, rx in targets:
        text = p.read_text(encoding="utf-8")
        # ignore links inside fenced code blocks in Markdown
        if p.suffix == ".md":
            text = re.sub(r"```.*?```", "", text, flags=re.S)
        for link in rx.findall(text):
            u = urlparse(link)
            if u.scheme or link.startswith(("#", "mailto:")):
                continue
            path = unquote(u.path)
            if not path:
                continue
            target = (p.parent / path).resolve()
            if not target.exists():
                errors.append(f"{rel(p)}: broken link -> {link}")


def check_dev_pages():
    for n in range(1, 5):
        p = ROOT / f"docs/developer-{n}.html"
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        for sec in DEV_SECTIONS:
            if f'id="{sec}"' not in html:
                errors.append(f"{rel(p)}: missing section id=\"{sec}\"")


def check_secrets():
    me = Path(__file__).resolve()
    for p in files("*"):
        if not p.is_file() or p.resolve() == me or p.suffix not in TEXT_EXT:
            continue
        if p.name == ".env":  # local, git-ignored
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for rx in SECRET_PATTERNS:
            if rx.search(text):
                errors.append(f"{rel(p)}: looks like a credential ({rx.pattern[:20]}…)")


SDK_IMPORT = re.compile(r"^\s*(import|from)\s+(anthropic|openai)\b", re.M)


def check_model_agnostic():
    """Only model/model_gateway/ may import a provider SDK (ARCHITECTURE.md §5)."""
    allowed = ROOT / "model" / "model_gateway"
    for p in files("*.py"):
        if allowed in p.resolve().parents or p.resolve() == Path(__file__).resolve():
            continue
        if SDK_IMPORT.search(p.read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"{rel(p)}: imports a model SDK directly; use model_gateway.run_turn()")


def check_misc():
    if (ROOT / "mcp/__init__.py").exists():
        errors.append("mcp/__init__.py exists: it shadows the official `mcp` SDK (see ARCHITECTURE.md §5)")
    try:
        tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
        if tracked:
            errors.append(".env is tracked by git: remove it and rotate any keys inside")
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    checks = [("required files", check_required), ("JSON schemas", check_schemas),
              ("local links", check_links), ("developer pages", check_dev_pages),
              ("secret scan", check_secrets), ("model-agnostic", check_model_agnostic), ("misc", check_misc)]
    for name, fn in checks:
        before = len(errors)
        fn()
        print(f"  {'ok  ' if len(errors) == before else 'FAIL'}  {name}")
    if errors:
        print("\nProblems:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nmake check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
