# PLAN.md — POC Plan

**Role in the chain:** the *order of work*. We build a **first proof of concept** live, in one short hackathon session. Everything that can be prepared is done before. Team order of actions is in [WORKFLOW.md](WORKFLOW.md).

## 1. What the POC is

One workflow, end to end, on synthetic DK1 data:

```text
page → review → deterministic EUR by cause → AI explanation → recommendation
     → proposal → human approval → audit line
```

It is not a product. It proves three things: the number is trustworthy, the model is swappable, and actions need a human.

## 2. Phases

### Phase A — Before the hackathon
- GitHub repo created; `dev` branch created; everyone cloned it and `make setup` passes
- Anthropic API key in each `.env` (never committed)
- the five decisions in `intent.md` confirmed; schemas frozen
- formula v1 and the demo data checked with an energy colleague (15 minutes)
- golden cases G-01 to G-03 and G-07 worked out by hand (Dev 4)
- hackathon judging criteria read; demo story mapped to them (Lead)

Gate: nobody builds before these are done.

### Phase B — Build (two or three tasks each, in parallel)

| Dev | Tasks in the session |
|---|---|
| 1 | Price reader · curtailment-advisor skill |
| 2 | Propose/approve/audit · workflow · real smoke test |
| 3 | Portfolio reader · model gateway · offline reply |
| 4 | Golden case files · calculator |
| 5 | Screen + local API on a recorded result · connect to real workflow · demo assets |

Every task runs the loop: branch → build → test → verify → PR → CI + review → merge.

### Phase C — First end-to-end run
`make demo-smoke` passes, then `make run` shows the full story on screen.

### Phase D — Rehearse and present
One timed run, one with Wi-Fi off (`MODEL_PROFILE=offline`), merge `dev` into `main`, present.

## 3. Critical path

```text
Golden cases by hand (before) → calculator (Dev 4) → workflow (Dev 2) → screen connected (Dev 5) → smoke test → rehearsal
```
Everyone else builds against the frozen schemas, the fixture that already exists, and stubs.

## 4. Parallel work rules
- Each developer edits only their own paths ([TEAM.md](TEAM.md)).
- Shared files (`CLAUDE.md`, `Makefile`, `schemas/`) change only through their owner.
- One task = one branch = one PR into `dev`.

## 5. Stop conditions
Stop and tell the lead when:
- a change would break `SPEC.md` or a safety rule;
- a schema has to change;
- a golden value changes;
- approval can be bypassed;
- a task grows beyond the POC.

## 6. After the POC

In this order, only when the POC works:

1. EnergyBench-Lite runner and evals (`EVALS.md §4`)
2. Claude Code hooks (`.claude/hooks/README.md`)
3. CI test gating
4. Lovable polish of the screen
5. Real public DK1 prices from Energi Data Service, frozen as a fixture
6. Data-class ceiling and a second model vendor
7. Company data adapters
