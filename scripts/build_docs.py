#!/usr/bin/env python3
"""Builds the docs/ portal (owner: Dev 3). Run: make docs

Edit this file, not the generated HTML. Standard library only.
Writing rules: .claude/brand-voice-guidelines.md (one action per step, link every file).
"""
from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "docs"
REPO = "https://github.com/TarasNS/energy-agent.git"
e = html.escape
C = lambda s: f"<code>{e(s)}</code>"

# ───────────────────────── small building blocks ─────────────────────────

def f(path, label=None):
    """Link to a repo file from docs/."""
    return f'<a href="../{path}">{e(label or path)}</a>'


def code(text):
    return f"<pre data-copy><code>{e(text)}</code></pre>"


def step(title, text="", files=(), cmd=None, claude=None, see=None):
    h = f'<li><span class="t">{title}</span>'
    if text:
        h += f"<p>{text}</p>"
    if files:
        h += '<p class="files">Files: ' + ", ".join(f(x) if isinstance(x, str) else f(*x) for x in files) + "</p>"
    if cmd:
        h += code(cmd)
    if claude:
        h += '<p class="say">Tell Claude</p>' + code(claude)
    if see:
        h += f'<p class="see">You should see: {see}</p>'
    return h + "</li>"


def route(*steps):
    return '<ol class="busbar">' + "".join(steps) + "</ol>"


def block(title, sub, inner, id_=None):
    i = f' id="{id_}"' if id_ else ""
    s = f"<p>{sub}</p>" if sub else ""
    return f'<section class="wrap"{i}><div class="side-label"><h2>{title}</h2>{s}</div><div>{inner}</div></section>'


def done(items):
    return '<ul class="done">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


# ───────────────────────── page chrome ─────────────────────────

COL = {1: "var(--d1)", 2: "var(--d2)", 3: "var(--d3)", 4: "var(--d4)", 5: "var(--d5)", "L": "var(--lead)"}
SUN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="none" stroke="#1a5c00" stroke-width="1.8"/>'
       '<g stroke="#1a5c00" stroke-width="1.6" stroke-linecap="round"><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1"/></g></svg>')
NAV = [("index.html", "Start", "L"), ("harness.html", "How the harness works", "L"), ("lead.html", "Lead", "L"), ("developer-1.html", "Dev 1 · Prices & skill", 1),
       ("developer-2.html", "Dev 2 · Harness & approval", 2), ("developer-3.html", "Dev 3 · Portfolio & model", 3),
       ("developer-4.html", "Dev 4 · Calculator", 4), ("developer-5.html", "Dev 5 · Demo screen", 5)]
FOOT = ('<footer class="dark"><h2>Background, only when a step links to it</h2><ul class="refs">'
        + "".join(f"<li>{f(x)}</li>" for x in ["intent.md", "SPEC.md", "ARCHITECTURE.md", "PLAN.md", "TASKS.md", "TEAM.md", "EVALS.md", "DEMO.md", "CLAUDE.md", "WORKFLOW.md"])
        + f'</ul><div class="fine"><span>Energy 4.0 Harness · first proof of concept · AI in Energy Hackathon</span><span>Writing rules: {f(".claude/brand-voice-guidelines.md")}</span></div></footer>')


def page(slug, title, body, accent="var(--d1)"):
    nav = "".join(f'<a href="{h}"{" aria-current=\"page\"" if h == slug else ""}><i style="background:{COL[c]}"></i>{e(t)}</a>' for h, t, c in NAV)
    cls = "home" if slug == "index.html" else "role"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} — Energy 4.0 Harness</title>
<link rel="stylesheet" href="css/tokens.css">
<link rel="stylesheet" href="css/style.css">
</head>
<body class="{cls}" style="--accent:{accent}">
<header class="top">
  <a class="mark" href="index.html">{SUN}energy 4.0 harness</a>
  <details class="menu"><summary aria-label="Menu"><span></span></summary><nav aria-label="Pages">{nav}</nav></details>
