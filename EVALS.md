# EVALS.md: what "correct" means

**Owner:** Dev 2 · **Role:** defines how we prove the numbers are right. The calculator is `mcp/kpi-solar`; the model is never the calculator of record.

## 1. Three layers of proof

| Layer | Question it answers | Where | Status |
|---|---|---|---|
| Formula tests | Does each KPI function return the hand-worked value, and refuse bad input? | `mcp/kpi-solar/tests/` | Task #5 (Dev 2) |
| Golden cases | Does each tool, with no model, return the hand-worked value for the demo data? | `evals/cases/golden.json`, `tests/test_golden.py` | Task #19 (Dev 2), also through the live server |
| Number check | Is a number the tools never returned always withheld? | `tests/test_number_check.py` | Task #12 (Dev 1) |

## 2. Rules for a golden case

1. One case per KPI (the 13 in [SPEC.md §3](SPEC.md)).
2. Fields: `id`, `question`, `tool`, `arguments`, `expected` (decimal string), `unit`, `note`.
3. The expected value is worked out **by hand** from the fixture in `data/synthetic/`. The `note` shows the working. At least three are checked by hand before anyone trusts the code output.
4. Compared exactly, as strings. No tolerance.
5. A golden value changes only with the lead's approval.

## 3. Rules for the number check

- A number in the answer must appear in the question or in a tool result.
- The same value written differently (`12.5` and `12.50`) passes.
- Years, dates and small counts must not cause false alarms.
- A failed check withholds the text. Charts and tool results still show.

## 4. After the POC

- An eval runner (`evals/run.py`, `make eval`) with a score per question set.
- Scripted-model tests for every standard question: right tool, right KPI.
- Real data: a KPI is production-ready only with trusted data, a validated formula and a named owner. See [KPI_REVIEW.md](KPI_REVIEW.md).
