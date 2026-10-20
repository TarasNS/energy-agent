"""The model gateway, tested with no network (SPEC.md §4).

Owner: Dev 1. A fake transport stands in for the HTTP call, so no test sends anything to a model.
The real key is never read: every test that needs a key sets it or points at a temporary .env.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from model.model_gateway import ModelTurn, ModelUnavailable, ToolCall, run_turn
from model.model_gateway.gateway import convert_messages, convert_tools, load_profile

ROOT = Path(__file__).resolve().parents[2]

WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_kpi",
        "description": "One KPI for one asset.",
        "parameters": {
            "type": "object",
            "properties": {"kpi": {"type": "string"}, "asset": {"type": "string"}},
            "required": ["kpi"],
        },
    },
}


class FakeTransport:
    """Records the request and returns a canned reply body (or raises)."""

    def __init__(self, reply: dict | None = None, error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.calls: list[dict] = []

    def __call__(self, url: str, headers: dict, body: bytes, timeout: float) -> str:
        self.calls.append({"url": url, "headers": headers, "body": json.loads(body)})
        if self.error is not None:
            raise self.error
        return json.dumps(self.reply)


@pytest.fixture
def no_key(monkeypatch, tmp_path):
    """No key in the environment, and a .env with no key in it."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    empty_env = tmp_path / ".env"
    empty_env.write_text("ANTHROPIC_API_KEY=\n", encoding="utf-8")
    return empty_env


@pytest.fixture
def with_key(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    return tmp_path / ".env"


def test_tool_schema_is_converted_to_provider_format() -> None:
    assert convert_tools([WEATHER_TOOL]) == [
        {
            "name": "get_kpi",
            "description": "One KPI for one asset.",
            "input_schema": {
                "type": "object",
                "properties": {"kpi": {"type": "string"}, "asset": {"type": "string"}},
                "required": ["kpi"],
            },
        }
    ]


def test_messages_with_a_tool_round_trip_are_converted() -> None:
    messages = [
        {"role": "user", "content": "Availability?"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "toolu_1", "type": "function",
                         "function": {"name": "get_kpi", "arguments": "{\"kpi\": \"availability\"}"}}]},
        {"role": "tool", "tool_call_id": "toolu_1", "content": "{\"value\": \"96.5\"}"},
    ]
    assert convert_messages(messages) == [
        {"role": "user", "content": "Availability?"},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "get_kpi", "input": {"kpi": "availability"}}]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "{\"value\": \"96.5\"}"}]},
    ]


def test_text_reply_gives_text_and_no_tool_calls(with_key, tmp_path) -> None:
    transport = FakeTransport({"content": [{"type": "text", "text": "Availability was 96.5 percent."}],
                               "stop_reason": "end_turn"})
    turn = run_turn("You answer questions.", [{"role": "user", "content": "Hi"}], [WEATHER_TOOL],
                    transport=transport, env_file=tmp_path / ".env")
    assert turn == ModelTurn(text="Availability was 96.5 percent.", tool_calls=[])


def test_tool_call_reply_gives_tool_calls_with_parsed_input(with_key, tmp_path) -> None:
    transport = FakeTransport({
        "content": [
            {"type": "text", "text": "Let me check."},
            {"type": "tool_use", "id": "toolu_1", "name": "get_kpi", "input": {"kpi": "availability"}},
        ],
        "stop_reason": "tool_use",
    })
    turn = run_turn("sys", [{"role": "user", "content": "Availability?"}], [WEATHER_TOOL],
                    transport=transport, env_file=tmp_path / ".env")
    assert turn.text == "Let me check."
    assert turn.tool_calls == [ToolCall(id="toolu_1", name="get_kpi", input={"kpi": "availability"})]


def test_request_carries_model_system_tools_and_key_header(with_key, tmp_path) -> None:
    transport = FakeTransport({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"})
    run_turn("Be brief.", [{"role": "user", "content": "Hi"}], [WEATHER_TOOL], max_tokens=600,
             transport=transport, env_file=tmp_path / ".env")
    sent = transport.calls[0]
    assert sent["body"]["model"] == "claude-haiku-5-5"
    assert sent["body"]["system"] == "Be brief."
    assert sent["body"]["max_tokens"] == 600
    assert sent["body"]["tools"][0]["name"] == "get_kpi"
    assert sent["headers"]["x-api-key"] == "test-key-not-real"


def test_missing_key_raises_model_unavailable(no_key) -> None:
    transport = FakeTransport({"content": [], "stop_reason": "end_turn"})
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=transport, env_file=no_key)
    assert transport.calls == [], "no request may be sent without a key"


def test_failed_call_raises_model_unavailable(with_key, tmp_path) -> None:
    transport = FakeTransport(error=OSError("connection refused"))
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=transport,
                 env_file=tmp_path / ".env")


def test_model_profile_selects_the_model(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PROFILE", raising=False)
    assert load_profile()["model"] == "claude-haiku-5-5"  # default profile
    monkeypatch.setenv("MODEL_PROFILE", "fast")
    assert load_profile()["model"] == "claude-haiku-5-5"
    assert set(json.loads((ROOT / "model" / "profiles.json").read_text())) >= {"default", "fast", "offline"}


SDK_IMPORT = re.compile(r"^\s*(import|from)\s+(anthropic|openai)\b", re.M)
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


def test_no_file_outside_the_gateway_imports_a_provider_sdk() -> None:
    gateway = ROOT / "model" / "model_gateway"
    offenders = []
    for path in ROOT.rglob("*.py"):
        parts = path.relative_to(ROOT).parts
        if any(p in SKIP_DIRS for p in parts) or gateway in path.resolve().parents:
            continue
        if SDK_IMPORT.search(path.read_text(encoding="utf-8", errors="ignore")):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], f"provider SDK imported outside model/model_gateway: {offenders}"


def test_key_in_a_utf8_bom_env_file_is_found(monkeypatch, tmp_path) -> None:
    # Windows editors often save .env with a byte-order mark; the key must still be read.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    bom_env = tmp_path / ".env"
    bom_env.write_bytes("﻿ANTHROPIC_API_KEY=test-key-from-bom\r\n".encode("utf-8"))
    transport = FakeTransport({"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"})
    run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=transport, env_file=bom_env)
    assert transport.calls[0]["headers"]["x-api-key"] == "test-key-from-bom"


def test_unknown_profile_raises_model_unavailable(with_key, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROFILE", "no-such-profile")
    transport = FakeTransport({"content": [], "stop_reason": "end_turn"})
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=transport, env_file=tmp_path / ".env")
    assert transport.calls == []


def test_non_object_reply_raises_model_unavailable(with_key, tmp_path) -> None:
    class ListReply:
        def __call__(self, url, headers, body, timeout):
            return "[1, 2]"
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=ListReply(), env_file=tmp_path / ".env")


def test_malformed_tool_use_block_raises_model_unavailable(with_key, tmp_path) -> None:
    transport = FakeTransport({"content": [{"type": "tool_use", "name": "get_kpi", "input": {}}]})  # no id
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"role": "user", "content": "Hi"}], [], transport=transport, env_file=tmp_path / ".env")


def test_malformed_message_history_raises_model_unavailable(with_key, tmp_path) -> None:
    transport = FakeTransport({"content": [], "stop_reason": "end_turn"})
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [{"content": "no role here"}], [], transport=transport, env_file=tmp_path / ".env")
    assert transport.calls == []
