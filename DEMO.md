# DEMO.md — Story and Rehearsal

**Owner:** Dev 5 · **Role in the chain:** the acceptance test for the POC. If this demo works, the POC works.

**Demo input:** `demo-solar-dk` · `DK1` · `2026-06` · threshold `1000.00` EUR
**Expected numbers:** _from golden case G-07 (EVALS.md), worked out by hand before the hackathon_

| Number on screen | G-07 value |
|---|---|
| Portfolio negative-price exposure (headline) | _fill in_ |
| Engbakke Solar negative-price exposure | _fill in_ |
| Avoided by self-curtailment | _fill in_ |
| Grid-operator curtailment (may be compensated) | _fill in_ |

## One-line pitch
**Energy 4.0 Harness turns portfolio and market data into auditable EUR decisions, keeps the model swappable, and puts a human in front of every action.**

## 30-second problem
Portfolio teams already have the data, but it sits in asset systems, market feeds and spreadsheets. A generic AI assistant can summarise it, but nobody can answer: *Can I trust the number? Where did my data go? Can it act without me?*

Energy 4.0 Harness separates those concerns:
- code owns the number;
- tools own data access;
- the model owns the explanation;
- a person owns the action.

## Three-minute demo

### 0:00–0:25 — The job
"It's June. I'm reviewing curtailment and negative prices for our DK1 solar portfolio." Select portfolio, DK1, month. Click **Run review**. Point at the tool trace: "The AI chose these tools itself. It had no other tools, and no way to approve."

### 0:25–1:15 — The number
Show the headline and the split:
- Two parks self-curtail at negative prices and **avoid** a cost.
- The grid operator curtailed one park; that loss **may be compensated**.
- **Engbakke Solar keeps producing into negative prices.** That is the cost.

> "The AI chose to call the calculator, and it had to: a review without it fails. Deterministic code made every number, from 15-minute market data. The model only explains it."

### 1:15–1:45 — The recommendation
Read the recommendation: enable negative-price curtailment on Engbakke.

Optional, only if rehearsed: switch `MODEL_PROFILE` to `fast` or `offline` and rerun. "Different model, identical numbers."

### 1:45–2:35 — The control
Click **Create proposal**, type the approver name, click **Approve**. Show the audit line.

> "The assistant prepares the action. A person approves it, and the decision is logged."

### 2:35–3:00 — Close
> "This is a first proof of concept on synthetic data. The reusable part is the energy layer: calculations, data tools, approvals and audit, working with any model. Next: real company data and a second workflow."

## Fallback ladder
1. **No internet:** `MODEL_PROFILE=offline` on the local page — the same agent loop replays recorded model turns, same numbers.
2. **Lovable unreachable:** switch to the local page (`make run`).
3. **Screen fails:** screenshots of each step in `presentation/`.

## Rehearsal checklist
- [ ] Under three minutes
- [ ] No terminal in the main story
- [ ] Presenter knows every G-07 number
- [ ] Approval and audit line clearly visible
- [ ] One run with Wi-Fi off
- [ ] Last sentence is about business value, not technology
