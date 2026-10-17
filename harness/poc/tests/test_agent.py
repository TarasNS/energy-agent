import json

from conftest import ScriptedLLM, answer, tool_call

from energy_harness.agent import STEP_LIMIT_PROMPT, Agent
from energy_harness.builtin_tools import calculate
from energy_harness.tools import ToolRegistry
from energy_harness.trace import Tracer


def make_agent(llm, **kwargs):
    return Agent(llm, ToolRegistry([calculate]), today=lambda: "2026-10-17", **kwargs)


def test_answers_directly_without_tools():
    llm = ScriptedLLM(answer("Hello"))
    result = make_agent(llm).run("hi")
    assert result.answer == "Hello" and result.stopped_reason == "answered" and result.steps == 1
    system = llm.calls[0]["messages"][0]
    assert system["role"] == "system" and "2026-10-17" in system["content"]
    assert llm.calls[0]["tools"][0]["function"]["name"] == "calculate"


def test_runs_tool_and_feeds_result_back():
    llm = ScriptedLLM(tool_call("calculate", '{"expression": "0.17 * 2400"}'), answer("408 kWh"))
    result = make_agent(llm).run("What is 17% of 2.4 MWh in kWh?")

    assert result.answer == "408 kWh" and result.steps == 2
    tool_msg = llm.calls[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1"
    assert json.loads(tool_msg["content"])["result"] == 408.0
    assert result.models_used == ["fake/model:free", "fake/model:free"]


def test_normalizes_object_arguments_and_missing_ids():
    llm = ScriptedLLM(tool_call("calculate", {"expression": "1+1"}, call_id=None), answer("2"))
    make_agent(llm).run("1+1?")
    assistant, tool_msg = llm.calls[1]["messages"][-2:]
    call = assistant["tool_calls"][0]
    assert call["id"] == "call_1_0" and tool_msg["tool_call_id"] == "call_1_0"
    assert call["function"]["arguments"] == '{"expression": "1+1"}'
    assert assistant["content"] == ""


def test_invalid_arguments_go_back_to_model_for_repair():
    llm = ScriptedLLM(
        tool_call("calculate", '{"expr": "1+1"}'),
        tool_call("calculate", '{"expression": "1+1"}', call_id="call_2"),
        answer("2"),
    )
    result = make_agent(llm).run("1+1?")
    first_error = llm.calls[1]["messages"][-1]["content"]
    assert first_error.startswith("Error: invalid arguments") and "expression" in first_error
    assert result.answer == "2" and result.steps == 3


def test_step_limit_forces_final_answer_without_tools():
    loop = [tool_call("calculate", '{"expression": "1"}', call_id=f"c{i}") for i in range(3)]
    llm = ScriptedLLM(*loop, answer("best effort"))
    result = make_agent(llm, max_steps=3).run("loop forever")

    assert result.stopped_reason == "max_steps" and result.answer == "best effort"
    final = llm.calls[-1]
    assert final["tool_choice"] == "none"
    assert final["messages"][-1] == {"role": "user", "content": STEP_LIMIT_PROMPT}


def test_history_carries_over_between_runs():
    llm = ScriptedLLM(answer("first"), answer("second"))
    agent = make_agent(llm)
    first = agent.run("q1")
    agent.run("q2", history=first.history)
    contents = [m["content"] for m in llm.calls[1]["messages"]]
    assert contents[1:] == ["q1", "first", "q2"]
    assert sum(m["role"] == "system" for m in llm.calls[1]["messages"]) == 1


def test_empty_answer_is_flagged():
    assert "empty" in make_agent(ScriptedLLM({"role": "assistant", "content": None})).run("?").answer


def test_trace_records_llm_and_tool_events(tmp_path):
    tracer = Tracer(tmp_path)
    llm = ScriptedLLM(tool_call("calculate", '{"expression": "2*3"}'), answer("6"))
    make_agent(llm, tracer=tracer).run("2*3?")
    events = [json.loads(line) for line in tracer.path.read_text().splitlines()]
    assert [e["event"] for e in events] == ["run_start", "llm_call", "tool_call", "llm_call", "run_end"]
    assert events[1]["model"] == "fake/model:free"
    assert events[2]["ok"] is True and events[2]["name"] == "calculate"
