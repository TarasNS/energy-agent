# Prompt 2 — Dev 2: agent loop, approval and audit

**Owner:** Dev 2 · **Use:** run `claude` from the repo root, then say "Read prompts/02-dev2-orchestration-feedback.md and follow it."

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

You own: mcp/actions/, harness/, scripts/demo-smoke.sh, .claude/agents/

Tasks, in order:
1. Actions (mcp/actions/README.md): propose_action, issue_approval_token,
   approve_action, JSON-lines audit. Write the refusal tests first: missing,
   wrong, reused and other-proposal tokens are refused and execute nothing.
Start from the team's POC harness (branch claude/awesome-planck-bt3ymf, folder
harness/poc/src/energy_harness/). Copy and adapt; do not rewrite from scratch.
Mapping: TASKS.md, "What we reuse from the POC".

2. Tool registry (T2.1): copy the POC tools.py to harness/tools/registry.py;
   add harness/config.py; register stubs for exactly the five tools. Test:
   exactly five tools, no calculate and no approval tool, unknown tool and bad
   arguments return an error result.
3. Agent loop (T2.2, harness/README.md): copy the POC agent.py and
   tests/conftest.py; turn Agent.run() into run_review() plus a CLI. Same loop
   and forced final answer, model_gateway.get_client().run_turn() instead of
   the OpenRouter client, until final text or STEP_BUDGET. Test with a scripted fake client:
   stops on text, stops at the budget, fails if calc was never called, copies
   result numbers from the last calc output. Output validates against
   schemas/review-result.schema.json.
4. Trace and audit (T2.4): copy the POC trace.py to harness/trace.py; every
   tool call also appends an audit line; large outputs are saved in full to
   artifacts/ and the model gets the truncated result with the path.
5. Wire the real tools as they merge, then make scripts/demo-smoke.sh real
   (T2.5, the checks listed at its top), with MODEL_PROFILE=offline.

Rules:
- one agent loop, not a multi-agent runtime; the model gets exactly the five registered tools;
- numbers shown to the user come from the calc result, never from model text;
- never import anthropic or any provider SDK in harness/; do not copy the POC
  llm.py, budget.py, probe.py, builtin_tools.py, energy/ or web/.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
