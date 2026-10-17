# mcp/energy-data — market and context data (read-only)

**Owner:** Dev 1 · **Status:** not implemented · **Contract:** [`schemas/market-price.schema.json`](../../schemas/market-price.schema.json)

## POC interface (proposed)
```python
get_day_ahead_prices(zone: str, month: str) -> list[MarketPriceInterval]
```
- Reads fixtures from `data/synthetic/`.
- No write functions. No network in synthetic mode.

## Stretch
Live retrieval from Energi Data Service or ENTSO-E, **always** with fixture fallback when the call fails or `ENERGY_DATA_MODE=synthetic`.

## Must not
Calculate EUR values, cache to shared files, or require a network connection for the demo.
