# harness/: the agent loop

**Owner:** Dev 2 · **Status:** working · **Flow:** [ARCHITECTURE.md §2](../ARCHITECTURE.md#2-one-question) · **Tasks:** [Dev 2 page](../docs/developer-2.html)

The model picks tools from a fixed registry. The harness enforces the controls.

```text
harness/
├── agent.py         run(): ask model → run tools → repeat; check_numbers; 8 rounds max
├── registry.py      @tool decorator, argument validation, never-raising execute
├── energy_tools.py  the nine tools over the synthetic portfolio
├── dataset.py       seeded synthetic portfolio (2 parks, 1 battery, June 2026)
└── tests/           scripted-model tests, no network
```

## Rules
1. The registry holds exactly nine tools: `list_assets`, `list_kpis`, `get_kpi`, `compare_kpi`, `get_series`, `get_prices`, `get_events`, `make_chart`, `propose_action`. No approval tool.
2. Every KPI value comes from `mcp/kpi-solar`. The model never calculates.
3. A number in the answer that is not in the question or a tool result withholds the text.
4. Stop after `MAX_STEPS` (8) rounds and after the daily model cap, each with a clear note.
5. Call the model only through `model_gateway.run_turn` ([model/README.md](../model/README.md)). Never import a provider SDK here.
6. Not yet: every tool call in the audit log, and the skill file as the system prompt (Dev 2's tasks).
