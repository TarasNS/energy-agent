# .claude/skills/

**Owner:** Dev 1 · **Task:** [Dev 1 page](../../docs/developer-1.html)

The POC has **one** skill: `kpi-advisor/SKILL.md`. It is the model's instruction file. Today the same text is a string in `harness/agent.py`; Dev 2 makes the agent read the file when it exists.

## The skill must
1. **Say the data is synthetic** and every answer must say so.
2. **Name the nine tools** and when to use each: `list_assets`, `list_kpis`, `get_kpi`, `compare_kpi`, `get_series`, `get_prices`, `get_events`, `make_chart`, `propose_action`.
3. **Forbid model arithmetic.** Never calculate, add, average, round or estimate a number. Quote tool values exactly.
4. **Handle "unavailable".** Say so and give the tool's reason. Do not estimate.
5. **Limit charts and length.** One chart at most. At most 120 words.
6. **Use proposal mode.** Propose only when the data clearly justifies it. Never say an action is approved or done.

Layout:
```text
kpi-advisor/
├── SKILL.md         frontmatter (name, description) + instructions, under 150 lines
└── test_skill.py    fails if a tool name or the never-calculate rule is missing
```
