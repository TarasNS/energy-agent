# TEAM.md: who owns what

**Role:** the *who*. What to build is in [SPEC.md](SPEC.md). Exact tasks and prompts are on each person's page in [docs/](docs/index.html).

| Person | Owns | Paths | Branches |
|---|---|---|---|
| **Dev 1**: Anna | Model gateway, contracts, repo health, docs, the server | `CLAUDE.md`, `Makefile`, `scripts/` (except demo-smoke and test_container), `requirements*.txt`, `pytest.ini`, `.env.example`, `.github/`, `model/` (except `model/recorded/`), `schemas/`, `docs/`, `tools/kpi-lab/server.py`, `tools/kpi-lab/test_server.py` | `dev1/<task>` |
| **Dev 2**: Huiling | KPI calculator, golden cases, evals | `mcp/kpi-solar/`, `evals/`, `tests/`, `data/synthetic/`, `EVALS.md`, `KPI_REVIEW.md` | `dev2/<task>` |
| **Dev 3**: Raul | Tools, agent loop, audit of tool calls, recordings, smoke test | `harness/`, `model/recorded/`, `scripts/demo-smoke.sh`, `.claude/agents/` | `dev3/<task>` |
| **Dev 4**: Søren | Skill, charts, approval, container, Azure release | `.claude/skills/`, `.claude/hooks/`, `tools/kpi-lab/charts.js`, `mcp/actions/`, `Dockerfile`, `.dockerignore`, `scripts/test_container.py` | `dev4/<task>` |
| **Dev 5**: Taras (lead) | Decisions, approvals and merges, the chat page in Lovable, the presentation | `INTENT.md`, `ARCHITECTURE.md`, `SPEC.md`, `TEAM.md`, `README.md`, `DEMO.md`, `scripts/slides.py`, the Lovable repository `energy-agent-ui` | `dev5/<task>`, Lovable |

Søren is the team's software developer; Anna, Huiling and Raul bring the solar knowledge. Everyone builds with Claude Code on Claude Haiku 5.5; the lead builds the chat page in Lovable.

## Shared paths
- `schemas/`: Dev 1 owns it. Dev 2 and Dev 3 review changes. A change to a contract needs the lead's approval.
- `tools/kpi-lab/`: Dev 1 owns `server.py` and `test_server.py`; Dev 4 owns `charts.js`. The chat page itself lives in the Lovable repository `energy-agent-ui`.

## Done when
| Person | Done when |
|---|---|
| Dev 1 | Server routes, cap and allowed origins work; the server runs the real loop and approval; the five-question answers are saved |
| Dev 2 | 13 golden cases pass exactly, also through the live server; a made-up number is withheld, with a test; the demo is rehearsed |
| Dev 3 | Demo recordings replay offline; every tool call is audited; `make demo-smoke` passes offline |
| Dev 4 | Approval is one-time and audited, with no token in any line; the container files are on main; the release on Azure answers `/health` |
| Dev 5 | The Lovable chat page shows every state and works against the real server; every pull request is approved and merged |
