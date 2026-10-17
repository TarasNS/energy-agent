# ARCHITECTURE.md — Energy 4.0 Harness

**Status:** draft → lead approval before the hackathon · **Scope:** first proof of concept (POC)
**Role in the chain:** the *how*. This is the single source of truth for layers, component boundaries and shared contracts. Other documents link here instead of repeating it.

## 1. Principle

> The model explains and reasons. Deterministic code calculates the business numbers. Humans approve real actions.

| Concern | Owned by |
|---|---|
| Numbers | Deterministic code (`energy-calc`) |
| Data access | Controlled, read-only tools |
| Actions | Human approval enforced in code (`actions`) |
| Everything | Append-only audit log |

## 2. Layers

```text
                         ┌─────────────────────┐
                         │      Web / UI       │   1. Experience
                         │  Hackathon Demo UI  │
                         └──────────┬──────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Harness: agent loop │   2. Orchestration
                         │ + tool registry     │
                         └───────┬─────┬───────┘
                    ┌────────────┘     └────────────┐
                    ▼                               ▼
          ┌──────────────────┐             ┌──────────────────┐
          │ Energy Skills    │             │ Model Profile    │   3. Energy intelligence
          │ SKILL.md         │             │ Claude / other   │   6. Models
          └────────┬─────────┘             └──────────────────┘
        ┌──────────┼───────────┬──────────────┐
        ▼          ▼           ▼              ▼
┌────────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐
│ Energy Data│ │ Portfolio │ │Energy Calc│ │  Actions   │       4. Energy tools
└─────┬──────┘ └─────┬─────┘ └─────┬─────┘ └─────┬──────┘
      ▼              ▼             ▼             ▼
 Market data     Synthetic /   Deterministic   Proposal            5. Data
 Weather         company data  EUR logic       Approval
 Prices                                         Audit log
```

| # | Layer | Contents | Lives in | Owner |
|---|---|---|---|---|
| 1 | Experience | Lovable screen calling a small local FastAPI server; one plain HTML page as the offline fallback | `apps/web/` | Dev 5 |
| 2 | Orchestration | Agent loop (template-style): the model picks tools from a fixed registry; the harness enforces step budget, calc-of-record and audit | `harness/` (replaces `workflow/`) | Dev 2 |
| 3 | Energy intelligence | Skill, context, rules | `.claude/skills/curtailment-advisor/` | Dev 1 |
| 4 | Energy tools | `energy-data`, `portfolio`, `energy-calc`, `actions` | `mcp/*/` | Dev 1, 3, 4, 2 |
| 5 | Data | Synthetic portfolio, market fixtures; later ERP / data platform / SCADA adapters | `data/synthetic/` | Dev 4 |
| 6 | Models | Model gateway: Anthropic SDK behind one interface; profiles `default`, `fast`, `offline` | `model/` | Dev 3 |

**Models are replaceable.** They explain and reason. They are never the calculator of record and never the permission system. All model calls go through `model_gateway.get_client()`; only `model/model_gateway/` imports a provider SDK (enforced by `make check`). Contract: [model/README.md](model/README.md).

## 3. Request flow (Monthly Curtailment Review)

```text
UI ── POST /api/review {portfolio, zone, month, threshold_eur}
 └─▶ harness.agent.run_review(request)
      messages = [system.txt + curtailment-advisor skill, request]
      loop, at most STEP_BUDGET rounds:
        turn = model_gateway.get_client().run_turn(messages, registry.schemas())
        no tool calls   → final explanation + recommendation, stop
        each tool call  → registry.dispatch(name, args) → result (offloaded if large)
                          audit: tool_call {name, args_hash}
      typical model-chosen order:
        list_assets → get_production → get_day_ahead_prices
        → calculate_curtailment_value → (optional) propose_action
      harness check: calc was called; result numbers = last calc output, unchanged
 ◀── review-result (+ proposal_id if proposed, + tool trace)
UI ── [human approves] POST /api/proposals/{id}/approve
      → actions.issue_approval_token + approve_action(id, token, approver) → simulated result, audit
```

The model sequences the tools; the controls live in the tools and the harness, not in the prompt. It is still **one** loop, not a multi-agent runtime. `issue_approval_token` and `approve_action` are not in the registry.

### Harness layout (template structure, trimmed)

```text
harness/
├── agent.py              run_review(): ReAct loop, step budget, calc-of-record check
├── config.py             STEP_BUDGET, MODEL_PROFILE
├── prompts/system.txt    short system prompt; skill appended at load
├── tools/registry.py     the five tools: JSON schema + dispatch over mcp/* pure functions
├── context/offloader.py  large outputs → artifacts/, summary to the model
└── tests/
```

The model gateway contract grows from `explain(...)` to `run_turn(messages, tools) → ModelTurn{text, tool_calls}`. The `offline` profile replays recorded turns, so the same loop runs without network.

## 4. Shared contracts