</header>
<main class="page">
{body}
</main>
{FOOT}
<script src="js/app.js"></script>
</body>
</html>
"""


# ───────────────────────── diagrams ─────────────────────────

def part(d, x, y, w, h, t, s):
    return (f'<g class="part d{d}"><rect class="fill{d}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'
            f'<text class="t" x="{x + w / 2}" y="{y + h / 2 - 3}" text-anchor="middle">{e(t)}</text>'
            f'<text class="s" x="{x + w / 2}" y="{y + h / 2 + 16}" text-anchor="middle">{e(s)}</text>'
            f'<circle class="badge" cx="{x + 4}" cy="{y + 4}" r="11"/><text class="bn" x="{x + 4}" y="{y + 8}" text-anchor="middle">{d}</text></g>')


def arch(id_, focus=None):
    fa = f' data-focus="{focus}"' if focus else ""
    g = [f'<div class="arch" id="{id_}"{fa}><svg viewBox="-10 -10 975 655" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{id_}-t">',
         f'<title id="{id_}-t">Energy 4.0 Harness POC architecture; the number on each box is the developer who builds it</title>',
         '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1c1c1c" fill-opacity=".6"/></marker></defs>',
         '<path class="wire" d="M480 84V118"/>', '<path class="wire" d="M440 184L320 218"/>', '<path class="wire" d="M520 184L640 218"/>',
         '<path class="wire" d="M270 284L120 328"/>', '<path class="wire" d="M315 284L358 328"/>', '<path class="wire" d="M360 284L590 328"/>',
         '<path class="wire" d="M585 151H840V328"/>',
         '<path class="wire" d="M115 396V436"/>', '<path class="wire" d="M355 396V436"/>', '<path class="wire" d="M595 396V436"/>', '<path class="wire" d="M835 396V436"/>',
         part(5, 370, 20, 220, 64, "Lovable screen + API", "apps/web · local fallback"),
         part(2, 370, 120, 220, 64, "Agent loop", "model picks tools · harness/"),
         part(1, 200, 220, 230, 64, "curtailment-advisor", "the AI skill"),
         part(3, 530, 220, 230, 64, "Model gateway", "Anthropic SDK · swappable"),
         part(1, 10, 330, 210, 66, "energy-data", "prices · read-only"),
         part(3, 250, 330, 210, 66, "portfolio", "assets · read-only"),
         part(4, 490, 330, 210, 66, "energy-calc", "EUR by cause"),
         part(2, 730, 330, 220, 66, "actions", "propose → approve"),
         part(4, 10, 438, 210, 62, "Price fixtures", "15-minute · DK1"),
         part(4, 250, 438, 210, 62, "Portfolio fixtures", "3 demo parks"),
         part(4, 490, 438, 210, 62, "Golden tests", "hand-worked EUR"),
         part(2, 730, 438, 220, 62, "Audit log", "tool calls, proposals, approvals"),
         '<text class="band" x="10" y="540">Across everything</text>',
         part(3, 10, 552, 225, 62, "Contracts & merges", "schemas · make verify"),
         part(3, 245, 552, 225, 62, "Offline turns", "model/recorded"),
         part(2, 480, 552, 225, 62, "Smoke test", "make demo-smoke"),
         part(5, 715, 552, 235, 62, "Demo story", "DEMO.md · screenshots"),
         "</svg></div>"]
    return "".join(g)


def legend(target):
    names = {1: "Dev 1 · Prices & skill", 2: "Dev 2 · Harness & approval", 3: "Dev 3 · Portfolio & model", 4: "Dev 4 · Calculator", 5: "Dev 5 · Demo screen"}
    return (f'<ul class="legend" data-legend="{target}">'
            + "".join(f'<li><button type="button" data-d="{d}" aria-pressed="false"><i>{d}</i>{n}</button></li>' for d, n in names.items())
            + "</ul>")


def loop_svg():
    labels = [("Branch", "from dev"), ("Build", "tell Claude"), ("Test", "focused test"), ("Verify", "verifier subagent"),
              ("Pull request", "into dev"), ("CI + review", "check + partner"), ("Merge", "squash, sync")]
    gate = {2, 5}
    w, gap, y, h = 120, 16, 70, 58
    xs = [10 + i * (w + gap) for i in range(len(labels))]
    out = ['<div class="loopdiagram"><svg viewBox="0 0 960 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="lt">'
           '<title id="lt">The task loop: branch, build, test, verify, pull request, CI and review, merge, then the next task</title>'
           '<defs><marker id="la" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1c1c1c" fill-opacity=".6"/></marker></defs>']
    for i, (t, s) in enumerate(labels):
        x = xs[i]
        out.append(f'<g class="{"n g" if i in gate else "n"}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="29"/>'
                   f'<text x="{x + w / 2}" y="{y + 25}" text-anchor="middle">{t}</text><text class="s" x="{x + w / 2}" y="{y + 42}" text-anchor="middle">{s}</text></g>')
        if i:
            out.append(f'<path class="w" d="M{xs[i - 1] + w + 1} {y + h / 2}H{x - 2}"/>')
    tx, bx = xs[2] + w / 2, xs[1] + w / 2
    out.append(f'<path class="w back" d="M{tx} {y + h + 2}V{y + h + 40}H{bx}V{y + h + 4}"/>')
    out.append(f'<text class="lab" x="{tx + 14}" y="{y + h + 44}" text-anchor="start">red: fix the code, run the test again</text>')
    rx = xs[5] + w / 2
    out.append(f'<path class="w back" d="M{rx} {y + h + 2}V{y + h + 78}H{bx - 28}V{y + h + 4}"/>')
    out.append(f'<text class="lab" x="{(rx + bx) / 2 + 60}" y="{y + h + 96}" text-anchor="middle">changes asked in review: back to Build on the same branch</text>')
    mx, brx = xs[6] + w / 2, xs[0] + w / 2
    out.append(f'<path class="w back" d="M{mx} {y - 2}V{y - 34}H{brx}V{y - 4}"/>')
    out.append(f'<text class="lab" x="{(mx + brx) / 2}" y="{y - 42}" text-anchor="middle">merged: start the next task on a new branch</text>')
    out.append("</svg></div>")
    return "".join(out)


LOOP = loop_svg()

GL = {
    1: '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"><circle cx="32" cy="32" r="11"/><path d="M32 6v8M32 50v8M6 32h8M50 32h8M13.6 13.6l5.7 5.7M44.7 44.7l5.7 5.7M13.6 50.4l5.7-5.7M44.7 19.3l5.7-5.7"/></svg>',
    2: '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="32" r="6"/><circle cx="32" cy="32" r="6"/><circle cx="52" cy="32" r="6"/><path d="M18 32h8M38 32h8"/><path d="M47 20l5 5 5-5M52 25V12"/></svg>',
    3: '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round"><path d="M14 18h40l-6 26H8z"/><path d="M12 31h40M28 18l-5 26M41 18l-5 26"/><path d="M28 44v10M22 54h12" stroke-linecap="round"/></svg>',
    4: '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round"><path d="M44 18a16 16 0 1 0 0 28"/><path d="M14 28h22M14 36h22"/></svg>',
    5: '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round"><rect x="8" y="12" width="48" height="32" rx="2"/><path d="M26 54h12M32 44v10" stroke-linecap="round"/><path d="M16 36l8-8 6 5 10-11" stroke-linecap="round"/></svg>',
    "L": '<svg viewBox="0 0 64 64" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M18 56V8"/><path d="M18 10h30l-7 9 7 9H18"/></svg>',
}


def tile(href, d, k, title):
    cls = "tile lead" if d == "L" else "tile"
    return f'<a class="{cls}" href="{href}" style="background:{COL[d]}"><span class="k">{k}</span>{GL[d]}<b>{title}</b></a>'


# ───────────────────────── the task loop inside each task ─────────────────────────

REVIEWER = {1: "Dev 4", 2: "Dev 3", 3: "Dev 2", 4: "Dev 1", 5: "Dev 2"}
SFX = " Write the test first, run it, and keep fixing until it passes. Show me the output."


def _build(b):
    if "\n<paste" in b:
        i = b.index("\n<paste")
        return b[:i] + SFX + b[i:]
    return b + SFX


def row(label, body, cls="", sub=None):
    s = f"<small>{sub}</small>" if sub else ""
    c = f' class="{cls}"' if cls else ""
    return f'<li{c}><div class="lbl">{label}{s}</div><div class="body">{body}</div></li>'


def task(n, title, slug, build, test, see, files=(), text=""):
    br = f"dev{n}/{slug}"
    head = f'<li><span class="t">{title}</span>' + (f"<p>{text}</p>" if text else "")
    if files:
        head += '<p class="files">Files: ' + ", ".join(f(x) if isinstance(x, str) else f(*x) for x in files) + "</p>"
    plain_title = html.unescape(re.sub("<[^>]+>", "", title))
    rows = [
        row("Branch", code(f"git checkout dev && git pull\ngit checkout -b {br}")),
        row("Build", '<p class="say">Tell Claude</p>' + code(_build(build))),
        row("Test", code(test) + f'<p class="see">You should see: {see}</p>', "gate", "must be green"),
        row("If red", code("The test failed. Here is the output:\n<paste>\nFix the code, not the test, and run it again."), "red", "loop back"),
        row("Verify", code(f"Use the verifier subagent to check this task against docs/developer-{n}.html. Report, don't fix."), "", "fix any P0 / P1"),
        row("Pull request", code(f'make check && make test\ngit add -A\ngit commit -m "Dev {n}: {plain_title}"\ngit push -u origin {br}\ngh pr create --base dev --fill')),
        row("CI + review", f"<p>Wait for the <code>check</code> job to go green on the PR. {REVIEWER[n]} reviews it. Changes asked? Go back to <b>Build</b> on the same branch.</p>", "gate", "both green"),
        row("Merge", code("gh pr merge --squash --delete-branch\ngit checkout dev && git pull"), "", "then next task"),
    ]
    return head + '<ol class="loopsteps">' + "".join(rows) + "</ol></li>"


def setup(prompt, extra=()):
    return route(
        step("Get the code", cmd=f"git clone {REPO}\ncd energy-agent\ngit checkout dev"),
        step("Install", cmd="make setup\nmake check", see="<code>Setup complete</code>, then <code>make check passed.</code>"),
        step("Add the API key", "Paste the Anthropic key the lead gives you into <code>.env</code>. Never commit it. Without a key, <code>MODEL_PROFILE=offline</code> still works.", files=[".env.example"]),
        step("Read the problem and the harness (10 minutes)", "Read only these two. Claude Code reads the rest for you.", files=["intent.md", ("docs/harness.html", "How the harness works")]),
        *extra,
        step("Start Claude Code", "Do this when the build starts.", cmd="claude"),
        step("Give Claude your brief", "Claude replies with a plan. Check it only touches your files (top of this page). Then reply <b>go</b>.",
             files=[f"prompts/{prompt}"], claude=f"Read prompts/{prompt} and follow it. Show me your plan before changing anything."),
    )


DEMO_CMD = "MODEL_PROFILE=offline python -m harness.agent --portfolio demo-solar-dk --zone DK1 --month 2026-06 --json"

# ───────────────────────── developer content (POC scope) ─────────────────────────

DEVS = {
    1: dict(title="Price Data &amp; AI Skill", own=["mcp/energy-data/", ".claude/skills/"], prompt="01-dev1-prices-skill.md", extra=(),
            tasks=[
                task(1, "Build the price reader", "price-reader",
                     "Build get_day_ahead_prices in mcp/energy-data as described in its README, reading data/synthetic/demo-solar-dk/prices-DK1-2026-06.jsonl. Use interval_minutes from each row; never assume 60.",
                     "pytest mcp/energy-data -q", "all tests pass with Wi-Fi off.",
                     files=["mcp/energy-data/README.md", "schemas/market-price.schema.json", "data/synthetic/README.md"]),
                task(1, "Write the skill and system prompt", "skill",
                     "Create .claude/skills/curtailment-advisor/SKILL.md following .claude/skills/README.md, under 150 lines, and a short harness/prompts/system.txt. The agent loop sends both to the model with five tools. The skill names the tools, makes calculate_curtailment_value mandatory and allows actions only through propose_action. Add a test that checks the six contract points are present.",
                     "pytest .claude/skills -q\nmake check", "the six-point test passes.", files=[".claude/skills/README.md"],
                     text="Send the PR link to Dev 4 to check every rule about numbers."),
            ],
            spare="Help Dev 2 with the smoke test, or pair with Dev 5 on the screen text.",
            done=["Prices for DK1, June 2026 load with Wi-Fi off.", "The skill names the five tools, makes the calculator mandatory and never invents numbers.", "Both tasks were merged through a green PR."]),
    2: dict(title="Harness, Approval &amp; Audit", own=["mcp/actions/", "harness/", "scripts/demo-smoke.sh", ".claude/agents/"], prompt="02-dev2-orchestration-feedback.md", extra=(),
            tasks=[
                task(2, "Build propose, approve and audit", "actions",
                     "Build mcp/actions as described in its README. Start with tests that refuse a missing, wrong, reused or other-proposal token, then the audit log.",
                     "pytest mcp/actions -q", "every bad token is refused and nothing runs; each event is a line in artifacts/audit.jsonl.",
                     files=["mcp/actions/README.md", "schemas/action-proposal.schema.json"]),
                task(2, "Build the tool registry", "registry",
                     "Copy the POC tools.py to harness/tools/registry.py and add harness/config.py, as described in harness/README.md. Register stubs for exactly the five tools. Test: exactly five tools; no calculate, approve_action or issue_approval_token; unknown tool and bad arguments return an error result.",
                     "git fetch origin claude/awesome-planck-bt3ymf\ngit show origin/claude/awesome-planck-bt3ymf:harness/poc/src/energy_harness/tools.py > harness/tools/registry.py\npytest harness -q", "the registry tests pass.", files=["harness/README.md", ("TASKS.md", "TASKS.md (what we reuse)")]),
                task(2, "Build the agent loop with stubs", "harness",
                     "Copy the POC agent.py to harness/agent.py and tests/conftest.py to harness/tests/conftest.py. Turn Agent.run() into run_review() as described in harness/README.md: same loop and forced final answer, STEP_BUDGET, model via model_gateway. Test with the POC ScriptedLLM: stop on final text, stop at STEP_BUDGET, fail when calc was never called, copy result numbers from the calc output, no approval tool in the registry. Call the model only through model_gateway.get_client().run_turn().",
                     "pytest harness -q\n" + DEMO_CMD, "JSON that validates against review-result.schema.json.",
                     files=["harness/README.md", "schemas/review-result.schema.json", "model/README.md"]),
                task(2, "Add the trace and tool audit", "trace",
                     "Copy the POC trace.py to harness/trace.py. Append every tool_call event to AUDIT_LOG_PATH. When the registry truncates a large result, save the full output to artifacts/ and give the model the path.",
                     "pytest harness -q", "every call is in artifacts/audit.jsonl; large outputs land in artifacts/.", files=["harness/README.md"]),
                task(2, "Wire the real tools and the smoke test", "smoke",
                     "Replace the stubs with the real portfolio, energy-data and energy-calc tools from dev, then replace the placeholder in scripts/demo-smoke.sh with the five checks listed at its top.",
                     "pytest harness -q\nmake demo-smoke", "the golden EUR value for DK1, June 2026, and all five smoke checks pass offline.",
                     files=["scripts/demo-smoke.sh"], text="Start when Dev 3 and Dev 4 have merged their tools. Then tell Dev 5 the harness is ready."),
            ],
            spare="Pair with Dev 5 on connecting the screen.",
            done=["The agent loop returns the golden EUR value for DK1, June 2026, within the step budget.", "The registry has exactly five tools and no approval tool.", "Bad approval tokens are refused, and nothing runs.", "An approved proposal writes proposed, approved and executed_simulated to the audit log.", "<code>make demo-smoke</code> passes offline.", "Every task was merged through a green PR."]),
    3: dict(title="Portfolio, Model Gateway &amp; Merges", own=["mcp/portfolio/", "model/", "schemas/", "CLAUDE.md", "Makefile", "scripts/", ".github/", "docs/"], prompt="03-dev3-claude-integration.md", extra=(),
            tasks=[
                task(3, "Build the portfolio reader", "portfolio",
                     "Build list_assets and get_production in mcp/portfolio as described in its README, over data/synthetic/demo-solar-dk. Reject malformed rows with a clear error.",
                     "pytest mcp/portfolio -q", "valid rows load; a broken row raises a clear error.",
                     files=["mcp/portfolio/README.md", "schemas/asset.schema.json", "schemas/production.schema.json"]),
                task(3, "Build the model gateway", "model-gateway",
                     "Build model/model_gateway as described in model/README.md, shaped like the POC llm.py ChatClient protocol: get_client() with run_turn(messages, tools), an Anthropic SDK client with tool use and a recorded offline client that replays turns. Only this package may import anthropic. Mock the SDK in tests.",
                     "pytest model -q\nmake check", "tests pass and the model-agnostic check says ok.",
                     files=["model/README.md", "model/profiles.json"]),
                task(3, "Record the offline turns", "offline-reply",
                     "Run the demo review once with MODEL_PROFILE=default, save the model turns as model/recorded/G-07.json, and add a test that every number in it appears in the calc result.",
                     "pytest model -q\n" + DEMO_CMD, "the same numbers as with the default profile, with no internet.",
                     files=["model/recorded/README.md"], text="Start when Dev 2's agent loop runs end to end."),
                task(3, "Add the tool trace to the result schema", "tool-trace",
                     "With Dev 2: add an optional tool_trace array (name, order, ok) to schemas/review-result.schema.json, before the schema freeze. Update ARCHITECTURE.md §4 if the contract text changes.",
                     "make check", "JSON schemas ok.", files=["schemas/review-result.schema.json"]),
            ],
            spare="After each merge into dev: <code>git pull && make verify</code>, and post the result in the team chat.",
            done=["Portfolio loads and rejects a broken row clearly.", "run_turn works with default and replays with offline; nothing outside model/ imports the SDK.", "<code>model/recorded/G-07.json</code> holds the recorded turns and uses only calc numbers.", "review-result has tool_trace.", "dev stays green after every merge."]),
    4: dict(title="Calculator &amp; Golden Tests", own=["mcp/energy-calc/", "data/synthetic/", "evals/", "EVALS.md"], prompt="04-dev4-evals-calc.md",
            extra=(step("Work out the golden cases by hand", "G-01 to G-03 and G-07, in a spreadsheet, not Claude. Claude must never produce a golden number.", files=[("EVALS.md", "EVALS.md (§2 formula, §3 cases)"), "data/synthetic/README.md"],
                        cmd="python data/synthetic/generate.py --summary"),
                   step("Send the G-07 numbers to Dev 5", "They go into DEMO.md and the presenter's notes.")),
            tasks=[
                task(4, "Add the golden tests", "golden",
                     "Turn my hand-worked golden cases below into pytest tests in mcp/energy-calc/tests/. Do not change any expected value.\n<paste your spreadsheet results>",
                     "pytest mcp/energy-calc -q", "the tests run and fail, because the calculator does not exist yet.", files=[("EVALS.md", "EVALS.md (§3)")]),
                task(4, "Build the calculator", "energy-calc",
                     "Build calculate_curtailment_value in mcp/energy-calc as described in its README and EVALS.md §2, test-first until every golden case passes with exact equality.",
                     "pytest mcp/energy-calc -q", "G-01 to G-03 and G-07 pass with exact string equality.", files=["mcp/energy-calc/README.md"]),
                task(4, "Check the agent never invents EUR", "no-invented-eur",
                     "Add a test that reads the offline agent trace (model/recorded/G-07.json) and checks every EUR value in the final text appears in the calc output.",
                     "make test", "the check passes; changing a number in the trace makes it fail.", files=["EVALS.md", "model/recorded/README.md"],
                     text="Start when Dev 3 has recorded the offline turns."),
            ],
            spare="Help Dev 2 wire the calculator into the agent loop, then check the numbers on Dev 5's screen.",
            done=["G-01 to G-03 and G-07 pass exactly in <code>make test</code>.", "Every golden value has its hand working in the test.", "Broken input gives a clear error and no number.", "Both tasks were merged through a green PR."]),
    5: dict(title="Lovable Screen &amp; Story", own=["apps/web/", "presentation/", "DEMO.md"], prompt="05-dev5-ui-presentation.md", extra=(),
            tasks=[
                task(5, "Build the screen and local API", "screen",
                     "Build apps/web as described in its README: a FastAPI server with the three endpoints returning apps/web/recorded.json for now, one fallback HTML page, and apps/web/run.sh. Test the endpoints with TestClient. Build the main screen in Lovable from presentation/lovable-brief.md against the same recorded.json.",
                     "pytest apps/web -q\nmake run", "the page at localhost:8000 shows the full story from the recorded result.",
                     files=["apps/web/README.md", "presentation/lovable-brief.md", "schemas/review-result.schema.json", "DEMO.md"]),
                task(5, "Show the tool trace", "tool-trace",
                     "On the result card, list the tools the AI used, in order, from tool_trace. Numbers still render only from the calculation fields.",
                     "pytest apps/web -q", "the trace shows on both screens.", text="Start when Dev 3 has added tool_trace to the schema."),
                task(5, "Connect to the harness", "connect",
                     "Switch the endpoints from recorded.json to harness.agent.run_review and mcp/actions. The approve endpoint is the only caller of issue_approval_token and approve_action. Render every number from the calculation fields.",
                     "pytest apps/web -q\nmake run", "the headline on screen equals G-07 exactly; Approve writes an audit line.",
                     text="Start when Dev 2 says the harness is ready."),
                task(5, "Add the demo numbers and fallback", "demo-assets",
                     "Fill the G-07 table in DEMO.md and add one screenshot per demo step to presentation/.",
                     "make check", "links valid; DEMO.md shows the exact numbers.", files=["DEMO.md", "presentation/README.md"]),
            ],
            spare="Rehearse twice with a timer, once with Wi-Fi off. Use the checklist in DEMO.md.",
            done=["The full story runs on the Lovable screen with no terminal and no code edits.", "The local fallback page works with Wi-Fi off.", "The tool trace is visible.", "The headline equals G-07 exactly.", "Proposal, approval and audit are clearly visible.", "The demo runs with <code>MODEL_PROFILE=offline</code> and Wi-Fi off."]),
}


def dev_page(n, d):
    tasks = list(d["tasks"])
    tasks.append(step("If you finish early", d["spare"]))
    body = f"""<header class="rolehead"><div class="big" aria-hidden="true">{n}</div><div>
