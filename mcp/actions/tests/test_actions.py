import json

import pytest

from actions import approve_action, issue_approval_token, propose_action


@pytest.fixture(autouse=True)
def audit_path(tmp_path, monkeypatch):
    path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(path))
    return path


def read_audit(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_approve_with_valid_token_writes_three_lines(audit_path):
    pid = propose_action("schedule_inspection", "north", "low availability")
    token = issue_approval_token(pid)

    result = approve_action(pid, token, "Taras")

    assert result == {"status": "executed_simulated"}
    lines = read_audit(audit_path)
    assert [line["event"] for line in lines] == ["proposed", "approved", "executed_simulated"]
    assert all(line["proposal_id"] == pid for line in lines)
    assert all(line["action"] == "schedule_inspection" for line in lines)
    assert all(line["asset"] == "north" for line in lines)
    assert lines[0]["approver"] is None  # nobody approves at proposal time
    assert [line["approver"] for line in lines[1:]] == ["Taras", "Taras"]
    assert all(line["ts"] for line in lines)


def test_reused_token_is_denied(audit_path):
    pid = propose_action("schedule_inspection", "north", "r")
    token = issue_approval_token(pid)
    approve_action(pid, token, "Taras")

    second = approve_action(pid, token, "Taras")

    assert second == {"status": "denied"}
    assert read_audit(audit_path)[-1]["event"] == "approval_denied"


def test_token_for_other_proposal_is_denied(audit_path):
    first = propose_action("schedule_inspection", "north", "r")
    second = propose_action("review_ppa_volume", "south", "r")
    token_for_first = issue_approval_token(first)

    result = approve_action(second, token_for_first, "Taras")

    assert result == {"status": "denied"}
    last = read_audit(audit_path)[-1]
    assert last["event"] == "approval_denied"
    assert last["proposal_id"] == second


def test_token_never_in_audit(audit_path):
    pid = propose_action("schedule_inspection", "north", "r")
    token = issue_approval_token(pid)
    approve_action(pid, token, "Taras")
    approve_action(pid, token, "Taras")

    assert token not in audit_path.read_text(encoding="utf-8")
