"""Local web UI for testing the harness: chat with live step trace, eval runner, simulated-data explorer.

    energy-harness-web            # or: python -m energy_harness.web
    → http://127.0.0.1:8765

Standard library only. Binds to localhost; the API key stays on the server and
is never sent to the browser. Long-running calls stream NDJSON (one JSON event
per line) so the page can show each model call and tool call as it happens.
"""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from datetime import date, datetime, time, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from ..agent import Agent
from ..budget import BudgetExceeded, RequestBudget
from ..config import POC_ROOT, Settings, load_settings
from ..energy.parks import ParkRegistry
from ..energy.sim import Scenario, Simulator
from ..evals import EvalSuite, run_case
from ..factory import build_agent, build_budget, build_registry
from ..llm import LLMError
from ..trace import Tracer

STATIC = Path(__file__).parent / "static"
MAX_BODY = 1_000_000


class App:
    """Everything the HTTP handler needs. Tests subclass it and override `make_agent`."""

    def __init__(self, settings: Settings, evals_file: Path = POC_ROOT / "evals.yaml") -> None:
        self.settings = settings
        self.simulator = Simulator(Scenario.from_file(settings.simulation_file))
        self.suite = EvalSuite.from_file(evals_file) if Path(evals_file).exists() else None
        self.budget: RequestBudget = build_budget(settings)
        self._lock = threading.Lock()  # one agent run at a time keeps the free-tier budget predictable

    # --- agents -------------------------------------------------------------------

    def make_agent(self, mode: str, models: list[str] | None, tracer: Tracer) -> Agent:
        settings = self.settings.model_copy(update={"data_source": mode})
        simulator = self.simulator if mode == "simulation" else None
        return build_agent(settings, models=models, tracer=tracer, simulator=simulator, budget=self.budget)

    def registry(self, mode: str):
        settings = self.settings.model_copy(update={"data_source": mode})
        return build_registry(settings, simulator=self.simulator if mode == "simulation" else None)

    # --- endpoints --------------------------------------------------------------------

    def info(self) -> dict:
        live_parks = ParkRegistry.from_file(self.settings.parks_file).parks
        return {
            "models": self.settings.models,
            "default_mode": self.settings.data_source,
            "has_key": bool(self.settings.api_key),
            "max_steps": self.settings.max_steps,
            "budget": {"used_today": self.budget.used_today, "per_day": self.budget.per_day},
            "simulation": {
                "now": self.simulator.now().isoformat(),
                "parks": [p.model_dump(exclude_none=True) for p in self.simulator.parks.parks],
                "events": [e.model_dump(mode="json", exclude_none=True) for e in self.simulator.scenario.events],
            },
            "live_parks": [p.model_dump(exclude_none=True) for p in live_parks],
            "evals": [c.model_dump(mode="json", exclude_none=True) for c in self.suite.cases] if self.suite else [],
        }

    def ask(self, body: dict, emit: Callable[[dict], None]) -> None:
        question = str(body.get("question") or "").strip()
        if not question:
            emit({"event": "error", "message": "Empty question."})
            return
        mode = "live" if body.get("mode") == "live" else "simulation"
        if not self._ready(emit):
            return
        with self._lock:
            tracer = Tracer(self.settings.runs_dir, listener=emit)
            try:
                agent = self.make_agent(mode, _models(body), tracer)
                result = agent.run(question, history=body.get("history") or None)
            except (LLMError, BudgetExceeded) as e:
                emit({"event": "error", "message": str(e)})
                return
            emit(
                {
                    "event": "answer",
                    "answer": result.answer,
                    "stopped_reason": result.stopped_reason,
                    "steps": result.steps,
                    "models_used": list(dict.fromkeys(result.models_used)),
                    "history": result.history,
                    "trace_file": str(tracer.path),
                    "budget": {"used_today": self.budget.used_today, "per_day": self.budget.per_day},
                }
            )

    def run_evals(self, body: dict, emit: Callable[[dict], None]) -> None:
        if not self.suite:
            emit({"event": "error", "message": "No evals.yaml found."})
            return
        wanted = set(body.get("cases") or [])
        cases = [c for c in self.suite.cases if not wanted or c.id in wanted]
        if not self._ready(emit):
            return
        registry = self.registry("simulation")
        with self._lock:
            tracer = Tracer(self.settings.runs_dir)
            agent = self.make_agent("simulation", _models(body), tracer)
            for case in cases:
                emit({"event": "case_start", "id": case.id})
                try:
                    r = run_case(agent, case, registry)
                except (LLMError, BudgetExceeded) as e:
                    emit({"event": "error", "message": str(e)})
                    return
                emit(
                    {
                        "event": "case_result",
                        "id": r.id,
                        "passed": r.passed,
                        "checks": [c.__dict__ for c in r.checks],
                        "answer": r.answer,
                        "steps": r.steps,
                        "models": r.models,
                        "tools": r.tools,
                        "seconds": r.seconds,
                        "error": r.error,
                    }
                )
            emit({"event": "done", "trace_file": str(tracer.path), "budget": {"used_today": self.budget.used_today, "per_day": self.budget.per_day}})

    def sim_day(self, park_id: str, day: date) -> dict:
        sim = self.simulator
        park = sim.parks.get(park_id)
        start = datetime.combine(day, time(), timezone.utc)
        end = start + timedelta(days=1)
        now = sim.now()
        samples = sim.production(park, start, end)
        prices = []
        if park.bidding_zone:
            for p in sim.prices(park.bidding_zone, day - timedelta(days=1), day + timedelta(days=1)):
                if start <= p.time < end:
                    prices.append({"t": p.time.isoformat(), "eur_per_mwh": p.eur_per_mwh})
        events = [
            e.model_dump(mode="json", exclude_none=True)
            for e in sim.scenario.events
            if e.start < end and e.end > start and (e.park == park.id or (e.zone and e.zone == park.bidding_zone))
        ]
        return {
            "park": park.model_dump(exclude_none=True),
            "date": day.isoformat(),
            "now": now.isoformat(),
            "samples": [
                {
                    "t": s.time.isoformat(),
                    "expected_mw": s.expected_mw,
                    "metered_mw": s.metered_mw if s.time < now else None,
                    "availability": s.availability,
                    "curtailed": s.curtailed,
                }
                for s in samples
            ],
            "prices": prices,
            "events": events,
            "expected_mwh": round(sum(s.expected_mw for s in samples) * 0.25, 1),
            "metered_mwh": round(sum((s.metered_mw or 0) for s in samples if s.time < now) * 0.25, 1),
        }

    def _ready(self, emit) -> bool:
        if not self.settings.api_key:
            emit({"event": "error", "message": "OPENROUTER_API_KEY is not set. Put it in harness/poc/.env and restart the server."})
            return False
        if self._lock.locked():
            emit({"event": "status", "message": "Waiting for the previous run to finish…"})
        return True


