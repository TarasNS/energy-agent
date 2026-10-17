# Energy Agent Harness — Implementation Plan

> Status: **DRAFT, awaiting approval.** No code has been written yet.
> Date: 2026-10-17 · Branch: `claude/awesome-planck-bt3ymf` · Folder: `harness/`

## 1. Goal

Build a small, self-contained **agent harness** in `harness/`: the loop that sends
messages to an LLM, executes the tools it asks for, feeds results back, and stops
when the model gives a final answer. It runs on **OpenRouter free (`:free`) models
only**, at zero cost, and degrades gracefully when a free model is rate-limited or
removed.

The harness is the foundation that the energy-domain tools (production data,
prices, forecasts, etc.) plug into later. This plan covers the harness itself
plus a couple of trivial demo tools to prove the loop works.

### Non-goals (for this iteration)
- Real energy-data integrations (SCADA, market APIs) — later, as tools.
- Web UI, multi-user serving, persistence beyond local JSONL logs.
- Paid models. (The config makes switching to a paid model a one-line change.)

## 2. Model selection

### Constraints of the OpenRouter free tier (as of Oct 2026)
- **20 requests/minute**, **50 requests/day** per account (rises to **1,000/day**
  once the account has bought ≥ $10 of credits, lifetime). Failed requests count.
- Each `:free` variant is usually served by **a single provider**, so outages and
  429s are common, and models are rotated out of the free list without notice.
- Free endpoints may log prompts for training — **do not send confidential
  Nordic Solar data** through free models.

**Consequence:** "most reliable" can't mean one hard-coded model. It means a
good primary plus an ordered fallback chain, and a probe that re-checks the
chain.

### Recommended chain (pending live verification, see Task 2)

| Priority | Model ID | Why |
|---|---|---|
| 1 (primary) | `openai/gpt-oss-120b:free` | Most consistently recommended free model for tool calling and structured output; open weights from a major lab; configurable reasoning effort. |
| 2 | `qwen/qwen3-coder:free` | Explicitly built for function calling / tool use, long context. |
| 3 | `nvidia/nemotron-3-super-120b-a12b:free` | Good output discipline / structured output. |
| 4 (last resort) | `openrouter/free` | OpenRouter's router; picks any free model that supports the features the request needs (e.g. tools). Always available, but non-deterministic. |

OpenRouter also supports server-side fallback via the `models: [...]` array on a
request; the harness will use that **and** keep its own retry/fallback logic,
because a 429 caused by the daily cap won't be fixed by switching models.

> ⚠️ I could not verify these against the live API from this environment
> (OpenRouter is blocked by the cloud container's network policy, and no API key
> is configured). The model IDs come from current public listings and guides.
> Task 2 adds a probe script that you run once with your key to confirm the chain
> and reorder it based on real results.

## 3. Architecture

**Language:** Python 3.11+. **Dependencies:** `openai` SDK (OpenRouter is
OpenAI-compatible, so we just set `base_url`), `pydantic` for tool schemas,
`python-dotenv`, `pytest` for tests. No agent framework, so the loop stays
small enough to read in one sitting.

```
harness/
├── PLAN.md                 # this file
├── README.md               # setup + usage
├── pyproject.toml
├── .env.example            # OPENROUTER_API_KEY=...
├── config.yaml             # model chain, limits, temperature, max_steps
├── src/energy_harness/
│   ├── __init__.py
│   ├── config.py           # load .env + config.yaml → typed Settings
│   ├── llm.py              # OpenRouter client: fallback chain, retry/backoff, 429 handling
│   ├── tools.py            # @tool decorator → JSON schema registry; safe execution
│   ├── agent.py            # the loop: messages → model → tool calls → results → … → answer
│   ├── budget.py           # local request counter (RPM + daily cap) to avoid burning quota
│   ├── logging.py          # JSONL trace per run (messages, tool calls, model used, latency)
│   ├── cli.py              # `energy-harness "question"` / interactive REPL
│   └── demo_tools.py       # get_time, calculator, (stub) get_solar_production
├── scripts/
│   └── probe_models.py     # live check of each free model: reachability, tool-call correctness, latency
└── tests/
    ├── test_tools.py
    ├── test_agent_loop.py  # uses a fake LLM, no network
    └── test_llm_fallback.py
```

