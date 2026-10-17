# mcp/actions — proposal, approval and audit

**Owner:** Dev 2 · **Status:** not implemented · **Contract:** [`schemas/action-proposal.schema.json`](../../schemas/action-proposal.schema.json)

## Interface
```python
propose_action(payload: dict) -> str                                # proposal_id; audit: proposed
issue_approval_token(proposal_id: str) -> str                       # one-time token, kept in memory
approve_action(proposal_id: str, approval_token: str, approver: str) -> dict
                                                                    # simulated result; audit: approved, executed_simulated
```

## POC approval design
- Only the human **Approve** endpoint in `apps/web` calls `issue_approval_token` and then `approve_action`. The model gets no tools, so it cannot reach either.
- A token is valid once, for one proposal. Missing, wrong, reused or another proposal's token → refused, nothing executed, audit `approval_denied`.
- The approver types their name in the UI; it goes into the audit record. Real identity and login come after the POC.
- The token is never logged or returned to the browser.

## Rules
- `ACTION_MODE=proposal_only`: execution is simulated. There is no code path to a real system.
- Every event appends one JSON line to `AUDIT_LOG_PATH` (format in the schema's `audit_record`). Never rewrite or delete lines.
