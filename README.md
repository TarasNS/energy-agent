# Energy 4.0 Harness

**Ask your portfolio. Get checked numbers. Approve the action.**

A chat assistant for a solar and battery portfolio. The model picks tools, deterministic code makes every number, the server checks each number in the answer, and a person approves any action. Everything is audited.

> **Status:** first proof of concept on synthetic data. **Team:** five people, Dev 1 to Dev 5; Dev 5 is the lead.

## Start here

1. Read [INTENT.md](INTENT.md) (five minutes): why, scope and what "done" means.
2. Read [SPEC.md](SPEC.md), the build contract.
3. Open [docs/index.html](docs/index.html) in a browser.
4. Click your role and follow your page. Each task is one prompt you paste into Claude Code.

| Role | Your page |
|---|---|
| Lead | [docs/lead.html](docs/lead.html) |
| Dev 1 · Contracts & model | [docs/developer-1.html](docs/developer-1.html) |
| Dev 2 · Data, calculator & tools | [docs/developer-2.html](docs/developer-2.html) |
| Dev 3 · Agent loop & smoke | [docs/developer-3.html](docs/developer-3.html) |
| Dev 4 · Approval, server & release | [docs/developer-4.html](docs/developer-4.html) |
| Dev 5 · Chat page in Lovable (lead) | [docs/developer-5.html](docs/developer-5.html) |

Reference, only when a task links to it: [SPEC.md](SPEC.md), [ARCHITECTURE.md](ARCHITECTURE.md), [TEAM.md](TEAM.md), [EVALS.md](EVALS.md), [DEMO.md](DEMO.md), [KPI_REVIEW.md](KPI_REVIEW.md), [CLAUDE.md](CLAUDE.md).

## What the team builds

The repository starts with documents and checks only. The team builds the whole harness in 23 numbered tasks over four rounds, following [SPEC.md](SPEC.md). The harness is made of:

- the synthetic portfolio and 13 KPI formulas (`mcp/kpi-solar`, `data/synthetic`)
- nine read-only tools, the agent loop and the number check (`harness/`)
- propose, approve once, audit (`mcp/actions`)
- the server (`tools/kpi-lab/server.py`) and the chat page, built in Lovable (repository `energy-agent-ui`)
- the model gateway with Claude Haiku 5.5 and offline replay (`model/`)

## Repository map

```text
energy-agent/
├── INTENT.md, SPEC.md, ARCHITECTURE.md, TEAM.md, EVALS.md, DEMO.md, KPI_REVIEW.md
├── docs/            the team guide, with every document above readable as a page
├── scripts/         dev.py (all commands), checks, docs build
└── .claude/         subagents, skills, hooks, brand voice rules
```

The folders the team creates are listed in [SPEC.md §1](SPEC.md). The finished version of an earlier build is kept on tag `reference-v1`; the team does not use it.

## Requirements

Python 3.11+, Git, Node.js for the chart test, and an Anthropic API key in `.env`. Claude Code runs the setup for you: see the first prompt on your page.
