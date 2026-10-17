from __future__ import annotations

from collections import deque

import pytest

from energy_harness.llm import ChatResult


class FakeClock:
    def __init__(self, start: float = 1_790_000_000.0) -> None:  # 2026-09-21 UTC
        self.now = start
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class ScriptedLLM:
    """Returns pre-baked assistant messages in order and records every request."""

    def __init__(self, *messages: dict, model: str = "fake/model:free") -> None:
        self.replies = deque(messages)
        self.model = model
        self.calls: list[dict] = []

    def chat(self, messages, tools=None, tool_choice=None) -> ChatResult:
        self.calls.append({"messages": [dict(m) for m in messages], "tools": tools, "tool_choice": tool_choice})
        return ChatResult(message=self.replies.popleft(), model=self.model, requested_model=self.model, latency_s=0.01)


def tool_call(name: str, arguments, call_id: str | None = "call_1") -> dict:
    call = {"type": "function", "function": {"name": name, "arguments": arguments}}
    if call_id:
        call["id"] = call_id
    return {"role": "assistant", "content": None, "tool_calls": [call]}


def answer(text: str) -> dict:
    return {"role": "assistant", "content": text}


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()
