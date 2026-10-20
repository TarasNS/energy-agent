"""Guards .claude/skills/kpi-advisor/SKILL.md: it must name all nine tools and keep the rules."""

import re
from pathlib import Path

SKILL = Path(__file__).with_name("SKILL.md")
TOOLS_FILE = Path(__file__).resolve().parents[3] / "harness" / "energy_tools.py"

NINE_TOOLS = [
    "list_assets", "list_kpis", "get_kpi", "compare_kpi", "get_series",
    "get_prices", "get_events", "make_chart", "propose_action",
]


def _text() -> str:
    assert SKILL.exists(), f"missing {SKILL}"
    return SKILL.read_text(encoding="utf-8")


def test_file_is_at_most_150_lines():
    assert len(_text().splitlines()) <= 150


def test_frontmatter_has_name_and_description():
    match = re.match(r"---\n(.*?)\n---\n", _text(), re.DOTALL)
    assert match, "no frontmatter"
    assert re.search(r"^name:\s*kpi-advisor\s*$", match.group(1), re.MULTILINE)
    assert re.search(r"^description:\s*\S", match.group(1), re.MULTILINE)


def test_every_one_of_the_nine_tools_is_named():
    text = _text()
    missing = [name for name in NINE_TOOLS if name not in text]
    assert not missing, f"tool names missing from SKILL.md: {missing}"


def test_tool_list_matches_the_code():
    code = TOOLS_FILE.read_text(encoding="utf-8")
    registered = re.search(r"ToolRegistry\(\[(.*?)\]\)", code, re.DOTALL)
    assert registered, "ToolRegistry list not found in harness/energy_tools.py"
    in_code = re.findall(r"\w+", registered.group(1))
    assert sorted(in_code) == sorted(NINE_TOOLS), f"code registers {in_code}"


def test_never_calculate_rule_is_present():
    lines = [l.lower() for l in _text().splitlines()]
    rule = [l for l in lines if "never" in l and all(w in l for w in ("calculate", "add", "average", "round", "estimate"))]
    assert rule, "the never calculate/add/average/round/estimate rule is gone"


def test_other_rules_are_present():
    text = _text().lower()
    for needle in ("synthetic", "unavailable", "at most once", "120 words", "never say", "approved"):
        assert needle in text, f"rule missing: {needle}"
