"""Tests for the explanation server. No network: the provider is replaced by a mock transport.

Run: python -m pytest tools/kpi-lab/test_server.py -q
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import server  # noqa: E402
from model.model_gateway import anthropic_client  # noqa: E402

RESULTS = [
    {"title": "Actual vs expected generation", "value": 92.6, "display": "92.6 %"},
    {"title": "Downtime", "value": 51.0, "display": "51.00 h"},
    {"title": "Incident resolution", "value": None, "unavailable": "no ticket data"},
]


def test_quoting_calculator_numbers_passes():
    reply = "Output was 92.6 % of expected, with 51.00 h of downtime."
    assert server.check_numbers(reply, RESULTS, "how is it going") == []


def test_invented_number_is_caught():
    reply = "Output was 95.0 % of expected."
    assert server.check_numbers(reply, RESULTS, "how is it going") == ["95.0"]


def test_numbers_in_the_question_are_allowed():
    # "3" is in the question, and the count of KPIs is also allowed
    assert server.check_numbers("Checked 3 KPIs for day 3.", RESULTS, "day 3") == []


def test_unavailable_kpi_has_no_value_line():
    msg = server.build_user_message("q", RESULTS)
    assert "Incident resolution: UNAVAILABLE (no ticket data)" in msg
    assert "92.6 %" in msg


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


# ── Daily cap and CORS ────────────────────────────────────────────────────

from datetime import datetime, timezone  # noqa: E402


def test_daily_cap_stops_calls_at_the_limit(monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 3)
    monkeypatch.setitem(server._cap, "day", None)
    monkeypatch.setitem(server._cap, "used", 0)
    day = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
    assert [server.take_call_slot(day) for _ in range(4)] == [True, True, True, False]


def test_daily_cap_resets_on_a_new_day(monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 1)
    monkeypatch.setitem(server._cap, "day", None)
    monkeypatch.setitem(server._cap, "used", 0)
    assert server.take_call_slot(datetime(2026, 10, 20, tzinfo=timezone.utc))
    assert not server.take_call_slot(datetime(2026, 10, 20, 23, tzinfo=timezone.utc))
    assert server.take_call_slot(datetime(2026, 10, 21, tzinfo=timezone.utc))


def test_capped_request_makes_no_provider_call(monkeypatch):
    monkeypatch.setattr(server, "DAILY_CAP", 0)
    monkeypatch.setitem(server._cap, "day", None)
    monkeypatch.setitem(server._cap, "used", 0)
    called = []
    monkeypatch.setattr(server, "explain", lambda *a, **k: called.append(1))
    out = server.explain_results({"question": "q", "results": [{"title": "A", "value": 1.0, "display": "1.0 %"}]})
    assert out["status"] == 429 and called == []


def test_cors_allows_only_listed_origins(monkeypatch):
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", {"https://example.azurestaticapps.net"})
    assert "https://example.azurestaticapps.net" in server.ALLOWED_ORIGINS
    assert "https://evil.example" not in server.ALLOWED_ORIGINS


# ── Tool use in the gateway ───────────────────────────────────────────────

import httpx  # noqa: E402

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
