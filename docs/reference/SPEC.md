# SPEC.md: what the team builds

**Owner:** Lead · **Role:** the build contract. [INTENT.md](INTENT.md) says why, [ARCHITECTURE.md](ARCHITECTURE.md) says how the parts connect, this file says exactly what each part must do. There is no harness code yet: the team builds every part from this file, in 24 numbered tasks. If two documents disagree, stop and tell the lead.

Names, shapes and limits below are fixed so the parts fit when they meet. Anything not stated here is your choice: keep it simple.

## 1. Layout

```text
schemas/                 JSON contracts                      Dev 1 (#1)
model/model_gateway/     run_turn(), offline replay          Dev 1 (#2)
.claude/skills/kpi-advisor/SKILL.md                          Dev 1 (#3)
data/source.py, data/synthetic/portfolio.py   load(), the synthetic portfolio   Dev 2 (#4)
data/api_source.py       the organizers' API (optional)    Dev 1 (#13)
mcp/kpi-solar/           KPI formulas (pure functions)       Dev 2 (#5)
harness/registry.py, energy_tools.py   nine tools            Dev 2 (#14)
harness/agent.py         agent loop, number check            Dev 3 (#6, #15)
scripts/demo-smoke.sh    smoke test                          Dev 3 (#7, #20)
model/recorded/          demo recordings                     Dev 4 (#21)
mcp/actions/             propose, approve, audit             Dev 4 (#8)
tools/kpi-lab/server.py  the server                          Dev 4 (#9, #16)
Dockerfile, .dockerignore  the container                     Dev 4 (#10)
evals/, tests/           golden cases (Dev 2), number check (Dev 1)
energy-agent-ui (Lovable repository)   the chat page         Dev 5 (#11, #17)
```

Import roots are set in `pytest.ini`. Never create `mcp/__init__.py`.

## 2. The portfolio data (Dev 2, task #4; the organizers' API, Dev 1, task #13)

Label everything `SYNTHETIC: not Nordic Solar data`. A fixed seed gives the same numbers on every run. No network.

| Asset id | Kind | Size | Notes |
|---|---|---|---|
| `north` | PV park | 10 MW, 10 000 kWp | 3 outage days |
| `south` | PV park | 8 MW, 8 000 kWp | 1 outage day |
| `battery` | BESS | 5 MW, 20 MWh usable | |

Every part gets the portfolio from `load()` in `data/source.py`, never from a file or an API directly. `ENERGY_DATA_MODE` picks the source: `synthetic` (the default, and always used by the tests and the golden cases) or `api`, the organizers' energy data API through `load_api()` in `data/api_source.py` (address and key in `ORGANIZER_API_URL` and `ORGANIZER_API_KEY`). Both return the same shape. If the API is missing or fails, `load()` falls back to the synthetic data and says so in the label.

Period: **1 to 30 June 2026**, daily rows (`YYYY-MM-DD`).

| Per park, per day | Plausible range |
|---|---|
| POA irradiation (kWh/m²) | 4.2 to 6.4 |
| Expected MWh | kWp × POA × 0.82 ÷ 1000 |
| Actual MWh | expected × 0.90 to 1.06; × 0.35 on an outage day |
| Available / outage hours | 24 − outage; about 8 % of days lose 1 to 3 h; outage days lose 10 to 13 h |
| Curtailed MWh | on about 20 % of days, 0.3 to 1.2 |

| Battery, per day | Plausible range |
|---|---|
| Charged MWh | 8 to 12 |
| Discharged MWh | charged × 0.84 to 0.91 |
| Throughput | charged + discharged |
| Available hours | 24, or 22 on about 10 % of days |

| Portfolio, per day | Plausible range |
|---|---|
| Mean day-ahead price (EUR/MWh) | 38 to 68; about 15 % of days negative, −4 to −16 |

`data/synthetic/portfolio.py` exposes `build(seed=20260601) -> dict`. Dev 3 and Dev 2 both rely on this shape:

