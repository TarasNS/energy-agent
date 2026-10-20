# evals/cases — case format

Golden cases live in one file, [golden.json](golden.json): a list with one case per KPI. The fields and rules are in [EVALS.md](../../EVALS.md) §3. The test that runs them is [tests/test_golden.py](../../tests/test_golden.py).

```json
{
  "id": "G-09",
  "question": "How much energy did the portfolio lose on 7-8 June?",
  "tool": "get_kpi",
  "arguments": {"kpi": "energy_loss", "asset": "portfolio", "start": "2026-06-07", "end": "2026-06-08"},
  "expected": "63.222",
  "unit": "MWh",
  "note": "CHECKED BY HAND. Expected: north 41.897 + 47.966 = 89.863, south 35.749 + 36.059 = 71.808, total 161.671. Actual: north 13.447 + 15.793 = 29.240, south 34.409 + 34.800 = 69.209, total 98.449. 161.671 - 98.449 = 63.222 MWh."
}
```

The note is worked from the raw rows of `harness/dataset.py`, never from tool output or an LLM.

A KPI that must return no number uses `"expected": null` and `"expected_unavailable": "<reason>"`.
