# Energy 4.0 Harness

**Ask your portfolio. Get checked numbers. Approve the action.**

A chat assistant for a solar and battery portfolio. The model picks tools, deterministic code makes every number, the server checks each number in the answer, and a person approves any action. Everything is audited.

> **Status:** first proof of concept on synthetic data. **Team:** 4 developers + lead.

## Start here

1. Read [INTENT.md](INTENT.md) (five minutes): why, scope and what "done" means.
2. Open [docs/index.html](docs/index.html) in a browser.
3. Click your role and follow your page. Each task is one prompt you paste into Claude Code.

| Role | Your page |
|---|---|
| Lead | [docs/lead.html](docs/lead.html) |
| Dev 1 · Skill, chat page & prices | [docs/developer-1.html](docs/developer-1.html) |
| Dev 2 · Harness, approval & audit | [docs/developer-2.html](docs/developer-2.html) |
| Dev 3 · Model, contracts & health | [docs/developer-3.html](docs/developer-3.html) |
| Dev 4 · Calculator & evals | [docs/developer-4.html](docs/developer-4.html) |

Reference, only when a task links to it: [ARCHITECTURE.md](ARCHITECTURE.md), [TEAM.md](TEAM.md), [EVALS.md](EVALS.md), [DEMO.md](DEMO.md), [KPI_REVIEW.md](KPI_REVIEW.md), [CLAUDE.md](CLAUDE.md).

## What works today

- 13 KPI formulas with tests (`mcp/kpi-solar`)
- Nine read-only tools and the agent loop with a number check (`harness/`)
- Propose, approve once, audit (`mcp/actions`)
- Chat page with charts and an Approve button (`tools/kpi-lab`)
- Model gateway with Claude Haiku 5.5 (`model/`)

## Repository map

```text
energy-agent/
├── INTENT.md, ARCHITECTURE.md, TEAM.md, EVALS.md, DEMO.md, KPI_REVIEW.md
├── docs/            the team guide (built from scripts/build_docs.py)
├── harness/         agent loop, tools, synthetic portfolio
├── mcp/             kpi-solar (numbers), actions (approval, audit), energy-data (price reader)
├── model/           model gateway; one place that may import a model SDK
├── tools/kpi-lab/   chat page and local server
├── schemas/         shared JSON contracts
├── data/synthetic/  demo fixtures
├── evals/, tests/   golden cases and checks
├── scripts/         setup, verify, docs build, smoke test
└── .claude/         subagents, skills, hooks, brand voice rules
```

## Requirements

Python 3.11+, Git, GNU Make, Bash, Node.js for the chart test, and an Anthropic API key in `.env`. Claude Code runs the setup for you: see the first prompt on your page.
