"""The nine tools (SPEC.md section 5) on the tiny hand-made portfolio in conftest.py.

Expected values are worked out by hand from the conftest.py numbers.
"""
import json
import re
from pathlib import Path

import jsonschema
import pytest

from harness.energy_tools import build_registry

NINE = ["list_assets", "list_kpis", "get_kpi", "compare_kpi", "get_series",
        "get_prices", "get_events", "make_chart", "propose_action"]
SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def call(reg, name, **args):
    out = reg.run(name, args)
    assert isinstance(out, str)
    return json.loads(out)


def no_floats(value):
    if isinstance(value, float):
        return False
    if isinstance(value, dict):
        return all(no_floats(v) for v in value.values())
    if isinstance(value, list):
        return all(no_floats(v) for v in value)
    return True


@pytest.fixture
def reg(tiny):
    return build_registry(tiny)


def kpi(reg, name, asset="portfolio", **dates):
    row = call(reg, "get_kpi", kpi=name, asset=asset, **dates)
    assert "error" not in row, row
    return row


# --- the registry -------------------------------------------------------------

def test_exactly_nine_tools(reg):
    assert sorted(reg.names()) == sorted(NINE)


def test_no_approve_tool(reg):
    names = reg.names() + [s["function"]["name"] for s in reg.schemas()]
    assert not [n for n in names if "approv" in n.lower()]
    assert not [n for n in names if "token" in n.lower()]


def test_every_description_says_when_to_use(reg):
    for s in reg.schemas():
        assert re.search(r"\buse\b", s["function"]["description"], re.I), s["function"]["name"]


# --- list_assets / list_kpis --------------------------------------------------

def test_list_assets(reg):
    out = call(reg, "list_assets")
    rows = {a["id"]: a for a in out["assets"]}
    assert set(rows) == {"north", "south", "battery"}
    assert rows["north"]["kind"] == "pv" and rows["north"]["capacity_mw"] == "10"
    assert rows["battery"]["kind"] == "bess" and rows["battery"]["capacity_mw"] == "5"
    assert "SYNTHETIC" in out["label"]


def test_list_kpis(reg):
    rows = call(reg, "list_kpis")
    assert len(rows) == 13
    for r in rows:
        assert set(r) == {"kpi", "title", "unit", "needs"}
    assert {r["kpi"] for r in rows} >= {"actual_vs_expected", "incident_resolution", "bess_round_trip"}


# --- get_kpi: hand-worked values ----------------------------------------------

@pytest.mark.parametrize("name,asset,value,unit", [
    # actual 522 / expected 576 = 90.625
    ("actual_vs_expected", "portfolio", "90.6", "%"),
    # north 266 / 320 = 83.125
    ("actual_vs_expected", "north", "83.1", "%"),
    ("actual_vs_expected", "south", "100.0", "%"),
    # north 266 000 kWh / (40 kWh/m2 x 10 000 kWp) = 66.5; south 80.0; simple average 73.25
    ("performance_ratio", "north", "66.5", "%"),
    ("performance_ratio", "portfolio", "73.3", "%"),
    # (180 + 192) h / (8 x 24 x 2) = 96.875
    ("availability", "portfolio", "96.9", "%"),
    ("availability", "north", "93.8", "%"),
    # 522 MWh / (18 MW x 192 h) = 15.104...
    ("capacity_factor", "portfolio", "15.1", "%"),
    # 0.5 x 266 / 0.5 x 320
    ("ppa_delivery", "north", "83.1", "%"),
    # (50 x 454 - 10 x 68) / 522 = 42.1839...
    ("realised_price", "portfolio", "42.18", "EUR/MWh"),
    # (50 x 230 - 10 x 36) / 266 = 41.8796...
    ("realised_price", "north", "41.88", "EUR/MWh"),
    # 522 x 0.5 x 10
    ("merchant_exposure", "portfolio", "2610.00", "EUR"),
    ("downtime", "portfolio", "12", "h"),
    ("downtime", "south", "0", "h"),
    # 576 - 522
    ("energy_loss", "portfolio", "54.000", "MWh"),
    # 190 / 192 = 98.958...
    ("bess_availability", "battery", "99.0", "%"),
    ("bess_availability", "portfolio", "99.0", "%"),
    # 70.4 / 80
    ("bess_round_trip", "battery", "88.0", "%"),
    # average daily throughput 18.8 / (2 x 20)
    ("bess_cycle_utilisation", "battery", "47.0", "%"),
])
def test_get_kpi_values(reg, name, asset, value, unit):
    row = kpi(reg, name, asset)
    assert row["value"] == value
    assert row["unit"] == unit
    assert row["unavailable"] is None
    assert set(row) == {"kpi", "title", "asset", "start", "end", "value", "unit", "unavailable", "inputs"}
    assert (row["start"], row["end"]) == ("2026-06-01", "2026-06-08")


