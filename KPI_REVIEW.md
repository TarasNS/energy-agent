# KPI_REVIEW.md — validated KPIs for four groups

**Status:** the 13 formulas are merged in `mcp/kpi-solar` ([SPEC.md §3](SPEC.md)); the definitions below are their reference. **No source data is verified yet**, so no KPI is production-ready.

**Verdict key:** KEEP = use as defined · MODIFY = use with the change shown · REMOVE = drop as a separate KPI.

Formulas are in `mcp/kpi-solar/` (Dev 2; definitions in [SPEC.md §3](SPEC.md)). A missing input returns "unavailable", never a number.

## 1. Solar generation

| KPI | Relevance to operations | Formula (code) | Inputs | Authoritative source (type) | Data sufficient? | Verdict |
|---|---|---|---|---|---|---|
| Actual vs expected generation | Shows underperformance by site and period | actual ÷ expected × 100 | metered MWh; validated expected MWh | Revenue-grade meter; approved expected-yield model | No: no validated expected baseline | KEEP. Define the expected model before use |
| Performance ratio | Plant health, degradation, and whether losses are weather or plant | actual kWh ÷ (POA irradiation kWh/m² × nameplate kWp) × 100 | metered kWh; POA irradiation; nameplate kWp | Metered output; plane-of-array irradiance sensor | No: no POA sensor data | KEEP. Needs a sensor source |
| Availability | Revenue protection; separates plant faults from weather | available hours ÷ period hours × 100 | inverter or plant status | SCADA status history | No: no status feed | MODIFY. State the daylight definition |
| Capacity factor | Compares sites; not an operational target on its own | MWh ÷ (capacity MW × period hours) × 100 | metered MWh; capacity | Metered output; asset register | Partly: needs the asset register | KEEP. State DC or AC basis |

## 2. Energy commercial

| KPI | Relevance | Formula (code) | Inputs | Authoritative source | Data sufficient? | Verdict |
|---|---|---|---|---|---|---|
| PPA performance | Contract compliance and penalty exposure | delivered MWh ÷ contracted MWh × 100 | delivered MWh; contracted volume | Signed PPA; metered output | No: contract terms not available | KEEP. Terms must come from the contract, not assumed |
| Merchant price exposure | Revenue risk on unhedged volume | merchant MWh × price move (EUR) | merchant MWh; price move | Position record; forward curve | No | MODIFY. Define as a sensitivity (EUR per EUR/MWh move), not a forecast |
| Realised (capture) price | Links output, curtailment and price in one number; the most decision-relevant commercial KPI | Σ(MWh_i × price_i) ÷ Σ MWh_i | metered 15-minute MWh; day-ahead price | Metered output; licensed market price feed | No: needs both | KEEP (priority). Refuses partial results |

## 3. Asset operations

| KPI | Relevance | Formula (code) | Inputs | Authoritative source | Data sufficient? | Verdict |
|---|---|---|---|---|---|---|
| Downtime | O&M priority; lost energy | hours of OUTAGE intervals × interval length; unknown status codes rejected | interval status codes; interval length | SCADA alarms; plant status | No: no status feed | KEEP |
| Energy losses | Shows how much output was lost, and to what | expected MWh − actual MWh | expected and actual MWh | Expected model; meter | No: no expected baseline | KEEP. Attribution to causes is a later step |
| Incident resolution | Service level for O&M | median hours, open to close | ticket open and close times | Ticket or work-order system | No: no ticket data | KEEP. Use median and P90, not mean |
| Asset performance | Overlaps with performance ratio and availability | none | — | — | — | REMOVE as a separate KPI. Use performance ratio and availability |

## 4. Battery energy storage (BESS)

| KPI | Relevance | Formula (code) | Inputs | Authoritative source | Data sufficient? | Verdict |
|---|---|---|---|---|---|---|
| BESS availability | Revenue and capacity protection | available ÷ period hours × 100 (same as plant) | BMS or SCADA status | BMS and SCADA history | No: no BESS data | KEEP. Exclude derated states |
| Round-trip efficiency | Performance and degradation | discharged MWh ÷ charged MWh × 100 | metered energy both sides, same period | Meters on charge and discharge; auxiliary load data | No | KEEP. Auxiliary loads must be stated |
| Cycle utilisation | Degradation and warranty | throughput ÷ (2 × usable MWh) × 100 (one full equivalent cycle = 100) | throughput MWh; usable energy | BMS throughput; rated usable energy | No | KEEP. State the cycle convention |

## 5. Missing metrics essential for these four groups

| Missing metric or input | Why it is needed | Where it would come from |
|---|---|---|
| Expected generation baseline | Actual vs expected, energy losses | Approved expected-yield model, validated against measured data |
| Plane-of-array irradiation | Performance ratio | Irradiance sensor or validated irradiance data |
| Plant and inverter status history | Availability, downtime | SCADA historian (read-only export) |
| Outage and incident log with times | Downtime attribution, incident resolution | Ticket or work-order system |
| PPA contract terms (volume, price, penalties) | PPA performance | Signed agreements |
| BESS state of charge, charge and discharge meters, auxiliary load | BESS KPIs | BMS and revenue-grade meters |
| Day-ahead prices for the metered period | Realised price, merchant exposure | Licensed market data |

## 6. Summary

- **Keep:** actual vs expected, performance ratio, availability, capacity factor, PPA performance, realised price, downtime, energy losses, incident resolution, the three BESS KPIs.
- **Modify:** availability (daylight definition), merchant exposure (sensitivity), and every KPI that needs a validated baseline before use.
- **Remove:** asset performance as a separate KPI.
- **Verified data available today:** none. The formulas are tested on hand-computed examples on synthetic data only.
