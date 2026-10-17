"""The agent loop: model → tool calls → results → model … → final answer."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from .llm import ChatClient, ChatResult
from .tools import ToolRegistry
from .trace import NullTracer

SYSTEM_PROMPT = """You are an energy analyst assistant for a solar power producer.

- Use the tools to get data. Never invent numbers; if a tool fails or data is missing, say so.
- Use the calculate tool for any non-trivial arithmetic.
- estimate_pv_production gives weather-based estimates, not measured output; say so when you use it.
- get_metered_production (when available) is measured output. Low output with full availability can mean
  curtailment (check curtailed_intervals and negative prices), degradation/soiling (compare with the estimate)
  or missing data (check data_completeness_pct).
- Today's date is {today} (UTC). Times are UTC unless a tool says otherwise.
- Answer concisely, with units (MW, MWh, EUR/MWh, W/m², kWh/m²)."""

STEP_LIMIT_PROMPT = "Step limit reached. Answer now with the information you already have. Do not call tools."


@dataclass
class AgentResult:
    answer: str
    stopped_reason: str  # "answered" | "max_steps"
    steps: int
    models_used: list[str]
    messages: list[dict] = field(repr=False, default_factory=list)

    @property
    def history(self) -> list[dict]:
        """Conversation without the system prompt, to pass into the next run()."""
        return [m for m in self.messages if m.get("role") != "system"]


class Agent:
    def __init__(
        self,
        llm: ChatClient,
        registry: ToolRegistry,
        *,
        max_steps: int = 8,
        system_prompt: str = SYSTEM_PROMPT,
        tracer=None,
        today: Callable[[], str] = lambda: datetime.now(timezone.utc).date().isoformat(),
    ) -> None:
        self.llm = llm
        self.registry = registry
        self.max_steps = max_steps
        self.system_prompt = system_prompt
        self.tracer = tracer or NullTracer()
        self._today = today

    def run(self, question: str, history: list[dict] | None = None) -> AgentResult:
        messages = [{"role": "system", "content": self.system_prompt.format(today=self._today())}]
        messages += history or []
        messages.append({"role": "user", "content": question})
        tools = self.registry.schemas() or None
        models_used: list[str] = []
        self.tracer.event("run_start", question=question)

        for step in range(1, self.max_steps + 1):
            message = self._call(messages, tools, None, step, models_used)
            calls = message.get("tool_calls") or []
            if not calls:
                return self._finish(message, "answered", step, models_used, messages)
            for call in calls:
                name, arguments = call["function"]["name"], call["function"]["arguments"]
                result = self.registry.execute(name, arguments)
                self.tracer.event("tool_call", step=step, name=name, arguments=arguments, ok=result.ok, result=result.content[:2000])
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result.content})

        messages.append({"role": "user", "content": STEP_LIMIT_PROMPT})
        message = self._call(messages, tools, "none", self.max_steps + 1, models_used)
        return self._finish(message, "max_steps", self.max_steps + 1, models_used, messages)

    def _call(self, messages: list[dict], tools, tool_choice, step: int, models_used: list[str]) -> dict:
        result: ChatResult = self.llm.chat(messages, tools=tools, tool_choice=tool_choice)
        models_used.append(result.model)
        self.tracer.event(
            "llm_call",
            step=step,
            model=result.model,
            requested_model=result.requested_model,
            latency_s=round(result.latency_s, 3),
            usage=result.usage,
            failed_models=result.failed_models,
        )
        message = _normalize_assistant(result.message, step)
        if tool_choice == "none":
            message.pop("tool_calls", None)
        messages.append(message)
        return message

    def _finish(self, message: dict, reason: str, steps: int, models_used: list[str], messages: list[dict]) -> AgentResult:
        answer = (message.get("content") or "").strip() or "(the model returned an empty answer)"
        self.tracer.event("run_end", reason=reason, steps=steps, answer=answer)
        return AgentResult(answer, reason, steps, models_used, messages)


def _normalize_assistant(message: dict, step: int) -> dict:
    """Keep only fields every provider accepts, and repair common tool-call quirks
    (missing ids, arguments sent as an object instead of a JSON string)."""
    normalized: dict = {"role": "assistant", "content": message.get("content") or ""}
    calls = []
    for i, call in enumerate(message.get("tool_calls") or []):
        function = call.get("function") or {}
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            arguments = json.dumps(arguments if arguments is not None else {})
        calls.append(
            {
                "id": call.get("id") or f"call_{step}_{i}",
                "type": "function",
                "function": {"name": function.get("name", ""), "arguments": arguments},
            }
        )
    if calls:
        normalized["tool_calls"] = calls
    return normalized
