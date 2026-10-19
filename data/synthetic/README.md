# data/synthetic — demo fixtures

**Owner:** Dev 4 · **Status:** starter fixture generated, **not frozen** · All data is synthetic. No real company data, ever.

## What is here
```text
data/synthetic/
├── generate.py                       seeded generator (stdlib only) — the source of truth
└── demo-solar-dk/
    ├── assets.json                   3 fictional DK1 solar parks (48, 30, 12 MW)
    ├── production-2026-06.jsonl      8,640 rows: 15-minute available / actual / curtailed MWh
    └── prices-DK1-2026-06.jsonl      2,880 rows: 15-minute day-ahead prices, EUR/MWh
```

Try it:
```bash
python data/synthetic/generate.py --summary   # what is in it (MWh and counts only)
python data/synthetic/generate.py             # regenerate (same seed → identical files)
```

## Why 15 minutes
The European day-ahead market, DK1 included, moved to a 15-minute market time unit from delivery day 1 October 2025. June 2026 data is therefore 15-minute. The calc must handle `interval_minutes` from the row, never assume 60.

## Scenarios built in
| Asset | What happens in June 2026 | Exercises |
|---|---|---|
| `dk1-solar-01` | Self-curtails 95 % in negative-price intervals; grid operator limits it to 40 % of capacity on 10 and 23 June, 10:00–14:00 UTC | `negative_price` and `grid_operator` reasons |
| `dk1-solar-02` | Self-curtails at negative prices; inverter fault on 17 June, 07:00–13:00 UTC (30 % loss) | `technical` reason |
| `dk1-solar-03` | **No** negative-price curtailment: keeps producing into negative prices. Rows omit `curtailed_mwh` | The demo's decision; derivation path (G-04) |

Price shape: morning and evening peaks, a solar-driven midday dip, about 22 hours of negative prices concentrated on sunny weekends. Yield is about 165 MWh per MW for the month.

## Rules
- **Inputs only.** The generator never computes EUR. Golden values are worked out by hand (EVALS.md §2).
- Dev 4 reviews the scenarios with an energy colleague, then sets `frozen` in the decision log. After that, changing a file changes golden values → tell the lead.
- Optional upgrade: replace the synthetic price curve with real public DK1 prices from Energi Data Service for June 2025, frozen as a fixture. More credible, still offline.
