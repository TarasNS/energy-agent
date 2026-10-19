# TEAM.md — Five-Person Split

**Role in the chain:** the *who*. Each person owns a **playbook responsibility and a piece of the energy product**, so the team cannot finish with excellent Claude configuration and no energy demo.

Replace `Dev N` with names at kickoff. Detailed instructions per person live on the developer pages in [`docs/`](docs/index.html).

| Person | Playbook responsibility | Product responsibility | Primary paths | Branches |
|---|---|---|---|---|
| **Dev 1** — _name_ | Skills + hooks | `curtailment-advisor` skill + read-only energy data | `.claude/skills/`, `.claude/hooks/`, `mcp/energy-data/` | `dev1/<task>` |
| **Dev 2** — _name_ | Subagents + feedback loop | Agent loop (`harness/`) + action approval + audit | `.claude/agents/`, `mcp/actions/`, `harness/`, `scripts/demo-smoke.sh` | `dev2/<task>` |
| **Dev 3** — _name_ | `CLAUDE.md` curator | Integration, model gateway, portfolio interface, schemas | `CLAUDE.md`, `Makefile`, `scripts/setup.sh`, `scripts/verify.sh`, `scripts/verify.py`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.env.example`, `.gitignore`, `.github/`, `model/`, `mcp/portfolio/`, `schemas/`, `docs/` | `dev3/<task>` |
| **Dev 4** — _name_ | Evals | Deterministic `energy-calc`, golden fixtures, EnergyBench-Lite | `mcp/energy-calc/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md` | `dev4/<task>` |
| **Dev 5** — _name_ | Presentation | Lovable screen, local API, storyline, fallback assets | `apps/web/` (page + local API), `presentation/`, `DEMO.md` | `dev5/<task>` |
| **Lead** — _name_ | Decisions | Scope, approvals, merge to `main` | `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `PLAN.md`, `TEAM.md`, `WORKFLOW.md`, `README.md`, `INIT.md` | — |

Shared-ownership exceptions:
- `schemas/` fixture schemas: Dev 3 + Dev 4. `action-proposal.schema.json`: Dev 2 + Dev 3. After the Milestone A freeze, any schema change needs lead approval.
- `prompts/`: each developer may tune their own prompt; Dev 3 keeps `00`, `06`, `07`.

## Lead responsibilities
- approve `intent.md`, `SPEC.md`, `ARCHITECTURE.md`, `PLAN.md`;
- close the open questions in `intent.md`;
- decide scope trade-offs and say "no" to late stretch features;
- resolve shared-contract conflicts;
- final merge to `main`.

The lead is not the only integrator. Dev 3 owns integration mechanics; the lead owns decisions.

## Done when (summary)

| Person | Done when |
|---|---|
| Dev 1 | Prices load offline; the skill names the five tools, makes calc mandatory and never invents EUR |
| Dev 2 | The agent loop returns the golden EUR within the step budget; no approval tool in the registry; bad tokens refused; tool calls and approval audited; `make demo-smoke` is real |
| Dev 3 | Portfolio loads and rejects bad rows; `run_turn` works with `default` and replays with `offline`; dev stays green |
| Dev 4 | G-01 to G-03 and G-07 pass exactly in `make test`; the agent trace never states a EUR value the calc did not return |
| Dev 5 | The Lovable screen shows the full story and tool trace from real results; the local page works offline; demo rehearsed |

Full acceptance criteria are on each developer page and in [TASKS.md](TASKS.md).

## Shared review pairing

| Reviewer | Reviews | Why |
|---|---|---|
| Dev 1 | Dev 4's calc contract | The skill quotes it |
| Dev 4 | Dev 1's numeric claims | No invented numbers |
| Dev 2 | Dev 3's integration commands | The smoke test depends on them |
| Dev 3 | Dev 2's runtime assumptions | Config lives with Dev 3 |
| Dev 5 | Everyone's output | Demo comprehensibility |

The lead resolves scope, not style preferences.
