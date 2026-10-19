"""Tests for the explanation server. No network: the provider is replaced by a mock transport.

Run: python -m pytest tools/kpi-lab/test_server.py -q
"""

import json
import sys
from pathlib import Path

import httpx
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


def test_gateway_reads_reply_from_mock_provider(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-real")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "model": "claude-sonnet-5-5",
            "content": [{"type": "text", "text": "Output was 92.6 % of expected."}],
        })

    reply = anthropic_client.explain("sys", "user", transport=httpx.MockTransport(handler))
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
        anthropic_client.explain("s", "u", transport=httpx.MockTransport(lambda r: httpx.Response(401)))
    assert "test-not-real" not in str(info.value)


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
