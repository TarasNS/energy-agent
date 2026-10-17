# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Curated by Dev 3. Keep it short and true: only stable rules, real commands and architecture the repo actually implements. Propose changes via PR.

## Project
Energy 4.0 Harness: an energy-native AI decision layer. Hackathon POC = one workflow, **Monthly Curtailment Review**, run by a small agent loop in `harness/`: the model picks from five tools (read data → deterministic EUR from `energy-calc` → explanation → action proposal), a human approves outside the loop, everything is audited. Built live in a short hackathon session.

**Scope: first proof of concept (POC), built in one short session.** **Current state: pre-implementation.** Structure, contracts, docs and a starter synthetic fixture (`data/synthetic/`, 15-minute, not frozen) exist. No product code exists yet. Update this line when that changes.

## Read before working
`intent.md` (why) → `SPEC.md` (what) → `ARCHITECTURE.md` (how) → `PLAN.md` (when) → `TASKS.md` (tasks) → `TEAM.md` (who) → your file in `prompts/`.
If documents conflict: stop, report the conflict, do not resolve it yourself.

## Non-negotiable rules
1. **EUR and MWh values come only from `mcp/energy-calc`.** Never compute, estimate, round or restate a financial number yourself. Quote calc output exactly.
2. Money crosses boundaries as decimal strings (`"85.00"`), never floats.
3. Data tools (`energy-data`, `portfolio`) are read-only.
4. Actions go through `actions.propose_action` → `actions.approve_action(token)`. Approval is enforced in code, never only in a prompt. Approval functions are never added to the agent's tool registry.
5. Every tool call, proposal and approval is appended to the audit log.
6. Synthetic data is the default. The demo must run offline.
7. Never put credentials in source, prompts, fixtures or logs. Use `.env` (git-ignored).
8. No production SCADA/ERP writes. No physical control actions.
9. Call models only through `model_gateway.get_client()`. Never import `anthropic` (or any provider SDK) outside `model/model_gateway/` — `make check` fails if you do.

## Ownership
Edit only paths your workstream owns (`TEAM.md`). Shared contracts in `schemas/` change only with coordination; after freeze, with lead approval.

| Path | Owner |
|---|---|
| `.claude/skills/`, `.claude/hooks/`, `mcp/energy-data/` | Dev 1 |
| `.claude/agents/`, `mcp/actions/`, `harness/`, `scripts/demo-smoke.sh` | Dev 2 |
| `CLAUDE.md`, `Makefile`, `scripts/setup.sh`, `scripts/verify.sh`, `scripts/verify.py`, `model/`, `mcp/portfolio/`, `schemas/`, `docs/`, `.github/` | Dev 3 |
| `mcp/energy-calc/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md` | Dev 4 |
| `apps/web/`, `presentation/`, `DEMO.md` | Dev 5 |

## Commands
| Command | Status |
|---|---|
| `make setup` | Works: checks tools, creates `.venv`, installs `requirements.txt` + `requirements-dev.txt`, checks the API key |
| `make check` | Works: structure, JSON schemas, doc links, secret scan, model-agnostic import guard |
| `make test` | Runs pytest; reports "no tests yet" until Dev 4 adds them |
| `make eval` | After the POC (EnergyBench-Lite) |
| `make run` | Starts the demo page once `apps/web/run.sh` exists (Dev 5) |
| `make docs` | Rebuilds `docs/` from `scripts/build_docs.py` (edit the script, not the HTML) |
| `make demo-smoke` | Reports missing stages; Dev 2 makes the end-to-end checks real |
| `make verify` | `check` + `test` + `demo-smoke` with a summary; a NOT IMPLEMENTED step counts as FAIL (by design) |

Single test: `.venv/bin/python -m pytest mcp/energy-calc/tests/test_x.py::test_name` (Makefile and scripts are bash; on Windows use Git Bash/WSL).

## Architecture (big picture)
Request flow: `apps/web` (UI + small local FastAPI) → `harness/` (data → calc → explain → propose → approve → audit) → skill `.claude/skills/curtailment-advisor/` + model via `model_gateway` → tools `mcp/{energy-data,portfolio,energy-calc,actions}` → synthetic data in `data/synthetic/`. Models explain; they are never the calculator of record or the permission system. Contracts live in `schemas/*.schema.json` (validated by `make check`); model profiles (`default`, `fast`, `offline`) in `model/profiles.json`. Full detail: `ARCHITECTURE.md` §2–§6.

Note: `energy-agent/` at the repo root is a nested copy of the project tree; work in the top-level files unless told otherwise.

## Code conventions
- Python 3.11+. Pure functions in `mcp/<tool>/<tool_pkg>/`, tests in `mcp/<tool>/tests/`.
- Do not create `mcp/__init__.py` (shadows the `mcp` SDK).
- Import paths are set in `pytest.ini`.
- Prefer the simplest thing that passes the acceptance criteria. No new frameworks, services or agents without a concrete repeated need.

## Working loop (one task = one branch = one PR)
1. Before editing, report: goal, owned files, dependencies, acceptance criteria, file-level plan. Wait for go-ahead.
2. Work only on the current task branch (`devN/<task>`). Write the test first.
3. Run the task's test; if red, fix the code (never weaken the test) and run again until green. Show the output.
4. Use the `verifier` subagent. It reports; it does not fix.
5. Stop when `make check` and `make test` pass. The human opens the PR; do not start the next task until it is merged.
6. Done = evidence (command + output), not a claim.

## Docs
Team-facing docs (`docs/`, READMEs, PR text) follow `.claude/brand-voice-guidelines.md`: numbered steps, one action each, link every file, no background on working pages.

## Subagents
`researcher` (read-only investigation), `verifier` (runs checks, reports deviations), `simplifier` (proposes deletions). Do not add others without a repeated job.
