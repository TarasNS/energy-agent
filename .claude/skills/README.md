# .claude/skills/

**Owner:** Dev 1

POC contains **one** skill: `curtailment-advisor/SKILL.md`. Build it well before considering a second one (stretch order in PLAN.md §7).

## `curtailment-advisor` — required contract (from SPEC.md §2.6)

The skill must:
1. **State when it applies** — monthly curtailment / economic-impact review for a portfolio, zone and month.
2. **Name the tools** it uses, in order: `portfolio` (assets, production) → `energy-data` (prices) → `energy-calc` (value) → `actions.propose_action` (only if the user asks for an action).
3. **Quote calc output exactly** — EUR and MWh values copied from the calc result, never recomputed, rounded differently or estimated.
4. **Show assumptions** — the `assumptions` list from the calc result, plus `calculation_version`.
5. **Prohibit invented values** — if a number is not in the calc result or the inputs, it must not appear.
6. **Use proposal mode** for any action — never claim an action was executed without an approval result.

Suggested layout:
```text
curtailment-advisor/
├── SKILL.md            frontmatter (name, description) + instructions
└── examples/           one good explanation per golden case (used by the no-invented-number eval)
```

Keep `SKILL.md` under ~150 lines. Put long reference material in separate files the skill links to.
