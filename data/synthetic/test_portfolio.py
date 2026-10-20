"""Tests for data/synthetic/portfolio.py (SPEC.md section 2)."""
import ast
import re
import socket
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

from data.synthetic.portfolio import build

LABEL = "SYNTHETIC: not Nordic Solar data"
DAYS = [(date(2026, 6, 1) + timedelta(days=i)).isoformat() for i in range(30)]
PV_KEYS = {"date", "poaKwhM2", "expectedMwh", "actualMwh", "availHours", "outageHours", "curtailedMwh"}
BESS_KEYS = {"date", "chargedMwh", "dischargedMwh", "throughputMwh", "usableMwh", "availHours"}
TOL = Decimal("0.001")  # ratios are computed from rounded strings


def d(text):
    assert isinstance(text, str), f"expected a decimal string, got {type(text).__name__}: {text!r}"
    return Decimal(text)


def decimals(text, places):
    pattern = r"^-?\d+$" if places == 0 else rf"^-?\d+\.\d{{{places}}}$"
    return isinstance(text, str) and re.match(pattern, text) is not None


def asset(data, asset_id):
    return next(a for a in data["assets"] if a["id"] == asset_id)


@pytest.fixture(scope="module")
def data():
    return build()


# 1. shape ---------------------------------------------------------------

def test_top_level_shape(data):
    assert set(data) == {"label", "period", "days", "assets", "prices", "ppa"}
    assert data["period"] == {"start": "2026-06-01", "end": "2026-06-30", "days": 30}
    assert data["ppa"] == {"shareOfExpected": 0.5}


def test_assets_shape(data):
    assert [(a["id"], a["kind"]) for a in data["assets"]] == [("north", "pv"), ("south", "pv"), ("battery", "bess")]
    north, south, battery = (asset(data, i) for i in ("north", "south", "battery"))
    assert (north["name"], north["capacityMw"], north["nameplateKwp"]) == ("Park North (synthetic)", 10, 10000)
    assert (south["name"], south["capacityMw"], south["nameplateKwp"]) == ("Park South (synthetic)", 8, 8000)
    assert (battery["name"], battery["capacityMw"]) == ("Battery (synthetic)", 5)
    for park in (north, south):
        assert all(set(row) == PV_KEYS for row in park["daily"])
    assert all(set(row) == BESS_KEYS for row in battery["daily"])
    assert all(set(row) == {"date", "meanPrice"} for row in data["prices"])


def test_label_says_synthetic(data):
    assert data["label"] == LABEL


def test_values_are_decimal_strings(data):
    for park_id in ("north", "south"):
        for row in asset(data, park_id)["daily"]:
            for key in ("poaKwhM2", "expectedMwh", "actualMwh", "curtailedMwh"):
                assert decimals(row[key], 3), (park_id, key, row[key])
            for key in ("availHours", "outageHours"):
                assert decimals(row[key], 0), (park_id, key, row[key])
    for row in asset(data, "battery")["daily"]:
        for key in ("chargedMwh", "dischargedMwh", "throughputMwh", "usableMwh"):
            assert decimals(row[key], 3), key
        assert decimals(row["availHours"], 0)
    assert all(decimals(row["meanPrice"], 2) for row in data["prices"])


# 2. thirty days --------------------------------------------------------

def test_thirty_days_of_june_2026(data):
    assert data["days"] == DAYS
    for a in data["assets"]:
        assert [row["date"] for row in a["daily"]] == DAYS
    assert [row["date"] for row in data["prices"]] == DAYS


# 3. determinism --------------------------------------------------------

def test_same_seed_same_data():
    assert build(seed=7) == build(seed=7)
    assert build() == build(seed=20260601)


def test_different_seed_different_data():
    assert build(seed=1) != build(seed=2)
    assert build(seed=1) != build()


