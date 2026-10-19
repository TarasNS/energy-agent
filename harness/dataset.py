"""Seeded synthetic portfolio: a line-by-line port of tools/kpi-lab/data.js.

SYNTHETIC: not Nordic Solar data. The RNG call order and the rounding must
match the JavaScript exactly, so both versions give the same numbers.
"""

import math
from datetime import date, timedelta

_MASK = 2**32


def _rng(seed):
    # JS: let s = seed >>> 0; s = (s * 1664525 + 1013904223) >>> 0; return s / 2**32
    s = seed % _MASK

    def next_value():
        nonlocal s
        s = (s * 1664525 + 1013904223) % _MASK
        return s / 4294967296

    return next_value


def _round(v, d):
    # JS Math.round(v * f) / f rounds halves toward +infinity; Python round() does not.
    f = 10.0**d
    return math.floor(v * f + 0.5) / f


def _dates(n):
    start = date(2026, 6, 1)  # synthetic month: June 2026
    return [(start + timedelta(days=i)).isoformat() for i in range(n)]


def build(seed=20260601):
    r = _rng(seed)
    days = _dates(30)
    pv = [
        {"id": "north", "name": "Park North (synthetic)", "capacityMw": 10, "nameplateKwp": 10000, "outageDays": [6, 7, 19]},
        {"id": "south", "name": "Park South (synthetic)", "capacityMw": 8, "nameplateKwp": 8000, "outageDays": [12]},
    ]

    assets = []
    for p in pv:
        daily = []
        for i, d in enumerate(days):
            poa = 4.2 + r() * 2.2  # kWh/m2 per day, plausible June range
            expected_mwh = (p["nameplateKwp"] * poa * 0.82) / 1000  # expected yield baseline (synthetic model)
            factor = 0.9 + r() * 0.16
            actual_mwh = expected_mwh * factor
            outage_hours = 0
            if r() < 0.08:
                outage_hours = 1 + math.floor(r() * 3)
            if i in p["outageDays"]:
                outage_hours = 10 + math.floor(r() * 4)
                actual_mwh *= 0.35
            curtailed_mwh = 0
            if r() < 0.2:
                curtailed_mwh = 0.3 + r() * 0.9
            daily.append(
                {
                    "date": d,
                    "poaKwhM2": _round(poa, 2),
                    "expectedMwh": _round(expected_mwh, 3),
                    "actualMwh": _round(actual_mwh, 3),
                    "availHours": 24 - outage_hours,
                    "outageHours": outage_hours,
                    "curtailedMwh": _round(curtailed_mwh, 3),
                }
            )
        assets.append({**p, "kind": "pv", "daily": daily})

    prices = []
    for d in days:
        base = 38 + r() * 30
        negative = r() < 0.15
        price = -4 - r() * 12 if negative else base
        prices.append({"date": d, "meanPrice": _round(price, 2)})

    bess_daily = []
    for d in days:
        usable = 20
        charged = 8 + r() * 4
        rte = 0.84 + r() * 0.07
        discharged = charged * rte
        avail_hours = 24 if r() < 0.9 else 24 - 2
        bess_daily.append(
            {
                "date": d,
                "chargedMwh": _round(charged, 3),
                "dischargedMwh": _round(discharged, 3),
                "throughputMwh": _round(charged + discharged, 3),
                "usableMwh": usable,
                "availHours": avail_hours,
            }
        )

    return {
        "label": "SYNTHETIC: not Nordic Solar data",
        "period": {"start": days[0], "end": days[-1], "days": len(days)},
        "days": days,
        "assets": assets
        + [{"id": "battery", "name": "Battery (synthetic)", "kind": "bess", "capacityMw": 5, "daily": bess_daily}],
        "prices": prices,
        "ppa": {"shareOfExpected": 0.5},  # ASSUMPTION for the demo: half of expected volume is under a PPA
    }
