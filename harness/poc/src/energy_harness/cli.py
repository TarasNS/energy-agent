"""Command line: one-shot question or interactive REPL."""

from __future__ import annotations

import argparse
import sys

from .budget import BudgetExceeded
from .config import load_settings
from .factory import build_agent
from .llm import LLMError
from .trace import Tracer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="energy-harness",
        description="Ask energy questions (PV production, day-ahead prices, irradiance) using free OpenRouter models.",
    )
    parser.add_argument("question", nargs="?", help="question to ask; omit for an interactive session")
    parser.add_argument("--config", help="path to config.yaml")
    parser.add_argument("--model", action="append", help="model to use (repeat for a fallback chain); overrides config")
    parser.add_argument("--max-steps", type=int, help="max LLM calls per question")
    parser.add_argument("-q", "--quiet", action="store_true", help="don't print model/tool activity to stderr")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    if args.max_steps:
        settings.max_steps = args.max_steps
    tracer = Tracer(settings.runs_dir, echo=not args.quiet)
    agent = build_agent(settings, models=args.model, tracer=tracer)

    if args.question:
        return 0 if _ask(agent, args.question, None) is not None else 1

    print("Energy agent — free OpenRouter models. Type 'exit' or Ctrl-D to quit.", file=sys.stderr)
    history: list[dict] | None = None
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return 0
        if question.lower() in {"exit", "quit"}:
            return 0
        if question:
            result = _ask(agent, question, history)
            if result is not None:
                history = result.history


def _ask(agent, question: str, history):
    try:
        result = agent.run(question, history=history)
    except (LLMError, BudgetExceeded) as e:
        print(f"error: {e}", file=sys.stderr)
        return None
    print(result.answer)
    note = " (step limit reached)" if result.stopped_reason == "max_steps" else ""
    print(f"\n[{', '.join(dict.fromkeys(result.models_used))} · {result.steps} steps{note} · trace: {agent.tracer.path}]", file=sys.stderr)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
