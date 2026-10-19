# NORDIC_SOLAR_ASSESSMENT.md — business context, sources, gaps

**Status:** draft for review · **Branch:** `feature/nordic-solar-real-world`

This document is public-safe. It states what exists, what is missing and what is verified. Company records, personal files and confidential figures are not in this repository. They are described by category only, in the git-ignored `private/` folder.

## 1. Business context

Nordic Solar is treated as a European solar and energy company with asset operations, finance, commercial (PPA and merchant exposure), projects, storage and IT/data functions. The first decision the harness supports is **monthly curtailment and negative-price review** for a DK1 solar portfolio. Its output is an EUR impact by cause and a recommendation that a person approves.

No company financial or operational figure is stated in this document. Where a value is needed, the harness shows "unavailable".

## 2. Source inventory (by category, verified status)

| Category | What it holds | Verified status | Where it lives |
|---|---|---|---|
| Market intelligence | Weekly briefs on competitors, policy, technology | Present, reviewed. Not an operational KPI source | `private/` |
| Finance and reporting process | Process observations for group reporting and close | Present, reviewed. Process material, not KPI data | `private/` |
| Daily business-intelligence collection job | Earlier automated daily summaries | **Not accessible.** Only configuration fragments found; no saved outputs | n/a |
| ERP and analytics platform | Finance tables, production data | **Access not verified.** An ERP connection exists in configuration only | Company systems |
| Plant telemetry | Production, availability, curtailment | **Access not verified** | Company systems |
| Personal and HR files | Payslips and similar | **Excluded.** Not read, not used, not referenced | Not in scope |

Confidential identifiers (tenant and environment IDs, account names, people's names) are kept out of this repository.

## 3. Existing harness: what it does today

Verified against the repository (branch `dev`, after PRs 1–3):

- Five fixed tools, approval not among them, audit log defined in the contracts.
- Calculator defined in `EVALS.md` §2 (formula v1), with golden cases planned. Calculator code and golden tests are **not yet implemented**.
- Data is synthetic (`data/synthetic/demo-solar-dk`). No real adapter exists.
- The Lovable screen and the local API are **not yet built**.
- Proposal and approval are defined in the spec; the code is not yet written.
- Azure deployment covers the docs site only.

## 4. Gaps against a real operating environment

| # | Gap | Why it matters | Planned fix |
|---|---|---|---|
| G1 | No real data adapter | Results cannot be checked against real production | Private adapter, read-only, one source first (see `INTEGRATION_MAP.md`) |
| G2 | KPI set covers curtailment only | Operations, finance and IT decisions have no measures | KPI audit (`KPI_AUDIT.md`) and a curated catalog |
| G3 | No source lineage in outputs | A reviewer cannot trace a number | Source record ID, extraction time and calculation version on each value |
| G4 | Approval token and audit not persisted | Audit must survive a restart | Append-only JSON Lines audit; token kept in memory and never logged |
| G5 | No missing-data display rule in code | Gaps could be silently filled | Explicit "unavailable" state, tested |
| G6 | Daily collection job outputs missing | Its history cannot be reused or validated | Request the outputs and job definition from the owner, or retire the job |
| G7 | No separation of confidential config | Risk of leaking tenant data into the repo | `private/` boundary and `config/nordic-solar.example.yaml` (done in this branch) |

## 5. Decision

Proceed with a **one-source, read-only POC** on a sanitized one-month extract, with synthetic prices labelled as such. Do not present any figure as company fact until its source is verified and its owner has signed off the formula. Do not merge this branch into `main` without review.

## 6. Verified vs. assumed

| Statement | Status |
|---|---|
| Five-tool registry; no approval tool | Verified (repo contracts and spec) |
| Formula v1 is the calculation of record | Defined, not yet implemented |
| Daily collection outputs exist | **Not verified** — not found |
| ERP and telemetry access exists | **Not verified** |
| Market price feed is licensed | **Not verified** |
