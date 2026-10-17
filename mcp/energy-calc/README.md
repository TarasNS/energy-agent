# mcp/energy-calc — deterministic calculations (calculator of record)

**Owner:** Dev 4 · **Status:** not implemented · **Formula:** [EVALS.md §2](../../EVALS.md#2-formula-v1)

## Interface
```python
calculate_curtailment_value(
    production: list[ProductionInterval],
    prices: list[MarketPriceInterval],
    threshold_eur: str | None = None,
) -> dict  # the `calculation` object in schemas/review-result.schema.json
```
Returns portfolio totals per bucket (lost revenue, grid-operator lost, avoided negative cost, negative-price exposure), the same per asset in `by_asset`, `economic_value_eur` (headline = portfolio negative-price exposure), `assumptions`, `input_hash`, `calculation_version`.

## Rules
- Pure functions. No I/O, no clock, no randomness, no network, no model calls.
- `decimal.Decimal` throughout; round once at the end; return decimal strings.
- Read `interval_minutes` from each row (15 for DK1).
- Malformed input raises a clear error. It never returns a partial number.
- Golden cases live as pytest tests in `mcp/energy-calc/tests/`.

Claude may explain the calculation. Claude is not the calculator of record.
