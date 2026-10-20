# TEAM.md: who owns what

**Role:** the *who*. Exact tasks and prompts are on each person's page in [docs/](docs/index.html). Replace `Dev N` with names when you kick off.

| Person | Owns | Paths | Branches |
|---|---|---|---|
| **Dev 1** | The model's skill file, the chat page and the price reader | `.claude/skills/`, `.claude/hooks/`, `mcp/energy-data/`, `tools/kpi-lab/` (page, charts, config) | `dev1/<task>` |
| **Dev 2** | Agent loop, approval, audit, smoke test | `harness/`, `mcp/actions/`, `tools/kpi-lab/server.py`, `scripts/demo-smoke.sh`, `.claude/agents/` | `dev2/<task>` |
| **Dev 3** | Model gateway, contracts, repo health, docs | `CLAUDE.md`, `Makefile`, `scripts/`, `requirements*.txt`, `pytest.ini`, `.env.example`, `.github/`, `model/`, `schemas/`, `docs/`, `Dockerfile`, `.dockerignore` | `dev3/<task>` |
| **Dev 4** | KPI calculator, golden cases, evals | `mcp/kpi-solar/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md`, `KPI_REVIEW.md`, `config/` | `dev4/<task>` |
| **Lead** | Decisions, the presentation, merges to `main`, deploy | `INTENT.md`, `ARCHITECTURE.md`, `TEAM.md`, `README.md`, `DEMO.md`, `scripts/slides.py` | none |

## Shared paths
- `schemas/`: Dev 3 owns it. Dev 4 and Dev 2 review changes. A change to a contract needs the lead's approval.
- `tools/kpi-lab/`: Dev 2 owns `server.py`, Dev 1 owns everything else in it. `test_server.py` follows `server.py`.

## Done when
| Person | Done when |
|---|---|
| Dev 1 | The skill names all nine tools and its test is green; every chat page state is clear; prices load offline |
| Dev 2 | Every tool call, proposal and approval is audited; the smoke test passes offline |
| Dev 3 | Offline replay matches live answers; schemas match the code; container files are on main; checks are green |
| Dev 4 | 13 golden cases pass exactly; a made-up number is withheld, with a test |
