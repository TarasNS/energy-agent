"""The synthetic portfolio (SPEC.md section 2).

SYNTHETIC: not Nordic Solar data. `build(seed)` is deterministic: the same seed
gives the same dict on every run. Standard library only, no network.
"""
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

LABEL = "SYNTHETIC: not Nordic Solar data"
DEFAULT_SEED = 20260601
START = date(2026, 6, 1)
DAYS = 30
PPA_SHARE = 0.5

PARKS = [  # id, name, MW, kWp, outage days
    ("north", "Park North (synthetic)", 10, 10000, 3),
    ("south", "Park South (synthetic)", 8, 8000, 1),
]
BATTERY_USABLE_MWH = Decimal("20")

# "About x %" of 30 days, as fixed counts so every seed meets the spec.
SHORT_LOSS_DAYS = 2  # about 8 %
CURTAILED_DAYS = 6  # about 20 %
NEGATIVE_PRICE_DAYS = 4  # about 15 %
BATTERY_REDUCED_DAYS = 3  # about 10 %


def _dec(value, places):
    """Round half up to `places` and return a decimal string."""
    step = Decimal(1).scaleb(-places)
    return str(Decimal(str(value)).quantize(step, ROUND_HALF_UP))


def _uniform(rng, low, high):
    return Decimal(str(rng.uniform(low, high)))


def _pick(rng, count, exclude=()):
    """`count` distinct day indexes, not in `exclude`."""
    return set(rng.sample([i for i in range(DAYS) if i not in exclude], count))


def _park(rng, days, park_id, name, mw, kwp, outage_count):
    outage = _pick(rng, outage_count)
    short_loss = _pick(rng, SHORT_LOSS_DAYS, exclude=outage)
    curtailed = _pick(rng, CURTAILED_DAYS)
    daily = []
    for i, day in enumerate(days):
        poa = Decimal(_dec(_uniform(rng, 4.2, 6.4), 3))
        expected = Decimal(_dec(Decimal(kwp) * poa * Decimal("0.82") / 1000, 3))
        factor = _uniform(rng, 0.90, 1.06)
        outage_hours = 0
        if i in outage:
            factor = Decimal("0.35")
            outage_hours = rng.randint(10, 13)
        elif i in short_loss:
            outage_hours = rng.randint(1, 3)
        daily.append({
            "date": day,
            "poaKwhM2": str(poa),
            "expectedMwh": str(expected),
            "actualMwh": _dec(expected * factor, 3),
            "availHours": _dec(24 - outage_hours, 0),
            "outageHours": _dec(outage_hours, 0),
            "curtailedMwh": _dec(_uniform(rng, 0.3, 1.2) if i in curtailed else 0, 3),
        })
    return {"id": park_id, "name": name, "kind": "pv", "capacityMw": mw, "nameplateKwp": kwp, "daily": daily}


def _battery(rng, days):
    reduced = _pick(rng, BATTERY_REDUCED_DAYS)
    daily = []
    for i, day in enumerate(days):
        charged = Decimal(_dec(_uniform(rng, 8, 12), 3))
        discharged = Decimal(_dec(charged * _uniform(rng, 0.84, 0.91), 3))
        daily.append({
            "date": day,
            "chargedMwh": str(charged),
            "dischargedMwh": str(discharged),
            "throughputMwh": str(charged + discharged),
            "usableMwh": _dec(BATTERY_USABLE_MWH, 3),
            "availHours": "22" if i in reduced else "24",
        })
    return {"id": "battery", "name": "Battery (synthetic)", "kind": "bess", "capacityMw": 5, "daily": daily}


def _prices(rng, days):
    negative = _pick(rng, NEGATIVE_PRICE_DAYS)
    return [
        {"date": day, "meanPrice": _dec(_uniform(rng, -16, -4) if i in negative else _uniform(rng, 38, 68), 2)}
        for i, day in enumerate(days)
    ]


def build(seed=DEFAULT_SEED):
    """Return the synthetic portfolio dict, 1 to 30 June 2026."""
    rng = random.Random(seed)
    days = [(START + timedelta(days=i)).isoformat() for i in range(DAYS)]
    assets = [_park(rng, days, *park) for park in PARKS]
    assets.append(_battery(rng, days))
    return {
        "label": LABEL,
        "period": {"start": days[0], "end": days[-1], "days": DAYS},
        "days": days,
        "assets": assets,
        "prices": _prices(rng, days),
        "ppa": {"shareOfExpected": PPA_SHARE},
    }
