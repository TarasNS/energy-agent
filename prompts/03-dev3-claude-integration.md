# Prompt 3 — Dev 3: portfolio, model gateway and integration

**Owner:** Dev 3 · **Use:** run `claude` from the repo root, then say "Read prompts/03-dev3-claude-integration.md and follow it."

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

You own: mcp/portfolio/, model/, schemas/, CLAUDE.md, Makefile, scripts/
(except demo-smoke.sh), .github/, docs/ (rebuilt by scripts/build_docs.py)

Tasks, in order:
1. Portfolio reader (mcp/portfolio/README.md): list_assets, get_production over
   data/synthetic/demo-solar-dk; validate rows; reject malformed ones clearly.
2. Model gateway (T3.2, model/README.md): get_client() with
   run_turn(system, messages, tools) -> ModelTurn, an Anthropic SDK client with
   tool use, and a recorded offline client that replays turns; profiles in
   model/profiles.json. Only
   model/model_gateway/ may import anthropic (make check enforces it). Mock the
   SDK in tests.
3. Offline replay (T3.3): once Dev 2's agent loop runs, run the demo review
   with MODEL_PROFILE=default, save the model turns as
   model/recorded/G-07.json, and check every number in the final text appears
   in the calc result.
4. Result schema (T3.5, with Dev 2): add an optional tool_trace array to
   schemas/review-result.schema.json (name, order, ok) for the screen.

Also, after each merge into dev: git pull && make verify, and post the result.
CLAUDE.md changes only when a command or rule actually changes.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
