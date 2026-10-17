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
2. Tool registry (T2.1): harness/config.py and harness/tools/registry.py with
   stubs for the five tools. Test: exactly five tools, no approval tool, an
   unknown tool name returns an error result.
3. Agent loop (T2.2, harness/README.md): harness/agent.py run_review() plus a
   CLI. Loop model_gateway.get_client().run_turn() → dispatch tool calls →
   repeat, until final text or STEP_BUDGET. Test with a scripted fake client:
   stops on text, stops at the budget, fails if calc was never called, copies
   result numbers from the last calc output. Output validates against
   schemas/review-result.schema.json.
4. Offloader and audit (T2.4): large tool outputs go to artifacts/ with a
   summary to the model; every dispatch appends an audit line.
5. Wire the real tools as they merge, then make scripts/demo-smoke.sh real
   (T2.5, the checks listed at its top), with MODEL_PROFILE=offline.

Rules:
- one agent loop, not a multi-agent runtime; the model gets exactly the five registered tools;
- numbers shown to the user come from the calc result, never from model text;
- never import anthropic or any provider SDK in harness/.

Work one task at a time, each on its own branch (devN/<task>, from dev).
For every task: write the test first, run it, and keep fixing the code until
it passes; never weaken a test to make it pass. Show me the test output, run
the verifier subagent, then stop so I can open the pull request. Do not start
the next task until I tell you the PR is merged.
```
