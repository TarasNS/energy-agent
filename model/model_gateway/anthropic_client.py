"""Anthropic Messages API over HTTP. The only file that talks to the provider.

Uses httpx directly so no provider SDK is imported (CLAUDE.md rule 9).
The key is read from ANTHROPIC_API_KEY (.env, git-ignored). It is never logged or returned.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class ModelUnavailable(Exception):
    """The provider could not answer. The caller shows a clear message; no number is invented."""


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str


def get_client_settings() -> tuple[str, str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ModelUnavailable("ANTHROPIC_API_KEY is not set. Add it to the git-ignored .env file.")
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5").strip()
    return key, model


def explain(system: str, user: str, *, max_tokens: int = 400, timeout_s: float = 60.0, transport=None) -> ModelReply:
    key, model = get_client_settings()
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {"x-api-key": key, "anthropic-version": API_VERSION, "content-type": "application/json"}
    try:
        with httpx.Client(timeout=timeout_s, transport=transport) as client:
            r = client.post(API_URL, json=body, headers=headers)
    except httpx.HTTPError as e:
        raise ModelUnavailable(f"network error reaching the model provider: {type(e).__name__}") from e
    if r.status_code != 200:
        raise ModelUnavailable(f"model provider returned HTTP {r.status_code}")
    data = r.json()
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text").strip()
    if not text:
        raise ModelUnavailable("model provider returned an empty answer")
    return ModelReply(text=text, model=data.get("model", model))
