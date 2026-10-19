"""Local server for the KPI chat.

- Serves the chat page (static files in this folder).
- POST /api/explain: asks the model to explain calculator results in plain words.

The model never computes numbers. It gets the calculator results and may only quote them.
Every number in its reply is checked against those results; if one is not there, the
explanation is withheld and the calculator output is shown instead.

Run from the repo root:  python tools/kpi-lab/server.py   (serves on http://127.0.0.1:8000)
Key: ANTHROPIC_API_KEY in the git-ignored .env file, or in the environment.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from model.model_gateway import ModelUnavailable, explain  # noqa: E402

HERE = Path(__file__).resolve().parent
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")

SYSTEM = (
    "You explain KPI results to an energy portfolio analyst in plain English, in at most 90 words.\n"
    "Rules:\n"
    "1. Use ONLY the numbers listed under RESULTS. Do not calculate, estimate, round or add any number.\n"
    "2. If a KPI says it is unavailable, say that it is unavailable and why. Do not guess a value.\n"
    "3. Say the data is synthetic, not company data.\n"
    "4. No recommendations to act on production systems."
)


DAILY_CAP = int(os.environ.get("KPI_DAILY_CAP", "100"))
ALLOWED_ORIGINS = {o.strip() for o in os.environ.get("KPI_ALLOWED_ORIGINS", "").split(",") if o.strip()}

_cap_lock = threading.Lock()
_cap = {"day": None, "used": 0}


def take_call_slot(now: datetime | None = None) -> bool:
    """Count one model call against today's cap (UTC day). False when the cap is used up.

    Counted before the call is made, so failed calls count too: the budget is protected either way.
    """
    day = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    with _cap_lock:
        if _cap["day"] != day:
            _cap["day"], _cap["used"] = day, 0
        if _cap["used"] >= DAILY_CAP:
            return False
        _cap["used"] += 1
        return True


def numbers_in(text: str) -> list[float]:
    return [float(m) for m in NUMBER.findall(text)]


def check_numbers(reply: str, results: list[dict], question: str) -> list[str]:
    """Return the numbers in the reply that do not appear in the calculator results.

    Allowed: values in the results, the question's own numbers, and the count of KPIs.
    """
    allowed = set()
    for r in results:
        if r.get("value") is not None:
            allowed.add(round(float(r["value"]), 6))
        for token in numbers_in(str(r.get("display", ""))):
            allowed.add(round(token, 6))
    allowed.update(round(n, 6) for n in numbers_in(question))
    allowed.add(float(len(results)))
    bad = []
    for n in numbers_in(reply):
        if round(n, 6) not in allowed and str(n) not in bad:
            bad.append(str(n))
    return bad


def build_user_message(question: str, results: list[dict]) -> str:
    lines = []
    for r in results:
        if r.get("value") is None:
            lines.append(f"- {r['title']}: UNAVAILABLE ({r.get('unavailable', 'no reason given')})")
        else:
            lines.append(f"- {r['title']}: {r.get('display', r['value'])}")
    return f"QUESTION: {question}\n\nRESULTS (calculator output, synthetic data):\n" + "\n".join(lines)


def explain_results(payload: dict) -> dict:
    question = str(payload.get("question", ""))[:500]
    results = payload.get("results") or []
    if not isinstance(results, list) or not results:
        return {"status": 400, "body": {"error": "results missing"}}
    if not take_call_slot():
        return {"status": 429, "body": {"error": f"The explanation limit for today ({DAILY_CAP} calls) is used up. The calculator answers still work; try again tomorrow (UTC)."}}
    try:
        reply = explain(SYSTEM, build_user_message(question, results), max_tokens=300)
    except ModelUnavailable as e:
        return {"status": 503, "body": {"error": str(e)}}
    bad = check_numbers(reply.text, results, question)
    if bad:
        return {"status": 200, "body": {
            "verified": False, "text": None, "model": reply.model,
            "note": f"Explanation withheld: it contained numbers not in the calculator output ({', '.join(bad)}). The calculator result is shown instead.",
        }}
    return {"status": 200, "body": {"verified": True, "text": reply.text, "model": reply.model}}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

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

    def do_POST(self):
        if self.path != "/api/explain":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "invalid JSON"})
        out = explain_results(payload)
        self._json(out["status"], out["body"])

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
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"KPI chat on http://{host}:{port}/index.html  (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        log_startup_error(exc)
        raise
