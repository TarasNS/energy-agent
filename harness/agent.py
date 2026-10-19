"""Agent loop: question -> model tool calls -> calculator results -> answer, with a number check.

The model chooses tools and words. It never decides a number: every number in the final text must
appear in the question or in a tool result, otherwise the text is withheld and the charts and
tool results still show. Models are called only through model/model_gateway.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal

from harness.registry import ToolRegistry
from model.model_gateway import ModelTurn, ModelUnavailable, run_turn

MAX_STEPS = 8
MAX_TOKENS = 600

SYSTEM_PROMPT = """You answer questions about a synthetic solar and battery portfolio. The data is synthetic: say so.
- Copy every number exactly as the tool returned it, digit for digit. Never shorten, round or rewrite a number.
- Use the tools for every number. Never calculate, add, average, round or estimate a number yourself; quote tool values exactly.
- If a tool says a value is unavailable, say so and give the reason. Do not estimate it.
- The data covers 2026-06-01 to 2026-06-30. Use those dates in get_prices, get_series and get_events.
- Call make_chart once when the question compares parks or weeks, or asks for a trend over days. Do not chart a single value. Pass ids, never numbers; the server builds the series. Never type numbers into make_chart.
  - A KPI for each park or each week ("each park", "the parks", "by week"): call compare_kpi, then make_chart with the same kpi and by. Example: make_chart(kind="bar", title="Performance ratio by park", kpi="performance_ratio", by="asset")
  - A daily trend: pass metric (the same ids as get_series). Example: make_chart(kind="line", title="Daily price, June 2026", metric="price_eur_mwh")