def test_no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    build(seed=3)
    tree = ast.parse((Path(__file__).parent / "portfolio.py").read_text(encoding="utf-8"))
    imported = {
        (n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
        for n in ast.walk(tree)
        if isinstance(n, (ast.Import, ast.ImportFrom))
        for a in (n.names if isinstance(n, ast.Import) else [n])
    }
    assert not imported & {"socket", "urllib", "http", "requests", "httpx", "aiohttp", "numpy", "pandas"}


# 4. ranges -------------------------------------------------------------

@pytest.mark.parametrize("seed", [20260601, 1, 99])
@pytest.mark.parametrize("park_id,kwp", [("north", 10000), ("south", 8000)])
def test_park_values_in_range(seed, park_id, kwp):
    for row in asset(build(seed=seed), park_id)["daily"]:
        poa, expected, actual = d(row["poaKwhM2"]), d(row["expectedMwh"]), d(row["actualMwh"])
        assert Decimal("4.2") <= poa <= Decimal("6.4")
        want = (Decimal(kwp) * poa * Decimal("0.82") / 1000).quantize(Decimal("0.001"), ROUND_HALF_UP)
        assert expected == want
        outage = d(row["outageHours"])
        ratio = actual / expected
        if outage >= 10:
            assert abs(ratio - Decimal("0.35")) <= TOL
        else:
            assert Decimal("0.90") - TOL <= ratio <= Decimal("1.06") + TOL
        assert d(row["availHours"]) == 24 - outage
        curtailed = d(row["curtailedMwh"])
        assert curtailed == 0 or Decimal("0.3") <= curtailed <= Decimal("1.2")


@pytest.mark.parametrize("seed", [20260601, 1, 99])
def test_battery_values_in_range(seed):
    for row in asset(build(seed=seed), "battery")["daily"]:
        charged, discharged = d(row["chargedMwh"]), d(row["dischargedMwh"])
        assert Decimal("8") <= charged <= Decimal("12")
        assert Decimal("0.84") - TOL <= discharged / charged <= Decimal("0.91") + TOL
        assert d(row["throughputMwh"]) == charged + discharged
        assert d(row["usableMwh"]) == 20
        assert row["availHours"] in ("24", "22")


@pytest.mark.parametrize("seed", [20260601, 1, 99])
def test_prices_in_range(seed):
    prices = [d(row["meanPrice"]) for row in build(seed=seed)["prices"]]
    for p in prices:
        assert Decimal("38") <= p <= Decimal("68") or Decimal("-16") <= p <= Decimal("-4")
    assert 2 <= sum(p < 0 for p in prices) <= 7  # about 15 % of 30 days


def test_about_counts_of_rare_days(data):
    for park_id in ("north", "south"):
        daily = asset(data, park_id)["daily"]
        short_loss = [r for r in daily if 1 <= d(r["outageHours"]) <= 3]
        curtailed = [r for r in daily if d(r["curtailedMwh"]) > 0]
        assert 1 <= len(short_loss) <= 4  # about 8 %
        assert 3 <= len(curtailed) <= 9  # about 20 %
    reduced = [r for r in asset(data, "battery")["daily"] if r["availHours"] == "22"]
    assert 1 <= len(reduced) <= 6  # about 10 %


# 5. outage days sit on the right parks ---------------------------------

@pytest.mark.parametrize("seed", [20260601, 1, 99])
def test_outage_days_on_the_right_parks(seed):
    data = build(seed=seed)
    outage_days = {}
    for park_id, count in (("north", 3), ("south", 1)):
        rows = [r for r in asset(data, park_id)["daily"] if d(r["outageHours"]) >= 10]
        assert len(rows) == count, (park_id, len(rows))
        assert all(10 <= d(r["outageHours"]) <= 13 for r in rows)
        outage_days[park_id] = {r["date"] for r in rows}
        for r in asset(data, park_id)["daily"]:
            if r["date"] not in outage_days[park_id]:
                assert d(r["outageHours"]) <= 3  # no hidden outage day
    battery = asset(data, "battery")["daily"]
    assert all("outageHours" not in r for r in battery)
