"""General-purpose tools. LLMs are unreliable at arithmetic, so give them a calculator."""

from __future__ import annotations

import ast
import math
import operator
from typing import Annotated

from pydantic import Field

from .tools import Tool, ToolError, tool

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {"abs": abs, "round": round, "min": min, "max": max, "sqrt": math.sqrt, "sum": lambda *a: sum(a)}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        right = _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ToolError("exponent too large")
        return _BINARY[type(node.op)](_eval(node.left), right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS and not node.keywords:
        return _FUNCS[node.func.id](*(_eval(arg) for arg in node.args))
    raise ToolError(f"unsupported expression element: {ast.dump(node)[:60]}")


@tool
def calculate(
    expression: Annotated[str, Field(description="Arithmetic expression, e.g. '0.17 * 2400' or 'round(sum(1.2, 3.4), 1)'")],
) -> dict:
    """Evaluate an arithmetic expression exactly. Supports + - * / // % **, abs, round, min, max, sqrt, sum."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        raise ToolError(f"cannot parse expression: {e.msg}") from e
    try:
        result = _eval(tree)
    except ZeroDivisionError as e:
        raise ToolError("division by zero") from e
    if isinstance(result, float):
        result = round(result, 10)  # hide binary noise like 408.00000000000006
    return {"expression": expression, "result": result}


def builtin_tools() -> list[Tool]:
    return [calculate]
