# ARCHITECTURE.md: how it is built

**Role:** the *how*. Why is in [INTENT.md](INTENT.md). Exact interfaces are in [SPEC.md](SPEC.md). Who owns what is in [TEAM.md](TEAM.md). This is the target design: the code is built by the team.

## 1. The picture

```text
Chat page (Lovable, repository energy-agent-ui)       render-only: shows what the server returns
        │  POST /api/chat · POST /api/approve · GET /health
Server (tools/kpi-lab/server.py)                       daily cap, allowed origins, approval through mcp/actions
        │
Agent loop (harness/agent.py)                          model picks tools · number check · 8 rounds max
   ├── model: model/model_gateway.run_turn()           Claude Haiku 5.5 · only place a model SDK may be used
   └── tools: harness/registry.py + energy_tools.py    nine tools
          ├── data/synthetic/portfolio.py                synthetic portfolio (2 parks, 1 battery, June 2026)
          ├── mcp/kpi-solar                            every KPI number (13 KPIs, four groups)
          └── mcp/actions                              propose → approve (one-time token) → audit
```

## 2. One question

1. The page posts `{question}` to `/api/chat`.
2. The server takes a slot from the daily cap, then runs `harness.agent.run`.
3. The loop sends the model the system prompt, the question and the nine tool schemas.
4. The model returns text or tool calls. The registry runs each call and never raises: a bad call becomes an error result the model can read.
5. When the model answers in text, `check_numbers` compares every number in the text with the question and all tool results. An unknown number means the text is withheld (`verified: false`, with a note). Charts and proposals still return.
6. The server returns `{text, verified, note, charts, proposals, trace, stopped}`.

## 3. Approval

1. The model may call `propose_action(action, asset, reason)`. This records a proposal and returns its id. It runs nothing.
2. The page shows an **Approve** button per proposal. A person enters a name and presses it.
3. `/api/approve` asks `mcp/actions` for a one-time token, then approves with it. The browser never sees the token.
4. A missing, wrong or reused token, or a proposal already approved, is refused and audited.
5. Execution is simulated. There is no path to a real system.

## 4. Contracts

| Contract | Where | Shape |
|---|---|---|
| Tool results | `harness/registry.py` | JSON string. Money and energy values are decimal strings |
| Model turn | `model/model_gateway` | `ModelTurn(text, tool_calls[])` from `run_turn(system, messages, tools)` |
| Chat answer | `/api/chat` | `{text, verified, note, charts, proposals, trace, stopped}` |
| Audit line | `artifacts/audit.jsonl` | `{ts, event, proposal_id, action, asset, approver}`; a `tool_call` line has `{ts, event, tool, input, ok}` |
| Data schemas | `schemas/*.schema.json` | Checked by `make check` |

## 5. Rules in code

| Rule | Where it is enforced |
|---|---|
| Numbers come from code | `mcp/kpi-solar` calculates; `check_numbers` withholds anything else |
| Approval is never a tool | The registry builds nine tools; none approves. Approval lives only in the server's `/api/approve` |
| Model-agnostic | Only `model/model_gateway/` may import a provider SDK. `make check` fails otherwise |
| No secrets in git | `make check` scans for key patterns; `.env` is git-ignored |
| Do not shadow the `mcp` SDK | Never create `mcp/__init__.py` |
| Synthetic by default | The dataset is seeded and labelled synthetic. No network is needed for tools |

## 6. Build order

Already merged: contracts, model gateway and replay code, synthetic portfolio, 13 KPI formulas, skill, charts, nine tools, agent loop with the number check. The rest is 17 numbered tasks in four rounds; the flow diagram is on the guide's front page ([docs/index.html#combine](docs/index.html#combine)). Every task in round 1 needs nothing, so all five people start at once.

| Round | Tasks | Waits for |
|---|---|---|
| 1 | #1 server routes (Dev 1), #2 container files (Dev 4), #3 golden cases (Dev 2), #4 number-check tests (Dev 2), #5 demo recordings (Dev 3), #6 smoke script (Dev 3), #7 actions and approval (Dev 4), #8 chat page in Lovable (Dev 5) | nothing |
| 2 | #9 server on the real loop (Dev 1), #10 audit every tool call (Dev 3), #11 page on the server (Dev 5) | #1, #7, #8 |
| 3 | #12 golden through the server (Dev 2), #13 five-question run (Dev 1), #14 run the smoke test (Dev 3) | #9, #10, #6 |
| 4 | #15 release to Azure (Dev 4), #16 fixes (Dev 4), #17 rehearse the demo (Dev 2) | #2, #11, #14 |

## 7. Deployment

The server runs as one container on Azure App Service. Dev 4 writes the `Dockerfile` and `.dockerignore` (task #2) and releases (task #15); the lead approves each change in Azure. The chat page is not in the container: it is built in Lovable and calls the server from the internet, so its address must be in `KPI_ALLOWED_ORIGINS`.

| Part | Detail |
|---|---|
| Image | `python:3.11-slim`, only the runtime code. `.dockerignore` is an allowlist: `.env`, tests and docs never enter the image |
| Build | `az acr build` in Azure Container Registry. No local Docker |
| Run | App Service pulls the image with its managed identity |
| Key | `ANTHROPIC_API_KEY` is an App Service setting, never in the image or git |
| Settings | `KPI_DAILY_CAP` (200), `KPI_ALLOWED_ORIGINS`, `KPI_LAB_HOST`, `KPI_LAB_PORT`, `KPI_CAP_FILE`, `AUDIT_LOG_PATH` |
| Health | `GET /health` returns 200 and the calls left today |

Release steps are in the guide: [docs/index.html#deploy](docs/index.html#deploy). Azure resource names are not in the repo.