### Key design decisions
1. **Provider-agnostic client interface** (`LLMClient.chat(messages, tools) -> Response`),
   so tests use a fake and a paid or local model can be swapped in later.
2. **Fallback policy:** on 5xx, timeout, or "model not found" → next model in the
   chain. On a 429 → read `Retry-After`/`X-RateLimit-*` headers; if it's the
   per-minute limit, back off and retry; if it's the daily cap, fail fast with a
   clear message (switching models won't help).
3. **Tool-call robustness:** free models sometimes emit malformed JSON
   arguments. The harness validates arguments with pydantic and, on failure,
   returns the validation error to the model as the tool result (one repair
   attempt) rather than crashing.
4. **Hard limits:** `max_steps` (default 8) per run and a local request budget,
   so a looping model can't eat the 50/day quota.
5. **Tracing:** every run writes `runs/<timestamp>.jsonl` (git-ignored) with
   the model actually used, which matters when the fallback chain kicks in.

## 4. Tasks (TDD, each one a small commit)

| # | Task | Done when |
|---|---|---|
| 1 | Scaffold `harness/` (pyproject, config, `.env.example`, `.gitignore`, README stub) | `pip install -e harness` works; `pytest` runs (0 tests) |
| 2 | `scripts/probe_models.py` — for each model in the chain: one plain call + one forced tool call; report ok/latency/valid-tool-call | Script runs offline with `--dry-run`; with a key prints a ranked table and suggests a `config.yaml` order |
| 3 | `config.py` + `budget.py` with tests | Settings load from env/yaml; budget blocks the 21st request in a minute (fake clock) |
| 4 | `tools.py` registry with tests | `@tool` turns a typed function into a valid OpenAI tool schema; bad args → structured error |
| 5 | `llm.py` with fallback/retry, tested against a fake HTTP layer | Tests cover 5xx→fallback, 404→fallback, RPM-429→backoff, daily-429→fail fast |
| 6 | `agent.py` loop, tested with a scripted fake LLM | Multi-step tool use, malformed-args repair, `max_steps` stop, final answer returned |
| 7 | `logging.py` JSONL traces + `cli.py` (one-shot + REPL) | `energy-harness "What is 17% of 2.4 MWh?"` runs end to end |
| 8 | Demo tools + live smoke test (manual, needs key) | Real free model completes a 2-tool question; trace shows model used |
| 9 | README: setup, choosing models, free-tier limits, privacy note | A teammate can run it from the README alone |

Estimated effort: about 1 day of focused work. Tasks 1–7 need no API key or
network; 2 and 8 need your OpenRouter key on your machine.

## 5. Risks

| Risk | Mitigation |
|---|---|
| Free model removed / renamed | Fallback chain + `openrouter/free` last resort; probe script to re-rank |
| 50 requests/day is tight for development | Fake-LLM tests for everything; local budget guard; consider a one-off $10 credit purchase to unlock 1,000/day (still using free models) |
| Prompts may be logged by free providers | Only non-confidential data; note in README; config switch to a paid/zero-retention model later |
| Inconsistent tool-call formats across models | pydantic validation + repair round-trip; probe script measures tool-call validity per model |
| Cloud container can't reach OpenRouter | Live steps run on your machine, or allow `openrouter.ai` in the environment's network policy |

## 6. Open questions for you

1. **Python OK?** (Alternative: TypeScript/Node.) The plan assumes Python.
2. **What should the first real energy tools be?** e.g. PV production by park,
   day-ahead prices, weather/irradiance forecast. Not needed for the harness,
   but it shapes the demo.
3. **$10 credit top-up** to lift the daily cap from 50 to 1,000? Optional.
