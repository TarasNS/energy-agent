# IMPLEMENTATION_PLAN.md — prioritised changes

**Status:** draft for review · **Branch:** `feature/nordic-solar-real-world` · **Do not merge to `main` without review.**

Principle kept from the spec: the open-source core stays generic; Nordic Solar specifics live in the private layer. Each step below is one task, one branch, one PR into `feature/nordic-solar-real-world`, following the normal loop in `WORKFLOW.md`.

## Priority 1 — Make the existing numbers trustworthy (blocks everything)

| # | Change | Owner | Done when |
|---|---|---|---|
| P1.1 | Implement `calculate_curtailment_value` for Formula v1, Decimal throughout | Dev 4 | Golden cases pass exactly |
| P1.2 | Flag fallback rows in `curtailed_mwh` and report their share | Dev 4 | Output includes a fallback count and share |
| P1.3 | Add missing-data state: any gap is "unavailable", never filled | Dev 4 + Dev 2 | Test: a gap yields "unavailable", not a number |
| P1.4 | Source lineage on every value: record ID or file hash, extraction time (UTC), calc version | Dev 2 | Audit line shows all three for one EUR figure |

## Priority 2 — One real source, read-only (proves value)

| # | Change | Owner | Done when |
|---|---|---|---|
| P2.1 | Private adapter interface for production (read-only), selected by config | Dev 3 | Synthetic adapter still default; switch needs no code change |
| P2.2 | Sanitized one-month production extract loaded through the private adapter | Dev 3 (access owner: Nordic Solar) | Same shape as `data/synthetic/`; no identifiers in repo |
| P2.3 | Price source labelled "synthetic" on screen until licence confirmed | Dev 1 + Dev 5 | Screen shows the label |
| P2.4 | Access requests raised for analytics platform, SCADA and market data | Lead | Requests logged; owners named |

## Priority 3 — KPI set (what the team is measuring)

| # | Change | Owner | Done when |
|---|---|---|---|
| P3.1 | Adopt `config/kpi_catalog.yaml`; resolve ASSUMPTION owner roles with Nordic Solar | Lead | Every POC KPI has a confirmed owner |
| P3.2 | Rename `lost_revenue_eur` as opportunity value; bridge headline to other KPIs | Dev 4 + Dev 5 | Screen shows the bridge |
| P3.3 | Add realised (capture) price once metered output and prices both exist | Dev 4 | Golden case for capture price |
| P3.4 | Introduce further KPIs only when their source is validated | Lead | No KPI shown without source and owner |

## Priority 4 — Agent and audit hardening

| # | Change | Owner | Done when |
|---|---|---|---|
| P4.1 | Audit log is append-only JSON Lines; one line per tool call, proposal and approval | Dev 2 | Test: no rewrite or delete path exists |
| P4.2 | Approval token kept in memory, never logged or returned to the browser | Dev 2 | Test: token absent from logs and responses |
| P4.3 | Structured error for a failed extraction (logged event, not silent skip) | Dev 2 | Test: failure appears in audit log |
| P4.4 | Agent output distinguishes observed values from inferred conclusions | Dev 1 | Skill text and test enforce the labels |

## Explicitly out of scope for this branch

- Live market feed, licensing and redistribution.
- ERP access (out of scope until finance-data sensitivity is cleared).
- Any SCADA write path, setpoint or control action (prohibited by the rules).
- Document ingestion from the document store.
- The daily business-intelligence job: its outputs are not accessible, so it is not reused.
- Finance KPIs computed by the harness (they are reference only, from the finance system of record).

## Risks

| Risk | Mitigation |
|---|---|
| Access to production data is delayed | Keep the synthetic adapter as default; the demo runs offline |
| A KPI formula is wrong and shown as fact | Golden tests; no KPI shown without owner sign-off |
| Confidential data leaks into git | `private/` is git-ignored; leak scan before every PR |
| Model states a number not in the calculator output | Calc-of-record check in the harness and an eval (Dev 4) |
