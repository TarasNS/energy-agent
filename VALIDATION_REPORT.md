# VALIDATION_REPORT.md — what was checked, results, limits

**Status:** first pass · **Branch:** `feature/nordic-solar-real-world`

## 1. Executed checks

| Check | Command | Result |
|---|---|---|
| Repo structure, schemas, doc links, secret scan, model-agnostic import guard | `python scripts/verify.py` (same as `make check`) | **Pass** |
| KPI catalog parses and has the expected fields | `yaml.safe_load('config/kpi_catalog.yaml')` | **Pass**: 15 KPIs parsed |
| Nordic Solar config template parses | `yaml.safe_load('config/nordic-solar.example.yaml')` | **Pass** |
| Confidential-data leak scan over tracked and new files (tenant and company identifiers, payroll and personal names) | `git grep` for the listed patterns | **Pass**: no identifiers found. One generic mention of payslips in the assessment's exclusion list, which is intended |
| `private/` is git-ignored | `git check-ignore -v private/README.md` | **Pass** (`.gitignore` line added) |
| Branch from latest `dev` | `git log` | **Pass**: branched from `3952f58` |

## 2. Not executed, and why

| Check | Reason | Impact |
|---|---|---|
| KPI formulas against source data | No validated source extract exists; calculator not implemented | No KPI value can be called verified. Formulas are design, not evidence |
| Golden tests for the calculator | `mcp/energy-calc` has no code yet (Dev 4) | No EUR result is verified |
| Test suite (`make test`) | No tests exist for the new config or KPI logic | Only structural checks ran |
| End-to-end workflow on real data | No real adapter; access not verified | Not possible on this branch |
| Accessibility and brand check of new documents | Documents are Markdown, not web pages | Not applicable |

## 3. Results against the brief's success criteria

| Criterion | Status |
|---|---|
| Source inventory with verified status | **Partly met**: categories and verified status are written; the daily job's outputs are confirmed inaccessible |
| KPI audit with formulas, relevance, evidence and recommendations | **Met as design**: 15 KPIs audited; evidence status marked per KPI |
| Integration map with permissions and missing data | **Met as design**: all sources marked accessible, unknown or not accessible |
| Real data replacing synthetic data | **Not met**: no access verified |
| Agents distinguish observation from inference | **Not met**: designed in the plan (P4.4), not yet implemented |
| Confidential records kept out of git | **Met**: see leak scan above |

## 4. Unresolved issues

1. **Daily collection job:** only configuration fragments found; no saved outputs. Owner must supply outputs or retire the job.
2. **Access:** analytics platform, plant telemetry and market data all need access requests. ERP connection exists in configuration only; its permissions are unverified.
3. **KPI owners:** every owner role in the catalog is an ASSUMPTION until Nordic Solar confirms it.
4. **Calculator:** Formula v1 is defined but not implemented or tested. Until it is, no EUR figure from this branch is evidence.
5. **Review:** the branch is for review only. It is not merged into `main`.

## 5. Source of the analysis

The KPI audit and integration map were drafted by two subagents working in parallel and then checked by the main agent. Subagent output was not verified against company data, because none was accessible. Treat the content as a structured draft, not as validated fact.
