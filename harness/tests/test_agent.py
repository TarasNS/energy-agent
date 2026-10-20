"""The agent loop and the number check (SPEC.md section 6), with a scripted model and no network."""
import json
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from harness.agent import FALLBACK_PROMPT, MAX_ROUNDS, check_numbers, load_system_prompt, run
from harness.energy_tools import build_registry
from model.model_gateway import ModelTurn, ModelUnavailable, ToolCall

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"


class Scripted:
    """A model that returns the given turns in order and records what it was sent."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.calls = []

    def __call__(self, system, messages, tools, max_tokens=600):
        self.calls.append({"system": system, "messages": json.loads(json.dumps(messages)), "tools": tools})
        turn = self.turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def tool(name, **args):
    return ModelTurn(text=None, tool_calls=[ToolCall(id=f"call_{name}", name=name, input=args)])


def answer(text):
    return ModelTurn(text=text, tool_calls=[])


@pytest.fixture
def reg(tiny):
    return build_registry(tiny)


def validate(result):
    schemas = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.schema.json")}
    registry = Registry().with_resources(
        (name, Resource.from_contents(s, default_specification=DRAFT202012)) for name, s in schemas.items())
    jsonschema.Draft202012Validator(schemas["chat-result.schema.json"], registry=registry).validate(result.to_dict())


# --- the five required cases --------------------------------------------------

def test_correct_answer_passes(reg):
    model = Scripted(tool("get_kpi", kpi="actual_vs_expected"),
                     answer("Actual vs expected energy was 90.6 % in June 2026 (synthetic data)."))
    result = run("How did the portfolio do?", model=model, registry=reg)
    assert result.verified is True
    assert result.text.startswith("Actual vs expected energy was 90.6 %")
    assert result.note is None
    assert result.stopped == "answered"
    assert result.trace == [{"tool": "get_kpi", "input": {"kpi": "actual_vs_expected"}, "ok": True}]
    validate(result)


def test_made_up_number_is_withheld_but_charts_return(reg):
    series = [{"name": "portfolio", "points": [{"x": "June", "y": "90.6"}]}]
    model = Scripted(tool("get_kpi", kpi="actual_vs_expected"),
                     tool("make_chart", kind="bar", title="Actual vs expected", series=series),
                     answer("Actual vs expected was 91.7 % (synthetic data)."))
    result = run("How did the portfolio do?", model=model, registry=reg)
    assert result.verified is False
    assert result.text is None
    assert "91.7" in result.note
    assert [c["id"] for c in result.charts] == ["chart_1"]
    assert result.stopped == "answered"
    validate(result)


def test_12_5_equals_12_50():
    assert check_numbers("Loss was 12.5 MWh.", ['{"value": "12.50"}'], "q") == []
    assert check_numbers("Loss was 12.500 MWh.", ['{"value": "12.5"}'], "q") == []


def test_year_date_and_count_are_no_false_alarm():
    reply = "In June 2026 north had 3 outage days, the worst on 2026-06-02, over 30 days and 2 weeks."
    assert check_numbers(reply, ['{"value": "83.1"}'], "q") == []


def test_nine_rounds_stop_with_max_steps(reg):
    model = Scripted(*[tool("list_assets") for _ in range(9)], answer("never reached"))
    result = run("Loop forever", model=model, registry=reg)
    assert MAX_ROUNDS == 8
    assert len(model.calls) == 8
    assert result.stopped == "max_steps"
    assert result.verified is False and result.text is None
    assert result.note
    assert len(result.trace) == 8
    validate(result)


# --- check_numbers details ----------------------------------------------------

def test_unknown_number_is_listed():
    assert check_numbers("Loss was 4500 MWh and 54.000 MWh.", ['{"value": "54.000"}'], "q") == ["4500"]


def test_number_from_the_question_is_known():
    assert check_numbers("Yes, 95.5 % is above target.", [], "Is it above 95.5 %?") == []


def test_thousands_separator_and_sign():
    tools = ['{"value": "2610.00"}', '{"value": "-10.00"}']
    assert check_numbers("Exposure is 2,610.00 EUR; the low was -10.00 or 10.00 EUR/MWh.", tools, "q") == []


def test_digits_inside_words_are_not_numbers():
    assert check_numbers("See chart_1 and prop_3f2a9c1b0d4e; POA is in kWh/m2.", [], "q") == []


def test_number_stuck_to_unit_is_checked():
    assert check_numbers("North made 3600MWh.", ['{"value": "36.000"}'], "q") == ["3600"]


def test_large_whole_number_is_checked():
    assert check_numbers("Downtime was 240 h.", ['{"value": "12"}'], "q") == ["240"]


@pytest.mark.parametrize("reply,unknown", [
    ("North made 1950 MWh.", ["1950"]),          # a year-like value with a unit is a value
    ("About 2,000 MWh were lost.", ["2,000"]),   # a year never has a thousands separator
    ("It cost EUR 2000.", ["2000"]),
    ("Capacity factor was 20 %.", ["20"]),       # a count-like value with a unit is a value
    ("Downtime was 24 h.", ["24"]),
    ("Curtailment was 3 MWh.", ["3"]),
])
def test_values_with_units_are_always_checked(reply, unknown):
    assert check_numbers(reply, ['{"value": "19.8"}'], "q") == unknown


def test_counts_and_years_without_units_still_pass():
    assert check_numbers("Over 3 days in 2026 there were 2 outages on 1 park.", [], "q") == []


# --- the loop -----------------------------------------------------------------

def test_number_the_model_put_in_a_chart_is_not_known(reg):
    series = [{"name": "portfolio", "points": [{"x": "June", "y": "90.7"}]}]
    model = Scripted(tool("get_kpi", kpi="actual_vs_expected"),
                     tool("make_chart", kind="bar", title="Share 90.7", series=series),
                     answer("Actual vs expected was 90.7 % (synthetic data)."))
    result = run("How did the portfolio do?", model=model, registry=reg)
    assert result.verified is False and "90.7" in result.note
    assert len(result.charts) == 1


def test_number_the_model_put_in_a_proposal_reason_is_not_known(reg):
    model = Scripted(tool("propose_action", action="schedule_inspection", asset="north", reason="loss of 77.7 MWh"),
                     answer("North lost 77.7 MWh; I proposed an inspection (synthetic data)."))
    result = run("Anything to do?", model=model, registry=reg)
    assert result.verified is False and "77.7" in result.note
    assert len(result.proposals) == 1


def test_number_echoed_in_a_tool_error_is_not_known(reg):
    model = Scripted(tool("get_kpi", kpi="4500.5"), answer("The value is 4500.5 (synthetic data)."))
    result = run("?", model=model, registry=reg)
    assert result.verified is False and "4500.5" in result.note


def test_model_gets_skill_prompt_nine_tools_and_tool_results(reg):
    model = Scripted(tool("get_kpi", kpi="downtime"), answer("Downtime was 12 h (synthetic data)."))
    run("Downtime?", model=model, registry=reg)
    first, second = model.calls
    assert first["system"] == load_system_prompt()
    assert len(first["tools"]) == 9
    assert first["messages"] == [{"role": "user", "content": "Downtime?"}]
    assistant, tool_msg = second["messages"][1:]
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"][0]["id"] == "call_get_kpi"
    assert json.loads(assistant["tool_calls"][0]["function"]["arguments"]) == {"kpi": "downtime"}
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_get_kpi"
    assert json.loads(tool_msg["content"])["value"] == "12"


def test_failed_tool_is_ok_false_in_trace(reg):
    model = Scripted(tool("get_kpi", kpi="profit"), answer("That KPI does not exist (synthetic data)."))
    result = run("Profit?", model=model, registry=reg)
    assert result.trace == [{"tool": "get_kpi", "input": {"kpi": "profit"}, "ok": False}]
    assert result.verified is True


def test_proposals_are_returned(reg):
    model = Scripted(tool("propose_action", action="schedule_inspection", asset="north", reason="outage days"),
                     answer("I proposed an inspection of north; a person must approve it (synthetic data)."))
    result = run("Anything to do?", model=model, registry=reg)
    assert len(result.proposals) == 1 and result.proposals[0]["status"] == "pending"
    validate(result)


def test_model_unavailable_is_model_error(reg):
    series = [{"name": "a", "points": [{"x": "1", "y": "90.6"}]}]
    model = Scripted(tool("make_chart", kind="bar", title="t", series=series), ModelUnavailable("no key"))
    result = run("Hi", model=model, registry=reg)
    assert result.stopped == "model_error"
    assert result.verified is False and result.text is None and result.note
    assert len(result.charts) == 1
    validate(result)


def test_empty_answer_is_not_verified(reg):
    result = run("Hi", model=Scripted(answer(None)), registry=reg)
    assert result.verified is False and result.text is None and result.note
    validate(result)


def test_text_beside_tool_calls_is_not_the_answer(reg):
    turn = ModelTurn(text="Let me check 99.9.", tool_calls=[ToolCall(id="c1", name="list_assets", input={})])
    model = Scripted(turn, answer("There are three assets (synthetic data)."))
    result = run("Assets?", model=model, registry=reg)
    assert result.verified is True and result.text == "There are three assets (synthetic data)."


# --- system prompt --------------------------------------------------------------

def test_system_prompt_is_the_skill_without_frontmatter():
    prompt = load_system_prompt()
    assert prompt.lstrip().startswith("# KPI advisor")
    assert "name: kpi-advisor" not in prompt


def test_system_prompt_falls_back(tmp_path):
    prompt = load_system_prompt(tmp_path / "missing.md")
    assert prompt == FALLBACK_PROMPT
    for word in ("synthetic", "never calculate", "propose"):
        assert word in prompt.lower()


def test_agent_imports_no_provider_sdk():
    source = (ROOT / "harness" / "agent.py").read_text(encoding="utf-8")
    assert "import anthropic" not in source and "from anthropic" not in source