def _models(body: dict) -> list[str] | None:
    models = [m.strip() for m in body.get("models") or [] if isinstance(m, str) and m.strip()]
    return models or None


class Handler(BaseHTTPRequestHandler):
    app: App  # set on the subclass created in make_server

    def log_message(self, fmt: str, *args: Any) -> None:  # keep the console quiet
        pass

    def do_GET(self) -> None:
        url = urlparse(self.path)
        try:
            if url.path in ("/", "/index.html"):
                self._send_file(STATIC / "index.html", "text/html; charset=utf-8")
            elif url.path == "/api/info":
                self._send_json(self.app.info())
            elif url.path == "/api/sim/day":
                q = parse_qs(url.query)
                self._send_json(self.app.sim_day(q["park"][0], date.fromisoformat(q["date"][0])))
            else:
                self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (KeyError, ValueError) as e:
            self._send_json({"error": f"bad request: {e}"}, HTTPStatus.BAD_REQUEST)
        except Exception as e:  # e.g. ToolError for an unknown park
            self._send_json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        url = urlparse(self.path)
        routes = {"/api/ask": self.app.ask, "/api/eval": self.app.run_evals}
        if url.path not in routes:
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send_json({"error": "request too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._send_json({"error": "invalid JSON"}, HTTPStatus.BAD_REQUEST)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(event: dict) -> None:
            try:
                self.wfile.write((json.dumps(event, default=str, ensure_ascii=False) + "\n").encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # browser went away; the run still finishes and is traced

        try:
            routes[url.path](body, emit)
        except Exception as e:
            emit({"event": "error", "message": f"{type(e).__name__}: {e}"})

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, path: Path, content_type: str) -> None:
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def make_server(app: App, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"app": app})
    return ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="energy-harness-web", description="Local web UI for the energy harness.")
    parser.add_argument("--config")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args(argv)

    app = App(load_settings(args.config))
    server = make_server(app, port=args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"Energy harness UI on {url}  (Ctrl+C to stop)")
    if not app.settings.api_key:
        print("warning: OPENROUTER_API_KEY not set; chat and evals will not work until you add it to .env")
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