```python
{"label": "SYNTHETIC: not Nordic Solar data",
 "period": {"start": "2026-06-01", "end": "2026-06-30", "days": 30},
 "days": ["2026-06-01", ...],
 "assets": [
   {"id": "north", "name": "Park North (synthetic)", "kind": "pv", "capacityMw": 10, "nameplateKwp": 10000,
    "daily": [{"date", "poaKwhM2", "expectedMwh", "actualMwh", "availHours", "outageHours", "curtailedMwh"}, ...]},
   {"id": "south", ...},
   {"id": "battery", "name": "Battery (synthetic)", "kind": "bess", "capacityMw": 5,
    "daily": [{"date", "chargedMwh", "dischargedMwh", "throughputMwh", "usableMwh", "availHours"}, ...]}],
 "prices": [{"date", "meanPrice"}, ...],
 "ppa": {"shareOfExpected": 0.5}}
```

Also fixed: a PPA covers **50 % of expected volume** (a demo assumption, say so wherever it is used). Import with `from data.source import load` and `from kpi_solar import metrics`. Money and energy leave the data layer as **decimal strings** (`"85.00"`, `"125.592"`): MWh 3 places, EUR/MWh and EUR 2 places, hours 0 places, percentages 1 place.

## 3. The 13 KPIs (Dev 2 builds `mcp/kpi-solar`, task #5)

Pure functions: strings in, `Decimal` or `Unavailable(reason)` out. How the tools feed them (all over the chosen days): `availability` = sum of `availHours` ÷ (days × 24 × number of parks); `capacity_factor` uses the summed capacity of the parks; `merchant_exposure` uses actual MWh × (1 − PPA share); `ppa_delivery` uses actual × share and expected × share; `performance_ratio` is computed per park and simple-averaged for `portfolio`; `downtime` builds one status per hour of each day, `"OUTAGE"` for the first `outageHours` hours and `"OK"` for the rest; `realised_price` uses one (daily portfolio MWh, daily price) pair per day. `portfolio` for a BESS KPI means the battery. Never a float. Refuse zero or missing inputs with `Unavailable`, never divide by zero. Round half up.

| id | Unit | Scope | Formula |
|---|---|---|---|
| `actual_vs_expected` | % | PV | actual ÷ expected × 100 |
| `performance_ratio` | % | PV | actual kWh ÷ (POA kWh/m² × nameplate kWp) × 100, per park, then the simple average |
| `availability` | % | PV | available hours ÷ (days × 24 × parks) × 100 |
| `capacity_factor` | % | PV | actual MWh ÷ (capacity MW × period hours) × 100 |
| `ppa_delivery` | % | PV | delivered ÷ contracted × 100, both 50 % of actual and expected |
| `realised_price` | EUR/MWh | PV | Σ(daily MWh × daily price) ÷ Σ daily MWh |
| `merchant_exposure` | EUR | PV | merchant MWh (the other 50 %) × 10 EUR/MWh move. A sensitivity, not a forecast |
| `downtime` | h | PV | hours with outage status |
| `energy_loss` | MWh | PV | expected − actual |
| `incident_resolution` | h | PV | median ticket hours. **No tickets are loaded, so always `Unavailable`** |
| `bess_availability` | % | BESS | available hours ÷ period hours × 100 |
| `bess_round_trip` | % | BESS | discharged ÷ charged × 100 |
| `bess_cycle_utilisation` | % | BESS | average daily throughput ÷ (2 × usable MWh) × 100 |

The functions live in `mcp/kpi-solar/kpi_solar/metrics.py`. `Unavailable` has a `reason` string. All inputs are strings or `Decimal`s.

```python
actual_vs_expected_pct(actual_mwh, expected_mwh)        performance_ratio_pct(actual_kwh, poa_irradiation_kwh_m2, nameplate_kwp)
availability_pct(available_hours, period_hours)         capacity_factor_pct(energy_mwh, capacity_mw, period_hours)
ppa_delivery_pct(delivered_mwh, contracted_mwh)         realised_price_eur_mwh(intervals)   # [(mwh, price), ...]
merchant_exposure_eur(merchant_mwh, price_move_eur_mwh) downtime_hours(statuses, interval_hours)  # "OK" / "OUTAGE"
energy_loss_mwh(expected_mwh, actual_mwh)               incident_resolution_hours(open_to_close_hours)
bess_availability_pct(available_hours, period_hours)    bess_round_trip_efficiency_pct(discharged_mwh, charged_mwh)
bess_cycle_utilisation_pct(throughput_mwh, usable_mwh)
```

