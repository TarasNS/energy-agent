import json
import threading
import urllib.request

import pytest

from conftest import ScriptedLLM, answer, tool_call

from energy_harness.agent import Agent
from energy_harness.config import POC_ROOT, load_settings
from energy_harness.web.server import App, make_server


class FakeApp(App):
    """Real server, real simulator and tools; only the LLM is scripted."""

    replies: list = []

    def make_agent(self, mode, models, tracer):
        llm = ScriptedLLM(*self.replies, model=(models or ["fake/model:free"])[0])
        return Agent(llm, self.registry(mode), tracer=tracer, today=lambda: self.simulator.today().isoformat())


@pytest.fixture
def server(tmp_path):
    settings = load_settings(POC_ROOT / "config.yaml", env={"OPENROUTER_API_KEY": "sk-test"})
    settings.runs_dir = tmp_path / "runs"
    app = FakeApp(settings)
    srv = make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield app, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def post_stream(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return [json.loads(line) for line in r.read().decode().splitlines() if line.strip()]


def test_serves_page_and_info(server):
    _, base = server
    status, ctype, body = get(base + "/")
    assert status == 200 and ctype.startswith("text/html") and b"Energy Agent Harness" in body
    info = json.loads(get(base + "/api/info")[2])
    assert info["has_key"] is True and "sk-test" not in json.dumps(info)  # key never leaves the server
    assert info["models"][0] == "nvidia/nemotron-3-super-120b-a12b:free"
    assert {p["id"] for p in info["simulation"]["parks"]} >= {"sim-dk-west", "sim-dk-east"}
    assert len(info["evals"]) >= 5 and info["budget"]["per_day"] == 50


def test_sim_day_matches_scenario(server):
    _, base = server
    data = json.loads(get(base + "/api/sim/day?park=sim-dk-east&date=2026-10-14")[2])
    assert len(data["samples"]) == 96 and data["metered_mwh"] == 0 and data["expected_mwh"] > 0
    assert [e["type"] for e in data["events"]] == ["outage"]
    dk1 = json.loads(get(base + "/api/sim/day?park=sim-dk-west&date=2026-10-11")[2])
    assert sum(p["eur_per_mwh"] < 0 for p in dk1["prices"]) == 12
    assert sum(s["curtailed"] for s in dk1["samples"]) == 12


def test_sim_day_bad_input(server):
    _, base = server
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base + "/api/sim/day?park=nope&date=2026-10-14")
    assert e.value.code == 400


def test_ask_streams_steps_then_answer(server):
    app, base = server
    app.replies = [
        tool_call("get_metered_production", '{"park": "sim-dk-east", "start_date": "2026-10-14"}'),
        answer("**sim-dk-east** produced 0 MWh: availability was 0 %."),
    ]
    events = post_stream(base + "/api/ask", {"question": "Which park produced nothing on 2026-10-14?", "mode": "simulation", "models": ["x/y:free"]})
    kinds = [e["event"] for e in events]
    assert kinds == ["run_start", "llm_call", "tool_call", "llm_call", "run_end", "answer"]
    assert events[1]["model"] == "x/y:free"
    tool = events[2]
    assert tool["ok"] and json.loads(tool["result"])["daily"][0]["availability_pct"] == 0
    final = events[-1]
    assert "sim-dk-east" in final["answer"] and final["history"][-1]["role"] == "assistant"


def test_ask_without_key_reports_error(server):
    app, base = server
    app.settings.api_key = None
    events = post_stream(base + "/api/ask", {"question": "hi"})
    assert events == [{"event": "error", "message": events[0]["message"]}] and "OPENROUTER_API_KEY" in events[0]["message"]


def test_eval_endpoint_streams_case_results(server):
    app, base = server
    truth = json.loads(app.registry("simulation").execute("get_metered_production", {"park": "sim-dk-west", "start_date": "2026-10-10"}).content)
    mwh = truth["daily"][0]["energy_mwh"]
    app.replies = [tool_call("get_metered_production", '{"park": "sim-dk-west", "start_date": "2026-10-10"}'), answer(f"It produced {mwh} MWh.")]
    events = post_stream(base + "/api/eval", {"cases": ["metered-energy"]})
    assert [e["event"] for e in events] == ["case_start", "case_result", "done"]
    assert events[1]["passed"] is True and events[1]["tools"] == ["get_metered_production"]
