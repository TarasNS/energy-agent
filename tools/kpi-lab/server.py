"""Local server for the KPI chat.

- GET  /               the chat page (index.html); charts.js and config.js are the only other files served.
- POST /api/chat       {question} -> the agent answer (harness/agent.py). 429 when the daily cap is used up first.
- POST /api/approve    {proposal_id, approver} -> {status}. The server issues the one-time token itself;
                       the browser never sees it.
- GET  /health         {status, calls_left_today}

The model never computes numbers: harness/agent.py checks every number in an answer against the
question and the tool results, and withholds the text if one is not there.

Run from the repo root:  python tools/kpi-lab/server.py   (serves on http://127.0.0.1:8000)
Key: ANTHROPIC_API_KEY in the git-ignored .env file, or in the environment.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# Same import roots as PYTHONPATH on Azure (see the deploy notes in PLAN.md, Task 9).
for _root in (ROOT, ROOT / "mcp" / "kpi-solar", ROOT / "mcp" / "actions"):
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from actions import approve_action, issue_approval_token, propose_action  # noqa: E402
from harness import agent as harness_agent  # noqa: E402
from harness.agent import check_numbers  # noqa: E402,F401  (re-exported; the agent does the number check)
from harness.dataset import build as build_dataset  # noqa: E402
from harness.energy_tools import build_energy_tools  # noqa: E402

PUBLIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "charts.js": "text/javascript; charset=utf-8",
    "config.js": "text/javascript; charset=utf-8",
}
MAX_BODY_BYTES = 64 * 1024

DATASET = build_dataset()

DAILY_CAP = int(os.environ.get("KPI_DAILY_CAP", "100"))
CAP_FILE = Path(os.environ.get("KPI_CAP_FILE", "./artifacts/cap.json"))
ALLOWED_ORIGINS = {o.strip() for o in os.environ.get("KPI_ALLOWED_ORIGINS", "").split(",") if o.strip()}

_cap_lock = threading.Lock()
_approve_lock = threading.Lock()
_spent: set[str] = set()  # proposals already approved by this process


def _today(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def _read_cap() -> dict:
    """The stored {day, used}. A missing or unreadable file counts as nothing used yet."""
    try:
        data = json.loads(CAP_FILE.read_text(encoding="utf-8"))
        return {"day": str(data["day"]), "used": int(data["used"])}
    except (OSError, ValueError, KeyError, TypeError):
        return {"day": None, "used": 0}


def _write_cap(state: dict) -> None:
    CAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CAP_FILE.with_name(CAP_FILE.name + ".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    os.replace(tmp, CAP_FILE)  # atomic on the same volume: a crash leaves the old file, never half a file


def take_call_slot(now: datetime | None = None) -> bool:
    """Count one model call against today's cap (UTC day). False when the cap is used up.

    Counted and saved before the call is made, so failed calls count too: the budget is protected either way.
    The count is kept in CAP_FILE, so a restart does not reset it.
    """
    day = _today(now)
    with _cap_lock:
        state = _read_cap()
        used = state["used"] if state["day"] == day else 0
        if used >= DAILY_CAP:
            return False
        _write_cap({"day": day, "used": used + 1})
        return True


def calls_left_today(now: datetime | None = None) -> int:
    day = _today(now)
    with _cap_lock:
        state = _read_cap()
    used = state["used"] if state["day"] == day else 0
    return max(0, DAILY_CAP - used)


def handle_chat(payload: dict) -> tuple[int, dict]:
    question = str(payload.get("question", "")).strip()[:500]
    if not question:
        return 400, {"error": "question is required"}

    drawn = {"calls": 0}

    def take_slot() -> bool:
        if not take_call_slot():
            return False
        drawn["calls"] += 1
        return True

    registry = build_energy_tools(DATASET, propose_action)
    result = harness_agent.run(question, registry, take_slot=take_slot)
    if result.stopped == "cap" and drawn["calls"] == 0:
        return 429, {"error": f"The daily limit of {DAILY_CAP} model calls is used up. Try again tomorrow (UTC)."}
    return 200, {
        "label": DATASET["label"],
        "text": result.text,
        "verified": result.verified,
        "note": result.note,
        "charts": result.charts,
        "proposals": result.proposals,
        "trace": result.trace,
        "stopped": result.stopped,
    }


def handle_approve(payload: dict) -> tuple[int, dict]:
    proposal_id = str(payload.get("proposal_id", ""))[:64]
    approver = str(payload.get("approver", "")).strip()[:100]
    if not proposal_id or not approver:
        return 400, {"error": "proposal_id and approver are required"}

    with _approve_lock:
        token = ""  # an empty token is always refused, and the refusal is audited
        if proposal_id not in _spent:
            try:
                token = issue_approval_token(proposal_id)
            except KeyError:  # unknown proposal: approve_action refuses it
                token = ""
        outcome = approve_action(proposal_id, token, approver)
        if outcome["status"] == "executed_simulated":
            _spent.add(proposal_id)
    return 200, {"status": outcome["status"]}


def handle_health() -> tuple[int, dict]:
    return 200, {"status": "ok", "calls_left_today": calls_left_today()}


class Handler(BaseHTTPRequestHandler):
    server_version = "kpi-lab"
    sys_version = ""

    def log_message(self, fmt, *args):  # keep the console quiet; never log request bodies
        return

    def _cors(self):
        origin = self.headers.get("Origin", "")
        if origin and origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            return self._json(*handle_health())
        name = "index.html" if path == "/" else path.lstrip("/")
        if name not in PUBLIC_FILES:
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = (HERE / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", PUBLIC_FILES[name])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        routes = {"/api/chat": handle_chat, "/api/approve": handle_approve}
        route = routes.get(urlsplit(self.path).path)
        if route is None:
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request too large"})
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "invalid JSON"})
        if not isinstance(payload, dict):
            return self._json(400, {"error": "a JSON object is required"})
        try:
            status, body = route(payload)
        except Exception as exc:  # noqa: BLE001  never send a traceback or a key to the browser
            print(f"request failed: {type(exc).__name__}", file=sys.stderr, flush=True)
            status, body = 500, {"error": "internal error; see the server log"}
        self._json(status, body)

    def _json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        self.wfile.write(data)


def load_local_env() -> None:
    """Local runs read .env; Azure sets the same variables as app settings."""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def log_startup_error(exc: BaseException) -> None:
    """Write the traceback where Azure exposes it (/home/LogFiles) or next to the app. No secrets in it."""
    import traceback

    text = "".join(traceback.format_exception(exc))
    for target in (Path("/home/LogFiles/kpi-lab-error.log"), HERE / "startup-error.log"):
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            break
        except OSError:
            continue
    print(text, file=sys.stderr, flush=True)


def main() -> None:
    load_local_env()
    host = os.environ.get("KPI_LAB_HOST", "127.0.0.1")
    port = int(os.environ.get("KPI_LAB_PORT") or os.environ.get("PORT", "8000"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"KPI chat on http://{host}:{port}/index.html  (Ctrl+C to stop)")
    httpd.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        log_startup_error(exc)
        raise
