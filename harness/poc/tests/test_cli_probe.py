import json

import httpx
import pytest
import respx

from energy_harness import cli, probe
from energy_harness.config import POC_ROOT
from energy_harness.energy.sources import PRICE_URL
from energy_harness.llm import ChatResult

from test_energy import TODAY, prices_response

OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"


class CannedClient:
    def __init__(self, model, *messages):
        self.models = [model]
        self.replies = list(messages)

    def chat(self, messages, tools=None, tool_choice=None):
        return ChatResult(self.replies.pop(0), "served/x", self.models[0], 0.5)


def test_probe_scores_tool_calls():
    good = CannedClient(
        "good:free",
        {"content": "OK"},
        {"tool_calls": [{"id": "1", "function": {"name": "add", "arguments": '{"a": 17, "b": 25}'}}]},
    )
    result = probe.probe_model(good)
    assert result.answers and result.tool_call_ok and result.error is None

    bad = CannedClient("bad:free", {"content": "OK"}, {"content": "It is 42."})
    result = probe.probe_model(bad)
    assert result.answers and not result.tool_call_ok and "text: It is 42." in result.error


def test_probe_ranks_working_tool_callers_first():
    slow_good = probe.ProbeResult("slow", answers=True, tool_call_ok=True, latency_s=9.0)
    fast_good = probe.ProbeResult("fast", answers=True, tool_call_ok=True, latency_s=1.0)
    fast_bad = probe.ProbeResult("no-tools", answers=True, tool_call_ok=False, latency_s=0.1)
    down = probe.ProbeResult("down")
    ranked = sorted([down, fast_bad, slow_good, fast_good], key=lambda r: r.rank_key)
    assert [r.model for r in ranked] == ["fast", "slow", "no-tools", "down"]


def test_probe_dry_run_makes_no_requests(capsys, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert probe.main(["--config", str(POC_ROOT / "config.yaml"), "--dry-run"]) == 0
    assert "openai/gpt-oss-120b:free" in capsys.readouterr().err


def test_cli_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here
    monkeypatch.setattr(cli, "load_settings", lambda path: _settings(tmp_path, api_key=None))
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        cli.main(["hello"])


def _settings(tmp_path, api_key="sk-test"):
    from energy_harness.config import load_settings

    settings = load_settings(POC_ROOT / "config.yaml", env={"OPENROUTER_API_KEY": api_key} if api_key else {})
    settings.runs_dir = tmp_path / "runs"
    return settings


@respx.mock
def test_end_to_end_price_question(monkeypatch, tmp_path, capsys):
    """Full stack: CLI → agent → OpenRouter (mocked, first model 404s) → price tool → Energy-Charts (mocked)."""
    monkeypatch.setattr(cli, "load_settings", lambda path: _settings(tmp_path))
    monkeypatch.setattr("energy_harness.energy.tools.utc_today", lambda: TODAY)  # resolved when tools are built
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json=prices_response(TODAY)))

    def openrouter(request):
        body = json.loads(request.content)
        if body["model"] == "openai/gpt-oss-120b:free":
            return httpx.Response(404, json={"error": {"message": "No endpoints found"}})
        if body["messages"][-1]["role"] == "tool":
            prices = json.loads(body["messages"][-1]["content"])
            text = f"DK1 averages {prices['daily'][0]['mean']} EUR/MWh today."
            return httpx.Response(200, json={"model": body["model"], "choices": [{"message": {"role": "assistant", "content": text}}]})
        call = {"id": "c1", "type": "function", "function": {"name": "get_day_ahead_prices", "arguments": '{"bidding_zone": "DK1"}'}}
        return httpx.Response(200, json={"model": body["model"], "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [call]}}]})

    respx.post(OPENROUTER).mock(side_effect=openrouter)
    assert cli.main(["What is the DK1 price today?"]) == 0

    out, err = capsys.readouterr()
    assert out.startswith("DK1 averages") and "EUR/MWh" in out
    assert "qwen/qwen3-coder:free" in err and "get_day_ahead_prices" in err
    events = [json.loads(line) for f in (tmp_path / "runs").glob("*.jsonl") for line in f.read_text().splitlines()]
    assert events[1]["failed_models"][0][0] == "openai/gpt-oss-120b:free"
    assert json.loads((tmp_path / "runs" / "budget.json").read_text())["count"] == 4  # 404 + fallback, twice
