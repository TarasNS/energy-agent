# KPI_AUDIT.md — KPI-by-KPI analysis

**Status:** draft for review · **Branch:** `feature/nordic-solar-real-world`
**Legend:** VERIFIED = stated in the repo. PUBLIC = general industry definition. ASSUMPTION = to be confirmed by Nordic Solar.
**Rule:** no KPI is production-ready without trusted data, a validated formula and a named owner. No company figure is stated here; company-level values are UNKNOWN.

Machine-readable version: [config/kpi_catalog.yaml](config/kpi_catalog.yaml).

## 1. Existing harness KPIs (Formula v1, `EVALS.md` §2)

| KPI | Level | Decision it supports | Formula (units) | Availability | Verdict |
|---|---|---|---|---|---|
| `curtailed_mwh` | asset | Size curtailment loss | Per 15-min interval: `curtailed_mwh`, else `max(available − actual, 0)` (MWh, 3 dp) | synthetic only | **Modify**: the fallback fills gaps silently; flag fallback rows and report their share |
| `lost_revenue_eur` | asset | Merchant loss from non-grid-operator curtailment | Σ curtailed × max(price, 0) (EUR, 2 dp) | synthetic only | **Modify**: label as opportunity value, not P&L |
| `grid_operator_lost_eur` | asset | Support a compensation claim | As above, grid-operator reason only (EUR) | missing (reason codes not in repo) | **Modify**: compensation rules must come from the contract or regulation |
| `avoided_negative_cost_eur` | asset | Value of curtailing at negative prices | Σ curtailed × abs(price) where price < 0 (EUR) | synthetic only | **Keep, with caveat**: a benefit only if curtailment would otherwise have cost money; never add to lost revenue |
| `negative_price_exposure_eur` | asset / portfolio | Headline: money at risk from negative prices | Σ actual × abs(price) where price < 0 (EUR) | synthetic only | **Modify**: an exposure, not a loss; not the headline until its source is validated |

**Findings:** the five KPIs mix three bases (curtailed volume, actual volume, opportunity value), so each needs a glossary entry. The headline uses actual output while the others use curtailed volume, so the headline needs a bridge to the others.

## 2. Existing PV metrics

| Metric | Level | Verdict |
|---|---|---|
| Estimated production (MWh) | asset | **Modify**: always label as an estimate |
| Metered energy (MWh) | asset | **Keep**: needs meter calibration, gap and DST handling |
| Peak MW | asset | **Keep** as a diagnostic only |
| Inverter availability (% of daylight) | asset | **Modify**: fix the daylight definition; separate from technical availability |
| Curtailed interval count | asset | **Modify**: always show with MWh; a count is not energy |
| Data completeness (%) | IT | **Keep** as the gating KPI for all others |
| Day-ahead price mean / min / max | market | **Keep** as context only; use realised price for decisions |

## 3. Candidate KPIs by domain

| Domain | KPI | Level | Formula (units) | Availability | Verdict |
|---|---|---|---|---|---|
| Solar generation | Actual vs expected generation | asset | Actual ÷ expected × 100 (%) | missing: no validated baseline | **Introduce** |
| | Performance ratio | asset | Actual energy ÷ (POA irradiance × nameplate DC) × 100, IEC 61724 style (PUBLIC) | missing: no POA sensor | **Introduce** |
| | Availability | asset | Available hours ÷ period hours × 100 | daylight form available | **Modify** |
| | Capacity factor | asset | Metered MWh ÷ (nameplate MW × hours) × 100 | available | **Keep** (state DC or AC basis) |
| Asset operations | Unplanned downtime | asset | Sum of unplanned outage hours | missing | **Introduce** |
| | Energy loss by cause | asset | Expected − actual MWh, split by availability, curtailment, grid (MWh) | missing | **Introduce** |
| | Incident resolution time | asset | Median and P90 hours, open to close | missing | **Introduce** (use median and P90, not mean) |
| Storage (BESS) | BESS availability | asset | Available hours ÷ period hours × 100 | missing | **Introduce** |
| | Round-trip efficiency | asset | Discharged MWh ÷ charged MWh × 100 | missing | **Introduce** |
| | Cycle utilisation | asset | Throughput ÷ (2 × usable MWh) (PUBLIC convention) | missing | **Introduce** |
| Commercial | PPA delivery vs contract | company | Delivered ÷ contracted MWh × 100 | missing: terms must come from the signed agreement | **Introduce** |
| | Realised (capture) price | asset | Σ(MWh_i × price_i) ÷ Σ MWh_i (EUR/MWh) | missing | **Introduce (priority)**: links output, curtailment and price |
| | Merchant price exposure | portfolio | Merchant MWh × price sensitivity (EUR per EUR/MWh) | missing | **Introduce** |
| Finance | Revenue, EBITDA, OPEX per MW, budget variance | company | Ledger-based | missing; system of record is the finance system | **Introduce, reference only**: the harness does not calculate them |
| Projects | Construction progress, milestone delay, CAPEX variance | project | Earned value or milestones ÷ total; days late; (actual − budget) ÷ budget | missing | **Introduce** |
| IT & data | Pipeline reliability | IT | On-time runs ÷ scheduled runs × 100 | missing | **Introduce** |
| | Data freshness | IT | Now − latest timestamp (minutes) | untestable on synthetic data | **Introduce** |
| | Telemetry coverage | IT | Same as data completeness | available | **Keep**, merged with completeness |
| | IT incident resolution | IT | Median hours | missing | **Remove** for POC (scope creep) |
| Risk & compliance | Data quality score | company | Checks passed ÷ checks run × 100 | missing: define the check catalogue | **Introduce** |
| | Audit trail completeness | company | Logged events ÷ expected events × 100 | designed, not yet measured | **Introduce** |
| | Open high-severity risks | company | Count | missing: the risk register is the record | **Introduce, reference only** |
| | Control effectiveness | company | Controls effective ÷ tested × 100 | missing | **Introduce** (outside POC) |

## 4. Readiness

- **Production-ready today:** none.
- **Validate first:** data completeness, `curtailed_mwh` (with fallback flagged), and the price source and zone mapping. Every price-based KPI depends on them.
- **Highest-value new KPI:** realised (capture) price.
- **Company-level figures** come from the finance system of record, not from the harness.
- **Owner roles** above are suggestions (ASSUMPTION) and must be confirmed.
