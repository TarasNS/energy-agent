# TASKS.md — Energy harness build, split by person

**Status:** draft → lead approval required
**Role in the chain:** the task list for the agent-loop harness in [SPEC.md §2.8](SPEC.md) and [ARCHITECTURE.md §3](ARCHITECTURE.md#3-request-flow-monthly-curtailment-review). Order and phases stay in [PLAN.md](PLAN.md). Owners and paths come from [TEAM.md](TEAM.md).

Template: [coderonfleek/harness-course-build](https://github.com/coderonfleek/harness-course-build). We keep its shape (`agent.py`, `config.py`, `tools/registry.py`, `prompts/`, `context/offloader.py`) and drop the sandbox, shell/git/web tools, compaction, RAG, memory, Ralph and subagents.

## How the template maps to this repo

| Template piece | Energy harness | Task |
|---|---|---|
| `harness/agent.py` (ReAct loop, step budget) | `harness/agent.py` `run_review()` | T2.2 |
| `harness/config.py` | `harness/config.py` | T2.1 |
| `harness/tools/registry.py` | Registry of the five energy tools | T2.1 |
| `harness/tools/*.py` (bash, git, web) | `mcp/energy-data`, `mcp/portfolio`, `mcp/energy-calc`, `mcp/actions` | T1.1, T3.1, T4.2, T2.3 |
| `harness/prompts/system.txt` | Short system prompt + `curtailment-advisor` skill | T1.2 |
| `harness/context/offloader.py` | Offload 15-minute rows to `artifacts/` | T2.4 |
| OpenAI client in `agent.py` | `model_gateway.run_turn()` (Anthropic + offline) | T3.2, T3.3 |
| `knowledge/` + RAG | Not in the POC | — |

## Tasks

Each task is one branch (`devN/<task>`) and one PR into `dev`. Write the test first.

| ID | Owner | Task | Depends on | Done when |
|---|---|---|---|---|
| T1.1 | Dev 1 | `get_day_ahead_prices(zone, month)` reads the fixture | — | Prices for DK1 2026-06 load offline; rows validate against `market-price.schema.json` |
| T1.2 | Dev 1 | `curtailment-advisor` skill + `harness/prompts/system.txt` | T2.1 schemas | Skill names the five tools, says calc is mandatory, forbids invented numbers, uses proposal mode |
| T2.1 | Dev 2 | `harness/config.py` + `tools/registry.py` with stubs for the five tools | — | Test: exactly five tools; `approve_action` and `issue_approval_token` absent; unknown tool name returns an error result |
| T2.2 | Dev 2 | `harness/agent.py` `run_review()` loop | T2.1, T3.2 | Test with a scripted fake client: stops on final text; stops at `STEP_BUDGET`; fails when calc was never called; result numbers equal the last calc output |
| T2.3 | Dev 2 | `actions`: propose, issue token, approve, audit | — | Bad or reused token refused; proposal and approval written to `AUDIT_LOG_PATH` |
| T2.4 | Dev 2 | `context/offloader.py` + tool-call audit lines in `dispatch` | T2.1 | Outputs over the limit go to `artifacts/`; model sees a summary; each call audited |
| T2.5 | Dev 2 | Make `scripts/demo-smoke.sh` real against `harness/` | T2.2, T4.2 | `make demo-smoke` passes with `MODEL_PROFILE=offline` |
| T3.1 | Dev 3 | `list_assets`, `get_production` in `mcp/portfolio` | — | Demo portfolio loads; bad rows rejected |
| T3.2 | Dev 3 | Gateway `run_turn(messages, tools) → ModelTurn` (Anthropic tool use); update `model/README.md` | — | Only `model/model_gateway/` imports `anthropic`; `make check` green |
| T3.3 | Dev 3 | `offline` profile replays recorded turns from `model/recorded/` | T3.2, T2.2 | Same loop, no network, same EUR as `default` |
| T3.4 | Dev 3 | Rename `workflow/` → `harness/` in `pytest.ini`, `Makefile`, `scripts/`, `docs/` generator, `CLAUDE.md`, `TEAM.md` paths | Lead approval | `make check` and `make docs` green; no `workflow/` references left |
| T4.1 | Dev 4 | Golden cases G-01 to G-03, G-07 as files | — | Values worked by hand, frozen |
| T4.2 | Dev 4 | `calculate_curtailment_value(...)` | T4.1 | Golden cases pass exactly in `make test` |
| T4.3 | Dev 4 | Eval: agent trace never states a EUR value not in the calc output | T2.2, T3.3 | Runs on the offline trace in `make test` |
| T5.1 | Dev 5 | Screen + local API on a recorded result | — | Full story renders from `recorded.json` |
| T5.2 | Dev 5 | Show the tool trace (which tools the model chose, in order) on the result card | T2.2 | Trace visible; numbers rendered from calc fields only |
| T5.3 | Dev 5 | Connect `POST /api/review` to `harness.agent.run_review` | T2.2 | `make run` shows a live review; approve works |

## Critical path

```text
T4.1 → T4.2 ┐
T3.2 → T2.2 ┼→ T3.3 → T2.5 → T5.3 → rehearsal
T2.1 ───────┘
```

Start T1.1, T2.1, T2.3, T3.1, T3.2, T4.1 and T5.1 at once. They need only the frozen schemas and stubs.
