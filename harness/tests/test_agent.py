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
    assert res.charts[0]["kind"] == "bar" and res.proposals[0]["status"] == "proposed"


def test_model_outage_is_reported_not_raised():
    def broken(*_, **__):
        raise ModelUnavailable("model provider returned HTTP 503")

    res = run("q", reg, turn=broken, take_slot=lambda: True)
    assert res.stopped == "model_error" and res.text is None and "503" in res.note