def test_get_kpi_inputs_are_strings(reg):
    row = kpi(reg, "energy_loss", "north")
    assert row["inputs"] == {"expected_mwh": "320.000", "actual_mwh": "266.000"}


def test_get_kpi_date_range(reg):
    # 06-02 only: north 14 / 40
    row = kpi(reg, "actual_vs_expected", "north", start="2026-06-02", end="2026-06-02")
    assert row["value"] == "35.0"
    assert (row["start"], row["end"]) == ("2026-06-02", "2026-06-02")


def test_incident_resolution_is_unavailable_with_reason(reg):
    row = kpi(reg, "incident_resolution")
    assert row["value"] is None
    assert row["unavailable"] == "no tickets loaded"


# --- compare_kpi --------------------------------------------------------------

def test_compare_by_asset(reg):
    out = call(reg, "compare_kpi", kpi="actual_vs_expected", by="asset")
    assert {r["asset"]: r["value"] for r in out["rows"]} == {"north": "83.1", "south": "100.0"}


def test_compare_by_week(reg):
    out = call(reg, "compare_kpi", kpi="actual_vs_expected", by="week")
    # week 1: 454 / 504 = 90.079...; week 2 (one day): 68 / 72 = 94.44...
    assert [(r["start"], r["end"], r["value"]) for r in out["rows"]] == [
        ("2026-06-01", "2026-06-07", "90.1"), ("2026-06-08", "2026-06-08", "94.4")]


def test_compare_bad_by(reg):
    assert "error" in call(reg, "compare_kpi", kpi="downtime", by="month")


# --- get_series / get_prices / get_events -------------------------------------

def test_get_series_portfolio_sums_parks(reg):
    out = call(reg, "get_series", metric="actual_mwh", asset="portfolio", start="2026-06-01", end="2026-06-02")
    assert out["unit"] == "MWh"
    assert out["points"] == [{"date": "2026-06-01", "value": "68.000"}, {"date": "2026-06-02", "value": "46.000"}]


def test_get_series_battery(reg):
    out = call(reg, "get_series", metric="bess_discharged_mwh", asset="battery", start="2026-06-01", end="2026-06-01")
    assert out["points"] == [{"date": "2026-06-01", "value": "8.800"}]


def test_get_series_price(reg):
    out = call(reg, "get_series", metric="price_eur_mwh", start="2026-06-04", end="2026-06-04")
    assert out["points"] == [{"date": "2026-06-04", "value": "-10.00"}]


def test_get_series_bad_metric(reg):
    assert "error" in call(reg, "get_series", metric="bogus")


def test_get_prices(reg):
    out = call(reg, "get_prices", start="2026-06-03", end="2026-06-04")
    assert out == {"start": "2026-06-03", "end": "2026-06-04", "unit": "EUR/MWh", "points": [
        {"date": "2026-06-03", "value": "50.00", "negative": False},
        {"date": "2026-06-04", "value": "-10.00", "negative": True}]}


