"""Score the agent on questions about the simulated fleet, whose answers are known.

    energy-harness-eval                      # all cases in evals.yaml, configured model chain
    energy-harness-eval --model openrouter/free --case outage-full
    energy-harness-eval --list

Expected numbers are computed by running the same tools on the simulator, so
a case checks the agent's reasoning, not the tools. Results go to runs/eval-*.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .agent import AgentResult
from .budget import BudgetExceeded
from .config import POC_ROOT, load_settings
from .factory import build_agent, build_registry, build_simulator
from .llm import FatalLLMError, LLMError
from .tools import ToolRegistry
from .trace import Tracer

# metric → (tool, how to build its arguments, how to read the value from its result)
METRICS = {
    "metered_mwh": ("get_metered_production", lambda n: {"park": n.park, "start_date": str(n.date)}, lambda r: r["daily"][0]["energy_mwh"]),
    "estimated_mwh": ("estimate_pv_production", lambda n: {"park": n.park, "start_date": str(n.date)}, lambda r: r["daily"][0]["energy_mwh"]),
    "mean_price": ("get_day_ahead_prices", lambda n: {"bidding_zone": n.zone, "start_date": str(n.date)}, lambda r: r["daily"][0]["mean"]),
    "min_price": ("get_day_ahead_prices", lambda n: {"bidding_zone": n.zone, "start_date": str(n.date)}, lambda r: r["daily"][0]["min"]),
    "max_price": ("get_day_ahead_prices", lambda n: {"bidding_zone": n.zone, "start_date": str(n.date)}, lambda r: r["daily"][0]["max"]),
}


class NumberCheck(BaseModel):
    metric: Literal["metered_mwh", "estimated_mwh", "mean_price", "min_price", "max_price"]
    date: date
    park: str | None = None
    zone: str | None = None
    tolerance_pct: float = 3.0


class Expect(BaseModel):
    contains_any: list[str] = []  # at least one must appear (case-insensitive)
    contains_all: list[str] = []
    not_contains: list[str] = []
    tools_called: list[str] = []  # each must have been called at least once
    number: NumberCheck | None = None  # some number in the answer must be within tolerance


class EvalCase(BaseModel):
    id: str
    question: str
    expect: Expect
    note: str | None = None


class EvalSuite(BaseModel):
    cases: list[EvalCase] = Field(min_length=1)

    @classmethod
    def from_file(cls, path: Path) -> "EvalSuite":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()))


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    id: str
    passed: bool
    checks: list[CheckResult] = field(default_factory=list)
    answer: str = ""
    steps: int = 0
    models: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    seconds: float = 0.0
    error: str | None = None


def expected_number(check: NumberCheck, registry: ToolRegistry) -> float:
    tool_name, make_args, read = METRICS[check.metric]
    result = registry.execute(tool_name, make_args(check))
    if not result.ok:
        raise ValueError(f"cannot compute expected {check.metric}: {result.content}")
    return float(read(json.loads(result.content)))


_NUMBER = re.compile(r"(?<![\w.])[-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.])[-−]?\d+(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    return [float(m.replace(",", "").replace("−", "-")) for m in _NUMBER.findall(text)]


def tools_called(result: AgentResult) -> list[str]:
    return [c["function"]["name"] for m in result.messages for c in m.get("tool_calls") or []]


def check_case(case: EvalCase, result: AgentResult, registry: ToolRegistry) -> list[CheckResult]:
    exp, answer = case.expect, result.answer
    lower = answer.lower()
    checks = []
    if exp.contains_any:
        hit = [w for w in exp.contains_any if w.lower() in lower]
        checks.append(CheckResult("contains_any", bool(hit), f"found {hit}" if hit else f"none of {exp.contains_any}"))
    if exp.contains_all:
        miss = [w for w in exp.contains_all if w.lower() not in lower]
        checks.append(CheckResult("contains_all", not miss, f"missing {miss}" if miss else "all found"))
    if exp.not_contains:
        bad = [w for w in exp.not_contains if w.lower() in lower]
        checks.append(CheckResult("not_contains", not bad, f"found {bad}" if bad else "ok"))
    if exp.tools_called:
        used = set(tools_called(result))
        miss = [t for t in exp.tools_called if t not in used]
        checks.append(CheckResult("tools_called", not miss, f"missing {miss}" if miss else "ok"))
    if exp.number:
        target = expected_number(exp.number, registry)
        tolerance = max(abs(target) * exp.number.tolerance_pct / 100, 0.05)
        close = [n for n in extract_numbers(answer) if abs(n - target) <= tolerance]
        checks.append(
            CheckResult("number", bool(close), f"expected {target} ±{exp.number.tolerance_pct}%, " + (f"found {close[0]}" if close else "no match"))
        )
    return checks


def run_case(agent, case: EvalCase, registry: ToolRegistry) -> CaseResult:
    started = time.monotonic()
    try:
        result = agent.run(case.question)
    except (FatalLLMError, BudgetExceeded):
        raise
    except LLMError as e:
        return CaseResult(case.id, False, error=str(e).splitlines()[0], seconds=time.monotonic() - started)
    checks = check_case(case, result, registry)
    return CaseResult(
        id=case.id,
        passed=all(c.passed for c in checks),
        checks=checks,
        answer=result.answer,
        steps=result.steps,
        models=list(dict.fromkeys(result.models_used)),
        tools=tools_called(result),
        seconds=round(time.monotonic() - started, 1),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="energy-harness-eval", description="Score the agent on the simulated fleet.")
    parser.add_argument("--config")
    parser.add_argument("--cases", default=str(POC_ROOT / "evals.yaml"), help="eval suite file")
    parser.add_argument("--case", action="append", help="run only these case ids")
    parser.add_argument("--model", action="append", help="model(s) to use instead of the configured chain")
    parser.add_argument("--list", action="store_true", help="list cases and exit")
    args = parser.parse_args(argv)

    suite = EvalSuite.from_file(Path(args.cases))
    cases = [c for c in suite.cases if not args.case or c.id in args.case]
    if args.list or not cases:
        for c in suite.cases:
            print(f"{c.id:22} {c.question}")
        return 0 if cases else 2

    settings = load_settings(args.config)
    settings.data_source = "simulation"
    simulator = build_simulator(settings)
    registry = build_registry(settings, simulator=simulator)
    tracer = Tracer(settings.runs_dir, echo=False)
    agent = build_agent(settings, models=args.model, tracer=tracer, simulator=simulator)
    print(f"Running {len(cases)} case(s) on {args.model or settings.models} (typically 2–5 requests each)", file=sys.stderr)

    results: list[CaseResult] = []
    for case in cases:
        try:
            r = run_case(agent, case, registry)
        except (FatalLLMError, BudgetExceeded) as e:
            print(f"stopped: {e}", file=sys.stderr)
            break
        results.append(r)
        status = "PASS" if r.passed else "FAIL"
        detail = r.error or "; ".join(f"{c.name}: {c.detail}" for c in r.checks if not c.passed)
        print(f"{status}  {r.id:22} {r.steps} steps {r.seconds:5.1f}s  {','.join(r.models)}  {detail}", file=sys.stderr)

    passed = sum(r.passed for r in results)
    print(f"\nScore: {passed}/{len(results)} passed" + (f" ({len(cases) - len(results)} not run)" if len(results) < len(cases) else ""))
    out = settings.runs_dir / f"eval-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"models": args.model or settings.models, "score": [passed, len(results)], "results": [asdict(r) for r in results]}, indent=2, default=str))
    print(f"Details: {out}  ·  trace: {tracer.path}", file=sys.stderr)
    return 0 if results and passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
