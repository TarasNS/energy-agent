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

There is also a **simulation mode** (`--simulate`): a fictional fleet with
metered 15-minute production, prices and weather, plus scripted incidents with
known answers. It needs no data APIs and comes with an eval suite that scores
how well each free model answers. See [Simulation and evals](#simulation-and-evals).

See [`../PLAN.md`](../PLAN.md) for the design and model-selection reasoning.

## Setup

```bash
cd harness/poc
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # then paste your key from https://openrouter.ai/keys
```

### Windows / Miniconda notes

- If `pip.exe` or `energy-harness.exe` gives "Access is denied" (security policy),
  use the module form instead: `python -m pip …`, `python -m energy_harness.cli`,
  `python -m energy_harness.probe`, `python -m energy_harness.evals`,
  `python -m energy_harness.energy.sim.cli`.
- With Miniconda, create the environment from conda-forge to avoid Anaconda's
  default-channel terms of service:
  `conda create -n energy -c conda-forge --override-channels python=3.12 -y`.
- Write the key with `Set-Content .env "OPENROUTER_API_KEY=sk-or-v1-..."`.

## Use

```bash
# Check which free models work right now (8 requests), then reorder config.yaml if needed
energy-harness-probe

# One question
energy-harness "What will Example Park Jutland produce tomorrow, and what's the average DK1 price?"

# Interactive session (keeps conversation history)
energy-harness

# Try a specific model / chain for one run
energy-harness --model nvidia/nemotron-3-super-120b-a12b:free --model openrouter/free "Irradiance forecast for SE3 parks?"
```

Model and tool activity is printed to stderr (`-q` to hide it). Every session
writes a trace to `runs/<timestamp>.jsonl`: which model answered, fallbacks,
latency, tokens, tool calls and results.

## Simulation and evals

`simulation.yaml` defines a **fictional** fleet (4 parks in DK1, DK2, SE3 and PL),
a seed, a simulated clock (`now: 2026-10-17T12:00Z`) and scripted incidents:

| Date (2026) | Incident | How the agent can see it |
|---|---|---|
| 10-09 | 40 % of inverters trip at sim-dk-west | `availability_pct` ≈ 69 % |
| 10-11 | DK1 price −18.5 EUR/MWh 12:00–15:00 CEST → sim-dk-west curtails to 0 | negative prices + `curtailed_intervals` |
| 10-12 | Datalogger gap at sim-pl | `data_completeness_pct` ≈ 83 % |
| 10-13 | Grid operator caps sim-se at 8 MW | `curtailed_intervals`, flat peak |
| 10-14 | Substation fault: sim-dk-east offline all day | 0 MWh, availability 0 % |
| 10-05 → | 15 % soiling at sim-pl | only metered vs estimate shows it |

The simulator models sun position, clear-sky irradiance, seeded cloud regimes,
tilted-plane irradiance, temperature, inverter clipping, 15-min day-ahead
prices (demand peaks, solar dip) and automatic curtailment at negative prices.
Same seed ⇒ same numbers on every machine. Weather "forecasts" equal the
simulated actuals.

```bash
energy-harness --simulate "Which park produced nothing on 2026-10-14?"
energy-harness --simulate          # interactive, on the simulated fleet

energy-harness-sim events                                   # parks + incidents
energy-harness-sim production sim-pl 2026-10-10 --end 2026-10-16   # expected vs metered MWh
energy-harness-sim prices DK1 2026-10-11 --csv dk1.csv      # export 15-min data

energy-harness-eval --list
energy-harness-eval                                         # all 8 cases (~25 requests!)
energy-harness-eval --case outage-full --case mean-price --model openrouter/free
```

The eval prints PASS/FAIL per case and a score, and writes details to
`runs/eval-*.json`. Checks are keyword matches, required tool calls, and
numbers within tolerance of what the tools return. Add cases in `evals.yaml`.
With the 50/day free cap, run subsets per model.

`get_metered_production` exists only in simulation mode for now. When real
monitoring data is available, implement the same `production(park, start, end)`
interface (see `energy/sim/adapters.py`) and pass it to `build_energy_tools`.

## Configure

- **`config.yaml`**: model fallback chain, temperature, `max_steps`, request budget.
- **`parks.yaml`**: your PV parks. **The shipped parks are placeholders**;
  replace them with real coordinates, DC/AC capacity, tilt/azimuth and bidding zone.
- **`simulation.yaml`**: simulated fleet, clock and incidents; **`evals.yaml`**: eval cases.
- **`.env`**: `OPENROUTER_API_KEY`, optional `ENERGY_HARNESS_MODELS` and
  `ENERGY_HARNESS_DATA_SOURCE=simulation` overrides.

### Model chain

```yaml
models:
  - nvidia/nemotron-3-super-120b-a12b:free   # primary
  - openrouter/free                          # OpenRouter's router: any free model with tool support
```

Probe results, 2026-10-17:

| Model | Answers | Tool call | Latency | Note |
|---|---|---|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` | yes | yes | 0.9 s | primary |
| `openrouter/free` | yes | yes | 2.1 s | served by `dots-studio/dots-3-note-preview:free` |
| `openai/gpt-oss-120b:free` | — | — | — | no longer free (404) |
| `qwen/qwen3-coder:free` | — | — | — | no longer free (404) |

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
pytest            # 71 tests, no network or API key needed (fake LLM + recorded API fixtures)
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
  evals.py         eval runner (energy-harness-eval)
  energy/          sources.py (APIs), parks.py, pv.py (model), tools.py (agent tools)
  energy/sim/      scenario.py, solar.py, simulator.py, adapters.py, cli.py (energy-harness-sim)
```

Adding a tool: write a typed function with a docstring, decorate it with
`@tool`, and add it to the registry in `factory.py`. Use
`Annotated[T, Field(description=...)]` to describe parameters, and raise
`ToolError` for errors the model should see and correct.
