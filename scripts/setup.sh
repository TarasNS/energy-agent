#!/usr/bin/env bash
# Owner: Dev 3. Prepares a local dev environment. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

ok()   { printf '  ok    %s\n' "$1"; }
fail() { printf '  MISSING %s\n' "$1"; missing=1; }
missing=0

echo "Checking tools"
command -v git >/dev/null && ok "git" || fail "git"
command -v make >/dev/null && ok "make" || fail "make"
if command -v python3 >/dev/null && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'; then
  ok "python3 $(python3 -c 'import platform; print(platform.python_version())')"
else
  fail "python3 >= 3.11"
fi
command -v claude >/dev/null && ok "claude (Claude Code)" || echo "  note  claude CLI not found — install Claude Code before Phase 3"
command -v node >/dev/null && ok "node (optional)" || echo "  note  node not found — only needed if Dev 5 picks a JS stack"

[ "$missing" -eq 0 ] || { echo "Install the missing tools and re-run make setup."; exit 1; }

echo "Python environment"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt -r requirements-dev.txt
ok ".venv with requirements.txt and requirements-dev.txt"

echo "Local config"
if [ -f .env ]; then ok ".env exists (not overwritten)"; else cp .env.example .env; ok ".env created from .env.example"; fi
if grep -qE '^ANTHROPIC_API_KEY=.+' .env; then ok "ANTHROPIC_API_KEY is set in .env"; else echo "  note  ANTHROPIC_API_KEY is empty in .env — ask the lead; the offline profile still works"; fi
mkdir -p artifacts

echo
echo "Setup complete. Next: make check, then open docs/index.html"
