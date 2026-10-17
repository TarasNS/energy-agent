"""JSONL traces: one file per session, one line per event."""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class NullTracer:
    def event(self, kind: str, **data: Any) -> None:
        pass


class Tracer:
    def __init__(self, runs_dir: Path, echo: bool = False) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.path = Path(runs_dir) / f"{stamp}-{uuid.uuid4().hex[:6]}.jsonl"
        self.echo = echo

    def event(self, kind: str, **data: Any) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "event": kind, **data}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
        if self.echo:
            _echo(kind, data)


def _echo(kind: str, data: dict) -> None:
    if kind == "llm_call":
        fallback = f" after {len(data['failed_models'])} failed" if data.get("failed_models") else ""
        print(f"  · step {data['step']}: {data['model']} ({data['latency_s']:.1f}s{fallback})", file=sys.stderr)
    elif kind == "tool_call":
        status = "ok" if data["ok"] else "ERROR"
        print(f"    ↳ {data['name']}({data['arguments']}) → {status}", file=sys.stderr)