<h1>{d['title']}</h1>
<p>Branches <code>dev{n}/&lt;task&gt;</code> · Reviewer: {REVIEWER[n]}<br>Your files: {", ".join(f(x) for x in d['own'])}</p></div></header>
{block("Your part", "Highlighted boxes are yours. Arrows show who calls whom.", '<div class="mini">' + arch(f"arch-{n}", focus=n) + "</div>", "part")}
{block("Set up", "Before the hackathon", setup(d['prompt'], d['extra']), "setup")}
{block("The loop", "Every task below runs it", LOOP + '<p class="loop-note">One task, one branch, one PR. Start the next task only after the merge.</p>', "loop")}
{block("Build", "In the session, in this order", route(*tasks), "tasks")}
{block("Done when", "Every item has evidence", done(d['done']), "done")}
"""
    return page(f"developer-{n}.html", f"Dev {n} — {html.unescape(d['title'])}", body, COL[n])


# ───────────────────────── lead page ─────────────────────────

def lead_page():
    body = f"""<header class="rolehead lead"><div class="big" aria-hidden="true">L</div><div>
<h1>Lead</h1>
<p>You own: {", ".join(f(x) for x in ["intent.md", "SPEC.md", "ARCHITECTURE.md", "PLAN.md", "TEAM.md"])}</p></div></header>
{block("The whole picture", "The number on each box is its developer. Point at a name to see their part.", arch("arch-lead") + legend("arch-lead"), "part")}
{block("Before the hackathon", "Everything that is not building", route(
        step("Check the repo", "It exists with <code>main</code> and <code>dev</code>. The team site is on GitHub Pages.", cmd="gh repo view TarasNS/energy-agent --web"),
        step("Read how the harness works", files=[("docs/harness.html", "How the harness works"), "TASKS.md"]),
        step("Add names and open a team chat", files=["TEAM.md"]),
        step("Get an Anthropic API key for the team", "Share it privately. Each developer puts it in their own <code>.env</code>; it is never committed."),
        step("Confirm the five decisions (30 minutes)", "With Dev 2, Dev 3 and Dev 4. Each already has a proposed answer. Freeze the schemas.", files=[("intent.md", "intent.md (decisions)"), "schemas/", ("ARCHITECTURE.md", "ARCHITECTURE.md (§9)")]),
        step("Check the numbers with an energy colleague (15 minutes)", "Formula v1 and the demo data. Is the split by cause right? Is the data realistic?", files=[("EVALS.md", "EVALS.md (§2)"), "data/synthetic/README.md"]),
        step("Get the judging criteria", "Map each criterion to a moment in the demo story.", files=["DEMO.md"]),
        step("Prepare Lovable with Dev 5", "Accept the invite, upload only synthetic data, paste the challenge brief.", files=["presentation/lovable-brief.md"]),
        step("Send each person their page", "Link: <code>docs/developer-N.html</code>. Everyone clones and runs <code>make setup</code> before the hackathon. Dev 4 works out the golden cases."),
    ), "before")}
{block("The loop", "How every task reaches dev", LOOP, "loop")}
{block("During the build", None, route(
        step("Check dev is green after each merge", "Dev 3 posts the <code>make verify</code> summary. If it is red, fixing it comes first."),
        step("Say no to new scope", "If it is not on someone's page, it is after the POC (PLAN.md §6)."),
        step("Never add a tool to the registry without a decision", "Five tools. Approval is never one of them."),
    ), "during")}
{block("Before presenting", None, route(
        step("Confirm the end-to-end run", cmd="make demo-smoke\nmake run"),
        step("Rehearse twice, once with Wi-Fi off", files=[("DEMO.md", "DEMO.md (rehearsal checklist)")], cmd="MODEL_PROFILE=offline make run"),
        step("Merge dev into main and present", cmd="git checkout main && git merge dev && git push"),
    ), "present")}
