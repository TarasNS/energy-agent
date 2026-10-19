#!/usr/bin/env bash
# Owner: Dev 2. End-to-end smoke test for the three-minute demo.
#
# CURRENT STATE: placeholder. It reports which pipeline stages exist and
# FAILS, because the real smoke test has not been written yet.
#
# Dev 2 replaces run_smoke() with the real path (scripted model, no network, synthetic data):
#   1. ask the three demo questions from DEMO.md through the chat server
#   2. assert each answer is verified and the numbers equal the golden cases
#   3. assert the trace has no approval tool and a chart came back
#   4. propose an action -> proposal_id, audit "proposed"
#   5. approve WITHOUT a valid token -> refused, audit "approval_denied"
#   6. approve with the server-issued token -> audit "approved"; a second approval is refused
set -uo pipefail
cd "$(dirname "$0")/.."

missing=0
stage() { # name, path, owner
  if [ -e "$2" ]; then printf '  present  %-28s %s\n' "$1" "$2"
  else printf '  MISSING  %-28s %s  (owner: %s)\n' "$1" "$2" "$3"; missing=1; fi
}

echo "Demo pipeline stages"
stage "synthetic fixture"        data/synthetic/demo-solar-dk           "Dev 4"
stage "KPI calculator"           mcp/kpi-solar/kpi_solar                "Dev 4"
stage "model gateway"            model/model_gateway                    "Dev 3"
stage "kpi-advisor skill"        .claude/skills/kpi-advisor/SKILL.md    "Dev 1"
stage "agent loop"               harness/agent.py                       "Dev 2"
stage "tool registry"            harness/registry.py                    "Dev 2"
stage "energy tools"             harness/energy_tools.py                "Dev 2"
stage "actions tool"             mcp/actions/actions                    "Dev 2"
stage "golden cases"             evals/cases/golden.json                "Dev 4"
stage "offline model turns"      model/recorded/demo-1.json             "Dev 3"
stage "chat page + server"       tools/kpi-lab/server.py                "Dev 1"

run_smoke() {
  echo
  echo "NOT IMPLEMENTED: the end-to-end assertions in scripts/demo-smoke.sh (owner: Dev 2)."
  return 1
}

if [ "$missing" -ne 0 ]; then
  echo
  echo "Smoke test cannot run: pipeline stages are missing (see above)."
  exit 1
fi
run_smoke
