"""Offline replay of recorded model turns (SPEC.md §4). No network: a transport that fails stands in for HTTP.

Owner: Dev 1. A recording is a JSON list of turns, one file per question. MODEL_PROFILE=offline replays
it in order through run_turn. The agent-loop test (harness/agent.py) waits for Dev 3's loop to merge.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from model.model_gateway import ModelTurn, ModelUnavailable, ToolCall, run_turn
from model.model_gateway import gateway
from model.model_gateway.gateway import reset_recordings

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "hand_written_turns.json"
EXPECTED = [
    ModelTurn(text=None, tool_calls=[ToolCall(id="toolu_1", name="get_kpi",
                                              input={"kpi": "availability", "asset": "portfolio"})]),
    ModelTurn(text="Availability was 96.5 percent.", tool_calls=[]),
]


def no_network(url, headers, body, timeout):
    raise AssertionError("offline replay must not make a network call")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("MODEL_PROFILE", "offline")
    monkeypatch.setenv("MODEL_RECORDING", str(FIXTURE))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # replay needs no key
    # Block the real HTTP path and every socket, so a regression that reaches the network fails the test.
    monkeypatch.setattr(gateway, "_http_post", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_socket)
    monkeypatch.setattr(socket, "create_connection", no_socket)
    reset_recordings()
    yield
    reset_recordings()


def no_socket(*args, **kwargs):
    raise AssertionError("offline replay must not open a socket")


def _ask_twice_in_order() -> list[ModelTurn]:
    return [run_turn("sys", [{"role": "user", "content": "Q"}], []) for _ in range(2)]


def test_the_test_guard_really_blocks_sockets() -> None:
    with pytest.raises(AssertionError):
        socket.create_connection(("example.invalid", 443))


def test_offline_profile_replays_turns_in_order_with_no_network() -> None:
    assert _ask_twice_in_order() == EXPECTED


def test_the_same_recording_gives_the_same_answers_twice() -> None:
    first = _ask_twice_in_order()
    reset_recordings()
    second = _ask_twice_in_order()
    assert first == second == EXPECTED


def test_a_recording_with_no_turns_left_raises_model_unavailable() -> None:
    _ask_twice_in_order()
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [], transport=no_network)


def test_offline_profile_without_a_recording_raises_model_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_RECORDING")
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [], transport=no_network)


def test_missing_recording_file_raises_model_unavailable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_RECORDING", str(tmp_path / "no-such-file.json"))
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [], transport=no_network)


@pytest.mark.parametrize("content", [
    {"text": "not a list"},                                  # not a list of turns
    [{"text": "no tool_calls key"}],                         # a turn missing a field
    [{"text": None, "tool_calls": [{"id": "x"}]}],           # a tool call missing name and input
])
def test_malformed_recording_raises_model_unavailable(monkeypatch, tmp_path, content) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(content), encoding="utf-8")
    monkeypatch.setenv("MODEL_RECORDING", str(bad))
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [], transport=no_network)


def test_a_profile_without_a_provider_raises_model_unavailable(monkeypatch, tmp_path) -> None:
    profiles = tmp_path / "profiles.json"
    profiles.write_text(json.dumps({"default": {"model": "claude-haiku-5-5"}}), encoding="utf-8")
    monkeypatch.setattr(gateway, "PROFILES_PATH", profiles)
    monkeypatch.setenv("MODEL_PROFILE", "default")
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [])


def test_a_profiles_file_that_is_not_an_object_raises_model_unavailable(monkeypatch, tmp_path) -> None:
    profiles = tmp_path / "profiles.json"
    profiles.write_text("[1, 2]", encoding="utf-8")
    monkeypatch.setattr(gateway, "PROFILES_PATH", profiles)
    monkeypatch.setenv("MODEL_PROFILE", "default")
    with pytest.raises(ModelUnavailable):
        run_turn("sys", [], [])
