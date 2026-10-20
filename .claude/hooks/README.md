# .claude/hooks/ — after the POC

**Owner:** Dev 4 · **Status:** not part of the hackathon session

In the POC, secrets are protected by `.gitignore` and the secret scan in `make check`. Hooks come after the POC:

| Hook | Event | Checks |
|---|---|---|
| Secret guard | PreToolUse on Write/Edit | Blocks API-key / private-key patterns and writes to `.env` |
| Calc guard | PreToolUse on Write/Edit | Warns on KPI arithmetic outside `mcp/kpi-solar/` |
| Golden guard | PreToolUse on Write/Edit | Blocks edits to frozen golden cases without confirmation |

Rules: each runs in well under a second; never run the full test suite from a hook.
