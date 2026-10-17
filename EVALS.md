# EVALS.md — Golden Truth

**Owner:** Dev 4 · **Status:** formula v1 proposed; confirm with an energy colleague before the hackathon
**Role in the chain:** defines what "correct" means and how the POC proves it. Code lives in [`mcp/energy-calc/`](mcp/energy-calc/).

> Claude may explain the calculation. Claude is not the calculator of record.
> **No golden EUR value may ever be produced by an LLM.** Golden values are computed by hand or in a spreadsheet, then frozen.

## 1. Principles
1. Exact equality on decimal strings. No tolerance for EUR.
2. Every golden case has a stable ID, a small fixture, an expected output and its hand working.
3. In the POC, golden cases run as plain pytest tests in `mcp/energy-calc/tests/` via `make test`. No separate eval runner.

## 2. Formula v1

Per asset, per market interval `i` (15 minutes for DK1 since 1 October 2025; read `interval_minutes` from the row, never assume 60):

```text
curtailed_i = curtailed_mwh                      if present
            = max(available_mwh − actual_mwh, 0)  otherwise

lost_revenue_eur            = Σ curtailed_i × price_i     where price_i > 0 and reason ≠ grid_operator
grid_operator_lost_eur      = Σ curtailed_i × price_i     where price_i > 0 and reason = grid_operator   (may be compensated by the TSO)
avoided_negative_cost_eur   = Σ curtailed_i × |price_i|   where price_i < 0   (self-curtailment saved this)
negative_price_exposure_eur = Σ actual_i × |price_i|      where price_i < 0   (paid to produce — the decision metric)
```

The **headline** (`economic_value_eur`) is `negative_price_exposure_eur` for the portfolio. Results are also returned per asset, so the recommendation can name the asset. `threshold_exceeded` is true when an asset's exposure is above `threshold_eur`.

Rounding: `Decimal` throughout, round once at the end, ROUND_HALF_UP; 2 decimals for EUR, 3 for MWh.

Why this shape: the three causes have different economics. Self-curtailment at negative prices *saves* money, grid-operator curtailment *may be compensated*, and producing into negative prices *costs* money. One blended number would be challenged by any energy expert.

Hand-worked illustration (not a golden case):

| Interval | Situation | MWh | Price EUR/MWh | Result |
|---|---|---:|---:|---|
| 1 | grid operator curtails | 0.500 curtailed | 50.00 | grid_operator_lost 25.00 |
| 2 | self-curtails at negative price | 0.400 curtailed | −10.00 | avoided 4.00 |
| 3 | produces into negative price | 0.300 actual | −20.00 | exposure 6.00 |

## 3. Golden cases for the POC

Work these out by hand **before the hackathon**. Turn them into case files and tests during the session.

| ID | Scenario | Proves |
|---|---|---|
| G-01 | One asset, all four situations above, a handful of intervals | Every bucket and its sign |
| G-02 | `curtailed_mwh` missing; derived from available − actual, clamped at 0 | Derivation path |
| G-03 | Malformed row (missing price) | Clear error, no number |
| G-07 | Demo fixture: `demo-solar-dk`, DK1, 2026-06 | The exact numbers the presenter says |

G-07 needs a spreadsheet over the fixture files (sum the 15-minute rows per bucket). Do it once, before the hackathon, and freeze it.

## 4. After the POC: EnergyBench-Lite

Not built in the hackathon session. When the POC works, extend in this order:

| # | Eval | Checks |
|---|---|---|
| 1 | `action-without-approval` | Missing, wrong or reused token executes nothing (already covered by Dev 2's unit tests in the POC) |
| 2 | `approved-action-audit` | Approval writes the audit lines |
| 3 | `offline-fallback` | The agent loop completes with the network off |
| 3b | `calc-is-called` | A review where the model skips the calculator fails |
| 4 | `no-invented-number` | Every number in the explanation appears in the calc result (POC version on the offline trace: T4.3) |
| 5 | `model-switch-invariance` | Two profiles → identical calc result |

Runner: `evals/run.py` behind `make eval`.
