# Energy Agent Harness — PoC

A minimal agent harness that answers energy questions with **free OpenRouter
models** and three data tools:

| Tool | What it does | Data source |
|---|---|---|
| `estimate_pv_production` | Estimated MWh/day, peak MW, capacity factor for a park (forecast or past dates) | Open-Meteo irradiance + `parks.yaml` |
| `get_day_ahead_prices` | Day-ahead spot prices per bidding zone (DK1, DK2, SE3, NO1, DE-LU, PL, …) | Energy-Charts (Fraunhofer ISE) |
| `get_irradiance_forecast` | GHI forecast (kWh/m²/day, peak W/m², clouds, temperature) for a park or coordinate | Open-Meteo |
| `list_parks`, `calculate` | Park registry; exact arithmetic | — |

All data sources are free and need no API key. Only OpenRouter needs a key.

See [`../PLAN.md`](../PLAN.md) for the design and model-selection reasoning.

## Setup

```bash
cd harness/poc
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # then paste your key from https://openrouter.ai/keys
```

## Use

```bash
# Check which free models work right now (8 requests), then reorder config.yaml if needed
energy-harness-probe

# One question
energy-harness "What will Example Park Jutland produce tomorrow, and what's the average DK1 price?"

# Interactive session (keeps conversation history)
energy-harness

# Try a specific model / chain for one run
energy-harness --model qwen/qwen3-coder:free --model openrouter/free "Irradiance forecast for SE3 parks?"
```

Model and tool activity is printed to stderr (`-q` to hide it). Every session
writes a trace to `runs/<timestamp>.jsonl`: which model answered, fallbacks,
latency, tokens, tool calls and results.

## Configure

- **`config.yaml`**: model fallback chain, temperature, `max_steps`, request budget.
- **`parks.yaml`**: your PV parks. **The shipped parks are placeholders**;
  replace them with real coordinates, DC/AC capacity, tilt/azimuth and bidding zone.
- **`.env`**: `OPENROUTER_API_KEY`, optional `ENERGY_HARNESS_MODELS` override.

### Model chain

```yaml
models:
  - openai/gpt-oss-120b:free               # primary: strongest free tool-caller
  - qwen/qwen3-coder:free                  # built for function calling
  - nvidia/nemotron-3-super-120b-a12b:free
  - openrouter/free                        # OpenRouter's router: any free model with tool support
```

Free models come and go without notice. If a model disappears, the harness
falls back to the next one automatically; re-run `energy-harness-probe` to
re-rank.

| Error from OpenRouter | Harness behaviour |
|---|---|
| 5xx, timeout, network error | retry once, then next model |
| 400 / 403 / 404, upstream 429, error in body | next model |
| 429 per-minute limit | wait for reset, retry same model |
| 429 daily limit, 401 bad key, 402 | stop with a clear message |

## Free-tier limits — read this

- **50 requests/day** per account, **20/minute**. Failed requests count too.
  A typical question takes 2–4 requests, so expect roughly 15–25 questions a day.
- Buying **$10 of credits once** raises the cap to **1,000 requests/day** on
  free models (credits aren't consumed by `:free` models). Then set
  `budget.requests_per_day: 1000` in `config.yaml`.
- The harness keeps its own count in `runs/budget.json` and stops before
  wasting requests. It's per machine; OpenRouter's count is per account.
- **Privacy:** free providers may log prompts and use them for training. Don't
  send confidential data (contract prices, unpublished production figures).
  Public prices, weather and the estimates here are fine.

## PV estimate: what it is and isn't

`P = capacity_mwp × irradiance/1000 × 0.85 × temperature derate`, clipped at
AC capacity, using tilted irradiance when `tilt` is set. It's a quick
weather-based estimate, not metered output. Expect roughly ±10–20 % on daily
energy for fixed-tilt parks. Trackers, snow, curtailment and outages aren't
modelled.

## Develop

```bash
pytest            # 56 tests, no network or API key needed (fake LLM + recorded API fixtures)
```

```
src/energy_harness/
  agent.py         the loop: model → tool calls → results → … → answer (max_steps guard)
  llm.py           OpenRouter client, fallback chain, rate-limit handling
  tools.py         @tool decorator: typed function → JSON schema; never-raising execution
  budget.py        local request guard
  config.py        config.yaml + .env
  trace.py         JSONL traces
  factory.py       wiring
  cli.py, probe.py command-line entry points
  builtin_tools.py calculate
  energy/          sources.py (APIs), parks.py, pv.py (model), tools.py (agent tools)
```

Adding a tool: write a typed function with a docstring, decorate it with
`@tool`, and add it to the registry in `factory.py`. Use
`Annotated[T, Field(description=...)]` to describe parameters, and raise
`ToolError` for errors the model should see and correct.
