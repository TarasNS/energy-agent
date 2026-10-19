"""Proposal, one-time approval and append-only audit for the KPI agent.

Approval tokens live only in memory and are never written to the audit log.
Execution is simulated: there is no path to a real system.
"""

import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

_proposals: dict[str, dict] = {}
_tokens: dict[str, str] = {}


def _audit_path() -> Path:
    return Path(os.environ.get("AUDIT_LOG_PATH", "./artifacts/audit.jsonl"))


def _audit(event: str, proposal_id: str, action, asset, approver) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "proposal_id": proposal_id,
        "action": action,
        "asset": asset,
        "approver": approver,
    }
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def propose_action(action: str, asset: str, reason: str) -> str:
    proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
    _proposals[proposal_id] = {"action": action, "asset": asset, "reason": reason}
    _audit("proposed", proposal_id, action, asset, None)
    return proposal_id


def issue_approval_token(proposal_id: str) -> str:
    if proposal_id not in _proposals:
        raise KeyError(f"unknown proposal: {proposal_id}")
    token = secrets.token_urlsafe(32)
    _tokens[proposal_id] = token
    return token


def approve_action(proposal_id: str, token: str, approver: str) -> dict:
    proposal = _proposals.get(proposal_id, {})
    action = proposal.get("action")
    asset = proposal.get("asset")
    expected = _tokens.get(proposal_id)

    if expected is None or not hmac.compare_digest(expected, token or ""):
        _audit("approval_denied", proposal_id, action, asset, approver)
        return {"status": "denied"}

    # One-time: a successful approval spends the token. A wrong token leaves the real one usable.
    del _tokens[proposal_id]
    _audit("approved", proposal_id, action, asset, approver)
    _audit("executed_simulated", proposal_id, action, asset, approver)
    return {"status": "executed_simulated"}
