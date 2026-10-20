#!/usr/bin/env bash
# Owner: Dev 3. Full local verification with a one-screen summary.
# Used by `make verify`, by developers before a PR, and after each merge into main.
# A step that reports NOT IMPLEMENTED counts as a failure, on purpose.
set -uo pipefail
cd "$(dirname "$0")/.."

declare -a names results
run() {
  local name=$1; shift
  echo "━━ $name ━━"
  if "$@"; then results+=("PASS"); else results+=("FAIL"); fi
  names+=("$name"); echo
}

run "check"      make --no-print-directory check
run "test"       make --no-print-directory test
run "demo-smoke" make --no-print-directory demo-smoke

echo "━━ summary ━━"
rc=0
for i in "${!names[@]}"; do
  printf '  %-10s %s\n' "${names[$i]}" "${results[$i]}"
  [ "${results[$i]}" = PASS ] || rc=1
done
exit $rc
