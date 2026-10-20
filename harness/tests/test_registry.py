"""ToolRegistry runs a tool by name and never raises: a bad call becomes {"error": ...}."""
import json

from harness.registry import ToolRegistry


def _registry():
    reg = ToolRegistry()
    reg.register("echo", lambda text: {"text": text}, "Echo the text back.",
                 {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})
    reg.register("boom", lambda: 1 / 0, "Always fails.", {"type": "object", "properties": {}})
    return reg


def test_run_returns_json_string():
    out = _registry().run("echo", {"text": "hi"})
    assert isinstance(out, str)
    assert json.loads(out) == {"text": "hi"}


def test_unknown_tool_is_an_error_not_an_exception():
    assert "error" in json.loads(_registry().run("nope", {}))


def test_bad_arguments_are_an_error():
    reg = _registry()
    assert "error" in json.loads(reg.run("echo", {"wrong": "x"}))
    assert "error" in json.loads(reg.run("echo", {}))
    assert "error" in json.loads(reg.run("echo", "not a dict"))


def test_exception_inside_a_tool_is_an_error():
    assert "error" in json.loads(_registry().run("boom", {}))


def test_unhashable_name_and_unserialisable_result_are_errors():
    reg = _registry()
    reg.register("odd", lambda: {"x": {1, 2}}, "Returns a set.", {"type": "object", "properties": {}})
    assert "error" in json.loads(reg.run(["echo"], {}))
    assert "error" in json.loads(reg.run("odd", {}))


def test_none_arguments_mean_no_arguments():
    assert "error" in json.loads(_registry().run("boom", None))


def test_schemas_are_openai_style():
    schemas = _registry().schemas()
    assert [s["function"]["name"] for s in schemas] == ["echo", "boom"]
    for s in schemas:
        assert s["type"] == "function"
        assert set(s["function"]) == {"name", "description", "parameters"}


def test_names():
    assert _registry().names() == ["echo", "boom"]
