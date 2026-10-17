# harness/ — Monthly Curtailment Review agent loop

**Owner:** Dev 2 · **Status:** not implemented · **Flow:** [ARCHITECTURE.md §3](../ARCHITECTURE.md#3-request-flow-monthly-curtailment-review) · **Tasks:** [TASKS.md](../TASKS.md)

A trimmed copy of the template [coderonfleek/harness-course-build](https://github.com/coderonfleek/harness-course-build). The model picks tools from a fixed registry; the harness enforces the controls.

```text
harness/
├── agent.py              run_review(): ReAct loop, step budget, calc-of-record check
├── config.py             STEP_BUDGET, MODEL_PROFILE
├── prompts/system.txt    short system prompt; skill appended at load
├── tools/registry.py     the five tools: JSON schema + dispatch over mcp/* pure functions
├── context/offloader.py  large outputs → artifacts/, summary to the model
└── tests/
```

## Rules
1. The registry holds exactly five tools: `list_assets`, `get_production`, `get_day_ahead_prices`, `calculate_curtailment_value`, `propose_action`. No approval tool.
2. A review with no `calculate_curtailment_value` call fails. Result numbers are copied from the last calc output, never from model text.
3. Stop after `STEP_BUDGET` rounds with a presenter-readable failure.
4. Every dispatched tool call is appended to `AUDIT_LOG_PATH`.
5. Call the model only through `model_gateway.get_client().run_turn(...)` ([model/README.md](../model/README.md)). Never import a provider SDK here.

## Entry point
One function and a CLI that `scripts/demo-smoke.sh` and the UI both use:
```bash
python -m harness.agent --portfolio demo-solar-dk --zone DK1 --month 2026-06 --json
```
Output must validate against `schemas/review-result.schema.json`.
