# Prompt 4 — Dev 4: calculator and golden tests

**Owner:** Dev 4 · **Use:** run `claude` from the repo root, then say "Read prompts/04-dev4-evals-calc.md and follow it."

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

You own: mcp/energy-calc/, data/synthetic/, evals/, EVALS.md

Before the session you already worked out G-01 to G-03 and G-07 by hand
(EVALS.md §3). The LLM must never be the source of a golden EUR value.

Tasks, in order:
1. Golden tests: turn my hand-worked cases (I will paste them) into pytest tests
   in mcp/energy-calc/tests/. Do not change any expected value.
2. Calculator (mcp/energy-calc/README.md, formula v1 in EVALS.md §2):
   calculate_curtailment_value, Decimal throughout, results by cause and by
   asset, decimal strings out, assumptions, input_hash, calculation_version.
   Work test-first until every golden case passes with exact equality.

Rules:
- pure functions: no I/O, clock, network or model calls;
- read interval_minutes from each row;
- the eval runner (evals/run.py) is after the POC — do not build it.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
