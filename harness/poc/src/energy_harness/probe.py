"""Live check of each free model in the chain: does it answer, and does it call tools correctly?

Uses 2 requests per model (of the 50/day free quota). Run it when picking or
re-ranking models: `energy-harness-probe` or `energy-harness-probe --model x:free`.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass

from .config import load_settings
from .factory import build_budget, build_client
from .llm import FatalLLMError, LLMError
from .tools import tool


@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@dataclass
class ProbeResult:
    model: str
    answers: bool = False
    tool_call_ok: bool = False
    latency_s: float | None = None
    served_by: str | None = None
    error: str | None = None

    @property
    def rank_key(self) -> tuple:
        return (not self.tool_call_ok, not self.answers, self.latency_s or float("inf"))


def probe_model(client) -> ProbeResult:
    result = ProbeResult(client.models[0])
    try:
        plain = client.chat([{"role": "user", "content": "Reply with exactly the word: OK"}])
        result.answers = "ok" in (plain.message.get("content") or "").lower()
        result.latency_s = plain.latency_s
        result.served_by = plain.model

        resp = client.chat(
            [{"role": "user", "content": "What is 17 + 25? Use the add tool."}],
            tools=[add.schema()],
        )
        calls = resp.message.get("tool_calls") or []
        if calls and calls[0]["function"]["name"] == "add":
            args = calls[0]["function"]["arguments"]
            args = json.loads(args) if isinstance(args, str) else args
            result.tool_call_ok = float(args.get("a")) + float(args.get("b")) == 42
        if not result.tool_call_ok:
            got = json.dumps(calls) if calls else f"text: {resp.message.get('content') or ''}"
            result.error = f"bad tool call: {got[:150]}"
    except FatalLLMError:
        raise
    except (LLMError, ValueError, TypeError, KeyError) as e:
        result.error = str(e).splitlines()[-1][:200]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="energy-harness-probe", description=__doc__.splitlines()[0])
    parser.add_argument("--config")
    parser.add_argument("--model", action="append", help="model(s) to probe instead of the configured chain")
    parser.add_argument("--dry-run", action="store_true", help="show what would be probed without calling the API")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    models = args.model or settings.models
    print(f"Probing {len(models)} model(s), {2 * len(models)} requests:", file=sys.stderr)
    for m in models:
        print(f"  - {m}", file=sys.stderr)
    if args.dry_run:
        return 0

    budget = build_budget(settings)
    results = []
    for model in models:
        client = build_client(settings, [model], budget=budget, retries_per_model=0)
        try:
            results.append(probe_model(client))
        except FatalLLMError as e:
            print(f"\nstopped: {e}", file=sys.stderr)
            break
        r = results[-1]
        print(f"  {model}: {'tools ok' if r.tool_call_ok else 'tools FAIL' if r.answers else 'unreachable'}", file=sys.stderr)

    results.sort(key=lambda r: r.rank_key)
    print(f"\n{'model':45} {'answers':8} {'tools':6} {'latency':8} served_by / error")
    for r in results:
        latency = f"{r.latency_s:.1f}s" if r.latency_s else "-"
        print(f"{r.model:45} {'yes' if r.answers else 'no':8} {'yes' if r.tool_call_ok else 'no':6} {latency:8} {r.error or r.served_by or ''}")

    good = [r.model for r in results if r.tool_call_ok]
    if good:
        print("\nSuggested config.yaml chain:\nmodels:")
        for m in good + (["openrouter/free"] if "openrouter/free" not in good else []):
            print(f"  - {m}")
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
