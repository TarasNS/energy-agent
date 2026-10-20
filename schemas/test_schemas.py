"""Each shared contract accepts one valid example and rejects one invalid example (SPEC.md §5–§8).

Owner: Dev 1. The examples are the shapes the harness must produce; if a schema and a
real answer disagree, stop and tell the lead (schema changes need the lead's approval).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMAS = Path(__file__).resolve().parent

CHART = {
    "id": "chart_1",
    "kind": "line",
    "title": "Daily actual MWh, north",
    "series": [{"name": "north", "points": [{"x": "2026-06-01", "y": "12.345"}]}],
}

PROPOSAL = {
    "id": "prop_0123456789ab",
    "action": "enable_negative_price_curtailment",
    "asset": "north",
    "reason": "Prices were negative on 4 of 30 days.",
    "status": "pending",
}

CHAT_RESULT = {
    "text": "Availability for June was 96.5 percent.",
    "verified": True,
    "note": None,
    "charts": [CHART],
    "proposals": [],
    "trace": [
        {
            "tool": "get_kpi",
            "input": {"kpi": "availability", "asset": "portfolio", "start": "2026-06-01", "end": "2026-06-30"},
            "ok": True,
        }
    ],
    "stopped": "answered",
}

AUDIT_PROPOSED = {
    "ts": "2026-06-30T10:00:00Z",
    "event": "proposed",
    "proposal_id": "prop_0123456789ab",
    "action": "enable_negative_price_curtailment",
    "asset": "north",
    "approver": None,
}

# (schema file, valid instance, invalid instance)
CASES = {
    "chat-result": (
        CHAT_RESULT,
        {**copy.deepcopy(CHAT_RESULT), "stopped": "done"},  # not one of the four allowed values
    ),
    "chart": (
        CHART,
        {**copy.deepcopy(CHART), "series": [{"name": "north", "points": [{"x": "2026-06-01", "y": 12.345}]}]},  # y must be a string
    ),
    "proposal": (
        PROPOSAL,
        {**copy.deepcopy(PROPOSAL), "id": "prop_xyz"},  # id is prop_ + 12 hex
    ),
    "audit-line": (
        AUDIT_PROPOSED,
        {**copy.deepcopy(AUDIT_PROPOSED), "token": "one-time-secret"},  # a token never appears in the audit log
    ),
}


# Conditional rules (if/then in the schemas). Each valid one must pass; each invalid one must fail.
EXTRA_VALID = [
    ("chat-result", {**copy.deepcopy(CHAT_RESULT), "verified": False, "text": None,
                     "note": "Withheld: the answer contained a number no tool returned."}),
    ("chat-result", {**copy.deepcopy(CHAT_RESULT), "stopped": "max_steps", "verified": False, "text": None,
                     "note": "Stopped after 8 rounds."}),
    ("audit-line", {"ts": "2026-06-30T10:01:00Z", "event": "approved", "proposal_id": "prop_0123456789ab",
                    "action": "schedule_inspection", "asset": "south", "approver": "Anna"}),
    ("audit-line", {"ts": "2026-06-30T10:02:00Z", "event": "refused", "proposal_id": "prop_0123456789ab",
                    "action": "schedule_inspection", "asset": "south", "approver": "Anna"}),
    ("audit-line", {"ts": "2026-06-30T10:03:00Z", "event": "tool_call", "tool": "get_kpi",
                    "input": {"kpi": "availability", "asset": "north"}, "ok": True}),
]

EXTRA_INVALID = [
    ("chat-result", {**copy.deepcopy(CHAT_RESULT), "verified": True, "note": "Something."}),  # verified: no note
    ("chat-result", {**copy.deepcopy(CHAT_RESULT), "verified": False, "text": "Answer."}),  # withheld: no text
    ("chat-result", {**copy.deepcopy(CHAT_RESULT), "stopped": "max_steps", "note": None}),  # max_steps needs a note (SPEC §6)
    ("audit-line", {"ts": "2026-06-30T10:03:00Z", "event": "tool_call", "input": {}, "ok": True}),  # tool_call needs tool
    ("audit-line", {"ts": "2026-06-30T10:01:00Z", "event": "approved", "proposal_id": "prop_0123456789ab",
                    "action": "schedule_inspection", "asset": "south", "approver": None}),  # approval needs an approver
    ("audit-line", {"ts": "2026-06-30T10:01:00Z", "event": "approved", "proposal_id": None,
                    "action": "schedule_inspection", "asset": "south", "approver": "Anna"}),  # approval must name its proposal
    ("audit-line", {"ts": "2026-06-30T10:03:00Z", "event": "tool_call", "tool": "get_kpi",
                    "input": {"token": "one-time-secret"}, "ok": True}),  # no token inside tool inputs either
    ("chart", {**copy.deepcopy(CHART), "kind": "pie"}),  # kind is one of the four
    ("proposal", {**copy.deepcopy(PROPOSAL), "status": "done"}),  # status is pending, approved or refused
]


def _validator(name: str) -> jsonschema.Draft202012Validator:
    # chat-result refers to chart and proposal by file name, so every schema file goes in one registry.
    resources = []
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents, default_specification=DRAFT202012)))
    registry = Registry().with_resources(resources)
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema, registry=registry)


@pytest.mark.parametrize("name", sorted(CASES))
def test_valid_example_passes(name: str) -> None:
    valid, _ = CASES[name]
    errors = list(_validator(name).iter_errors(valid))
    assert errors == [], [e.message for e in errors]


@pytest.mark.parametrize("name", sorted(CASES))
def test_invalid_example_fails(name: str) -> None:
    _, invalid = CASES[name]
    assert list(_validator(name).iter_errors(invalid)), "the invalid example was accepted"


@pytest.mark.parametrize("name,instance", EXTRA_VALID)
def test_conditional_valid_example_passes(name: str, instance: dict) -> None:
    errors = list(_validator(name).iter_errors(instance))
    assert errors == [], [e.message for e in errors]


@pytest.mark.parametrize("name,instance", EXTRA_INVALID)
def test_conditional_invalid_example_fails(name: str, instance: dict) -> None:
    assert list(_validator(name).iter_errors(instance)), "the invalid example was accepted"
