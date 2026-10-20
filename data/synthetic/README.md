# data/synthetic

**Everything in this folder is synthetic.** It is made up by code. It is not Nordic Solar data, not market data and not a forecast. Every result carries the label `SYNTHETIC: not Nordic Solar data`.

Owner: Dev 2. Contract: [SPEC.md](../../SPEC.md) section 2.

## What it holds

[portfolio.py](portfolio.py) builds one made-up portfolio for 1 to 30 June 2026:

| Asset | Kind | Size | Notes |
|---|---|---|---|
| `north` | PV park | 10 MW, 10 000 kWp | 3 outage days |
| `south` | PV park | 8 MW, 8 000 kWp | 1 outage day |
| `battery` | BESS | 5 MW, 20 MWh usable | |

It also holds one day-ahead price per day (about 15 % of days are negative) and a PPA share of 0.5 of expected volume. The PPA share is a demo assumption.

## Use it

```python
from data.synthetic.portfolio import build

portfolio = build()            # seed 20260601
other = build(seed=7)          # different seed, different numbers
```

- The same seed gives the same data on every run. There is no network and no file read.
- Energy, prices and hours are decimal strings: MWh and POA 3 places, EUR/MWh 2 places, hours 0 places. Round half up.
- Outage days are fixed in number per park. Short losses, curtailment, negative prices and reduced battery hours are fixed counts that match the "about" shares in SPEC.md.

## Test it

```bash
python -m pytest data/synthetic
```

[test_portfolio.py](test_portfolio.py) checks the shape, 30 days, same seed same data, different seed different data, the ranges in SPEC.md and the outage days per park.
