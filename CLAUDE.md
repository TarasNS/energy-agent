# CLAUDE.md

This file guides Claude Code (claude.ai/code) in this repository.

Curated by Dev 3. Keep it short and true: only stable rules, real commands and architecture the repo actually implements. Propose changes via PR.

## Project
Energy 4.0 Harness: a chat assistant for a solar and battery portfolio. A small agent loop in `harness/` lets the model pick from nine read-only tools; code (`mcp/kpi-solar`) makes every number; the server checks each number in the answer; a person approves any action outside the loop; everything is audited. Synthetic data only.

**Scope: first proof of concept (POC).** **Current state:** KPI formulas, nine tools, agent loop with number check, propose/approve/audit, chat page and model gateway work. Not built yet: offline model replay, skill file, audit of tool calls, golden cases. Update this line when that changes.

## Read before working
`INTENT.md` (why, scope, done) → `ARCHITECTURE.md` (how) → `TEAM.md` (who) → your page in `docs/` (your tasks and prompts).
If documents conflict: stop, report the conflict, do not resolve it yourself.

## Non-negotiable rules
1. **Numbers come only from `mcp/kpi-solar`.** Never compute, estimate, round or restate a number yourself. Quote tool output exactly.
2. Money and energy cross boundaries as decimal strings (`"85.00"`), never floats.
3. Data tools are read-only.
4. Actions go through `propose_action` → server `/api/approve` → `approve_action(token)`. Approval is enforced in code, never only in a prompt. Approval functions are never in the agent's tool registry.
5. Every proposal, approval and refusal is appended to the audit log. Tool calls join them (Dev 2's task).
6. Synthetic data is the default. The demo must run offline.
7. Never put credentials in source, prompts, fixtures or logs. Use `.env` (git-ignored).
8. No production SCADA or ERP writes. No physical control actions.
9. Call models only through `model/model_gateway` (`run_turn`). Never import `anthropic` (or any provider SDK) outside `model/model_gateway/`; `make check` fails if you do.

## Ownership
Edit only paths your workstream owns ([TEAM.md](TEAM.md)). Shared contracts in `schemas/` change only with coordination.

| Path | Owner |
|---|---|
| `.claude/skills/`, `.claude/hooks/`, `mcp/energy-data/`, `tools/kpi-lab/` (page, charts, config) | Dev 1 |
| `harness/`, `mcp/actions/`, `tools/kpi-lab/server.py`, `scripts/demo-smoke.sh`, `.claude/agents/` | Dev 2 |
| `CLAUDE.md`, `Makefile`, `scripts/` (except demo-smoke), `model/`, `schemas/`, `docs/`, `.github/` | Dev 3 |
| `mcp/kpi-solar/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md`, `KPI_REVIEW.md`, `config/` | Dev 4 |
| `INTENT.md`, `ARCHITECTURE.md`, `TEAM.md`, `README.md`, `DEMO.md`, `scripts/slides.py` | Lead |

## Commands
| Command | Status |
|---|---|
| `make setup` | Works: checks tools, creates `.venv`, installs requirements, checks the API key |
| `make check` | Works: structure, JSON schemas, doc links, secret scan, model-agnostic import guard |
| `make test` | Runs pytest |
| `make run` | Starts the chat page and server (`tools/kpi-lab/server.py`) on http://127.0.0.1:8000 |
| `make docs` | Rebuilds `docs/` from `scripts/build_docs.py` (edit the script, not the HTML) |
| `make demo-smoke` | Fails until Dev 2 makes it real |
| `make verify` | `check` + `test` + `demo-smoke` with a summary; a NOT IMPLEMENTED step counts as FAIL (by design) |

No `make` (common on Windows)? Every row works as `python scripts/dev.py <command>` (setup, check, test, run, docs, verify, demo-smoke); `make` calls the same file.

Single test: `python -m pytest path/to/test_x.py::test_name`. `demo-smoke` needs bash (Git Bash or WSL on Windows).

## Architecture (big picture)
`tools/kpi-lab` (chat page + local server) → `harness/agent.py` (loop, number check) → model via `model/model_gateway` and tools in `harness/energy_tools.py` → `mcp/kpi-solar` (numbers), `mcp/actions` (propose, approve, audit), `harness/dataset.py` (synthetic portfolio). Models explain; they are never the calculator of record or the permission system. Full detail: [ARCHITECTURE.md](ARCHITECTURE.md).

## Code conventions
- Python 3.11+. Pure functions in `mcp/<tool>/<pkg>/`, tests in `mcp/<tool>/tests/`.
- Do not create `mcp/__init__.py` (shadows the `mcp` SDK).
- Import paths are set in `pytest.ini`.
- Prefer the simplest thing that passes the acceptance criteria. No new frameworks, services or agents without a concrete repeated need.

## Working loop (one task = one branch = one PR)
1. Before editing, report: goal, owned files, dependencies, acceptance criteria, file-level plan. Wait for the developer's "go".
2. Work on the task branch `devN/<task>` created from `main`. Write the test first.
3. Run the task's test. If red, fix the code (never weaken the test) and run again until green. Show the output.
4. Use the `verifier` subagent. It reports; it does not fix. Fix every P0 and P1 it reports.
5. Run `make check` and `make test`. When both pass, commit, push and open the pull request into `main` only when the developer asks.
6. Done = evidence (command + output), not a claim.

## Docs
Team-facing docs (`docs/`, READMEs, PR text) follow `.claude/brand-voice-guidelines.md`: one action per step, prompts instead of commands, link every file.

## Subagents
`researcher` (read-only investigation), `verifier` (runs checks, reports deviations), `simplifier` (proposes deletions). Do not add others without a repeated job.