- If make_chart returns an error, do not retry it; answer in text.
- Call propose_action only when the data clearly justifies an action. You can propose; a person approves.
- Answer in at most 120 words."""

CAP_NOTE = "The daily limit of model calls has been reached, so no answer was given. Try again tomorrow."
STEP_LIMIT_NOTE = "The question needed more steps than the limit allows, so no answer was given. Try a narrower question."

StopReason = Literal["answered", "max_steps", "cap", "model_error"]

NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")


@dataclass
class AgentResult:
    text: str | None
    verified: bool
    note: str | None
    charts: list[dict] = field(default_factory=list)
    proposals: list[dict] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    stopped: StopReason = "answered"


def numbers_in(text: str) -> list[float]:
    return [float(m) for m in NUMBER.findall(text)]


def check_numbers(reply: str, results: Iterable, question: str) -> list[str]:
    """Return the numbers in the reply that appear in neither the question nor the results.

    Results are tool-result strings (the agent) or KPI dicts with value/display (the server).
    """
    results = list(results)
    allowed: set[float] = set()
    for r in results:
        if isinstance(r, str):
            allowed.update(round(n, 6) for n in numbers_in(r))
            continue
        if r.get("value") is not None:
            allowed.add(round(float(r["value"]), 6))
        for token in numbers_in(str(r.get("display", ""))):
            allowed.add(round(token, 6))
    allowed.update(round(n, 6) for n in numbers_in(question))
    if all(not isinstance(r, str) for r in results):
        allowed.add(float(len(results)))
    bad: list[str] = []
    for n in numbers_in(reply):
        if round(n, 6) not in allowed and str(n) not in bad:
            bad.append(str(n))
    return bad


def _parse(content: str) -> dict | None:
    try:
        value = json.loads(content)
    except ValueError:  # truncated or not JSON: skip it rather than crash the loop
        return None
    return value if isinstance(value, dict) else None


def _assistant_blocks(turn: ModelTurn) -> list[dict]:
    blocks: list[dict] = []
    if turn.text:
        blocks.append({"type": "text", "text": turn.text})
    blocks += [{"type": "tool_use", "id": c.id, "name": c.name, "input": c.input} for c in turn.tool_calls]
    return blocks


def _fallback_chart(sources: list[str]) -> dict | None:
    """A chart of values the calculator returned, for an answer that was withheld. Only tool values; no arithmetic."""
    parsed = [p for p in (_parse(s) for s in sources) if isinstance(p, dict)]
    for r in parsed:
        if "metric" in r and r.get("points"):
            points = [{"x": p["date"], "y": p["value"]} for p in r["points"]]
            return {"chart_id": "fallback", "kind": "line", "title": f"{r['metric']} from the calculator",
                    "series": [{"name": r.get("unit", ""), "points": points}]}
    rows: list[dict] = []
    for r in parsed:
        if "rows" in r:
            rows += r["rows"]
        elif "kpi" in r and "value" in r:
            rows.append(r)
    rows = [r for r in rows if r.get("value") is not None]
    if not rows:
        return None
    kpi = rows[0]["kpi"]
    rows = [r for r in rows if r["kpi"] == kpi]
    if len(rows) < 2:
        return None
    by_asset = len({r["asset"] for r in rows}) > 1
    points = [{"x": r["asset"] if by_asset else f"{r['start']} to {r['end']}", "y": r["value"]} for r in rows]
    return {"chart_id": "fallback", "kind": "bar", "title": f"{rows[0]['title']} from the calculator",
            "series": [{"name": rows[0]["unit"], "points": points}]}


def _finish(text: str | None, question: str, sources: list[str], charts, proposals, trace) -> AgentResult:
    text = (text or "").strip()
    if not text:
        return AgentResult(None, False, "The model returned no answer text.", charts, proposals, trace)
    bad = check_numbers(text, sources, question)
    if bad:
        fallback = None if charts else _fallback_chart(sources)
        return AgentResult(
            None, False,
            f"Answer withheld: it contained numbers not in the calculator output ({', '.join(bad)}). "
            "The charts and tool results are shown instead.",
            charts + ([fallback] if fallback else []), proposals, trace,
        )
    return AgentResult(text, True, None, charts, proposals, trace)


def run(
    question: str,
    registry: ToolRegistry,
    *,
    turn: Callable[..., ModelTurn] = run_turn,
    take_slot: Callable[[], bool],
    max_steps: int = MAX_STEPS,
) -> AgentResult:
    """Ask the model, run the tools it picks, and repeat until it answers, the cap or the step limit stops it.

    `take_slot()` is called before every model call; False means the daily cap is used up and the loop stops.
    """
    messages: list[dict] = [{"role": "user", "content": question}]
    tools = registry.schemas()
    trace: list[dict] = []
    charts: list[dict] = []
    proposals: list[dict] = []
    sources: list[str] = []

    for _ in range(max_steps):
        if not take_slot():
            return AgentResult(None, False, CAP_NOTE, charts, proposals, trace, "cap")
        try:
            model_turn = turn(SYSTEM_PROMPT, messages, tools, max_tokens=MAX_TOKENS)
        except ModelUnavailable as e:
            return AgentResult(None, False, f"The model could not answer: {e}", charts, proposals, trace, "model_error")

        if not model_turn.tool_calls:
            return _finish(model_turn.text, question, sources, charts, proposals, trace)

        messages.append({"role": "assistant", "content": _assistant_blocks(model_turn)})
        results: list[dict] = []
        for call in model_turn.tool_calls:
            outcome = registry.execute(call.name, call.input)
            trace.append({"tool": call.name, "input": call.input, "ok": outcome.ok, "result": outcome.content[:400]})
            sources.append(outcome.content)
            if outcome.ok and call.name == "make_chart" and (chart := _parse(outcome.content)):
                charts.append(chart)
            if outcome.ok and call.name == "propose_action" and (proposal := _parse(outcome.content)):
                proposals.append(proposal)
            results.append({
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": outcome.content,
                "is_error": not outcome.ok,
            })
        messages.append({"role": "user", "content": results})

    return AgentResult(None, False, STEP_LIMIT_NOTE, charts, proposals, trace, "max_steps")
