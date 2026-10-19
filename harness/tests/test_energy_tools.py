import json

from harness.dataset import build
from harness.energy_tools import build_energy_tools
from harness.tests.conftest import fake_propose, registry_for_tests


def test_exactly_nine_tools_and_no_approval():
    names = set(build_energy_tools(build(), fake_propose).names())
    assert names == {"list_assets", "list_kpis", "get_kpi", "compare_kpi", "get_series",
                     "get_prices", "get_events", "make_chart", "propose_action"}


def test_kpis_match_the_current_chat():
    r = registry_for_tests()
    for kpi, value in [("actual_vs_expected", "92.6"), ("availability", "96.5"), ("performance_ratio", "76.2"),
                       ("capacity_factor", "16.5"), ("ppa_delivery", "92.6"), ("realised_price", "54.37"),
                       ("merchant_exposure", "10700.89"), ("downtime", "51.00"), ("energy_loss", "170.398"),
                       ("bess_availability", "99.4"), ("bess_round_trip", "87.4"), ("bess_cycle_utilisation", "46.1")]:
        assert json.loads(r.execute("get_kpi", {"kpi": kpi}).content)["value"] == value, kpi


def test_missing_data_is_unavailable_not_a_number():
    out = json.loads(registry_for_tests().execute("get_kpi", {"kpi": "incident_resolution"}).content)
    assert out["value"] is None and "ticket" in out["unavailable"]


def test_unknown_tool_and_bad_args_are_errors_not_crashes():
    r = registry_for_tests()
    assert not r.execute("approve_action", {}).ok
    assert not r.execute("get_kpi", {"kpi": "nope"}).ok


def test_propose_never_approves():
    out = json.loads(registry_for_tests().execute("propose_action",
        {"action": "enable_negative_price_curtailment", "asset": "north", "reason": "r"}).content)
    assert out["status"] == "proposed"


def test_compare_by_asset_returns_one_row_per_park():
    out = json.loads(registry_for_tests().execute("compare_kpi", {"kpi": "availability", "by": "asset"}).content)
    assert [row["asset"] for row in out["rows"]] == ["north", "south"]


def test_make_chart_builds_the_series_from_the_calculator():
    reg = registry_for_tests()
    out = json.loads(reg.execute("make_chart", {"kind": "line", "title": "Price", "metric": "price_eur_mwh"}).content)
    series = json.loads(reg.execute("get_series", {"metric": "price_eur_mwh"}).content)
    assert out["kind"] == "line" and len(out["series"]) == 1
    points = out["series"][0]["points"]
    assert len(points) == 30 and points[0]["x"] == "2026-06-01"
    assert [p["y"] for p in points] == [p["value"] for p in series["points"]]


def test_make_chart_one_series_per_asset():
    reg = registry_for_tests()
    out = json.loads(reg.execute("make_chart", {"kind": "line", "title": "Availability", "metric": "availability_hours",
                                                "assets": ["north", "south"]}).content)
    assert len(out["series"]) == 2
    north = json.loads(reg.execute("get_series", {"metric": "availability_hours", "asset": "north"}).content)
    assert [p["y"] for p in out["series"][0]["points"]] == [p["value"] for p in north["points"]]


def test_make_chart_refuses_unknown_asset_and_metric():
    reg = registry_for_tests()
    assert not reg.execute("make_chart", {"kind": "line", "title": "t", "metric": "price_eur_mwh", "assets": ["mars"]}).ok
    assert not reg.execute("make_chart", {"kind": "line", "title": "t", "metric": "nope"}).ok


def test_make_chart_charts_a_kpi_by_asset_from_compare_kpi():
    # Regression: 12 of the 13 standard questions are KPIs, and make_chart could only chart daily series,
    # so those answers never had a chart.
    reg = registry_for_tests()
    out = json.loads(reg.execute("make_chart", {"kind": "bar", "title": "PR by park", "kpi": "performance_ratio", "by": "asset"}).content)
    rows = json.loads(reg.execute("compare_kpi", {"kpi": "performance_ratio", "by": "asset"}).content)["rows"]
    points = out["series"][0]["points"]
    assert out["kind"] == "bar"
    assert [p["x"] for p in points] == [r["asset"] for r in rows]
    assert [p["y"] for p in points] == [r["value"] for r in rows]


def test_make_chart_charts_a_kpi_by_week():
    reg = registry_for_tests()
    out = json.loads(reg.execute("make_chart", {"kind": "line", "title": "Availability by week", "kpi": "availability", "by": "week"}).content)
    rows = json.loads(reg.execute("compare_kpi", {"kpi": "availability", "by": "week"}).content)["rows"]
    assert [p["y"] for p in out["series"][0]["points"]] == [r["value"] for r in rows]


def test_make_chart_needs_exactly_one_of_metric_or_kpi():
    reg = registry_for_tests()
    assert not reg.execute("make_chart", {"kind": "bar", "title": "t"}).ok
    assert not reg.execute("make_chart", {"kind": "bar", "title": "t", "metric": "actual_mwh", "kpi": "availability"}).ok
    assert not reg.execute("make_chart", {"kind": "bar", "title": "t", "kpi": "nope"}).ok


def test_compare_kpi_tells_the_model_how_to_chart_it():
    # Live run: the model called compare_kpi for "the parks" and then skipped make_chart.
    out = json.loads(registry_for_tests().execute("compare_kpi", {"kpi": "downtime", "by": "asset"}).content)
    assert out["chart_hint"] == 'make_chart(kind="bar", kpi="downtime", by="asset", title=...)'


def test_make_chart_with_kpi_refuses_metric_only_arguments():
    # assets, start and end were silently ignored with kpi, so a title could describe data that was not charted.
    reg = registry_for_tests()
    assert not reg.execute("make_chart", {"kind": "bar", "title": "t", "kpi": "availability", "assets": ["north"]}).ok
    assert not reg.execute("make_chart", {"kind": "bar", "title": "t", "kpi": "availability", "start": "2026-06-10"}).ok