"""
    return page("lead.html", "Lead", body, "var(--lead)")


# ───────────────────────── start page ─────────────────────────

def index_page():
    tiles = "".join([tile("lead.html", "L", "Lead", "Repo, decisions, rehearsal"),
                     tile("developer-1.html", 1, "Dev 1", "Price data & AI skill"),
                     tile("developer-2.html", 2, "Dev 2", "Harness, approval & audit"),
                     tile("developer-3.html", 3, "Dev 3", "Portfolio, model gateway & merges"),
                     tile("developer-4.html", 4, "Dev 4", "Calculator & golden tests"),
                     tile("developer-5.html", 5, "Dev 5", "Lovable screen & story")])
    body = f"""<section class="hero">
  <div class="hero-l">
    <div>
      <h1>Energy 4.0 Harness</h1>
      <p class="tag">Safe, auditable AI for renewable-energy companies</p>
    </div>
    <p class="hero-meta">First proof of concept, built live at the AI in Energy Hackathon<span>Monthly Curtailment Review · DK1</span></p>
  </div>
  <div class="hero-r"><div class="tiles">{tiles}</div></div>
</section>

<section class="sec" id="poc">
  <h2 class="reveal">A first proof of concept</h2>
  <p class="intro reveal">One workflow on synthetic data, run by one small agent loop, built in one short session. It proves the number is trustworthy, the model is swappable, and actions need a human. <a href="harness.html">How the harness works</a>.</p>
  <div class="scope reveal">
    <div class="card"><span class="k">In the POC</span><ul>
      <li>Agent loop with five fixed tools</li><li>DK1 demo data, 15-minute prices</li><li>EUR by cause, from code</li><li>Claude explanation, swappable model</li>
      <li>Proposal, human approval, audit line</li><li>Lovable screen, offline fallback page</li></ul></div>
    <div class="card muted"><span class="k">After the POC</span><ul>
      <li>Eval suite and CI gating</li><li>Claude Code hooks</li><li>Live market data</li>
      <li>Company data adapters</li></ul></div>
  </div>
