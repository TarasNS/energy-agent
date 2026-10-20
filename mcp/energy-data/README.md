# mcp/energy-data: day-ahead price reader

**Owner:** Dev 1 · **Status:** not built · **Task:** [Dev 1 page](../../docs/developer-1.html)

Read-only. Reads the DK1 price fixture and returns prices as decimal strings. It is not connected to the chat in the POC; the chat's `get_prices` tool reads the synthetic portfolio.

## Interface
```python
get_day_ahead_prices(zone: str, month: str) -> list[dict]
# [{"date": "2026-06-01", "mean_price_eur_mwh": "41.20", "negative": False}, ...]
```

## Rules
1. Read `data/synthetic/demo-solar-dk/prices-DK1-2026-06.jsonl`. No network.
2. Each row has `interval_minutes`. Use it. Never assume 60.
3. Rows must validate against [`schemas/market-price.schema.json`](../../schemas/market-price.schema.json). Reject bad rows with a clear error.
4. Prices cross the boundary as strings, never floats.
5. Put the code in `mcp/energy-data/energy_data/` and tests in `mcp/energy-data/tests/`. Do not create `mcp/__init__.py`.
