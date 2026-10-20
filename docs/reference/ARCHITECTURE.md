# ARCHITECTURE.md: how it is built

**Role:** the *how*. Why is in [INTENT.md](INTENT.md). Exact interfaces are in [SPEC.md](SPEC.md). Who owns what is in [TEAM.md](TEAM.md). This is the target design: the code is built by the team.

## 1. The picture

```text
Chat page (tools/kpi-lab/index.html, charts.js)        render-only: shows what the server returns
        │  POST /api/chat · POST /api/approve · GET /health
Server (tools/kpi-lab/server.py)                       daily cap, CORS, issues approval tokens
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
| Audit line | `artifacts/audit.jsonl` | `{ts, event, proposal_id, action, asset, approver}` |
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

The harness does not exist yet. The exact contracts are in [SPEC.md](SPEC.md).

| Step | What | Owner |
|---|---|---|
| 1 | Shared schemas, model gateway, import guard and checks | Dev 3 |
| 1 | Synthetic portfolio and the 13 KPI formulas (no other part needed) | Dev 4 |
| 2 | Registry, nine tools, agent loop and number check (a scripted model stands in until the gateway lands) | Dev 2 |
| 2 | Propose, approve once, audit | Dev 2 |
| 3 | Server and chat page against the `/api/chat` contract | Dev 2, Dev 1 |
| 3 | Skill file, golden cases, number-check tests | Dev 1, Dev 4 |
| 4 | Offline replay, smoke test, demo rehearsal | Dev 3, Dev 2, Lead |
| 5 | Container and Azure release | Dev 3, Lead |

## 7. Deployment

The chat runs as one container on Azure App Service. Dev 3 writes the `Dockerfile` and `.dockerignore` in step 5.

| Part | Detail |
|---|---|
| Image | `python:3.11-slim`, only the runtime code. `.dockerignore` is an allowlist: `.env`, tests and docs never enter the image |
| Build | `az acr build` in Azure Container Registry. No local Docker |
| Run | App Service pulls the image with its managed identity |
| Key | `ANTHROPIC_API_KEY` is an App Service setting, never in the image or git |
| Settings | `KPI_DAILY_CAP` (200), `KPI_ALLOWED_ORIGINS`, `KPI_LAB_HOST`, `KPI_LAB_PORT`, `KPI_CAP_FILE`, `AUDIT_LOG_PATH` |
| Health | `GET /health` returns 200 and the calls left today |

Release steps are in the guide: [docs/index.html#deploy](docs/index.html#deploy). Azure resource names are not in the repo.