</section>

<section class="sec alt" id="architecture">
  <h2 class="reveal">How it fits together</h2>
  <p class="intro reveal">One request flows down. The agent loop lets the model pick the tools below it. The number on each box is the developer who builds it. Point at a name to see their part.</p>
  <div class="reveal">{arch("arch-main")}{legend("arch-main")}</div>
</section>

<section class="sec" id="loop">
  <h2 class="reveal">How every task flows</h2>
  <p class="intro reveal">One small task, one branch, one pull request. Nothing reaches dev without a green test, a green check and a second pair of eyes.</p>
  <div class="reveal">{LOOP}</div>
</section>

<section class="sec alt" id="rules">
  <h2 class="reveal">Four rules</h2>
  <div class="cards">
    <div class="card reveal"><span class="k">Numbers</span><b>Come from code, never the AI</b><span class="n">01</span></div>
    <div class="card reveal"><span class="k">Data</span><b>Read-only and works offline</b><span class="n">02</span></div>
    <div class="card reveal"><span class="k">Actions</span><b>Need a human; the AI has no approval tool</b><span class="n">03</span></div>
    <div class="card reveal"><span class="k">Everything</span><b>Every tool call lands in the audit log</b><span class="n">04</span></div>
  </div>
</section>
"""
    return page("index.html", "Start", body)


# ───────────────────────── harness explainer ─────────────────────────

def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def harness_page():
    body = f"""<header class="rolehead lead"><div class="big" aria-hidden="true">H</div><div>
