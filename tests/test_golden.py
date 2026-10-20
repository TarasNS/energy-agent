"""Golden cases: every KPI tool result equals the hand-worked value in evals/cases/golden.json.

No model runs here. Each case goes through the same tool registry the agent uses,
and the value is compared exactly, as a string. No tolerance.
"""

import json
from pathlib import Path

import pytest

from harness.dataset import build
from harness.energy_tools import KPIS, build_energy_tools

CASES = json.loads((Path(__file__).resolve().parents[1] / "evals" / "cases" / "golden.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry():
    return build_energy_tools(build(), proposals=lambda action, asset, reason: "unused")


def test_one_case_per_kpi():
    assert sorted(c["arguments"]["kpi"] for c in CASES) == sorted(KPIS)


FIELDS = {"id", "question", "tool", "arguments", "expected", "unit", "note"}


def test_every_case_has_its_fields_and_working():
    for case in CASES:
        assert FIELDS <= case.keys(), f"{case.get('id')} misses {FIELDS - case.keys()}"
        assert case["note"].strip(), f"{case['id']} has no hand working"


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_golden(registry, case):
    result = registry.execute(case["tool"], case["arguments"])
    assert result.ok, result.content
    row = json.loads(result.content)
    assert row["unit"] == case["unit"]
    if case["expected"] is None:
        assert row["value"] is None
        assert row["unavailable"] == case["expected_unavailable"]
    else:
        assert row["unavailable"] is None
        assert row["value"] == case["expected"]
