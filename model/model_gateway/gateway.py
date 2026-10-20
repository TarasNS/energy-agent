"""The model gateway (SPEC.md §4). The only file that may talk to a model vendor.

Standard library HTTP only, so no provider SDK is imported anywhere. Tool schemas come in OpenAI style
and are converted to the provider format here. The key is ANTHROPIC_API_KEY, from the environment or
from .env at the repo root. A missing key or a failed call raises ModelUnavailable.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
PROFILES_PATH = ROOT / "model" / "profiles.json"
DEFAULT_ENV_FILE = ROOT / ".env"
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
TIMEOUT_S = 60

Transport = Callable[[str, dict, bytes, float], str]


class ModelUnavailable(Exception):
    """No key, a failed call, or an unreadable reply. The loop catches this, never a raw HTTP error."""


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict = field(default_factory=dict)


@dataclass
class ModelTurn:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


def convert_tools(tools: list[dict]) -> list[dict]:
    """OpenAI style {"type": "function", "function": {...}} to the provider's {name, description, input_schema}."""
    converted = []
    for tool in tools:
        fn = tool["function"]
        converted.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return converted


def convert_messages(messages: list[dict]) -> list[dict]:
    """OpenAI style messages (user, assistant with tool_calls, tool) to provider content blocks."""
    converted = []
    for m in messages:
        role = m["role"]
        if role == "user":
            converted.append({"role": "user", "content": m["content"]})
        elif role == "assistant":
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for call in m.get("tool_calls") or []:
                blocks.append({
                    "type": "tool_use",
                    "id": call["id"],
                    "name": call["function"]["name"],
                    "input": json.loads(call["function"]["arguments"] or "{}"),
                })
            converted.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            converted.append({"role": "user", "content": [{
                "type": "tool_result",
                "tool_use_id": m["tool_call_id"],
                "content": m["content"],
            }]})
        else:
            raise ValueError(f"unknown message role: {role!r}")
    return converted


def load_profile(name: str | None = None) -> dict:
    """The profile named by MODEL_PROFILE (default: "default") from model/profiles.json."""
    name = name or os.environ.get("MODEL_PROFILE") or "default"
    profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    if name not in profiles:
        raise ValueError(f"unknown MODEL_PROFILE {name!r}; choose one of {sorted(profiles)}")
    return profiles[name]


def read_key(env_file: Path) -> str | None:
    """ANTHROPIC_API_KEY from the environment, else from the .env file. Never logged."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key and env_file.exists():
        # utf-8-sig drops a byte-order mark, which Windows editors often add to .env
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "ANTHROPIC_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key or None


def _http_post(url: str, headers: dict, body: bytes, timeout: float) -> str:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def run_turn(system: str, messages: list[dict], tools: list[dict], max_tokens: int = 600, *,
             transport: Transport | None = None, env_file: Path | None = None) -> ModelTurn:
    """One model turn. `transport` and `env_file` exist so tests run with no network and no real key."""
    # Every failure the harness can meet comes out as ModelUnavailable, so the loop catches one error type.
    try:
        profile = load_profile()
    except (OSError, ValueError) as e:  # unknown MODEL_PROFILE, missing or malformed profiles.json
        raise ModelUnavailable(f"model profile is unusable: {e}") from e
    if profile["provider"] == "offline":
        raise ModelUnavailable("the offline replay profile is not built yet")

    key = read_key(env_file or DEFAULT_ENV_FILE)
    if not key:
        raise ModelUnavailable("ANTHROPIC_API_KEY is not set: add it to .env")

    try:
        body = {"model": profile["model"], "max_tokens": max_tokens, "system": system,
                "messages": convert_messages(messages)}
        if tools:
            body["tools"] = convert_tools(tools)
    except (KeyError, TypeError, ValueError) as e:  # a message or tool without the fields it needs
        raise ModelUnavailable(f"malformed messages or tools: {e!r}") from e
    headers = {"content-type": "application/json", "x-api-key": key, "anthropic-version": API_VERSION}

    try:
        raw = (transport or _http_post)(API_URL, headers, json.dumps(body).encode("utf-8"), TIMEOUT_S)
    except OSError as e:  # URLError, HTTPError and timeouts are all OSError
        raise ModelUnavailable(f"model call failed: {e}") from e

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("reply is not a JSON object")
        if data.get("type") == "error":
            message = (data.get("error") or {}).get("message", "unknown")
            raise ModelUnavailable(f"model returned an error: {message}")
        texts, calls = [], []
        for block in data.get("content", []):
            if block.get("type") == "text":
                texts.append(block["text"])
            elif block.get("type") == "tool_use":
                calls.append(ToolCall(id=block["id"], name=block["name"], input=block.get("input", {})))
    except ModelUnavailable:
        raise
    except (ValueError, KeyError, TypeError, AttributeError) as e:  # not JSON, or a block without its fields
        raise ModelUnavailable(f"model reply could not be read: {e!r}") from e
    return ModelTurn(text="".join(texts) if texts else None, tool_calls=calls)