<h1>How the harness works</h1>
<p>Read this once before the hackathon. It takes five minutes.</p></div></header>
{block("In one sentence", None, '<p class="oneliner">The AI decides which tool to use next. Code decides what the AI is allowed to do, and what the number is.</p>', "sentence")}
{block("One review, step by step", "What happens after someone clicks Run review", route(
        step("The screen sends the request", "Portfolio, zone, month, threshold. From the Lovable screen, or the local fallback page."),
        step("The harness starts the agent loop", "It sends the model three things: the <code>curtailment-advisor</code> skill, the request, and the list of five tools.", files=["harness/README.md"]),
        step("The model asks for a tool", "For example <code>list_assets</code>. The harness runs the real Python function, writes an audit line, and sends the result back."),
        step("This repeats", "The model asks for the next tool: production, prices, then the calculator. At most 10 rounds (<code>STEP_BUDGET</code>)."),
        step("The calculator makes the number", "<code>calculate_curtailment_value</code> returns the EUR by cause. The harness keeps that output. A review that never calls it fails."),
        step("The model explains", "It writes the explanation and the recommendation, and may call <code>propose_action</code>. Then it stops."),
        step("The harness builds the result", "The numbers are copied from the calculator output, never from the model's text. The result also lists the tools used, in order."),
        step("A person approves", "On the screen: name, then <b>Approve</b>. This is outside the loop; the model has no approval tool."),
        step("Everything is in the audit log", "Each tool call, the proposal and the approval are one line in <code>artifacts/audit.jsonl</code>."),
    ), "flow")}
{block("What the model can and cannot do", "Enforced in code, not in the prompt", '<div class="two">'
        '<div class="box"><h3>Can</h3><ul><li>Choose which of the five tools to call, and in what order</li><li>Read portfolio, production and price data</li><li>Ask the calculator for the EUR result</li><li>Explain the result and recommend a step</li><li>Propose an action</li></ul></div>'
        '<div class="box no"><h3>Cannot</h3><ul><li>Make up or change a number: the screen shows calculator output only</li><li>Skip the calculator: the review fails</li><li>Approve or execute an action: there is no tool for it</li><li>Write data, run shell commands or browse the web</li><li>Run forever: it stops after 10 rounds</li></ul></div>'
        "</div>", "can")}
{block("The five tools", "The only things the model can call", tbl(["Tool", "What it does", "Built by"], [
        ["<code>list_assets</code>", "The parks in the portfolio", "Dev 3"],
        ["<code>get_production</code>", "15-minute production and curtailment", "Dev 3"],
        ["<code>get_day_ahead_prices</code>", "15-minute DK1 prices from the fixture", "Dev 1"],
        ["<code>calculate_curtailment_value</code>", "EUR by cause and by asset. Mandatory", "Dev 4"],
        ["<code>propose_action</code>", "Creates a proposal. Does not execute it", "Dev 2"],
    ]), "tools")}
{block("What we take from our POC", '<a href="https://github.com/TarasNS/energy-agent/tree/claude/awesome-planck-bt3ymf/harness/poc">The working POC harness</a>, branch claude/awesome-planck-bt3ymf', tbl(["POC file", "Ours", "What changes"], [
        ["<code>agent.py</code>", "<code>harness/agent.py</code>", "Same loop and forced final answer; model via the gateway; must call the calculator; returns a review result"],
        ["<code>tools.py</code>", "<code>harness/tools/registry.py</code>", "Same validation and error handling; exactly five tools; no <code>calculate</code>"],
        ["<code>trace.py</code>", "<code>harness/trace.py</code>", "Same JSONL events; tool calls also go to the audit log"],
        ["<code>tests/conftest.py</code>", "<code>harness/tests/conftest.py</code>", "Same fake model for tests"],
        ["<code>llm.py</code> (OpenRouter)", "Not copied", "Replaced by <code>model_gateway</code>: Anthropic, swappable, offline replay"],
        ["Budget, probe, live APIs, PV estimate, simulator, chat UI", "Not copied", "Not needed for one review on synthetic data"],
    ]), "poc")}
{block("What we add to the POC", "The POC answers questions. It never proposes or approves, and the model may do arithmetic.", done([
        "A deterministic EUR calculator, in Decimal, split by cause (Dev 4).",
        "No arithmetic by the model: the POC calculate tool is removed (Dev 2).",
        "The review fails without a calculator call; numbers come from its output (Dev 2).",
        "Proposal, one-time approval token, simulated execution; approval is never a tool (Dev 2).",
        "An append-only audit log of tool calls, proposals and approvals (Dev 2).",
        "Offline demo by replaying recorded model turns (Dev 3).",
    ]), "add")}
{block("What fails, on purpose", "Each one has a test", done([
        "The model calls a tool that is not registered: error result, nothing runs.",
        "The model never calls the calculator: the review fails with a clear message.",
        "10 rounds pass without an answer: the review stops with a clear message.",
        "Approve with a missing, wrong or reused token: refused, nothing executed, audit line written.",
        "No internet: <code>MODEL_PROFILE=offline</code> replays recorded model turns through the same loop.",
    ]), "fails")}
{block("Who builds what", "Full list with dependencies in TASKS.md", tbl(["Person", "Builds", "Page"], [
        ["Dev 1", "Price tool, skill and system prompt", '<a href="developer-1.html">developer-1</a>'],
        ["Dev 2", "Tool registry, agent loop, approval and audit, smoke test", '<a href="developer-2.html">developer-2</a>'],
        ["Dev 3", "Portfolio tools, model gateway, offline replay, schemas, merges", '<a href="developer-3.html">developer-3</a>'],
        ["Dev 4", "Calculator, golden tests, no-invented-EUR check", '<a href="developer-4.html">developer-4</a>'],
        ["Dev 5", "Lovable screen, local API and fallback page, demo", '<a href="developer-5.html">developer-5</a>'],
    ]) + '<p class="files">Files: ' + ", ".join(f(x) for x in ["TASKS.md", "SPEC.md", "ARCHITECTURE.md"]) + "</p>", "who")}
{block("Words we use", None, tbl(["Word", "Means"], [
        ["Agent loop", "Ask the model, run the tools it asks for, send results back, repeat"],
        ["Tool registry", "The fixed list of five functions the model may call"],
        ["Step budget", "The most rounds one review may take (10)"],
        ["Calc of record", "The calculator output. The only source of a EUR number"],
        ["Proposal", "A suggested action, waiting for a person"],
        ["Approval token", "A one-time key the Approve button creates. The model never sees it"],
        ["Audit log", "One JSON line per tool call, proposal and approval"],
        ["Offline profile", "Replays recorded model turns, so the demo works without internet"],
    ]), "words")}
"""
    return page("harness.html", "How the harness works", body, "var(--lead)")


def main():
    (D / "index.html").write_text(index_page(), encoding="utf-8")
    (D / "harness.html").write_text(harness_page(), encoding="utf-8")
    (D / "lead.html").write_text(lead_page(), encoding="utf-8")
    for n, d in DEVS.items():
        (D / f"developer-{n}.html").write_text(dev_page(n, d), encoding="utf-8")
    print("docs/ rebuilt: index, harness, lead, developer-1..5")


if __name__ == "__main__":
    main()
