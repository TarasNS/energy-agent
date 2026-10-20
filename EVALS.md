# EVALS.md: what "correct" means

**Owner:** Dev 4 · **Role:** defines how we prove the numbers are right. The calculator is `mcp/kpi-solar`; the model is never the calculator of record.

## 1. Three layers of proof

| Layer | Question it answers | Where | Status |
|---|---|---|---|
| Formula tests | Does each KPI function return the hand-worked value, and refuse bad input? | `mcp/kpi-solar/tests/` | Done (31 tests) |
| Golden cases | Does each tool, with no model, return the hand-worked value for the demo data? | [evals/cases/golden.json](evals/cases/golden.json), [tests/test_golden.py](tests/test_golden.py) | Done (13 cases) |
| Number check | Is a number the tools never returned always withheld? | `tests/test_number_check.py` | Dev 4, task 2 |

## 2. Golden cases

One case per KPI in `harness/energy_tools.py`. Each one calls `get_kpi` over the synthetic portfolio (`harness/dataset.py`, seed `20260601`, June 2026) for a 1 or 2 day window. The windows are short on purpose: every raw input fits in the `note`, so a person can redo the sum on paper.

| Id | KPI | Asset | Window (June 2026) | Expected | Hand-checked |
|---|---|---|---|---|---|
| G-01 | actual_vs_expected | portfolio | 1–2 | 92.7 % | |
| G-02 | performance_ratio | north | 3 | 81.5 % | |
| G-03 | availability | portfolio | 7–8 (North outage) | 74.0 % | ✔ |
| G-04 | capacity_factor | south | 4 | 20.7 % | |
| G-05 | ppa_delivery | south | 2 | 95.6 % | |
| G-06 | realised_price | portfolio | 1–2 (1 June is negative-price) | 18.17 EUR/MWh | |
| G-07 | merchant_exposure | portfolio | 1–2 | 680.38 EUR | |
| G-08 | downtime | north | 7–8 | 25.00 h | ✔ |
| G-09 | energy_loss | portfolio | 7–8 | 63.222 MWh | ✔ |
| G-10 | incident_resolution | portfolio | 1–30 | unavailable: no tickets | |
| G-11 | bess_availability | battery | 1–2 | 95.8 % | |
| G-12 | bess_round_trip | battery | 1–2 | 85.8 % | ✔ |
| G-13 | bess_cycle_utilisation | battery | 1–2 | 46.8 % | |

Every case was worked from the raw dataset rows, then the arithmetic was re-run with Python `Decimal` (no project code imported) before the tool output was compared. The four ✔ cases say `CHECKED BY HAND` in their note.

What the test checks (`tests/test_golden.py`):

1. Each case runs through the same `ToolRegistry.execute` the agent uses. No model is involved.
2. The returned `value` equals `expected` as a string, and `unit` matches. No tolerance.
3. For G-10 the value is `null` and the `unavailable` reason matches. The right answer is "no number".
4. The cases cover exactly the KPI ids in `KPIS`, and every case has a note.

Run: `python -m pytest tests/test_golden.py` (also part of `make test`).

## 3. Rules for a golden case

1. Fields: `id`, `question`, `tool`, `arguments`, `expected` (decimal string, or `null` with `expected_unavailable`), `unit`, `note`.
2. The expected value is worked out **by hand** from `harness/dataset.py`, never copied from tool output. The `note` shows the working.
3. Pick windows with no rounding tie (a 5 in the first dropped digit), so the result does not depend on float representation. See G-05.
4. If the tool and the hand value disagree, find out which is wrong. Never edit the expected value to match the tool.
5. A golden value changes only with the lead's approval.

## 4. Rules for the number check

- A number in the answer must appear in the question or in a tool result.
- The same value written differently (`12.5` and `12.50`) passes.
- Years, dates and small counts must not cause false alarms.
- A failed check withholds the text. Charts and tool results still show.

## 5. After the POC

- An eval runner (`evals/run.py`, `make eval`) with a score per question set.
- Scripted-model tests for every standard question: right tool, right KPI. The `question` field in each golden case is the seed for these.
- Golden cases for `compare_kpi` and the full-month default window.
- Real data: a KPI is production-ready only with trusted data, a validated formula and a named owner. See [KPI_REVIEW.md](KPI_REVIEW.md).
