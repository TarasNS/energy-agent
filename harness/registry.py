"""Tool registry: typed Python functions → OpenAI-style tool schemas.

Execution never raises: every failure becomes an error string the model can
read and correct, because free models regularly send malformed arguments.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, get_type_hints

from pydantic import BaseModel, ValidationError, create_model

MAX_RESULT_CHARS = 12_000


class ToolError(Exception):
    """An expected failure whose message is shown to the model as-is."""


@dataclass
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    args_model: type[BaseModel]

    def schema(self) -> dict:
        parameters = self.args_model.model_json_schema()
        _strip_titles(parameters)
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": parameters},
        }


def tool(fn: Callable[..., Any] | None = None, *, name: str | None = None):
    """Turn a typed function into a Tool. Use `Annotated[T, Field(description=...)]`
    to describe parameters; the docstring becomes the tool description."""

    def wrap(f: Callable[..., Any]) -> Tool:
        hints = get_type_hints(f, include_extras=True)
        fields: dict[str, Any] = {}
        for pname, param in inspect.signature(f).parameters.items():
            default = ... if param.default is inspect.Parameter.empty else param.default
            fields[pname] = (hints.get(pname, Any), default)
        args_model = create_model(f"{f.__name__}_args", **fields)
        return Tool(name or f.__name__, inspect.getdoc(f) or "", f, args_model)

    return wrap(fn) if fn is not None else wrap


@dataclass
class ToolResult:
    content: str
    ok: bool


class ToolRegistry:
    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools:
            self.register(t)

    def register(self, t: Tool) -> None:
        if t.name in self._tools:
            raise ValueError(f"duplicate tool name: {t.name}")
        self._tools[t.name] = t

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self._tools.values()]

    def execute(self, name: str, arguments: Any) -> ToolResult:
        t = self._tools.get(name)
        if t is None:
            return ToolResult(f"Error: unknown tool '{name}'. Available tools: {', '.join(self._tools)}.", False)
        try:
            args = _parse_arguments(arguments)
        except ValueError as e:
            return ToolResult(f"Error: arguments for '{name}' must be a JSON object ({e}).", False)
        try:
            parsed = t.args_model.model_validate(args)
        except ValidationError as e:
            return ToolResult(f"Error: invalid arguments for '{name}': {_format_errors(e)}. Fix them and retry.", False)
        try:
            result = t.fn(**{field: getattr(parsed, field) for field in type(parsed).model_fields})
        except ToolError as e:
            return ToolResult(f"Error: {e}", False)
        except Exception as e:  # tool bugs and network failures must not kill the loop
            return ToolResult(f"Error: tool '{name}' failed: {type(e).__name__}: {e}", False)
        return ToolResult(_serialize(result), True)


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def _parse_arguments(arguments: Any) -> dict:
    if arguments is None or arguments == "":
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            value = json.loads(_FENCE.sub("", arguments.strip()))
        except json.JSONDecodeError as e:
            raise ValueError(f"not valid JSON: {e.msg}") from e
        if isinstance(value, dict):
            return value
    raise ValueError(f"got {type(arguments).__name__}")


def _format_errors(e: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, err['loc'])) or 'arguments'}: {err['msg']}" for err in e.errors())


def _serialize(result: Any) -> str:
    text = result if isinstance(result, str) else json.dumps(result, default=str, ensure_ascii=False)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + f"... [truncated {len(text) - MAX_RESULT_CHARS} chars]"
    return text


def _strip_titles(schema: Any) -> None:
    """Remove pydantic's auto-generated 'title' keys (noise for the model),
    without touching properties that happen to be named 'title'."""
    if isinstance(schema, dict):
        schema.pop("title", None)
        for key, value in schema.items():
            if key in ("properties", "$defs") and isinstance(value, dict):
                for sub in value.values():
                    _strip_titles(sub)
            else:
                _strip_titles(value)
    elif isinstance(schema, list):
        for item in schema:
            _strip_titles(item)
