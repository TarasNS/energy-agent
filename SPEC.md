# SPEC.md — Energy 4.0 Harness Hackathon POC

**Status:** draft → lead approval required
**Role in the chain:** the *what*. Why is in [intent.md](intent.md); how is in [ARCHITECTURE.md](ARCHITECTURE.md); when is in [PLAN.md](PLAN.md).

## 1. Product scope

### Core workflow
**Monthly Curtailment Review**

User selects:
- portfolio / asset group
- price zone (POC: DK1)
- month
- optional decision threshold (EUR)

System (an agent loop in `harness/`, built from the team's POC harness):
1. the model receives the request, the `curtailment-advisor` skill and a fixed tool registry;
2. the model chooses and calls read-only tools to load the portfolio and market fixtures;
3. the model must call `energy-calc` for curtailed energy and economic impact;
4. the model explains the result and gives a recommendation;
5. the model may call `propose_action` (proposal only);
6. a human approves outside the loop before simulated execution;
7. every tool call, proposal and approval is recorded in the audit log.

### Architectural rule
The model plans, sequences tools and explains.
**The model does not invent the financial number, and it cannot approve.** The harness builds the result's numbers from the recorded `energy-calc` tool output, never from model text. A review with no `energy-calc` call fails.

The layer diagram, component boundaries and data flow are in [ARCHITECTURE.md](ARCHITECTURE.md). This document does not repeat them.

---

## 2. Components (what each must do)

### 2.1 Synthetic data — `data/synthetic/`
Must contain enough information for at least five known scenarios (see [EVALS.md](EVALS.md)).

Minimum fields (contracts in [`schemas/`](schemas/)):
- `asset_id`
- interval timestamp
- `price_zone`
- `actual_mwh`
- `available_mwh`
- `curtailed_mwh` or derivable equivalent
- `day_ahead_price_eur_mwh`

Optional: reason, PPA/reference price, weather, asset technology.

### 2.2 `energy-calc`
Pure deterministic functions.

```text
calculate_curtailment_value(...)
→ { curtailed_mwh, economic_value_eur, assumptions, input_hash, calculation_version }
```

The exact formula must be documented and covered by golden tests. Formula v1: [EVALS.md §2](EVALS.md#2-formula-v1). Results are split by cause and by asset.

### 2.3 `portfolio`
Read-only access to the synthetic portfolio.

POC: list assets; fetch monthly production / curtailment inputs.
Stretch: data-class ceiling, CSV adapter, live company adapter.

### 2.4 `energy-data`
POC uses fixture market prices.
Stretch: Energi Data Service / ENTSO-E runtime retrieval, weather, expected solar yield.

The demo may never depend exclusively on a live public API.

### 2.5 `actions`
Two-stage design:

```text
propose_action(payload)                                → proposal_id
issue_approval_token(proposal_id)                      → one-time token (human-only path)
approve_action(proposal_id, approval_token, approver)  → simulated_result + audit_record
```

Without a valid, unused token for that proposal, execution must fail. Only `propose_action` is in the agent's tool registry. The model has no tool that can reach `issue_approval_token` or `approve_action`. The POC action is `enable_negative_price_curtailment` on one asset, simulated only. No physical control action is permitted.

### 2.6 Skill — `curtailment-advisor`
One production-quality skill. It must:
- state when it applies;
- identify required tools;
- instruct the model to quote calc output exactly;
- require assumptions to be shown;
- prohibit invented values;
- use proposal mode for any action.

### 2.7 Model profiles
Provider: Anthropic Python SDK, behind a model-agnostic gateway (`model/`). POC profiles: `default` and `fast` (two Anthropic models) plus `offline` (recorded replies, no network). No code outside `model/` may import a provider SDK.

Model switching is complete only when the same fixture yields the same deterministic EUR result and the workflow remains functional.

### 2.8 Harness — `harness/`
A small agent loop built from the team's working POC harness (branch `claude/awesome-planck-bt3ymf`, `harness/poc/`). The loop, tool registry and trace are reused; the safety layer is added. File-by-file mapping: [TASKS.md](TASKS.md#what-we-reuse-from-the-poc).

| Piece | From the POC | Energy version |
|---|---|---|
| `agent.py` | The ReAct loop with `max_steps` and one forced "answer now" call | `run_review()`: same loop, `STEP_BUDGET` (default 10), model via `model_gateway`, calc-of-record check, returns a review result |
| `tools/registry.py` | `@tool` decorator, pydantic argument validation, errors returned to the model, never raises | Exactly five tools: `list_assets`, `get_production`, `get_day_ahead_prices`, `calculate_curtailment_value`, `propose_action`. No `calculate` tool |
| `trace.py` | One JSONL line per model call and tool call | Same, plus every tool call appended to the audit log |
| `prompts/system.txt` | The POC system prompt ("never invent numbers") | Short system prompt; the `curtailment-advisor` skill is appended at load time |
| `tests/` | `ScriptedLLM` fake model, no network | Same pattern for the loop tests |

Not taken from the POC: the OpenRouter client and fallback chain, request budget, probe, live weather and price APIs, PV estimate, simulator and chat UI. The POC also has no calculator of record, proposal, approval or audit; those are the additions above.

Step budget hit, unknown tool, or no `energy-calc` call → the review fails with a presenter-readable message.

### 2.9 UI
Primary objective: make the business flow legible to a non-developer. POC runtime: a screen built in Lovable that calls a small local FastAPI server (`apps/web`), API in [ARCHITECTURE.md §4](ARCHITECTURE.md#4-shared-contracts). One plain HTML page in `apps/web` is the offline fallback. Only synthetic data goes into Lovable ([brief](presentation/lovable-brief.md)).

Minimum screen: inputs, "Run review", result card with EUR value, assumptions, recommendation, the tools the AI used (in order), proposal/approval control, audit confirmation.

Do not build a general-purpose agent desktop or a generic chat UI.

---

## 3. Functional requirements

| ID | Requirement | Priority | Acceptance | Owner |
|---|---|---:|---|---|
| FR-01 | Run monthly curtailment review on synthetic data | Must | Agent loop finishes within the step budget and returns a valid review result | Dev 2 |
| FR-01b | Fixed tool registry | Must | Test proves exactly five tools exist and approval is not one of them | Dev 2 |
| FR-02 | Calculate economic value in code | Must | Exact golden result | Dev 4 |
| FR-03 | Explain result with model | Must | Explanation cites tool output, no new number; result numbers come from the recorded calc call | Dev 1 |
| FR-04 | Create action proposal | Must | Proposal ID returned | Dev 2 |
| FR-05 | Block execution without approval | Must | Test proves denial | Dev 2 |
| FR-06 | Record approved action | Must | Audit line created | Dev 2 |
| FR-07 | Offline/synthetic demo mode | Must | Demo works without public APIs; `offline` replays recorded model turns through the same loop | Dev 3 |
| FR-08 | Switch model profile | Should | `default` ↔ `offline` gives the same numbers | Dev 3 |
| FR-09 | Second harness | After POC | Same skill runs elsewhere | — |
| FR-10 | Live market API | After POC | Graceful fallback to fixture | — |

---

## 4. Safety invariants

These are not prompt rules; they are enforced by code where applicable. Where each is enforced: [ARCHITECTURE.md §6](ARCHITECTURE.md#6-safety-invariants-and-where-they-are-enforced).

1. **Financial truth:** every displayed EUR decision value comes from `energy-calc`.
2. **Read-only default:** data tools have no write side effects.
3. **Human approval:** an action cannot execute without an approval token.
4. **Traceability:** action proposal and approval are written to the audit log.
5. **Offline demo:** no live API is a single point of failure.
6. **No secret leakage:** credentials never appear in source, prompts, fixtures or logs.

Stretch:
7. **Data class ceiling:** the portfolio tool refuses data beyond the active profile's class.

---

## 5. Non-functional requirements
- Core demo starts in under 2 minutes from a clean local environment after dependencies are installed.
- Core demo response target: <20 seconds per review under normal provider conditions; instant with the `offline` profile.
- Tests run with one documented command (`make test`).
- No hidden manual data edits during the demo.
- Failure messages must be understandable to a presenter.
- Audit records are human-readable (JSON Lines).

---

## 6. Demo request / result contract

Request (illustrative):

```json
{ "portfolio": "demo-solar-dk", "zone": "DK1", "month": "2026-06", "threshold_eur": 5000 }
```

Result: [`schemas/review-result.schema.json`](schemas/review-result.schema.json). Golden values are filled by Dev 4 and frozen before integration.

---

## 7. POC / stretch gate

A stretch item may be started only after:
- all Must requirements pass;
- the demo smoke test passes;
- the latest integrated build has been rehearsed once.

If a stretch feature breaks the core flow, revert it. Stretch order: [PLAN.md §7](PLAN.md#7-optional-stretch-order).
