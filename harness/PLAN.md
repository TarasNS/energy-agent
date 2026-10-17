# Energy Agent Harness — Implementation Plan

> Status: **Tasks 1–8 implemented in `harness/poc/` (56 offline tests passing). Task 9, the live smoke test, needs an OpenRouter key and network access.**
> Date: 2026-10-17 · Branch: `claude/awesome-planck-bt3ymf`

## 0. Decisions

| Question | Decision |
|---|---|
| Language | **Python** (3.11+) |
| First energy tools | **PV production**, **day-ahead prices**, **irradiance forecasts** |
| $10 OpenRouter top-up (50 → 1,000 free requests/day) | **Not now.** Development runs against a fake LLM and recorded fixtures, so 50/day is enough. Revisit if the cap is hit in real use. |
| Location | Code lives in `harness/poc/` (proof of concept); this plan stays in `harness/`. |

## 1. Goal

Build a small, self-contained **agent harness**: the loop that sends messages
to an LLM, executes the tools it asks for, feeds results back, and stops when
the model gives a final answer. It runs on **OpenRouter free (`:free`) models
only**, at zero cost, and degrades gracefully when a free model is rate-limited
or removed. The first tools answer energy questions about PV production,
day-ahead prices and irradiance.

### Non-goals (for the PoC)
- Metered production data from SCADA / the asset-management system. The PV
  tool *estimates* production from irradiance and park specs; a metered source
  can replace it later behind the same tool.
- Web UI, multi-user serving, persistence beyond local JSONL traces.
- Paid models. (The config makes switching to a paid model a one-line change.)

## 2. Model selection

### Constraints of the OpenRouter free tier (as of Oct 2026)
- **20 requests/minute**, **50 requests/day** per account (rises to **1,000/day**
  once the account has bought ≥ $10 of credits, lifetime). Failed requests count.
- Each `:free` variant is usually served by **a single provider**, so outages and
  429s are common, and models are rotated out of the free list without notice.
- Free endpoints may log prompts for training: **do not send confidential
  Nordic Solar data** through free models.

**Consequence:** "most reliable" can't mean one hard-coded model. It means a
good primary plus an ordered fallback chain, and a probe that re-checks the
chain.

### Chain (pending live verification with `energy-harness-probe`)

| Priority | Model ID | Why |
|---|---|---|
| 1 (primary) | `openai/gpt-oss-120b:free` | Most consistently recommended free model for tool calling and structured output; open weights from a major lab. |
| 2 | `qwen/qwen3-coder:free` | Explicitly built for function calling / tool use, long context. |
| 3 | `nvidia/nemotron-3-super-120b-a12b:free` | Good output discipline / structured output. |
| 4 (last resort) | `openrouter/free` | OpenRouter's router; picks any free model that supports the request's features (e.g. tools). Always available, non-deterministic. |

Fallback is done client-side so the trace always shows which model answered,
and so a daily-cap 429 fails fast instead of being retried on every model.

> ⚠️ The cloud container that wrote this cannot reach OpenRouter (network
> policy) and has no API key. Model IDs come from current public listings. Run
> `energy-harness-probe` once with your key to confirm and reorder the chain.

## 3. Data sources (free, no API key)

