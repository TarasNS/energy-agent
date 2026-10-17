# mcp/portfolio — portfolio and production data (read-only)

**Owner:** Dev 3 · **Status:** not implemented · **Contracts:** [`asset`](../../schemas/asset.schema.json), [`production`](../../schemas/production.schema.json)

## POC interface (proposed)
```python
list_assets(portfolio_id: str) -> list[Asset]
get_production(asset_ids: list[str], month: str) -> list[ProductionInterval]
```
- Reads fixtures from `data/synthetic/`.
- Validates fixture rows against the schemas and fails loudly on malformed data.

## Adapter boundary
Company adapters (CSV export, data platform, ERP) are future work. They implement the same two functions and live beside the synthetic adapter; the workflow does not change.

## Stretch
Data-class ceiling: refuse assets whose `data_class` exceeds the active model profile's allowance.

## Must not
Write anything, compute EUR values, or reach production systems.
