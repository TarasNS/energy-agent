# CHANGES.md — what changed, what is unavailable, what remains

**Branch:** `feature/nordic-solar-real-data` (from `feature/nordic-solar-real-world`) · **Not merged.** Review before merge.

## 1. Implemented

| Change | Where | Verification |
|---|---|---|
| Pure KPI formulas for the four groups (14 functions): solar generation, commercial, asset operations, BESS | `mcp/kpi-solar/kpi_solar/metrics.py` | 31 tests, hand-worked expected values, `pytest` passes |
| Rules: floats, NaN and infinity rejected; missing input returns "unavailable"; partial price results and negative energy refused; unknown status codes raise; DATA_GAP is never counted as downtime | same file | 31 tests, all pass |
| Test path added so `make test` finds the package | `pytest.ini` (owned by Dev 3; the change is one line) | `python -m pytest` runs |
| KPI review for the four groups | `KPI_REVIEW.md` | Reviewed against the formulas |
| Local working notes, not for git | `private/notes/real-data-findings.md` (git-ignored) | Kept for future steps |

## 2. Not implemented, and why

| Item from the brief | Status | Reason |
|---|---|---|
| Replace mock data with verified Nordic Solar data | **Not done** | No verified operational data is accessible. The only production file found has no provenance, so it is not used as company fact |
| Production, price and ticket adapters | **Not done** | Source access is not verified; adapters would have no real endpoint to test against |
| Agent workflows and dashboards updated for the KPIs | **Not done** | Wiring KPIs into the agent or screen before the data exists would produce unverified output. Deferred until a source is validated |
| Independent verification by a second agent | **Done** | Hand-recomputed 13 formulas: all matched except hours precision. Its 8 findings were fixed: hours to 2 dp, NaN and infinity rejected, string input rejected, `None` returns unavailable, negative energy refused, DATA_GAP excluded from downtime. 10 regression tests added |

## 3. Unavailable data (never invented)

| Input | Needed for | Status |
|---|---|---|
| Expected generation baseline | Actual vs expected, energy losses | Unavailable |
| Plane-of-array irradiation | Performance ratio | Unavailable |
| Plant and inverter status history | Availability, downtime | Unavailable |
| Outage and ticket log | Incident resolution | Unavailable |
| PPA contract terms | PPA performance | Unavailable |
| BESS meters, state of charge, auxiliary load | All three BESS KPIs | Unavailable |
| Day-ahead prices for the metered period | Realised price, merchant exposure | Unavailable (licence to confirm) |

## 4. Remaining gaps

1. No verified source data for any of the four groups.
2. Daily collection job: outputs not accessible; owner must supply them or retire the job.
3. Owners for `mcp/kpi-solar/` are not assigned. It is a new path outside the TEAM.md table, so the lead must assign it.
4. Access requests are still open for the analytics platform, SCADA, market data and ticket system.
5. Dashboards and agents are not yet connected to the KPI functions.
6. The branch is not merged. It needs review first.
