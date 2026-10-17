# Prompt 5 — Dev 5: demo screen, local API and story

**Owner:** Dev 5 · **Use:** run `claude` from the repo root, then say "Read prompts/05-dev5-ui-presentation.md and follow it."

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

You own: apps/web/, presentation/, DEMO.md

Tasks, in order:
1. Screen + local API (apps/web/README.md): a FastAPI server with the three
   endpoints and one HTML page, returning apps/web/recorded.json for now.
   Test the endpoints with FastAPI's TestClient. Add apps/web/run.sh so
   `make run` starts it.
2. Connect: when Dev 2 says the workflow is ready, call harness/agent.py and
   mcp/actions from the endpoints. The approve endpoint is the only caller of
   issue_approval_token and approve_action.
3. Demo assets: put the G-07 numbers in DEMO.md; add one screenshot per demo
   step to presentation/ as the fallback.

Rules:
- an energy workflow screen, not a chat window;
- render every number from the calculation fields, never from model text;
- Lovable polish is after the POC.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
