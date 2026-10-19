"""Anthropic Messages API over HTTPS. The only file that talks to the provider.

explain() uses only the standard library (urllib). run_turn() uses httpx, which is already in
requirements.txt. No provider SDK is imported (CLAUDE.md rule 9). The key is read from
ANTHROPIC_API_KEY (.env, git-ignored, or an app setting). It is never logged or returned.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# (url, headers, body_bytes, timeout_s) -> (status_code, response_bytes). Replaceable in tests.
Transport = Callable[[str, dict, bytes, float], tuple[int, bytes]]


class ModelUnavailable(Exception):
    """The provider could not answer. The caller shows a clear message; no number is invented."""


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ModelTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""
    model: str = ""


def get_client_settings() -> tuple[str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ModelUnavailable("ANTHROPIC_API_KEY is not set. Add it to the git-ignored .env file.")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5").strip()
    return key, model


def _urllib_transport(url: str, headers: dict, body: bytes, timeout_s: float) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def explain(system: str, user: str, *, max_tokens: int = 400, timeout_s: float = 60.0, transport: Transport | None = None) -> ModelReply:
    key, model = get_client_settings()
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    try:
        status, payload = (transport or _urllib_transport)(API_URL, headers, body, timeout_s)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ModelUnavailable(f"network error reaching the model provider: {type(e).__name__}") from e
    if status != 200:
        raise ModelUnavailable(f"model provider returned HTTP {status}")
    try:
        data = json.loads(payload)
    except ValueError as e:
        raise ModelUnavailable("model provider returned an unreadable answer") from e
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()
    if not text:
        raise ModelUnavailable("model provider returned an empty answer")
    return ModelReply(text=text, model=data.get("model", model))


def _to_anthropic_tool(tool: dict) -> dict:
    """Registry tools are OpenAI-style ({"type": "function", "function": {...}}); Anthropic wants input_schema."""
    fn = tool.get("function")
    if fn is None:
        return tool  # already {name, description, input_schema}
    return {
        "name": fn["name"],
        "description": fn.get("description", ""),
        "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
    }


def run_turn(
    system: str,
    messages: list[dict],
    tools: list[dict],
    *,
    max_tokens: int = 1024,
    timeout_s: float = 60.0,
    transport: httpx.BaseTransport | None = None,
) -> ModelTurn:
    """One Messages API call with tools. Returns the text and any tool_use blocks; the caller runs the loop."""
    key, model = get_client_settings()
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "tools": [_to_anthropic_tool(tool) for tool in tools],
    }
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    try:
        with httpx.Client(transport=transport, timeout=timeout_s) as client:
            response = client.post(API_URL, headers=headers, json=body)
    except httpx.HTTPError as e:
        raise ModelUnavailable(f"network error reaching the model provider: {type(e).__name__}") from e
    if response.status_code != 200:
        raise ModelUnavailable(f"model provider returned HTTP {response.status_code}")
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("not an object")
        blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        calls = [
            ToolCall(id=b["id"], name=b["name"], input=b.get("input", {}))
            for b in blocks if b.get("type") == "tool_use"
        ]
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ModelUnavailable("model provider returned an unreadable answer") from e
    return ModelTurn(text=text, tool_calls=calls, stop_reason=data.get("stop_reason", ""), model=data.get("model", model))
