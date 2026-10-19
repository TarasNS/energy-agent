# Energy 4.0 Harness

**An energy-native AI decision layer for renewable-energy companies.**

Energy 4.0 Harness turns portfolio and market data into auditable EUR decisions. The model explains and reasons, deterministic code calculates the business numbers, and a person approves any real-world action.

> **Event:** AI in Energy Hackathon (Implement Consulting Group × Lovable), built live during the event
> **Team:** 5 developers + lead
> **Status:** Repository prepared for a first proof of concept (POC). Built live at the hackathon.

---

## What the POC demonstrates

One workflow, end to end: **Monthly Curtailment Review** on synthetic DK1 data (15-minute prices, June 2026).

A portfolio manager picks a portfolio, DK1 and a month. The system:

1. hands the request to a small **agent loop** (`harness/`), which lets the model (Anthropic SDK, swappable) pick from five fixed tools,
2. the model reads synthetic portfolio and market data through read-only tools,
3. the model must call the calculator: the EUR impact comes **from deterministic code**, split by cause (self-curtailment savings, grid-operator curtailment, production into negative prices),
4. the model explains it and recommends a step: *enable negative-price curtailment on Engbakke Solar*, as a **proposal**,
5. a person **approves** on screen, outside the loop, and every step is written to the **audit log**.

How it works: the guide at [docs/index.html](docs/index.html). The loop is built from the team's working POC harness (branch `claude/awesome-planck-bt3ymf`, `harness/poc/`); [TASKS.md](TASKS.md) says which files to copy.

Not in the POC: hooks, eval runner, CI test gating, live prices, company data. The screen is built in Lovable, with a local page as the offline fallback. See [PLAN.md §6](PLAN.md#6-after-the-poc).

Four rules hold everywhere:

| Concern | Owner |
|---|---|
| Numbers | Deterministic code (`mcp/energy-calc`) |
| Data access | Read-only, controlled tools |
| Actions | Human approval, enforced in code |
| Everything | Auditable |

---

## Start here

1. Open [`docs/index.html`](docs/index.html) in a browser (or [`index.html`](index.html) in the repo root, which forwards there).
2. Click your role.
3. Follow the numbered steps on your page, top to bottom.

| Role | Your page |
|---|---|
| Lead | [docs/lead.html](docs/lead.html) |
| Dev 1 · Price Data & AI Skill | [docs/developer-1.html](docs/developer-1.html) |
| Dev 2 · Harness, Approval & Audit | [docs/developer-2.html](docs/developer-2.html) |
| Dev 3 · Portfolio, Model Gateway & Merges | [docs/developer-3.html](docs/developer-3.html) |
| Dev 4 · Calculator & Golden Tests | [docs/developer-4.html](docs/developer-4.html) |
| Dev 5 · Demo Screen & Story | [docs/developer-5.html](docs/developer-5.html) |

Reference documents (open them only when a step links to them): [intent.md](intent.md), [SPEC.md](SPEC.md), [ARCHITECTURE.md](ARCHITECTURE.md), [PLAN.md](PLAN.md), [TASKS.md](TASKS.md), [TEAM.md](TEAM.md), [EVALS.md](EVALS.md), [DEMO.md](DEMO.md), [CLAUDE.md](CLAUDE.md), [WORKFLOW.md](WORKFLOW.md).

---

## Running

```bash
make setup        # works now: checks tools, creates .venv, installs dev deps
make check        # works now: repo structure, schemas, doc links, secret scan
make test         # unit + golden tests; reports "no tests yet" at the start
make eval         # after the POC (EnergyBench-Lite)
make run          # starts the demo page once Dev 5 adds apps/web/run.sh
make demo-smoke   # reports which stages are missing, then runs the end-to-end checks
make docs         # rebuilds the docs/ portal from scripts/build_docs.py
```

Commands that depend on unbuilt code **fail with an explanation** rather than pretending to pass. That is intentional: a green check must mean something.

Requirements: Python 3.11+, Git, GNU Make, Bash, an Anthropic API key in `.env` (the `offline` profile works without one). Node.js only if Dev 5 picks a JS UI stack.

To view the portal: open `docs/index.html` directly, or run `python3 -m http.server` from the repo root and open `http://localhost:8000/docs/`.

---

## Repository map

```text
energy-agent/
├── *.md                 project artifacts (see "Start here")
├── docs/                static HTML control center (published on GitHub Pages)
├── prompts/             Claude Code session prompts, one per workstream
├── .claude/             agents (researcher, verifier, simplifier), skills, hooks
├── schemas/             shared JSON contracts (draft until Milestone A freeze)
├── data/synthetic/      demo fixtures and golden inputs
├── mcp/                 energy tools: energy-data, portfolio, energy-calc, actions
├── model/               model gateway: Anthropic SDK behind one interface
├── harness/             agent loop: model picks tools, code enforces the rules
├── apps/web/            local API + fallback page (Lovable screen calls the API)
├── evals/               EnergyBench-Lite cases and runner
├── presentation/        slides, Lovable brief, screenshots
├── artifacts/           runtime output (audit log), git-ignored
└── scripts/             setup, verify, demo-smoke
```

## The rule that protects the schedule

> **If a feature does not strengthen the three-minute story, it is not POC.**

Long-term, the reusable energy layer (skills, calculations, adapters, guardrails, evals) is the product. For the hackathon, we prove it with one workflow run by one small agent loop. Roadmap items are listed in [PLAN.md](PLAN.md#7-optional-stretch-order).