| Tool | Source | Notes |
|---|---|---|
| Irradiance forecast | [Open-Meteo](https://open-meteo.com/) forecast API | GHI (`shortwave_radiation`), tilted irradiance, temperature, cloud cover; up to 16 days ahead, 92 days back |
| PV production (estimate) | Open-Meteo (forecast + archive) + `parks.yaml` | Simple model: plane-of-array irradiance × capacity × performance ratio, temperature-derated, clipped at AC capacity |
| Day-ahead prices | [Energy-Charts API](https://api.energy-charts.info/) (Fraunhofer ISE) | All Nordic + European bidding zones (DK1, DK2, SE3, NO1, DE-LU, …), EUR/MWh |

`parks.yaml` ships with **placeholder example parks**. Replace them with real
park coordinates and capacities.

## 4. Architecture

**Dependencies:** `httpx` (direct calls to OpenRouter's OpenAI-compatible
`/chat/completions`, so we can read rate-limit headers and mock HTTP in tests),
`pydantic` (tool schemas + validation), `pyyaml`, `python-dotenv`, `pytest` +
`respx`. No agent framework, so the loop stays readable in one sitting.

```
harness/
├── PLAN.md
└── poc/
    ├── README.md
    ├── pyproject.toml
    ├── .env.example            # OPENROUTER_API_KEY=...
    ├── config.yaml             # model chain, limits, temperature, max_steps
    ├── parks.yaml              # PV parks (placeholders)
    ├── src/energy_harness/
    │   ├── config.py           # .env + config.yaml → typed Settings
    │   ├── budget.py           # local request guard (per-minute + daily cap)
    │   ├── llm.py              # OpenRouter client: fallback chain, retry, 429 handling
    │   ├── tools.py            # @tool decorator → JSON schema; safe execution
    │   ├── agent.py            # the loop
    │   ├── trace.py            # JSONL trace per session
    │   ├── factory.py          # wires settings → client + tools → Agent
    │   ├── cli.py              # `energy-harness "question"` / REPL
    │   ├── probe.py            # `energy-harness-probe`: live check of each free model
    │   ├── builtin_tools.py    # calculate
    │   └── energy/
    │       ├── sources.py      # Open-Meteo + Energy-Charts clients
    │       ├── parks.py        # park registry
    │       ├── pv.py           # PV estimation math
    │       └── tools.py        # list_parks, get_irradiance_forecast,
    │                           # estimate_pv_production, get_day_ahead_prices
    └── tests/                  # no network: fake LLM + respx fixtures
```

### Key design decisions
1. **Fallback policy:** 5xx / timeout → retry once, then next model.
   404 / 400 / upstream-provider 429 / error-in-body → next model. Per-minute
   429 → wait for reset, retry same model (the limit is account-wide, so
   switching doesn't help). Daily-cap 429, 401, 402 → fail fast, clear message.
2. **Tool-call robustness:** arguments are validated with pydantic; JSON
   wrapped in code fences or passed as an object is accepted; invalid
   arguments come back to the model as a tool error it can correct.
3. **Hard limits:** `max_steps` per question (default 8, then one final
   "answer now" call) and a local request budget persisted per UTC day.
4. **Token thrift:** tools return daily summaries; hourly detail only for
   short ranges.
5. **Tracing:** `runs/<timestamp>.jsonl` (git-ignored) records every LLM call
   (model actually used, fallbacks, latency, tokens) and tool call.

## 5. Tasks

| # | Task | Done when |
|---|---|---|
| 1 | Scaffold `poc/` (pyproject, config, parks, `.env.example`, `.gitignore`) | `pip install -e .` works |
| 2 | `budget.py`, `config.py` + tests | Budget waits at 21st request/min and blocks at daily cap (fake clock) |
| 3 | `tools.py` registry + tests | Typed function → valid tool schema; bad args → structured error |
| 4 | `llm.py` + tests (respx) | 5xx→retry→fallback, 404→fallback, per-min 429→wait, daily 429→fail fast |
| 5 | `agent.py` + `trace.py` + tests (fake LLM) | Multi-step tool use, arg repair, max-steps stop |
| 6 | Energy tools + tests (recorded fixtures) | Irradiance, PV estimate, prices return correct summaries |
| 7 | `cli.py`, `factory.py`, `probe.py` | `energy-harness --help` and `energy-harness-probe --dry-run` work offline |
| 8 | README | A teammate can run it from the README alone |
| 9 | **Live smoke test (you, with key)** | Probe ranks models; a real question uses ≥ 2 tools |

## 6. Risks

| Risk | Mitigation |
|---|---|
| Free model removed / renamed | Fallback chain + `openrouter/free`; probe to re-rank |
| 50 requests/day is tight | Fake-LLM tests; local budget guard; optional $10 top-up later |
| Prompts may be logged by free providers | Only public/non-confidential data; README note |
| API response formats drift | Parsing isolated in `energy/sources.py`; fixture tests; live smoke test |
| Cloud container can't reach OpenRouter / data APIs | Live steps run locally, or allow the hosts in the environment's network policy |
