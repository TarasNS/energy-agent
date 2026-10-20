"""The agent loop and the number check (SPEC.md section 6).

The model picks tools and writes words; it never calculates. Every number in
its answer must appear in the question or a tool result, or the text is
withheld. The model is called only through model.model_gateway.run_turn.
"""
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from harness.energy_tools import build_registry
from model.model_gateway import ModelUnavailable, run_turn

MAX_ROUNDS = 8
SKILL_PATH = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "kpi-advisor" / "SKILL.md"
FALLBACK_PROMPT = (
    "You help a portfolio manager review a synthetic solar and battery portfolio for June 2026.\n"
    "Say that the data is synthetic. Never calculate, add, average, round or estimate a number:\n"
    "quote tool values exactly. Call make_chart at most once. You may propose an action with\n"
    "propose_action when the data clearly justifies it; never say it is approved.\n"
    "Answer in at most 120 words."
)

_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
# A number not glued to a word before it (skips m2, chart_1, prop_3f...). 2,610.00 is one number.
# A comma followed by 1 or 2 digits is a decimal comma (20,7); followed by 3 digits it separates thousands.
_NUMBER = re.compile(r"(?<![A-Za-z_\d.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+,\d{1,2}(?!\d)|\d+(?:\.\d+)?)(?!\d)")
_DECIMAL_COMMA = re.compile(r"\d+,\d{1,2}")
_MAX_COUNT = 31  # a bare whole number up to this is a count (days, weeks, assets) and never raises an alarm
# A unit before or after a number makes it a value, never a count or a year.
_UNIT_AFTER = re.compile(
    r"\s?(%|per\s?cent|percent|pp\b|[kMG]W[hp]?\b|(?:kilo|mega|giga)watt|euros?\b|EUR|MEUR|€|USD|\$"
    r"|hours?\b|hrs?\b|h\b)", re.I)
_UNIT_BEFORE = re.compile(r"(EUR|€|USD|\$)\s?$", re.I)
# Tools that echo what the model wrote; their output never makes a number known.
_ECHO_TOOLS = {"make_chart", "propose_action"}


@dataclass
class AgentResult:
    text: str | None
    verified: bool
    note: str | None
    charts: list = field(default_factory=list)
    proposals: list = field(default_factory=list)
    trace: list = field(default_factory=list)
    stopped: str = "answered"

    def to_dict(self):
        return asdict(self)


def _numbers(text):
    """(written form, value, has unit) for every number in `text`, dates removed. Signs are ignored."""
    text = _DATE.sub(" ", text or "")
    found = []
    for m in _NUMBER.finditer(text):
        written = m.group(1)
        try:
            value = Decimal(written.replace(",", ".") if _DECIMAL_COMMA.fullmatch(written)
                            else written.replace(",", ""))
        except InvalidOperation:
            continue
        has_unit = bool(_UNIT_AFTER.match(text, m.end()) or _UNIT_BEFORE.search(text[:m.start()]))
        found.append((written, value, has_unit))
    return found


def _harmless(written, value, has_unit):
    """A bare year or small count never raises a false alarm. A value with a unit always counts."""
    if has_unit or not written.isdigit():
        return False
    return value <= _MAX_COUNT or (len(written) == 4 and 1900 <= value <= 2100)


def check_numbers(reply, tool_results, question):
    """Every number in `reply` that is in neither the question nor any tool result, in order, once each."""
    known = {value for source in [question, *tool_results] for _, value, _ in _numbers(source)}
    unknown = []
    for written, value, has_unit in _numbers(reply):
        if value not in known and not _harmless(written, value, has_unit) and written not in unknown:
            unknown.append(written)
    return unknown


def load_system_prompt(path=SKILL_PATH):
    """The kpi-advisor skill without its frontmatter, or the built-in fallback."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, ValueError):  # missing, a folder, or not UTF-8
        return FALLBACK_PROMPT
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) < 3:  # frontmatter never closes
            return FALLBACK_PROMPT
        text = parts[2]
    return text.strip() or FALLBACK_PROMPT


def run(question, *, model=run_turn, registry=None):
    """Answer one question. Never raises for a model or tool failure."""
    registry = registry or build_registry()
    system, tools = load_system_prompt(), registry.schemas()
    messages = [{"role": "user", "content": question}]
    tool_results, trace, charts, proposals = [], [], [], []

    def result(text, note, stopped):
        return AgentResult(text=text, verified=text is not None, note=note, charts=charts,
                           proposals=proposals, trace=trace, stopped=stopped)

    for _ in range(MAX_ROUNDS):
        try:
            turn = model(system, messages, tools)
        except ModelUnavailable as exc:
            return result(None, f"The model could not be reached ({exc}). Tool results and charts are shown.",
                          "model_error")

        if not turn.tool_calls:
            reply = (turn.text or "").strip()
            if not reply:
                return result(None, "The model gave no answer. Tool results and charts are shown.", "answered")
            unknown = check_numbers(reply, tool_results, question)
            if unknown:
                return result(None, "The answer was withheld because it contained numbers the tools did not "
                                    f"return: {', '.join(unknown)}. Tool results and charts are shown.",
                              "answered")
            return result(reply, None, "answered")

        messages.append({"role": "assistant", "content": turn.text, "tool_calls": [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.input)}}
            for c in turn.tool_calls]})
        for call in turn.tool_calls:
            out = registry.run(call.name, call.input)
            parsed = json.loads(out)
            ok = not (isinstance(parsed, dict) and "error" in parsed)
            trace.append({"tool": call.name, "input": call.input if isinstance(call.input, dict) else {}, "ok": ok})
            if ok and call.name not in _ECHO_TOOLS:  # only data the tools made can vouch for a number
                tool_results.append(out)
            if ok and call.name == "make_chart":
                charts.append(parsed)
            if ok and call.name == "propose_action":
                proposals.append(parsed)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": out})

    return result(None, f"Stopped after {MAX_ROUNDS} rounds without an answer. Tool results and charts are shown.",
                  "max_steps")
