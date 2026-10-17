# Prompt 1 — Dev 1: price data and AI skill

**Owner:** Dev 1 · **Use:** run `claude` from the repo root, then say "Read prompts/01-dev1-prices-skill.md and follow it."

```text
Read intent.md, SPEC.md, ARCHITECTURE.md, PLAN.md, TEAM.md and CLAUDE.md.

This is a first proof of concept (POC), built in one short hackathon session.
Build only the tasks below. Anything else is after the POC.

Before changing any file, report:
1. Goal (one sentence)
2. Owned files (from TEAM.md)
3. Dependencies and whether each is ready
4. Acceptance criteria (the 'Done when' list on my page in docs/)
5. Proposed file-level plan
Then stop and wait for my go-ahead.

If the documents conflict, identify the conflict and stop.

You own: mcp/energy-data/, .claude/skills/

Tasks, in order:
1. Price reader: get_day_ahead_prices(zone, month) in mcp/energy-data, reading
   data/synthetic/demo-solar-dk/prices-DK1-2026-06.jsonl (contract in its README).
   Read interval_minutes from each row; never assume 60. No network, no writes.
2. curtailment-advisor skill: .claude/skills/curtailment-advisor/SKILL.md per
   .claude/skills/README.md. Dev 2 uses it as the system prompt. It must tell the
   model to quote calc output exactly, show assumptions, never invent numbers, and
   recommend actions only as proposals. Add a test that checks the six points.

Rules:
- all EUR values come from mcp/energy-calc; the skill never computes or re-rounds;
- hooks are after the POC — do not build them.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
