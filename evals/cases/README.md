# evals/cases — case format

One file per case, named `<id>.json`. Proposed shape:

```json
{
  "id": "G-01",
  "kind": "golden",
  "description": "Single asset, positive prices only",
  "fixture": { "production": [], "prices": [] },
  "request": { "threshold_eur": null },
  "expected": {
    "curtailed_mwh": "0.000",
    "economic_value_eur": "0.00"
  },
  "expected_hand_working": "Explain how the expected value was computed (spreadsheet/hand). Never by an LLM.",
  "frozen": false
}
```

`kind` is one of: `golden`, `action-without-approval`, `approved-action-audit`, `malformed-data`, `offline-fallback`, `no-invented-number`, `model-switch-invariance`.

Set `"frozen": true` once the lead approves the case. Frozen cases change only with a recorded formula decision.
