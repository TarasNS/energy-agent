"""Shared test helpers for the harness. No network, no real API key: the model is always scripted."""

from __future__ import annotations

from collections import deque

from harness.dataset import build
from harness.energy_tools import build_energy_tools
from model.model_gateway import ModelTurn, ToolCall


def fake_propose(action: str, asset: str, reason: str) -> str:
    return "P-1"


def registry_for_tests():
    return build_energy_tools(build(), fake_propose)


class Scripted:
    """Stands in for run_turn: returns the given ModelTurns in order and records each request."""

    def __init__(self, *turns: ModelTurn) -> None:
        self.turns = deque(turns)
        self.requests: list[dict] = []

    def __call__(self, system, messages, tools, *, max_tokens: int = 1024, **_) -> ModelTurn:
        self.requests.append({"system": system, "messages": [dict(m) for m in messages], "tools": tools})
        if not self.turns:
            raise AssertionError("the scripted model ran out of turns")
        return self.turns.popleft()


def tool_call(name: str, input: dict, call_id: str = "t1") -> ModelTurn:
    return ModelTurn(text="", tool_calls=[ToolCall(id=call_id, name=name, input=input)],
                     stop_reason="tool_use", model="scripted")


def answer(text: str) -> ModelTurn:
    return ModelTurn(text=text, tool_calls=[], stop_reason="end_turn", model="scripted")


CHART = {"kind": "line", "title": "t", "metric": "price_eur_mwh", "assets": None}
PROPOSAL = {"action": "schedule_inspection", "asset": "north", "reason": "r"}
