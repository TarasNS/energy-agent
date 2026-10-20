# TEAM.md: who owns what

**Role:** the *who*. What to build is in [SPEC.md](SPEC.md). Exact tasks and prompts are on each person's page in [docs/](docs/index.html).

| Person | Owns | Paths | Branches |
|---|---|---|---|
| **Dev 1**: Anna | Model gateway, contracts, repo health, docs | `CLAUDE.md`, `Makefile`, `scripts/`, `requirements*.txt`, `pytest.ini`, `.env.example`, `.github/`, `model/`, `schemas/`, `docs/`, `Dockerfile`, `.dockerignore` | `dev1/<task>` |
| **Dev 2**: Huiling | KPI calculator, golden cases, evals | `mcp/kpi-solar/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md`, `KPI_REVIEW.md` | `dev2/<task>` |
| **Dev 3**: Raul | Agent loop, approval, audit, smoke test | `harness/`, `mcp/actions/`, `tools/kpi-lab/server.py`, `scripts/demo-smoke.sh`, `.claude/agents/` | `dev3/<task>` |
| **Dev 4**: Søren | The model's skill file and the chat page | `.claude/skills/`, `.claude/hooks/`, `tools/kpi-lab/` (page, charts, config) | `dev4/<task>` |
| **Lead**: Taras | Decisions, the presentation, merges to `main`, deploy | `INTENT.md`, `ARCHITECTURE.md`, `SPEC.md`, `TEAM.md`, `README.md`, `DEMO.md`, `scripts/slides.py` | none |

## Shared paths
- `schemas/`: Dev 1 owns it. Dev 2 and Dev 3 review changes. A change to a contract needs the lead's approval.
- `tools/kpi-lab/`: Dev 3 owns `server.py`, Dev 4 owns everything else in it. `test_server.py` follows `server.py`.

## Done when
| Person | Done when |
|---|---|
| Dev 1 | Contracts match the code; only the gateway imports a model SDK; offline replay matches live answers; container files are on main; checks are green |
| Dev 2 | The synthetic portfolio and 13 KPIs match [SPEC.md](SPEC.md); 13 golden cases pass exactly; a made-up number is withheld, with a test |
| Dev 3 | Nine tools, the loop and the number check work; every tool call, proposal and approval is audited; the smoke test passes offline |
| Dev 4 | The skill names all nine tools and its test is green; every chat page state is clear at phone width |
