import json

import httpx
import pytest
import respx

from energy_harness.budget import BudgetExceeded, RequestBudget
from energy_harness.llm import AllModelsFailed, DailyLimitError, FatalLLMError, OpenRouterClient

URL = "https://openrouter.ai/api/v1/chat/completions"


def ok(content="hi", model=None):
    def respond(request):
        sent = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": model or sent["model"],
                "choices": [{"message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            },
        )

    return respond


def error(status, message, headers=None):
    return httpx.Response(status, json={"error": {"code": status, "message": message}}, headers=headers or {})


def make_client(clock, models=("a:free", "b:free"), **kwargs):
    return OpenRouterClient("sk-test", list(models), sleep=clock.sleep, clock=clock, **kwargs)


def requested_models(route):
    return [json.loads(call.request.content)["model"] for call in route.calls]


@respx.mock
def test_success_sends_tools_and_reports_served_model(clock):
    route = respx.post(URL).mock(side_effect=ok(model="real/model"))
    tools = [{"type": "function", "function": {"name": "t", "parameters": {"type": "object"}}}]
    result = make_client(clock, models=["openrouter/free"]).chat([{"role": "user", "content": "x"}], tools=tools, tool_choice="auto")

    sent = json.loads(route.calls[0].request.content)
    assert sent["tools"] == tools and sent["tool_choice"] == "auto"
    assert route.calls[0].request.headers["Authorization"] == "Bearer sk-test"
    assert result.message["content"] == "hi"
    assert result.model == "real/model" and result.requested_model == "openrouter/free"
    assert result.failed_models == []


@respx.mock
def test_no_tools_key_when_no_tools(clock):
    route = respx.post(URL).mock(side_effect=ok())
    make_client(clock).chat([{"role": "user", "content": "x"}], tool_choice="none")
    assert "tools" not in json.loads(route.calls[0].request.content)


@respx.mock
def test_404_falls_back_to_next_model(clock):
    route = respx.post(URL).mock(side_effect=[error(404, "No endpoints found for a:free"), ok()])
    result = make_client(clock).chat([])
    assert requested_models(route) == ["a:free", "b:free"]
    assert result.requested_model == "b:free"
    assert result.failed_models[0][0] == "a:free" and "404" in result.failed_models[0][1]


@respx.mock
def test_5xx_retries_once_then_falls_back(clock):
    route = respx.post(URL).mock(side_effect=[error(502, "bad gateway"), error(503, "down"), ok()])
    result = make_client(clock).chat([])
    assert requested_models(route) == ["a:free", "a:free", "b:free"]
    assert result.requested_model == "b:free"
    assert clock.sleeps == [2.0]


@respx.mock
def test_network_error_retries_then_falls_back(clock):
    route = respx.post(URL).mock(side_effect=[httpx.ConnectTimeout("t"), httpx.ConnectTimeout("t"), ok()])
    assert make_client(clock).chat([]).requested_model == "b:free"
    assert requested_models(route) == ["a:free", "a:free", "b:free"]


@respx.mock
def test_per_minute_429_waits_and_retries_same_model(clock):
    reset_ms = str(int((clock.now + 12) * 1000))
    route = respx.post(URL).mock(
        side_effect=[error(429, "Rate limit exceeded: free-models-per-min.", {"X-RateLimit-Reset": reset_ms}), ok()]
    )
    result = make_client(clock).chat([])
    assert requested_models(route) == ["a:free", "a:free"]
    assert result.requested_model == "a:free"
    assert 12 <= clock.sleeps[0] <= 13


@respx.mock
def test_daily_429_fails_fast_without_fallback(clock):
    route = respx.post(URL).mock(
        side_effect=[error(429, "Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day")]
    )
    with pytest.raises(DailyLimitError, match="00:00 UTC"):
        make_client(clock).chat([])
    assert route.call_count == 1


@respx.mock
def test_upstream_429_falls_back(clock):
    route = respx.post(URL).mock(side_effect=[error(429, "a:free is temporarily rate-limited upstream"), ok()])
    assert make_client(clock).chat([]).requested_model == "b:free"
    assert route.call_count == 2


@respx.mock
@pytest.mark.parametrize("status", [401, 402])
def test_auth_and_payment_errors_are_fatal(clock, status):
    respx.post(URL).mock(return_value=error(status, "nope"))
    with pytest.raises(FatalLLMError):
        make_client(clock).chat([])


@respx.mock
def test_error_in_200_body_and_empty_choices_fall_back(clock):
    route = respx.post(URL).mock(
        side_effect=[
            httpx.Response(200, json={"error": {"message": "Provider returned error"}}),
            httpx.Response(200, json={"choices": []}),
            ok(),
        ]
    )
    result = make_client(clock, models=["a:free", "b:free", "c:free"]).chat([])
    assert result.requested_model == "c:free"
    assert route.call_count == 3


@respx.mock
def test_all_models_failing_lists_every_reason(clock):
    respx.post(URL).mock(return_value=error(400, "tools not supported"))
    with pytest.raises(AllModelsFailed) as exc:
        make_client(clock).chat([])
    assert [m for m, _ in exc.value.failures] == ["a:free", "b:free"]
    assert "tools not supported" in str(exc.value)


@respx.mock
def test_budget_is_charged_per_request_and_stops_at_cap(clock):
    respx.post(URL).mock(side_effect=[error(502, "x"), error(502, "x"), ok()])
    budget = RequestBudget(per_minute=None, per_day=2, clock=clock)
    with pytest.raises(BudgetExceeded):
        make_client(clock, budget=budget).chat([])
    assert budget.used_today == 2
