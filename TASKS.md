# TASKS.md — Energy harness build, split by person

**Status:** draft → lead approval required
**Role in the chain:** the task list for the agent-loop harness in [SPEC.md §2.8](SPEC.md) and [ARCHITECTURE.md §3](ARCHITECTURE.md#3-request-flow-monthly-curtailment-review). Order and phases stay in [PLAN.md](PLAN.md). Owners and paths come from [TEAM.md](TEAM.md).

**Code base:** the team's working POC harness on branch [`claude/awesome-planck-bt3ymf`](https://github.com/TarasNS/energy-agent/tree/claude/awesome-planck-bt3ymf/harness/poc) (commit `165bbfd`, with an offline test suite). Do not delete that branch. The course template [coderonfleek/harness-course-build](https://github.com/coderonfleek/harness-course-build) is background reading only.

T2.1 and T2.2 start by copying three POC files, then adapting them. Everything else in the POC (OpenRouter fallback chain, request budget, probe, live weather and price APIs, PV estimate, simulator, chat web UI) stays out.

## What we reuse from the POC

| POC file | Becomes | Keep | Change | Task |
|---|---|---|---|---|
| [`agent.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/src/energy_harness/agent.py) | `harness/agent.py` | The loop, `max_steps` + one forced "answer now" call, `_normalize_assistant` (repairs missing ids, object arguments) | `max_steps` → `STEP_BUDGET`; call `model_gateway` instead of the OpenRouter client; add the calc-of-record check; return a review result, not a chat answer | T2.2 |
| [`tools.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/src/energy_harness/tools.py) | `harness/tools/registry.py` | `@tool` decorator, pydantic validation, never-raising `execute`, unknown-tool error, result truncation | A fixed list of exactly five tools; no `calculate` tool; full output of large results saved to `artifacts/` | T2.1, T2.4 |
| [`trace.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/src/energy_harness/trace.py) | `harness/trace.py` | One JSONL line per event | Also append every `tool_call` to `AUDIT_LOG_PATH` | T2.4 |
| [`tests/conftest.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/tests/conftest.py) | `harness/tests/conftest.py` | `ScriptedLLM`, `tool_call()`, `answer()` | Return our `ModelTurn` shape | T2.2 |
| [`llm.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/src/energy_harness/llm.py) `ChatClient` protocol | `model/model_gateway/` | The idea: one `chat`-style method the loop depends on | Anthropic SDK + recorded offline client behind `run_turn` | T3.2, T3.3 |
| [`evals.py`](https://github.com/TarasNS/energy-agent/blob/165bbfd/harness/poc/src/energy_harness/evals.py) number checks | Dev 4's eval | Checking numbers in the answer against tool output | Exact decimal match against the calc output | T4.3 |

## Safety pieces the POC does not have

The POC answers questions; it never proposes or approves anything, and the model may do arithmetic. These are added on top, each with a test:

| Missing in the POC | Added by | Task |
|---|---|---|
| Deterministic EUR in `Decimal`, split by cause | `calculate_curtailment_value` in `mcp/energy-calc` | T4.2 |
| No model arithmetic: the POC's `calculate` tool is removed | Registry test: exactly five tools, no `calculate` | T2.1 |
| Calc of record: review fails if the calculator was not called; result numbers copied from its output | `run_review()` | T2.2 |
| Proposal, one-time approval token, simulated execution | `mcp/actions`; approval functions never in the registry | T2.1, T2.3 |
| Append-only audit of tool calls, proposal and approval | `trace.py` + `mcp/actions` → `AUDIT_LOG_PATH` | T2.3, T2.4 |
| Offline demo without any provider (POC simulation still needs OpenRouter) | Recorded model turns replayed through the same loop | T3.3 |
| Structured result with `tool_trace` | `review-result.schema.json` | T2.2, T3.5 |
| Synthetic fixtures instead of live APIs; no company data to free model providers | `mcp/energy-data`, `mcp/portfolio`; Anthropic via the gateway | T1.1, T3.1, T3.2 |

## Tasks

Each task is one branch (`devN/<task>`) and one PR into `dev`. Write the test first.

| ID | Owner | Task | Depends on | Done when |
|---|---|---|---|---|
| T1.1 | Dev 1 | `get_day_ahead_prices(zone, month)` reads the fixture | — | Prices for DK1 2026-06 load offline; rows validate against `market-price.schema.json` |
| T1.2 | Dev 1 | `curtailment-advisor` skill + `harness/prompts/system.txt` | T2.1 schemas | Skill names the five tools, says calc is mandatory, forbids invented numbers, uses proposal mode |
| T2.1 | Dev 2 | Copy POC `tools.py` → `harness/tools/registry.py`; add `harness/config.py`; register stubs for the five tools | — | Test: exactly five tools; no `calculate`, `approve_action` or `issue_approval_token`; unknown tool and bad arguments return an error result |
| T2.2 | Dev 2 | Copy POC `agent.py` and `tests/conftest.py`; turn `Agent.run()` into `run_review()` over `model_gateway` | T2.1, T3.2 | Test with a scripted fake client: stops on final text; stops at `STEP_BUDGET`; fails when calc was never called; result numbers equal the last calc output |
| T2.3 | Dev 2 | `actions`: propose, issue token, approve, audit | — | Bad or reused token refused; proposal and approval written to `AUDIT_LOG_PATH` |
| T2.4 | Dev 2 | Copy POC `trace.py` → `harness/trace.py`; audit every tool call; save full large outputs to `artifacts/` | T2.1 | Each call is one line in `AUDIT_LOG_PATH`; the model sees a truncated result with the file path |
| T2.5 | Dev 2 | Make `scripts/demo-smoke.sh` real against `harness/` | T2.2, T4.2 | `make demo-smoke` passes with `MODEL_PROFILE=offline` |
| T3.1 | Dev 3 | `list_assets`, `get_production` in `mcp/portfolio` | — | Demo portfolio loads; bad rows rejected |
| T3.2 | Dev 3 | Gateway `run_turn(messages, tools) → ModelTurn` (Anthropic tool use); update `model/README.md` | — | Only `model/model_gateway/` imports `anthropic`; `make check` green |
| T3.3 | Dev 3 | `offline` profile replays recorded turns from `model/recorded/` | T3.2, T2.2 | Same loop, no network, same EUR as `default` |
| T3.4 | Dev 3 | Rename `workflow/` → `harness/` everywhere | — | Done in PR 1 |
| T3.5 | Dev 3 + Dev 2 | Add optional `tool_trace` (name, order, ok) to `review-result.schema.json` | Before schema freeze | Schema validates; T5.2 can render it |
| T4.1 | Dev 4 | Golden cases G-01 to G-03, G-07 as files | — | Values worked by hand, frozen |
| T4.2 | Dev 4 | `calculate_curtailment_value(...)` | T4.1 | Golden cases pass exactly in `make test` |
| T4.3 | Dev 4 | Eval: agent trace never states a EUR value not in the calc output | T2.2, T3.3 | Runs on the offline trace in `make test` |
| T5.1 | Dev 5 | Lovable screen + local API and fallback page on a recorded result | — | Full story renders from `recorded.json` in Lovable and on the local page |
| T5.2 | Dev 5 | Show the tool trace (which tools the model chose, in order) on the result card | T2.2, T3.5 | Trace visible; numbers rendered from calc fields only |
| T5.3 | Dev 5 | Connect `POST /api/review` to `harness.agent.run_review` | T2.2 | `make run` shows a live review; approve works |

## Critical path

```text
T4.1 → T4.2 ┐
T3.2 → T2.2 ┼→ T3.3 → T2.5 → T5.3 → rehearsal
T2.1 ───────┘
```

Start T1.1, T2.1, T2.3, T3.1, T3.2, T3.5, T4.1 and T5.1 at once. They need only the frozen schemas and stubs.
