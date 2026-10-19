"""Tests for the KPI chat server. No network: the model is replaced by a fake or a mock transport.

Run: python -m pytest -o addopts="" tools/kpi-lab/test_server.py -q
"""

import importlib
import json
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import server  # noqa: E402
from actions import propose_action  # noqa: E402
from harness import agent as harness_agent  # noqa: E402
from harness.agent import AgentResult  # noqa: E402
from model.model_gateway import anthropic_client  # noqa: E402

RESULTS = [
    {"title": "Actual vs expected generation", "value": 92.6, "display": "92.6 %"},
    {"title": "Downtime", "value": 51.0, "display": "51.00 h"},
    {"title": "Incident resolution", "value": None, "unavailable": "no ticket data"},
]

CHART = {"chart_id": "c1", "kind": "bar", "title": "Availability by park",
         "series": [{"name": "Availability %", "points": [{"x": "north", "y": "96.5"}]}]}

NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own cap file, audit log and spent-proposal set. Nothing is written to artifacts/."""
    monkeypatch.setattr(server, "CAP_FILE", tmp_path / "cap.json", raising=False)
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setattr(server, "_spent", set(), raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
def base_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


def call(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with NO_PROXY.open(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def audit_lines(tmp_path):
    path = tmp_path / "audit.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# ── Numbers are checked against the calculator output ─────────────────────

def test_quoting_calculator_numbers_passes():
    reply = "Output was 92.6 % of expected, with 51.00 h of downtime."
    assert server.check_numbers(reply, RESULTS, "how is it going") == []


def test_invented_number_is_caught():
    reply = "Output was 95.0 % of expected."
    assert server.check_numbers(reply, RESULTS, "how is it going") == ["95.0"]


def test_numbers_in_the_question_are_allowed():
    # "3" is in the question, and the count of KPIs is also allowed
    assert server.check_numbers("Checked 3 KPIs for day 3.", RESULTS, "day 3") == []


def test_check_numbers_is_the_agent_check():
    # server.py imports the agent's check instead of keeping its own copy
    assert server.check_numbers is harness_agent.check_numbers


def test_gateway_reads_reply_from_fake_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")
    seen = {}

    def transport(url, headers, body, timeout_s):
        seen["headers"], seen["body"] = headers, json.loads(body)
        return 200, json.dumps({
            "model": "claude-haiku-5-5",
            "content": [{"type": "text", "text": "Output was 92.6 % of expected."}],
        }).encode()

    reply = anthropic_client.explain("sys", "user", transport=transport)
    assert reply.text == "Output was 92.6 % of expected."
    assert seen["headers"]["x-api-key"] == "test-not-real"
    assert seen["body"]["system"] == "sys"


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(anthropic_client.ModelUnavailable, match="ANTHROPIC_API_KEY is not set"):
        anthropic_client.explain("s", "u")


def test_provider_error_is_surfaced_without_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")
    with pytest.raises(anthropic_client.ModelUnavailable, match="HTTP 401") as info:
        anthropic_client.explain("s", "u", transport=lambda *a: (401, b""))
    assert "test-not-real" not in str(info.value)


def test_unreadable_provider_answer_is_an_error(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")
    with pytest.raises(anthropic_client.ModelUnavailable, match="unreadable"):
        anthropic_client.explain("s", "u", transport=lambda *a: (200, b"not json"))


# ── Daily cap (persisted in KPI_CAP_FILE) ─────────────────────────────────

def test_daily_cap_stops_calls_at_the_limit(monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 3)
    day = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    assert [server.take_call_slot(day) for _ in range(4)] == [True, True, True, False]


def test_daily_cap_resets_on_a_new_day(monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 1)
    assert server.take_call_slot(datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert not server.take_call_slot(datetime(2026, 10, 20, 23, tzinfo=timezone.utc))
    assert server.take_call_slot(datetime(2026, 10, 21, tzinfo=timezone.utc))


def test_cap_survives_restart(tmp_path, monkeypatch):
    cap_file = tmp_path / "restart-cap.json"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cap_file.write_text(json.dumps({"day": today, "used": 2}), encoding="utf-8")
    monkeypatch.setenv("KPI_CAP_FILE", str(cap_file))
    monkeypatch.setenv("KPI_DAILY_CAP", "3")
    try:
        restarted = importlib.reload(server)  # a restarted process reads the environment again
        assert restarted.take_call_slot() is True      # the 3rd call of the day
        assert restarted.take_call_slot() is False     # the count continued from 2, so the cap is reached
        assert json.loads(cap_file.read_text(encoding="utf-8")) == {"day": today, "used": 3}
    finally:
        monkeypatch.undo()
        importlib.reload(server)


def test_cors_allows_only_listed_origins(monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {"https://example.azurestaticapps.net"})
    assert "https://example.azurestaticapps.net" in server.ALLOWED_ORIGINS
    assert "https://evil.example" not in server.ALLOWED_ORIGINS


# ── Endpoints ─────────────────────────────────────────────────────────────

def test_chat_returns_agent_result(base_url, monkeypatch):
    seen = {}

    def fake_run(question, registry, *, take_slot, **_):
        seen["question"] = question
        seen["tools"] = set(registry.names())
        assert take_slot() is True
        return AgentResult(
            text="Availability was 96.5 %.", verified=True, note=None,
            charts=[CHART],
            proposals=[],
            trace=[{"tool": "get_kpi", "input": {"kpi": "availability"}, "ok": True}],
            stopped="answered",
        )

    monkeypatch.setattr(harness_agent, "run", fake_run)
    status, raw = call(base_url, "POST", "/api/chat", {"question": "availability?"})
    body = json.loads(raw)

    assert status == 200
    assert set(body) == {"label", "text", "verified", "note", "charts", "proposals", "trace", "stopped"}
    assert body["label"] == "SYNTHETIC: not Nordic Solar data"
    assert body["text"] == "Availability was 96.5 %." and body["verified"] is True
    assert body["charts"] == [CHART] and body["stopped"] == "answered"
    assert seen["question"] == "availability?"
    assert len(seen["tools"]) == 9 and "approve_action" not in seen["tools"]


def test_chat_is_429_when_cap_is_used_up_before_the_first_call(base_url, monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 0)
    # No API key is set, so any model call would fail with model_error. A 429 proves no call was made.
    status, raw = call(base_url, "POST", "/api/chat", {"question": "availability?"})
    assert status == 429
    assert "error" in json.loads(raw)


def test_approve_endpoint_never_returns_token(base_url, monkeypatch, tmp_path):
    pid = propose_action("schedule_inspection", "north", "low availability")
    issued = []
    real_issue = server.issue_approval_token

    def spy(proposal_id):
        token = real_issue(proposal_id)
        issued.append(token)
        return token

    monkeypatch.setattr(server, "issue_approval_token", spy)
    status, raw = call(base_url, "POST", "/api/approve", {"proposal_id": pid, "approver": "reviewer-a"})

    assert status == 200
    assert json.loads(raw) == {"status": "executed_simulated"}
    assert issued and issued[0].encode("utf-8") not in raw
    assert issued[0] not in (tmp_path / "audit.jsonl").read_text(encoding="utf-8")


def test_second_approve_of_the_same_proposal_is_denied(base_url, tmp_path):
    pid = propose_action("review_ppa_volume", "south", "r")
    first = call(base_url, "POST", "/api/approve", {"proposal_id": pid, "approver": "reviewer-a"})
    second = call(base_url, "POST", "/api/approve", {"proposal_id": pid, "approver": "reviewer-a"})

    assert json.loads(first[1]) == {"status": "executed_simulated"}
    assert json.loads(second[1]) == {"status": "denied"}
    assert audit_lines(tmp_path)[-1]["event"] == "approval_denied"


def test_health_reports_calls_left(base_url, tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 100)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (tmp_path / "cap.json").write_text(json.dumps({"day": today, "used": 40}), encoding="utf-8")

    first = call(base_url, "GET", "/health")
    second = call(base_url, "GET", "/health")

    assert first[0] == 200
    assert json.loads(first[1]) == {"status": "ok", "calls_left_today": 60}
    assert json.loads(second[1]) == {"status": "ok", "calls_left_today": 60}  # reading does not spend a call


def test_source_files_are_not_served(base_url):
    index = (HERE / "index.html").read_bytes()

    assert call(base_url, "GET", "/")[1] == index
    assert call(base_url, "GET", "/index.html")[1] == index
    assert call(base_url, "GET", "/charts.js")[0] == 200
    assert call(base_url, "GET", "/config.js")[0] == 200
    for path in ["/server.py", "/test_server.py", "/data.js", "/engine.js", "/kpi.js",
                 "/tools", "/../server.py", "/%2e%2e/server.py", "/api/explain"]:
        assert call(base_url, "GET", path)[0] == 404, path
    assert call(base_url, "POST", "/api/explain", {"question": "q"})[0] == 404


# ── Tool use in the gateway ───────────────────────────────────────────────

GET_KPI_TOOL = {
    "type": "function",
    "function": {
        "name": "get_kpi",
        "description": "Get one KPI by id.",
        "parameters": {"type": "object", "properties": {"kpi": {"type": "string"}}, "required": ["kpi"]},
    },
}


def test_run_turn_parses_tool_use(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "model": "claude-haiku-5-5",
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": "Checking."},
                {"type": "tool_use", "id": "t1", "name": "get_kpi", "input": {"kpi": "availability"}},
            ],
        })

    turn = anthropic_client.run_turn(
        "sys", [{"role": "user", "content": "q"}], [GET_KPI_TOOL],
        transport=httpx.MockTransport(handler),
    )
    assert turn.tool_calls == [anthropic_client.ToolCall("t1", "get_kpi", {"kpi": "availability"})]
    assert turn.stop_reason == "tool_use"
    assert turn.text == "Checking."
    assert seen["body"]["tools"][0]["input_schema"] == GET_KPI_TOOL["function"]["parameters"]


def test_run_turn_error_does_not_leak_the_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")

    def handler(request):
        return httpx.Response(401, json={"error": "invalid"})

    with pytest.raises(anthropic_client.ModelUnavailable, match="HTTP 401") as info:
        anthropic_client.run_turn("s", [{"role": "user", "content": "u"}], [GET_KPI_TOOL],
                                  transport=httpx.MockTransport(handler))
    assert "test-not-real" not in str(info.value)
