# harness/ — Monthly Curtailment Review agent loop

**Owner:** Dev 2 · **Status:** not implemented · **Flow:** [ARCHITECTURE.md §3](../ARCHITECTURE.md#3-request-flow-monthly-curtailment-review) · **Tasks:** [TASKS.md](../TASKS.md)

Built from the team's working POC harness: branch [`claude/awesome-planck-bt3ymf`](https://github.com/TarasNS/energy-agent/tree/claude/awesome-planck-bt3ymf/harness/poc), folder `harness/poc/src/energy_harness/`. The model picks tools from a fixed registry; the harness enforces the controls.

## Start from these POC files

1. Copy `agent.py` → `harness/agent.py` (T2.2).
2. Copy `tools.py` → `harness/tools/registry.py` (T2.1).
3. Copy `trace.py` → `harness/trace.py` (T2.4).
4. Copy `tests/conftest.py` → `harness/tests/conftest.py` for the `ScriptedLLM` fake model.

```bash
git fetch origin claude/awesome-planck-bt3ymf
git show origin/claude/awesome-planck-bt3ymf:harness/poc/src/energy_harness/agent.py > harness/agent.py
```

Then adapt them as in [TASKS.md](../TASKS.md#what-we-reuse-from-the-poc). Do not copy `llm.py`, `budget.py`, `probe.py`, `builtin_tools.py`, `energy/` or `web/`.

```text
harness/
├── agent.py              run_review(): POC loop + step budget + calc-of-record check
├── config.py             STEP_BUDGET, MODEL_PROFILE
├── prompts/system.txt    short system prompt; skill appended at load
├── tools/registry.py     POC tools.py: @tool + validation; exactly five tools
├── trace.py              POC trace.py: JSONL events; tool calls also to the audit log
└── tests/
```

## Rules
1. The registry holds exactly five tools: `list_assets`, `get_production`, `get_day_ahead_prices`, `calculate_curtailment_value`, `propose_action`. No approval tool, and no POC `calculate` tool.
2. A review with no `calculate_curtailment_value` call fails. Result numbers are copied from the last calc output, never from model text.
3. Stop after `STEP_BUDGET` rounds with one forced "answer now" call, as in the POC; if calc was still not called, fail with a presenter-readable message.
4. Every dispatched tool call is appended to `AUDIT_LOG_PATH`. Large outputs are truncated for the model and saved in full to `artifacts/`.
5. Call the model only through `model_gateway.get_client().run_turn(...)` ([model/README.md](../model/README.md)). Never import a provider SDK here; the POC's OpenRouter client is not used.

## Entry point
One function and a CLI that `scripts/demo-smoke.sh` and the UI both use:
```bash
python -m harness.agent --portfolio demo-solar-dk --zone DK1 --month 2026-06 --json
```
Output must validate against `schemas/review-result.schema.json`.
