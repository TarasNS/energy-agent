# TEAM.md: who owns what

**Role:** the *who*. What to build is in [SPEC.md](SPEC.md). Exact tasks and prompts are on each person's page in [docs/](docs/index.html).

| Person | Owns | Paths | Branches |
|---|---|---|---|
| **Dev 1**: Anna | Contracts, model gateway, skill, number-check tests, repo health, docs | `schemas/`, `model/` (except `model/recorded/`), `.claude/skills/`, `tests/test_number_check.py`, `CLAUDE.md`, `Makefile`, `scripts/` (except demo-smoke, smoke_turns and test_container), `requirements*.txt`, `pytest.ini`, `.env.example`, `.github/`, `docs/` | `dev1/<task>` |
| **Dev 2**: Huiling | Synthetic portfolio, KPI calculator, nine tools, golden cases | `data/synthetic/`, `mcp/kpi-solar/`, `harness/registry.py`, `harness/energy_tools.py`, `evals/`, `tests/` (except `test_number_check.py`), `EVALS.md`, `KPI_REVIEW.md` | `dev2/<task>` |
| **Dev 3**: Raul | Agent loop and number check, tool-call audit, smoke test, recordings | `harness/agent.py`, `harness/tests/test_agent.py`, `scripts/demo-smoke.sh`, `scripts/smoke_turns.json`, `model/recorded/`, `.claude/agents/` | `dev3/<task>` |
| **Dev 4**: Søren | Approval, server, container, Azure release | `mcp/actions/`, `tools/kpi-lab/`, `Dockerfile`, `.dockerignore`, `scripts/test_container.py` | `dev4/<task>` |
| **Dev 5**: Taras (lead) | Decisions, approvals and merges, the chat page in Lovable, the presentation | `INTENT.md`, `ARCHITECTURE.md`, `SPEC.md`, `TEAM.md`, `README.md`, `DEMO.md`, `scripts/slides.py`, `scripts/flow.py`, the Lovable repository `energy-agent-ui` | `dev5/<task>`, Lovable |

Søren is the team's software developer; Anna, Huiling and Raul bring the solar knowledge. Everyone builds with Claude Code on Claude Haiku 5.5; the lead builds the chat page in Lovable.

## Shared paths
- `schemas/`: Dev 1 owns it. Dev 2 and Dev 3 review changes. A change to a contract needs the lead's approval.
- `harness/`: Dev 2 owns `registry.py` and `energy_tools.py`; Dev 3 owns `agent.py`. `tests/`: Dev 1 owns `test_number_check.py`; Dev 2 owns the rest.

## Done when
| Person | Done when |
|---|---|
| Dev 1 | The four schemas validate; the gateway runs with no network on the offline profile; the skill names all nine tools; number-check tests are green; the five answers are saved |
| Dev 2 | The portfolio is the same on every run; 13 formulas pass hand-worked tests; nine tools answer; 13 golden cases pass exactly, also live; the demo is rehearsed |
| Dev 3 | The loop withholds a made-up number; every tool call is audited; demo recordings replay offline; `make demo-smoke` passes offline |
| Dev 4 | Approval is one-time and audited, with no token in any line; the server answers every route on the real loop; the container files are on main; the release on Azure answers `/health` |
| Dev 5 | The Lovable chat page shows every state and works against the real server; every pull request is approved and merged |
