"""A tiny hand-made portfolio with the SPEC.md section 2 shape, 1 to 8 June 2026.

Round values so every expected KPI in the tests can be worked out by hand:
- north: 10 MW, 10 000 kWp. Every day POA 5.000, expected 40.000, actual 36.000,
  except 06-02 (outage: actual 14.000, 12 h out) and 06-03 (0.500 MWh curtailed).
- south: 8 MW, 8 000 kWp. Every day POA 5.000, expected 32.000, actual 32.000, no outage.
- battery: every day charged 10.000, discharged 8.800, usable 20.000, 24 h; 06-05 has 22 h.
- prices: 50.00 every day, -10.00 on 06-04.
"""
import pytest

DAYS = [f"2026-06-0{i}" for i in range(1, 9)]


def _north(day):
    outage = day == "2026-06-02"
    return {"date": day, "poaKwhM2": "5.000", "expectedMwh": "40.000",
            "actualMwh": "14.000" if outage else "36.000",
            "availHours": "12" if outage else "24", "outageHours": "12" if outage else "0",
            "curtailedMwh": "0.500" if day == "2026-06-03" else "0.000"}


def _south(day):
    return {"date": day, "poaKwhM2": "5.000", "expectedMwh": "32.000", "actualMwh": "32.000",
            "availHours": "24", "outageHours": "0", "curtailedMwh": "0.000"}


def _battery(day):
    return {"date": day, "chargedMwh": "10.000", "dischargedMwh": "8.800", "throughputMwh": "18.800",
            "usableMwh": "20.000", "availHours": "22" if day == "2026-06-05" else "24"}


def tiny_portfolio():
    return {
        "label": "SYNTHETIC: not Nordic Solar data",
        "period": {"start": DAYS[0], "end": DAYS[-1], "days": len(DAYS)},
        "days": list(DAYS),
        "assets": [
            {"id": "north", "name": "Park North (test)", "kind": "pv", "capacityMw": 10, "nameplateKwp": 10000,
             "daily": [_north(d) for d in DAYS]},
            {"id": "south", "name": "Park South (test)", "kind": "pv", "capacityMw": 8, "nameplateKwp": 8000,
             "daily": [_south(d) for d in DAYS]},
            {"id": "battery", "name": "Battery (test)", "kind": "bess", "capacityMw": 5,
             "daily": [_battery(d) for d in DAYS]},
        ],
        "prices": [{"date": d, "meanPrice": "-10.00" if d == "2026-06-04" else "50.00"} for d in DAYS],
        "ppa": {"shareOfExpected": 0.5},
    }


@pytest.fixture
def tiny():
    return tiny_portfolio()
