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


def test_make_chart_echoes_the_spec_with_strings():
    spec = {"kind": "bar", "title": "Availability by park",
            "series": [{"name": "Availability %", "points": [{"x": "north", "y": "96.5"}]}]}
    out = json.loads(registry_for_tests().execute("make_chart", spec).content)
    assert out["kind"] == "bar" and out["series"][0]["points"][0] == {"x": "north", "y": "96.5"}


def test_make_chart_accepts_numbers_and_keeps_them_as_strings():
    # A model often passes y as a JSON number; the value is still copied from a tool result.
    spec = {"kind": "line", "title": "Price",
            "series": [{"name": "EUR/MWh", "points": [{"x": "Jun 01", "y": 54.1}, {"x": "Jun 02", "y": -4}]}]}
    result = registry_for_tests().execute("make_chart", spec)
    assert result.ok, result.content
    points = json.loads(result.content)["series"][0]["points"]
    assert points == [{"x": "Jun 01", "y": "54.1"}, {"x": "Jun 02", "y": "-4"}]
