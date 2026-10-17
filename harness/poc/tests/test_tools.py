import json
from datetime import date
from typing import Annotated

from pydantic import Field

from energy_harness import tools as tools_module
from energy_harness.builtin_tools import calculate
from energy_harness.tools import ToolError, ToolRegistry, tool


@tool
def lookup(
    title: Annotated[str, Field(description="A property literally named title")],
    day: date | None = None,
    limit: int = 3,
) -> dict:
    """Look something up."""
    if title == "boom":
        raise RuntimeError("kaput")
    if title == "nope":
        raise ToolError("no such thing")
    return {"title": title, "day": day, "limit": limit}


def test_schema_is_openai_shaped_without_noise_titles():
    schema = lookup.schema()
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == "lookup" and fn["description"] == "Look something up."
    params = fn["parameters"]
    assert params["type"] == "object"
    assert params["required"] == ["title"]
    assert "title" not in params  # auto title stripped...
    assert params["properties"]["title"]["description"] == "A property literally named title"  # ...real property kept
    assert "title" not in params["properties"]["limit"]


def test_execute_parses_json_string_and_validates_types():
    result = ToolRegistry([lookup]).execute("lookup", '{"title": "x", "day": "2026-10-17", "limit": "5"}')
    assert result.ok
    assert json.loads(result.content) == {"title": "x", "day": "2026-10-17", "limit": 5}


def test_execute_accepts_dict_and_fenced_json():
    reg = ToolRegistry([lookup])
    assert reg.execute("lookup", {"title": "x"}).ok
    assert reg.execute("lookup", '```json\n{"title": "x"}\n```').ok


def test_errors_are_returned_not_raised():
    reg = ToolRegistry([lookup])
    unknown = reg.execute("missing", "{}")
    assert not unknown.ok and "unknown tool" in unknown.content and "lookup" in unknown.content
    assert "JSON object" in reg.execute("lookup", "{title: x").content
    invalid = reg.execute("lookup", '{"limit": "many"}')
    assert not invalid.ok and "title" in invalid.content and "limit" in invalid.content
    assert reg.execute("lookup", '{"title": "nope"}').content == "Error: no such thing"
    crash = reg.execute("lookup", '{"title": "boom"}')
    assert not crash.ok and "RuntimeError: kaput" in crash.content


def test_long_results_are_truncated(monkeypatch):
    monkeypatch.setattr(tools_module, "MAX_RESULT_CHARS", 20)
    content = ToolRegistry([lookup]).execute("lookup", {"title": "x" * 100}).content
    assert content.endswith("chars]") and "truncated" in content


def test_calculate():
    reg = ToolRegistry([calculate])
    assert json.loads(reg.execute("calculate", {"expression": "0.17 * 2400"}).content)["result"] == 408.0
    assert json.loads(reg.execute("calculate", {"expression": "round(sum(1.25, 2), 1)"}).content)["result"] == 3.2
    assert "unsupported" in reg.execute("calculate", {"expression": "__import__('os')"}).content
    assert "division by zero" in reg.execute("calculate", {"expression": "1/0"}).content
    assert "too large" in reg.execute("calculate", {"expression": "9**9999"}).content