def test_get_events(reg):
    out = call(reg, "get_events", asset="portfolio")
    assert out["events"] == [
        {"date": "2026-06-02", "asset": "north", "kind": "outage", "value": "12"},
        {"date": "2026-06-03", "asset": "north", "kind": "curtailment", "value": "0.500"}]
    assert call(reg, "get_events", asset="south")["events"] == []


# --- make_chart / propose_action ----------------------------------------------

def _schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def test_make_chart(reg):
    series = [{"name": "north", "points": [{"x": "2026-06-01", "y": "36.000"}]}]
    first = call(reg, "make_chart", kind="bar", title="Actual", series=series)
    second = call(reg, "make_chart", kind="line", title="Again", series=series)
    assert first["id"] == "chart_1" and second["id"] == "chart_2"
    jsonschema.validate(first, _schema("chart"))


def test_make_chart_rejects_number_y_and_bad_kind(reg):
    assert "error" in call(reg, "make_chart", kind="bar", title="t",
                           series=[{"name": "a", "points": [{"x": "1", "y": 36.0}]}])
    assert "error" in call(reg, "make_chart", kind="pie", title="t", series=[])


def test_propose_action(reg):
    out = call(reg, "propose_action", action="schedule_inspection", asset="north", reason="3 outage days")
    assert re.fullmatch(r"prop_[0-9a-f]{12}", out["id"])
    assert out["status"] == "pending"
    jsonschema.validate(out, _schema("proposal"))


def test_propose_action_rejects_unknown_action(reg):
    assert "error" in call(reg, "propose_action", action="approve_action", asset="north", reason="x")


# --- bad calls become errors --------------------------------------------------

def test_unknown_kpi(reg):
    assert "error" in call(reg, "get_kpi", kpi="profit")


def test_unknown_asset(reg):
    assert "error" in call(reg, "get_kpi", kpi="downtime", asset="east")
    assert "error" in call(reg, "get_series", metric="actual_mwh", asset="east")


@pytest.mark.parametrize("start,end", [
    ("2026-05-31", "2026-06-02"),   # before June 2026
    ("2026-06-01", "2026-07-01"),   # after June 2026
    ("2026-06-31", "2026-06-31"),   # not a date
    ("1 June", "2026-06-02"),       # wrong format
    ("2026-06-05", "2026-06-02"),   # start after end
])
def test_bad_dates(reg, start, end):
    assert "error" in call(reg, "get_kpi", kpi="downtime", start=start, end=end)
    assert "error" in call(reg, "get_prices", start=start, end=end)


@pytest.mark.parametrize("start", ["", 0, 20260601, False])
def test_non_string_or_empty_date_is_an_error(reg, start):
    assert "error" in call(reg, "get_kpi", kpi="downtime", start=start)


def test_pv_kpi_on_battery_is_an_error(reg):
    assert "error" in call(reg, "get_kpi", kpi="performance_ratio", asset="battery")


# --- every result: JSON, no floats, money and energy as strings ---------------

def test_no_floats_anywhere(reg):
    results = [call(reg, "list_assets"), call(reg, "list_kpis"), call(reg, "get_prices"),
               call(reg, "get_events"), call(reg, "compare_kpi", kpi="energy_loss", by="week"),
               call(reg, "get_series", metric="curtailed_mwh")]
    results += [call(reg, "get_kpi", kpi=r["kpi"], asset="battery" if r["kpi"].startswith("bess") else "portfolio")
                for r in call(reg, "list_kpis")]
    for r in results:
        assert "error" not in r, r
        assert no_floats(r), r


# --- the real synthetic portfolio --------------------------------------------

def test_real_portfolio_smoke():
    real = build_registry()
    row = call(real, "get_kpi", kpi="actual_vs_expected")
    assert (row["start"], row["end"]) == ("2026-06-01", "2026-06-30")
    assert isinstance(row["value"], str)
    assert len(call(real, "compare_kpi", kpi="downtime", by="week")["rows"]) == 5
