# INTEGRATION_MAP.md — sources, adapters, permissions, missing data

**Status:** draft for review · **Branch:** `feature/nordic-solar-real-world` · **Scope:** read-only integration of enterprise and market sources into the Monthly Curtailment Review.

Systems are named by type only. A source is "accessible" only when it has been verified. Confidential identifiers, tenant or environment IDs and personal data stay in `private/` (git-ignored); see [config/nordic-solar.example.yaml](config/nordic-solar.example.yaml).

## 1. Source systems

| Source type | Data needed (KPI) | Ingestion | Adapter location | Permission model | Data contract | Status | Missing data shows as | Risk |
|---|---|---|---|---|---|---|---|---|
| Analytics platform (lakehouse or warehouse), read-only | Production per asset and interval; asset list | Batch daily; on demand for re-runs | Private adapter package; open core keeps the `energy-data` interface and a synthetic adapter | One read-only identity, one workspace; no write or admin rights | Existing production and asset schemas, if they match; otherwise a new schema | **Unknown — needs access request** | "unavailable" with the interval range; never interpolated | Scope creep into other workspaces; timezone and DST mismatch on 15-minute data |
| ERP, finance tables | Contract and tariff parameters, for EUR context only | Batch daily; on demand | Private adapter; interface in open core | Read-only API user, table-level least privilege; no posting rights | New schema for contract terms; no EUR taken from ERP into agent output | **Needs access request.** An MCP connection exists in configuration: available in principle, permissions unverified | If contract terms are absent, the calculation shows "unavailable"; no default rate | Finance data in prompts; the agent quoting ERP figures instead of calc output |
| Cloud hosting | Not a KPI source; hosts the harness and any sanitized extract | n/a | Deployment config, outside the core repo | Managed identity with read access to the extract store only | n/a | Azure guide site deployed (docs only); harness not yet deployed | n/a | Secrets in app settings; use `.env` locally and the vault in cloud |
| Plant telemetry (SCADA historian or export) | Actual production, curtailment instructions, availability, downtime | Intraday for monitoring; batch daily for the review | Private adapter; open core interface only | Read-only historian or export account; **no control or setpoint write path** | Production and availability schemas | **Needs access request.** Highest-value source | Telemetry gaps shown as "unavailable" with the gap window; no curtailment EUR for gaps | Physical-control exposure if the account can write; raw data quality |
| Document store | Curtailment notices, grid-operator instructions (reference only) | On demand | Private adapter; interface only if needed | Read-only app permission on one library | New schema; documents are citations, never KPI inputs | Unknown | "no source document"; the agent must not paraphrase missing terms | Confidential contract text in prompts; permission over-grant |
| Market data: day-ahead prices | 15-minute prices per bidding zone | Batch daily | Open core: synthetic adapter; real adapter private | Read-only key from `.env`, never in source | Price schema; money as decimal strings | Unknown: licence and feed access to confirm | Missing intervals "unavailable"; no default price | Licence limits on redistributing data in demo output |
| Market data: weather (irradiance, temperature) | Actuals and forecasts for curtailment explanations | Batch daily | Private adapter; interface in open core | Read-only key | New schema | Unknown | "unavailable"; the explanation says the weather factor could not be checked | Explanations overstate causality |
| Daily business-intelligence collection job (history) | Possibly prior KPI snapshots | n/a | None | n/a | n/a | **Not accessible.** Only configuration fragments exist; no saved outputs found | Figures from it are not used; the page says "not available in this POC" | Reusing stale or undocumented figures as truth |

## 2. Traceability requirements

1. Every number carries a source record ID (or an extract file hash for the POC), the extraction time in UTC, and the calculation version from `mcp/energy-calc`.
2. Every EUR and MWh value is copied exactly from `calculate_curtailment_value`. The model does not compute, round or restate it.
3. Money and energy cross boundaries as decimal strings.
4. Each tool call, proposal and approval is appended to the JSON Lines audit log with the same IDs, so a reviewer can trace a figure back to its source row.
5. Missing or failed extraction is logged as an event, never silently skipped.

## 3. Boundary rule

- **Open core:** interfaces (`energy-data`, `portfolio`, price and production contracts) and synthetic adapters only. The demo runs offline on `data/synthetic/`.
- **Nordic Solar layer:** adapters, endpoint configuration and any credentials live in the git-ignored `private/` folder. Nothing private is committed, printed in logs, or placed in prompts or fixtures.
- Adapters are selected by configuration, not by code changes in the core.
- The agent's tool registry stays fixed at five tools. No adapter adds a write tool, and no approval function is exposed to the model.

## 4. Minimum integration to prove value in the POC

1. **One source only:** the plant production export from the analytics platform (or a SCADA export if platform access is not granted in time), read-only.
2. A sanitized extract covering one month, with identifiers replaced by asset codes, loaded through the private adapter into the same shape as `data/synthetic/`.
3. Day-ahead prices from the synthetic adapter, labelled "synthetic" on the page, until the market feed is licensed.
4. Run the Monthly Curtailment Review end to end: list assets, get production, get prices, calculate, propose, approve, audit. Show "unavailable" for anything missing.
5. **Success check:** a reviewer can pick one EUR figure and trace it, in the audit log, to a source record ID, extraction time and calculation version.

## 5. Open items

- Access requests are needed for the analytics platform, SCADA and market data. The team must name an owner for each.
- Confirm which existing `schemas/` files match production, asset and price data before any new schema is written.
- Confirm whether the ERP connection may be used at all, given finance-data sensitivity. Until confirmed, ERP is out of scope for the POC.
