# INIT.md — Team Bootstrap

## Mission
Build a working Energy 4.0 Harness demo live during the AI in Energy Hackathon.

The product must help an energy portfolio team make one decision better:
**understand monthly curtailment impact in EUR and safely propose the next action.**

## Read order
**People:** open `docs/index.html`, read it once top to bottom, then follow your page. You do not need to read the list below.

**Claude Code sessions** must read these before implementation:

1. [`intent.md`](intent.md) — why
2. [`SPEC.md`](SPEC.md) — what
3. [`ARCHITECTURE.md`](ARCHITECTURE.md) — how (layers, contracts)
4. [`PLAN.md`](PLAN.md) — when
5. [`TEAM.md`](TEAM.md) — who owns what, and [`TASKS.md`](TASKS.md) — the tasks
6. [`CLAUDE.md`](CLAUDE.md) — repo rules and commands
7. the task-specific prompt in [`prompts/`](prompts/)

If they conflict, stop and report the conflict. Do not invent a resolution. The lead resolves it.

## Product principles
1. Business value before architecture.
2. Deterministic calculations before model-generated numbers.
3. Read-only by default.
4. Human approval before side effects.
5. Synthetic/anonymised data first.
6. One workflow in one small agent loop before three partial workflows.
7. Pure tools at the core; the agent loop and model SDK stay at the edge.
8. Evidence before "done".
9. Prefer deletion and simplification over abstraction.
10. Presentation stability beats stretch functionality.

## Git workflow

### Branches
| Branch | Purpose |
|---|---|
| `main` | Stable, rehearsed, tagged demo only. Protected. |
| `dev` | Integrated pre-hackathon build. All PRs target this. |
| `dev1/<task>` … `dev5/<task>` | One short-lived branch per task, e.g. `dev4/energy-calc`. Created from `dev`, merged by squash, then deleted. |

### The task loop
Every task runs the same loop: **branch → build → test (fix until green) → verify → pull request → CI check + review → merge → next task**. The exact commands for each task are on the developer pages.

### PR rules
- One task = one branch = one PR into `dev`, using [the PR template](.github/PULL_REQUEST_TEMPLATE.md).
- A PR merges only when `make check` and `make test` pass locally, the CI `check` job is green and the review partner approves.
- Small, reviewable diffs.
- Squash-merge and delete the branch.
- One owner per file wherever possible; see [TEAM.md](TEAM.md).
- No unrelated cleanup in feature PRs.
- `main` receives only the rehearsed release (`v0.1-hackathon`).

## Environment
Copy `.env.example` to `.env`. Never commit credentials.

```bash
ENERGY_DATA_MODE=synthetic
MODEL_PROFILE=default
STEP_BUDGET=10
ACTION_MODE=proposal_only
AUDIT_LOG_PATH=./artifacts/audit.jsonl
```

Provider keys belong only in your local `.env` or CI secrets.

## Commands
```bash
make setup        # tools check + .venv + dev dependencies
make check        # structure, schemas, links, secret scan
make test         # unit + golden tests (Dev 4 provides)
make eval         # EnergyBench-Lite (Dev 4 provides)
make run          # demo UI (Dev 5 + Dev 3 provide)
make demo-smoke   # end-to-end smoke (Dev 2 provides)
```

Until a command's implementation exists, it fails with a message naming what is missing and who owns it. That is expected at the start.

## Demo invariant
The core demo must work in **synthetic/offline mode** even if an external API or model provider is unavailable.

## First meeting checklist
- [ ] Approve `intent.md`
- [ ] Approve `SPEC.md` and `ARCHITECTURE.md`
- [ ] Approve POC / stretch boundary
- [ ] Put real names into `TEAM.md`
- [ ] Close the five open questions in `intent.md`
- [ ] Confirm synthetic fixture and the one deterministic EUR formula (candidate in `EVALS.md`)
- [ ] Freeze the schemas in `schemas/`
- [ ] Confirm PR merge owner and presentation owner
- [ ] Create `dev`, protect `main`, start feature branches
