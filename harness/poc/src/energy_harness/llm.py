"""OpenRouter chat client with a client-side fallback chain.

Failure handling, per model in the chain:
- 5xx / 408 / network error  → retry, then next model
- 400 / 403 / 404 / error-in-body / upstream 429 → next model (this model can't serve it)
- 429 per-minute limit       → wait for reset, retry same model (limit is account-wide)
- 429 daily limit, 401, 402  → raise immediately; another model won't help
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import httpx

from .budget import RequestBudget


class LLMError(Exception):
    pass


class FatalLLMError(LLMError):
    """Errors no fallback model can fix (auth, payment, daily cap)."""


class DailyLimitError(FatalLLMError):
    pass


class AllModelsFailed(LLMError):
    def __init__(self, failures: list[tuple[str, str]]) -> None:
        self.failures = failures
        lines = "\n".join(f"  - {model}: {reason}" for model, reason in failures)
        super().__init__(f"All models in the chain failed:\n{lines}")


class _ModelUnavailable(Exception):
    pass


@dataclass
class ChatResult:
    message: dict
    model: str
    requested_model: str
    latency_s: float
    usage: dict | None = None
    failed_models: list[tuple[str, str]] = field(default_factory=list)


class ChatClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict] | None = None, tool_choice: Any = None) -> ChatResult: ...


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        models: list[str],
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.2,
        timeout_s: float = 90,
        budget: RequestBudget | None = None,
        http: httpx.Client | None = None,
        retries_per_model: int = 1,
        max_rate_limit_wait_s: float = 65,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
        app_name: str = "energy-agent harness",
    ) -> None:
        if not models:
            raise ValueError("models must not be empty")
        self.api_key = api_key
        self.models = list(models)
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.temperature = temperature
        self.timeout_s = timeout_s
        self.budget = budget
        self.retries_per_model = retries_per_model
        self.max_rate_limit_wait_s = max_rate_limit_wait_s
        self._http = http or httpx.Client()
        self._sleep = sleep
        self._clock = clock
        self._headers = {"Authorization": f"Bearer {api_key}", "X-Title": app_name}

    def chat(self, messages: list[dict], tools: list[dict] | None = None, tool_choice: Any = None) -> ChatResult:
        failures: list[tuple[str, str]] = []
        for model in self.models:
            try:
                result = self._chat_with_model(model, messages, tools, tool_choice)
            except _ModelUnavailable as e:
                failures.append((model, str(e)))
                continue
            result.failed_models = failures
            return result
        raise AllModelsFailed(failures)

    def _chat_with_model(self, model: str, messages: list[dict], tools: list[dict] | None, tool_choice: Any) -> ChatResult:
        payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": self.temperature}
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

        attempt = 0
        while True:
            if self.budget:
                self.budget.acquire()
            started = time.monotonic()
            try:
                resp = self._http.post(self.url, json=payload, headers=self._headers, timeout=self.timeout_s)
            except httpx.HTTPError as e:
                if attempt < self.retries_per_model:
                    attempt += 1
                    self._sleep(2.0 * attempt)
                    continue
                raise _ModelUnavailable(f"network error: {type(e).__name__}: {e}") from e
            latency = time.monotonic() - started

            body = _json_or_none(resp)
            error = _error_message(body) or resp.text[:300]
            status = resp.status_code

            if status == 200 and isinstance(body, dict) and not body.get("error"):
                choices = body.get("choices") or []
                message = choices[0].get("message") if choices else None
                if not message:
                    raise _ModelUnavailable("empty response (no choices)")
                return ChatResult(
                    message=message,
                    model=body.get("model") or model,
                    requested_model=model,
                    latency_s=latency,
                    usage=body.get("usage"),
                )
            if status == 401:
                raise FatalLLMError(f"OpenRouter rejected the API key (401): {error}. Check OPENROUTER_API_KEY.")
            if status == 402:
                raise FatalLLMError(f"OpenRouter requires payment (402): {error}")
            if status == 429:
                lowered = error.lower()
                if "per-day" in lowered or "per day" in lowered:
                    raise DailyLimitError(
                        f"OpenRouter daily free-model limit reached: {error}. "
                        "It resets at 00:00 UTC (buying $10 of credits once raises it to 1,000/day)."
                    )
                if "per-min" in lowered or "per minute" in lowered:
                    wait = self._rate_limit_wait(resp)
                    if attempt < self.retries_per_model and wait <= self.max_rate_limit_wait_s:
                        attempt += 1
                        self._sleep(wait)
                        continue
                    raise _ModelUnavailable(f"per-minute rate limit: {error}")
                raise _ModelUnavailable(f"rate-limited upstream: {error}")
            if status >= 500 or status == 408:
                if attempt < self.retries_per_model:
                    attempt += 1
                    self._sleep(2.0 * attempt)
                    continue
            raise _ModelUnavailable(f"HTTP {status}: {error}")

    def _rate_limit_wait(self, resp: httpx.Response) -> float:
        retry_after = resp.headers.get("retry-after")
        if retry_after:
            try:
                return max(1.0, float(retry_after))
            except ValueError:
                pass
        reset = resp.headers.get("x-ratelimit-reset")  # epoch milliseconds
        if reset:
            try:
                return max(1.0, float(reset) / 1000.0 - self._clock() + 0.5)
            except ValueError:
                pass
        return 10.0


def _json_or_none(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return None


def _error_message(body: Any) -> str | None:
    if not isinstance(body, dict) or not body.get("error"):
        return None
    error = body["error"]
    if isinstance(error, dict):
        message = str(error.get("message") or error)
        raw = (error.get("metadata") or {}).get("raw")
        return f"{message} ({raw})" if raw and str(raw) not in message else message
    return str(error)