Background on the real-world meaning of these KPIs: [KPI_REVIEW.md](KPI_REVIEW.md).

## 4. Model gateway (Dev 1, task #2)

```python
from model.model_gateway import run_turn, ModelTurn, ToolCall, ModelUnavailable
turn = run_turn(system: str, messages: list[dict], tools: list[dict], max_tokens: int = 600) -> ModelTurn
# ModelTurn(text: str | None, tool_calls: list[ToolCall(id, name, input)]); no tool calls means the loop stops
```

- Tool schemas come in OpenAI style (`{"type":"function","function":{name, description, parameters}}`); the gateway converts them.
- Profiles are chosen by `MODEL_PROFILE` (`default`, `fast`, `offline`) from `model/profiles.json`. Default model: Claude Haiku 5.5 (`claude-haiku-5-5`), also for `fast`. The model id is changed there only. A recording is a JSON list of turns: `[{"text": "...", "tool_calls": [{"id", "name", "input"}]}, ...]`, one file per question.
- `offline` replays recorded turns in order from `MODEL_RECORDED_PATH` (default `model/recorded/`). No network. The smoke test points it at `scripts/smoke_turns.json`.
- Only `model/model_gateway/` may import a provider SDK. `make check` fails otherwise.
- The key is `ANTHROPIC_API_KEY`, read from `.env` or the environment. A missing key or a failed call raises `ModelUnavailable`.

## 5. The nine tools (Dev 2, task #14)

Read-only. Each returns a JSON string. Money and energy are decimal strings. A bad call returns `{"error": "..."}`; the registry never raises into the loop. Assets are `portfolio` (default), `north`, `south`, `battery`. Dates are `YYYY-MM-DD` inside June 2026; the default period is the whole month.

| Tool | Arguments | Returns |
|---|---|---|
| `list_assets` | none | id, name, kind, `capacity_mw` per asset |
| `list_kpis` | none | `kpi`, title, unit, `needs` for each of the 13 |
| `get_kpi` | `kpi`, `asset`, `start`, `end` | `kpi, title, asset, start, end, value (string or null), unit, unavailable (reason or null), inputs` |
| `compare_kpi` | `kpi`, `by` = `asset` or `week` | one `get_kpi` row per asset, or per 7-day block |
| `get_series` | `metric`, `asset`, `start`, `end` | `{metric, unit, start, end, points: [{date, value}]}` |
| `get_prices` | `start`, `end` | daily mean price and a `negative` flag |
| `get_events` | `asset`, `start`, `end` | outage and curtailment days |
| `make_chart` | `kind` = `line`, `bar`, `area`, `table`; `title`; `series: [{name, points: [{x, y}]}]` | a chart id. Every `y` is a string copied from a tool result |
| `propose_action` | `action`, `asset`, `reason` | a proposal id. It records only; it runs nothing |

`compare_kpi` with `by=week` splits the chosen days into consecutive 7-day blocks (the last one may be shorter) and returns one row per block, labelled by its first and last day.

Row shapes the page and the schemas rely on:

| Where | Shape |
|---|---|
| `get_prices` | `{start, end, unit: "EUR/MWh", points: [{date, value, negative: true or false}]}` |
| `get_events` | `{start, end, events: [{date, asset, kind: "outage" or "curtailment", value}]}`; `value` is hours or MWh as a decimal string |
| `list_kpis` | `[{kpi, title, unit, needs}]` with `needs` a short phrase |
| chart | `{id: "chart_1", kind, title, series}` |
| proposal | `{id: "prop_" + 12 hex, action, asset, reason, status: "pending", "approved" or "refused"}` |
| `trace` entry | `{tool, input, ok}`, one per tool call, in order |
| `note` | plain text for the manager, or `null` when `verified` is true |

`metric` is one of `actual_mwh`, `expected_mwh`, `availability_hours`, `outage_hours`, `curtailed_mwh`, `price_eur_mwh`, `bess_charged_mwh`, `bess_discharged_mwh`. `action` is one of `enable_negative_price_curtailment`, `schedule_inspection`, `review_ppa_volume`.

The registry has `schemas()` and `call(name, input)`; the agent loop takes any object with those two methods, so its tests use a fake. **There is no approval tool.** `approve_action` and token issuing are never in the registry. A test says so.