Contracts are JSON Schemas in [`schemas/`](schemas/). They are **draft** until the Milestone A freeze; after that, changes need lead approval (see [PLAN.md §6](PLAN.md#6-stop-conditions)).

| Schema | Describes | Producer → consumer |
|---|---|---|
| [`asset.schema.json`](schemas/asset.schema.json) | One asset in a portfolio | portfolio → harness, calc |
| [`production.schema.json`](schemas/production.schema.json) | One interval of available/actual/curtailed energy | portfolio → calc |
| [`market-price.schema.json`](schemas/market-price.schema.json) | One interval of day-ahead price | energy-data → calc |
| [`review-result.schema.json`](schemas/review-result.schema.json) | Output of one review (calc + explanation; `tool_trace` added in T3.5) | harness → UI, evals |
| [`action-proposal.schema.json`](schemas/action-proposal.schema.json) | Proposal, approval and audit record | actions → harness, UI, audit log |

### UI ↔ server API (POC)

| Method | Path | Returns |
|---|---|---|
| `POST` | `/api/review` | review result |
| `POST` | `/api/proposals` | proposal |
| `POST` | `/api/proposals/{id}/approve` | proposal + audit record |

Details: [apps/web/README.md](apps/web/README.md). The approve endpoint is the only caller of the token functions; the model's tools stop at `propose_action`.

Money rule: EUR values cross boundaries as **decimal strings with two decimals** (`"85.00"`), never as floats. Energy as strings with three decimals (`"12.500"`). The calc uses `decimal.Decimal`. This makes golden comparisons exact.

## 5. Code conventions (proposed — Dev 3 confirms at Milestone A)

- **Language:** Python 3.11+ for tools, calc, harness, evals. UI stack is Dev 5's choice.
- **Tool layout:** each `mcp/<tool>/` contains a pure Python package (hyphen → underscore), its tests, and optionally a thin MCP server wrapper:
  ```text
  mcp/energy-calc/
  ├── energy_calc/       pure functions, no I/O
  ├── tests/
  └── server.py          optional thin MCP wrapper, added only if a harness needs it
  ```
- **Do not create `mcp/__init__.py`.** The folder is not a package; making it one would shadow the official `mcp` Python SDK.
- **Import paths** are configured once in [`pytest.ini`](pytest.ini) (Dev 3).
- **Tool neutrality:** pure functions first; the agent loop, MCP and Claude Code specifics stay in wrappers at the edge (`harness/tools/registry.py`, optional `server.py`).
- **Model neutrality:** business code calls `model_gateway.get_client()` only. The Anthropic SDK lives in `model/model_gateway/anthropic_client.py`; a new vendor is one new class plus a profile in `model/profiles.json`.
- **No distributed services.** Everything runs in one local process for the demo unless the UI requires a small HTTP API.

## 6. Safety invariants and where they are enforced

| # | Invariant | Enforced by | Proved by |
|---|---|---|---|
| 1 | Every displayed EUR value comes from `energy-calc` | Harness copies the recorded calc tool output into the result unchanged and fails if calc was not called; UI renders numbers from the result object, never from model text | Golden tests; `no-invented-number` eval after the POC |
| 2 | Data tools are read-only | `energy-data` and `portfolio` expose only read functions; no write paths exist | Code review + test that no write function is exported |
| 3 | No action without approval | One-time token issued only by the human Approve endpoint; `approve_action` validates it in code; approval functions are not in the tool registry | Unit tests in `mcp/actions/tests/` |
| 4 | Tool calls, proposal and approval are audited | `registry.dispatch` and `actions` append JSON Lines to `AUDIT_LOG_PATH` before returning | Unit tests; `make demo-smoke` |
| 5 | No live API is a single point of failure | Synthetic data by default; `offline` model profile with recorded replies | Offline rehearsal |
| 6 | No secret leakage | `.env` git-ignored; `make check` secret scan (hooks after the POC) | `make check` in CI |
| 7 | (stretch) Data-class ceiling | `portfolio` refuses data above the active profile's class | Stretch eval |

## 7. Runtime configuration

From `.env` (template: [`.env.example`](.env.example)):

| Variable | POC value | Meaning |
|---|---|---|
| `ENERGY_DATA_MODE` | `synthetic` | `synthetic` or `live` (live falls back to fixtures) |
| `STEP_BUDGET` | `10` | Max tool-call rounds per review |
| `MODEL_PROFILE` | `default` | `default`, `fast` or `offline`; mapping in `model/profiles.json` |
| `ANTHROPIC_API_KEY` | _(local only)_ | Read by the Anthropic SDK; never committed |
| `ACTION_MODE` | `proposal_only` | Actions can only be proposed and simulated |
| `AUDIT_LOG_PATH` | `./artifacts/audit.jsonl` | Append-only audit log |

## 8. Not in this POC

Production SCADA control, enterprise identity/RBAC, ERP/data-platform adapters, branded desktop fork, production deployment, battery optimisation, multi-agent runtime, broad model/harness matrix, Claude Code hooks, the EnergyBench-Lite runner, CI test gating, live market data. These are roadmap items; the architecture leaves room for them as adapters at the data layer and wrappers at the edge.

## 9. Decision log

Record decisions here as one line each. Do not rewrite history; add a new line when a decision changes.

| Decision | By |
|---|---|
| One workflow (Monthly Curtailment Review) for POC | Lead |
| No custom harness; energy layer is harness-neutral (superseded below) | Lead |
| Formula v1 split by cause (EVALS.md §2), after a domain check | Dev 4 + Lead |
| Demo runtime: local HTML page + FastAPI (`apps/web`) | Lead + Dev 5 |
| Screen built in Lovable during the event; local page stays as offline fallback | Lead + Dev 5 |
| Anthropic SDK behind a model-agnostic gateway; profiles `default`, `fast`, `offline` | Lead |
| GitHub repo ready and cloned by everyone before the hackathon starts | Lead |
| Approved action: `enable_negative_price_curtailment` on one asset, simulated | Lead + Dev 2 |
| Scope is a first POC built in one short session; everything else is after the POC | Lead |
| Orchestration is a trimmed agent loop based on coderonfleek/harness-course-build; the model picks tools; replaces the fixed workflow | Lead |
| _pending:_ Schemas frozen | Dev 3 + Dev 4 + Dev 2 |
