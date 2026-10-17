#!/usr/bin/env bash
# Owner: Dev 2. End-to-end smoke test for the three-minute demo.
#
# CURRENT STATE: placeholder. It reports which pipeline stages exist and
# FAILS, because the real smoke test has not been written yet.
#
# Dev 2 replaces run_smoke() with the real path (MODEL_PROFILE=offline, synthetic data):
#   1. run review: demo-solar-dk / DK1 / 2026-06
#   2. assert calculation.economic_value_eur == golden G-07 (exact string)
#   3. propose enable_negative_price_curtailment for dk1-solar-03 -> proposal_id, audit "proposed"
#   4. approve WITHOUT a valid token -> refused, nothing executed, audit "approval_denied"
#   5. approve WITH a token from issue_approval_token -> audit "approved" and "executed_simulated"
set -uo pipefail
cd "$(dirname "$0")/.."

missing=0
stage() { # name, path, owner
  if [ -e "$2" ]; then printf '  present  %-28s %s\n' "$1" "$2"
  else printf '  MISSING  %-28s %s  (owner: %s)\n' "$1" "$2" "$3"; missing=1; fi
}

echo "Demo pipeline stages"
stage "synthetic fixture"        data/synthetic/demo-solar-dk           "Dev 4"
stage "portfolio tool"           mcp/portfolio/portfolio                "Dev 3"
stage "energy-data tool"         mcp/energy-data/energy_data            "Dev 1"
stage "energy-calc"              mcp/energy-calc/energy_calc            "Dev 4"
stage "model gateway"            model/model_gateway                    "Dev 3"
stage "curtailment-advisor skill" .claude/skills/curtailment-advisor/SKILL.md "Dev 1"
stage "workflow entry point"     harness/agent.py                     "Dev 2"
stage "actions tool"             mcp/actions/actions                    "Dev 2"
stage "offline model reply"      model/recorded/G-07.json               "Dev 3"
stage "demo page + API"          apps/web/run.sh                        "Dev 5"

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