## 6. The agent loop and the number check (Dev 3, task #6)

`harness.agent.run(question, model=None, registry=None) -> AgentResult(text, verified, note, charts, proposals, trace, stopped)`.

1. Send the model the system prompt (the skill file when it exists, otherwise a built-in fallback), the question and the nine tool schemas.
2. Run each requested tool through the registry. At most **8 rounds**; then stop with `stopped = "max_steps"` and a note.
3. When the model answers in text, `check_numbers(reply, tool_results, question)` lists every number in the reply that is in neither the question nor any tool result. The same value written differently (`12.5` and `12.50`) passes. Years, dates and small counts must not raise false alarms.
4. Any unknown number: `text` is withheld (`verified: false`, a note), and charts, proposals and the trace still return.
5. `stopped` is one of `answered`, `max_steps`, `cap`, `model_error`.

## 7. Approval and audit (Dev 4 builds `mcp/actions`, task #8; Dev 3 adds the `tool_call` lines, task #15)

- `propose_action(action, asset, reason) -> proposal_id`.
- `issue_approval_token(proposal_id)` and `approve_action(proposal_id, token, approver)` exist **only** inside the server's `/api/approve` path.
- A token is one-time and lives in memory. A missing, wrong or reused token, or a proposal already approved, is **refused and audited**. Approval is simulated: it writes an audit line and does nothing else.
- The audit log is `artifacts/audit.jsonl`, append-only, one JSON line per event: `{ts, event, proposal_id, action, asset, approver}`. Events: `proposed`, `approved`, `refused`, and `tool_call` (with `tool`, `input`, `ok`). A token never appears in any line. The path comes from `AUDIT_LOG_PATH` (default `./artifacts/audit.jsonl`).

## 8. The server (Dev 4, `tools/kpi-lab/server.py`, tasks #9 and #16)

Standard library or FastAPI, your choice. Serves on `127.0.0.1:8000` (`KPI_LAB_HOST`, `KPI_LAB_PORT`).

| Route | Body → answer |
|---|---|
| `POST /api/chat` | `{question}` → `{text, verified, note, charts, proposals, trace, stopped}`; **429** after the daily cap |
| `POST /api/approve` | `{proposal_id, approver}` → `{status}`; the server issues the token itself, the browser never sees it |
| `GET /health` | `{status: "ok", calls_left_today}` |

Daily model-call cap: `KPI_DAILY_CAP`, default 200, stored in `KPI_CAP_FILE`. Allowed origins: `KPI_ALLOWED_ORIGINS` (comma separated), including the Lovable page's address. The server answers the browser's preflight and sends `Access-Control-Allow-Private-Network: true`, so the Lovable page can call a server running on a laptop. The approve route calls `approve_for_server(proposal_id, approver)` in `mcp/actions`, which issues and uses the one-time token inside the module.

## 9. The chat page (Dev 5, the lead, in Lovable, tasks #11 and #17)

Built in Lovable and committed by Lovable to its own repository, `energy-agent-ui`. It calls the server's `/api/chat` and `/api/approve`; the server address is a setting (`API_BASE`, default `http://127.0.0.1:8000`). Render-only: it shows what the server returns and never calculates, adds, rounds or averages; every chart value is the string the server sent. Phone and desktop width. States: loading, verified answer, withheld answer (note, charts and tool results shown), daily limit reached (429), server not reachable, server error, proposal waiting, approved, approval refused. It asks for the approver's name before Approve is sent. It says **SYNTHETIC DATA** on screen. It needs internet; the server and the tests do not.

## 10. The skill (Dev 1, task #3)

`.claude/skills/kpi-advisor/SKILL.md`, at most 150 lines. It tells the model: the data is synthetic and every answer says so; which of the nine tools fits which question; never calculate, add, average, round or estimate; when a value is unavailable, say so and give the reason; call `make_chart` at most once; propose only when the data clearly justifies it and never say it is approved; answer in at most 120 words.

Changing a schema or a shape in this file needs the lead's approval; Dev 2 and Dev 3 review changes to `schemas/`.

## 11. Done

[INTENT.md §7](INTENT.md) lists the seven things that must be true. [EVALS.md](EVALS.md) says how to prove the numbers. [DEMO.md](DEMO.md) is the three-minute story the finished harness must run.
