# WORKFLOW.md — How the team works

Your exact steps are on your page: [docs/index.html](docs/index.html) → your role. This file is the short shared version.

## Before the hackathon (the repo is ready on GitHub)
1. `git clone`, `git checkout dev`, `make setup`, `make check`
2. Put the Anthropic API key from the lead into `.env` (never commit it)
3. Read [intent.md](intent.md) (5 minutes)
4. `claude` → "Read prompts/0N-….md and follow it. Show me your plan before changing anything." → check the plan → **go**

Review partners: Dev 1 ↔ Dev 4, Dev 2 ↔ Dev 3, Dev 5 → Dev 2.

## For every task: the loop
```text
branch → build → test ──green──→ verify → pull request → CI + review → merge → next task
            ↑        │red                                     │changes asked
            └── fix ─┘                                        └──→ back to build
```
1. **Branch:** `git checkout dev && git pull && git checkout -b devN/<task>`
2. **Build:** tell Claude the task from your page (test first, fix until it passes)
3. **Test:** the task's test command from your page. Red → tell Claude to fix the code, not the test
4. **Verify:** "Use the verifier subagent to check this task against docs/developer-N.html." Fix P0/P1
5. **Pull request:** `make check && make test`, commit, push, `gh pr create --base dev --fill`, using the [template](.github/PULL_REQUEST_TEMPLATE.md)
6. **CI + review:** the `check` job is green and your review partner approves
7. **Merge:** `gh pr merge --squash --delete-branch`, then `git checkout dev && git pull`

## After each merge (Dev 3)
`git checkout dev && git pull && make verify` → post the summary. Red build = top priority.

## Phases
| Phase | Gate | Owner |
|---|---|---|
| Before the hackathon | Repo on GitHub, everyone cloned, `make setup` passes, API key works, contracts frozen | Lead, Dev 3 |
| Build | Each slice passes its focused test and is merged | Each dev |
| First end-to-end run | `make demo-smoke` passes | Dev 2 |
| Stabilise | Tag `v0.1-hackathon`; no refactors after this | Lead |
| Rehearse and present | One timed run, one offline; merge `dev` into `main` | Dev 5 + all |

Branches: one per task, `dev1/<task>` … `dev5/<task>`, created from `dev` and deleted after merge.
