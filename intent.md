# Intent: Safe Energy Decision Assistant

**Status:** draft → team approval required
**Role in the chain:** the *why*. Requirements are in [SPEC.md](SPEC.md); design is in [ARCHITECTURE.md](ARCHITECTURE.md).
**Target:** a first proof of concept (POC), built live in a short session at the AI in Energy Hackathon.

## Problem
Renewable-energy portfolio teams make operational and commercial decisions from fragmented sources: asset production, expected production, market prices, contracts and operational constraints.

AI can summarise those sources, but a generic assistant creates three business problems:
1. numerical answers may be difficult to trust;
2. company data may be sent to the wrong model/provider;
3. an autonomous agent may take an action without the required human approval.

The result is that useful agentic workflows are hard to adopt for real portfolio work.

## Proposed outcome
An energy-native AI layer that:
- connects portfolio and market context;
- uses deterministic code for financial calculations;
- keeps the model choice flexible;
- produces a recommendation with assumptions;
- turns real-world actions into proposals that need human approval;
- records an audit trail.

## Job to be done

> **When I review the performance of my renewable portfolio, I want the system to show the economic impact of curtailment and negative prices in EUR and recommend what to change, so I can act faster without giving up control or auditability.**

## The decision the POC demonstrates
In June 2026, one DK1 park (Engbakke Solar, demo data) keeps producing into negative day-ahead prices because negative-price curtailment is not enabled. The other parks self-curtail and avoid that cost. Energy 4.0 Harness quantifies the exposure in EUR, recommends **enabling negative-price curtailment on Engbakke**, turns that into a proposal, and records the human approval.

## Primary user
Renewable portfolio / asset manager responsible for operational and economic performance.

## Secondary users
Energy analyst · Operations lead · Trading / commercial team · Risk / compliance reviewer

## Value proposition
- **Functional:** turn manual analysis into a repeatable decision workflow.
- **Economic:** quantify the issue in EUR so the user can prioritise.
- **Risk:** critical numbers come from code; actions stay human-approved.
- **Strategic:** the energy layer is portable across models and agent tools.

## What the POC must show in three minutes
1. an energy question;
2. a deterministic EUR result, split by cause;
3. an AI explanation and recommendation;
4. a human approval gate;
5. an audit record.

## Success criteria
- End-to-end demo completes in under 3 minutes.
- Golden EUR checks pass exactly.
- Approval without a valid token is rejected.
- Approved proposal is recorded in the audit log.
- The demo runs on synthetic data and survives loss of internet (offline model profile).

## Constraints
- Build time is one short hackathon session; prepare everything else before.
- The event values a working business app, not infrastructure for its own sake.
- No real production action. No confidential company data. One small agent loop (trimmed from a template), no general agent runtime.

## Not in this POC
Production SCADA control · enterprise identity / RBAC · ERP or data-platform adapters · branded desktop · deployment platform · battery optimisation · multi-agent runtime · broad model/harness matrix · full eval suite · CI hardening.

## Decisions (closed before the hackathon)

| # | Question | Decision for the POC | Owner |
|---|---|---|---|
| 1 | Which formula and fixture are the demo truth? | Formula v1 in [EVALS.md §2](EVALS.md#2-formula-v1) on the fixture in `data/synthetic/`, after a 15-minute check with an energy colleague | Dev 4 + Lead |
| 2 | Which runtime hosts the demo? | Screen built in Lovable on synthetic data, calling the local API (`apps/web`). The local HTML page stays as the offline fallback | Lead + Dev 5 |
| 3 | Which models? | Anthropic SDK behind a model-agnostic gateway; profiles `default`, `fast`, `offline` | Dev 3 |
| 4 | What does an approved action simulate? | `enable_negative_price_curtailment` on one asset, simulated and audited; nothing is sent anywhere | Lead + Dev 2 |
| 5 | Who has final merge authority? | Team lead | Team |
