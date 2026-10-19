import json
from harness.agent import run
from harness.tests.conftest import CHART, PROPOSAL, Scripted, answer, registry_for_tests, tool_call
from model.model_gateway import ModelUnavailable

reg = registry_for_tests()


def test_answers_after_tool_use():
    res = run("availability?", reg,
              turn=Scripted(tool_call("get_kpi", {"kpi": "availability"}), answer("Availability was 96.5 %.")),
              take_slot=lambda: True)
    assert res.stopped == "answered" and res.verified and res.trace[0]["tool"] == "get_kpi"


def test_invented_number_is_withheld():  # Review Focus 1
    res = run("q", reg,
              turn=Scripted(tool_call("get_kpi", {"kpi": "availability"}), answer("About 97.3 %.")),
              take_slot=lambda: True)
    assert res.text is None and not res.verified and "97.3" in res.note


def test_unavailable_stays_unavailable():  # Review Focus 2
    res = run("month-end forecast?", reg,
              turn=Scripted(answer("A forecast is unavailable in this data.")),
              take_slot=lambda: True)
    assert res.verified and res.charts == []


def test_cap_mid_loop_stops_cleanly():  # Review Focus 3
    slots = iter([True, False])
    res = run("q", reg,
              turn=Scripted(tool_call("get_kpi", {"kpi": "availability"}), answer("x")),
              take_slot=lambda: next(slots))
    assert res.stopped == "cap" and res.text is None


def test_step_limit():
    res = run("q", reg, turn=Scripted(*[tool_call("list_assets", {})] * 9),
              take_slot=lambda: True, max_steps=8)
    assert res.stopped == "max_steps"


def test_chart_and_proposal_are_collected():
    res = run("q", reg,
              turn=Scripted(tool_call("make_chart", CHART), tool_call("propose_action", PROPOSAL),
                            answer("See chart.")),
              take_slot=lambda: True)
    assert res.charts[0]["kind"] == "line" and res.proposals[0]["status"] == "proposed"


def test_model_outage_is_reported_not_raised():
    def broken(*_, **__):
        raise ModelUnavailable("model provider returned HTTP 503")

    res = run("q", reg, turn=broken, take_slot=lambda: True)
    assert res.stopped == "model_error" and res.text is None and "503" in res.note


def test_prompt_tells_the_model_how_to_build_a_chart():
    # The model passes a metric; the server builds the series, so no numbers are copied by the model.
    from harness.agent import SYSTEM_PROMPT
    assert 'metric="price_eur_mwh"' in SYSTEM_PROMPT
    assert "Never type numbers into make_chart" in SYSTEM_PROMPT
    assert "2026-06-01 to 2026-06-30" in SYSTEM_PROMPT


def test_trace_keeps_the_tool_result_so_the_page_can_show_it():
    # When an answer is withheld, the page still shows what the calculator returned.
    res = run("merchant exposure?", reg, turn=Scripted(tool_call("get_kpi", {"kpi": "availability"}), answer("x")), take_slot=lambda: True)
    assert res.trace[0]["result"] and "96.5" in res.trace[0]["result"]


def test_withheld_answer_gets_a_chart_from_the_tool_results():
    # The model quotes a number the calculator did not return; the page still gets a chart of the real values.
    north = reg.execute("get_kpi", {"kpi": "availability", "asset": "north"}).content
    south = reg.execute("get_kpi", {"kpi": "availability", "asset": "south"}).content
    res = run("availability?", reg, turn=Scripted(
        tool_call("get_kpi", {"kpi": "availability", "asset": "north"}),
        tool_call("get_kpi", {"kpi": "availability", "asset": "south"}),
        answer("About 97.3 % in total.")), take_slot=lambda: True)
    assert res.text is None and not res.verified
    assert len(res.charts) == 1 and res.charts[0]["kind"] == "bar"
    points = res.charts[0]["series"][0]["points"]
    assert [p["y"] for p in points] == [json.loads(north)["value"], json.loads(south)["value"]]


def test_withheld_answer_with_one_value_gets_no_chart():
    res = run("availability?", reg, turn=Scripted(
        tool_call("get_kpi", {"kpi": "availability"}), answer("About 97.3 %.")), take_slot=lambda: True)
    assert res.text is None and res.charts == []
