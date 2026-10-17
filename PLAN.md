# PLAN.md — POC Plan

**Role in the chain:** the *order of work*. We build a **first proof of concept** live, in one short hackathon session. Everything that can be prepared is done before. Team order of actions is in [WORKFLOW.md](WORKFLOW.md). The task list is [TASKS.md](TASKS.md).

## 1. What the POC is

One workflow, end to end, on synthetic DK1 data:

```text
screen → agent loop picks tools → read data → calculator (EUR by cause)
       → AI explanation + recommendation → proposal → human approval → audit line
```

It is not a product. It proves three things: the number is trustworthy, the model is swappable, and actions need a human.

## 2. Phases

### Phase A — Before the hackathon
- GitHub repo [TarasNS/energy-agent](https://github.com/TarasNS/energy-agent) with `main` and `dev`; everyone cloned it and `make setup` passes
- Anthropic API key in each `.env` (never committed)
- the five decisions in `intent.md` confirmed; schemas frozen
- formula v1 and the demo data checked with an energy colleague (15 minutes)
- golden cases G-01 to G-03 and G-07 worked out by hand (Dev 4)
- hackathon judging criteria read; demo story mapped to them (Lead)
- Lovable invite accepted; only synthetic data uploaded; challenge brief pasted ([presentation/lovable-brief.md](presentation/lovable-brief.md)) (Dev 5)

Gate: nobody builds before these are done.

### Phase B — Build (two or three tasks each, in parallel)

| Dev | Tasks in the session ([TASKS.md](TASKS.md)) |
|---|---|
| 1 | T1.1 price reader · T1.2 skill + system prompt |
| 2 | T2.1 tool registry · T2.2 agent loop · T2.3 approve + audit · T2.4 offloader · T2.5 smoke test |
| 3 | T3.1 portfolio reader · T3.2 gateway `run_turn` · T3.3 offline replay · T3.5 `tool_trace` in the result schema |
| 4 | T4.1 golden cases · T4.2 calculator · T4.3 no-invented-EUR eval |
| 5 | T5.1 Lovable screen on a recorded result · T5.2 tool trace · T5.3 connect to the harness |

Every task runs the loop: branch → build → test → verify → PR → CI + review → merge.

### Phase C — First end-to-end run
`make demo-smoke` passes, then `make run` shows the full story on screen.

### Phase D — Rehearse and present
One timed run, one with Wi-Fi off (`MODEL_PROFILE=offline`), merge `dev` into `main`, present.

## 3. Critical path

```text
Golden cases by hand (before) → calculator (Dev 4) + gateway (Dev 3) → agent loop (Dev 2) → offline replay (Dev 3) → smoke test (Dev 2) → screen connected (Dev 5) → rehearsal
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
4. Real public DK1 prices from Energi Data Service, frozen as a fixture
5. Data-class ceiling and a second model vendor
6. Company data adapters
