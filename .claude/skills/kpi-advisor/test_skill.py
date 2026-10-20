"""Guards the kpi-advisor skill: it must name the nine tools and keep the rules."""
import re
from pathlib import Path

SKILL = Path(__file__).with_name("SKILL.md")

TOOLS = [
    "list_assets", "list_kpis", "get_kpi", "compare_kpi", "get_series",
    "get_prices", "get_events", "make_chart", "propose_action",
]


def text() -> str:
    assert SKILL.exists(), "SKILL.md is missing"
    return SKILL.read_text(encoding="utf-8")


def test_at_most_150_lines():
    assert len(text().splitlines()) <= 150


def test_frontmatter_has_name_and_description():
    t = text()
    assert t.startswith("---\n")
    front = t.split("---", 2)[1]
    assert re.search(r"^name:\s*kpi-advisor\s*$", front, re.M)
    assert re.search(r"^description:\s*\S", front, re.M)


def test_all_nine_tools_named():
    t = text()
    missing = [n for n in TOOLS if not re.search(rf"(?<![\w]){n}(?![\w])", t)]
    assert not missing, f"tool names missing: {missing}"


def test_never_calculate_rule_present():
    t = text().lower()
    assert re.search(r"(never|do not|don't)[^.\n]*\bcalculate\b", t)
    for verb in ("add", "average", "round", "estimate"):
        assert re.search(rf"\b{verb}\b", t), f"never-calculate rule lacks '{verb}'"


def test_other_required_rules_present():
    t = text().lower()
    assert "synthetic" in t
    assert "unavailable" in t and "reason" in t
    assert re.search(r"make_chart[^.\n]*at most (once|one)|at most (once|one)[^.\n]*make_chart", t)
    assert re.search(r"never[^.\n]*approved", t)
    assert "120 words" in t
