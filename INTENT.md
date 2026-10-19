# Intent: ask your portfolio, get checked numbers, approve the action

**Read this first.** Every person and every Claude Code session starts here. It says why we build this, what "done" means and what we will not do. If another file disagrees with this one, stop and tell the lead.

**Scope:** a first proof of concept (POC) on synthetic data, built in two hours. Nothing here touches real company systems.

## 1. The problem

Portfolio and asset managers in renewable energy want to ask questions in plain words: "Which park lost most energy in June?" "What is our battery round-trip efficiency?"

A generic AI assistant can answer, but a manager cannot yet rely on it:

1. **The number may be wrong.** A language model can make up or mis-round a figure.
2. **The data may go to the wrong place.** Company data should not reach any model by accident.
3. **It may act alone.** An assistant that changes settings without a person is a risk.

So useful AI stays a demo and does not reach real portfolio work.

## 2. What we build

A chat assistant for a solar and battery portfolio.

1. The manager asks a question in the chat.
2. A small **agent loop** lets the model pick from nine read-only **tools**: list assets, list KPIs, get or compare a KPI, read a series, prices and events, make a chart, propose an action.
3. **Code calculates every number** (`mcp/kpi-solar`, 13 KPIs in four groups). The model only chooses tools and writes the words.
4. The server **checks every number in the answer** against the tool results. A number that is not there means the text is withheld and only charts and tool results are shown.
5. If the data clearly justifies a change, the model may **propose** an action. A **person approves** it in the chat. The model has no approval tool.
6. Every proposal, approval and refusal is written to the **audit log**.

Example action: *enable negative-price curtailment on a park*. It is simulated; nothing is sent anywhere.

## 3. The job to be done

> When I review my renewable portfolio, I want to ask a question and get a number I can trust, with a chart and a recommended next step, so that I can act faster without losing control or an audit trail.

## 4. Who it is for

- **Primary:** portfolio or asset manager.
- **Also:** energy analyst, operations lead, commercial team, risk and compliance reviewer.

## 5. Three promises (the rules behind everything)

| Promise | How it is enforced |
|---|---|
| **Numbers come from code** | Only `mcp/kpi-solar` calculates. The server rejects answers with a number the tools did not return. Money crosses boundaries as decimal strings. |
| **Actions need a person** | The model can propose, never approve. Approval is a separate server call with a one-time token the browser never sees. |
| **Everything is traceable** | Proposals, approvals and refusals are appended to `artifacts/audit.jsonl`. The model sits behind one gateway (`model/model_gateway`), so the vendor can change. |

Also fixed: data tools are read-only, the demo runs on synthetic data, no key is ever in git, no real SCADA or ERP write exists, and only `model/model_gateway/` may import a model SDK.

## 6. Where we are today

| Part | State |
|---|---|
| 13 KPI formulas with tests | Done |
| Synthetic portfolio (2 solar parks, 1 battery, June 2026) | Done |
| Nine tools, agent loop, number check | Done |
| Propose, approve once, audit | Done (tool calls are not yet in the audit log) |
| Chat page with charts and approve button | Done |
| Model gateway (Claude Haiku 5.5, daily cap) | Done |
| Hosting on Azure | An earlier explain-only server ran there. The current chat server is not verified there |
| Offline model replay | Not built |
| Skill file for the model | Not built (prompt is inline in `harness/agent.py`) |
| Evals and golden cases for the agent | Not built |
| Real company data | **Not available.** See `KPI_REVIEW.md` |

## 7. What "done" means for the POC

The POC is done when all of these are true and shown with evidence:

1. The three-minute demo ([DEMO.md](DEMO.md)) runs from the chat page on synthetic data.
2. Each KPI answer matches the hand-worked value in `mcp/kpi-solar/tests`.
3. A made-up number in a model answer is withheld (test exists).
4. Approving without a valid token, or approving twice, is refused and audited (test exists).
5. Every tool call and every approval is in the audit log.
6. The demo runs with no internet, using recorded model turns.
7. `make check` and `make test` are green on `main`.

## 8. Not in this POC

Real Nordic Solar data or adapters · live market prices · production SCADA or ERP writes · login and roles · more than one model vendor in use · multi-agent systems · a full eval suite · battery optimisation.

## 9. Decisions already made

| Question | Decision |
|---|---|
| Which model? | Claude Haiku 5.5 through the gateway. Change it in `.env` or `model/profiles.json` only. |
| Where does the number come from? | `mcp/kpi-solar`. Never from the model. |
| What does an approved action do? | Writes an audit line. It is simulated. |
| How do we ship? | Only `main`. One branch and one pull request per task, merged by the lead. No `dev` branch, no CI/CD. Checks run locally; Azure is released by hand. |

## 10. Open questions for the lead

1. Which real data source do we validate first? Without one, no KPI is production-ready.
2. Who owns `mcp/kpi-solar`? It is a new path that [TEAM.md](TEAM.md) assigns to Dev 4; confirm.
3. Is the Azure server the demo host, or do we run locally?
