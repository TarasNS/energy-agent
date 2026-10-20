#!/usr/bin/env python3
"""Builds the docs/ portal (owner: Dev 3). Run: make docs

Edit this file, not the generated HTML. Standard library only.
Writing rules: .claude/brand-voice-guidelines.md (one action per step, link every file).
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from slides import SLIDES  # noqa: E402
from docmd import REFERENCE, md_to_html  # noqa: E402
D = ROOT / "docs"
REPO = "https://github.com/TarasNS/energy-agent.git"
e = html.escape
C = lambda s: f"<code>{e(s)}</code>"

# ───────────────────────── small building blocks ─────────────────────────

def f(path, label=None, base=""):
    """Link to a document page in docs/reference/, or to a repo file that exists; otherwise plain code."""
    if path in REFERENCE:
        return f'<a href="{base}reference/{REFERENCE[path]}.html">{e(label or path)}</a>'
    if (ROOT / path).exists():
        return f'<a href="{base}../{path}">{e(label or path)}</a>'
    return C(label or path)


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

COL = {1: "var(--d1)", 2: "var(--d2)", 3: "var(--d3)", 4: "var(--d4)", "L": "var(--lead)"}
SUN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="none" stroke="#1a5c00" stroke-width="1.8"/>'
       '<g stroke="#1a5c00" stroke-width="1.6" stroke-linecap="round"><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1"/></g></svg>')
NAV = [("index.html", "Guide", "L"), ("lead.html", "Lead", "L"), ("developer-1.html", "Dev 1 · Skill & chat page", 1),
       ("developer-2.html", "Dev 2 · Harness & approval", 2), ("developer-3.html", "Dev 3 · Model & contracts", 3),
       ("developer-4.html", "Dev 4 · Calculator & evals", 4),
       ("presentation.html", "Presentation", "L")]
def foot(base=""):
    docs = ["INTENT.md", "SPEC.md", "ARCHITECTURE.md", "TEAM.md", "EVALS.md", "DEMO.md", "KPI_REVIEW.md", "CLAUDE.md"]
    return ('<footer class="dark"><h2>The documents, readable here</h2><ul class="refs">'
            + "".join(f"<li>{f(x, base=base)}</li>" for x in docs)
            + f'</ul><div class="fine"><span>Energy 4.0 Harness · first proof of concept</span>'
              f'<span>Writing rules: {f(".claude/brand-voice-guidelines.md", base=base)}</span></div></footer>')


def page(slug, title, body, accent="var(--d1)", base=""):
    nav = "".join(f'<a href="{base}{h}"{" aria-current=\"page\"" if h == slug else ""}><i style="background:{COL[c]}"></i>{e(t)}</a>' for h, t, c in NAV)
    cls = "role" if base else "home" if slug == "index.html" else ("role deck" if slug == "presentation.html" else "role")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} — Energy 4.0 Harness</title>
<link rel="stylesheet" href="{base}css/tokens.css">
<link rel="stylesheet" href="{base}css/style.css">
</head>
<body class="{cls}" style="--accent:{accent}">
<header class="top">
  <a class="mark" href="{base}index.html">{SUN}energy 4.0 harness</a>
  <details class="menu"><summary aria-label="Menu"><span></span></summary><nav aria-label="Pages">{nav}</nav></details>
</header>
<main class="page">
{body}
</main>
{foot(base)}
<script src="{base}js/app.js"></script>
</body>
</html>
"""


# ───────────────────────── diagrams ─────────────────────────

_PI = [0]


def part(d, x, y, w, h, t, s):
    _PI[0] += 1
    return (f'<g class="part d{d}" style="--i:{_PI[0]}"><rect class="fill{d}" x="{x}" y="{y}" width="{w}" height="{h}" rx="10"/>'
            f'<text class="t" x="{x + w / 2}" y="{y + h / 2 - 3}" text-anchor="middle">{e(t)}</text>'
            f'<text class="s" x="{x + w / 2}" y="{y + h / 2 + 16}" text-anchor="middle">{e(s)}</text>'
            f'<circle class="badge" cx="{x + 4}" cy="{y + 4}" r="11"/><text class="bn" x="{x + 4}" y="{y + 8}" text-anchor="middle">{d}</text></g>')


PULSES = [("M480 84V118", 0), ("M480 184V300", .5), ("M115 300V328", 1), ("M355 300V328", 1), ("M595 300V328", 1), ("M840 300V328", 1),
          ("M370 152H215V218", .5), ("M590 152H745V218", .5)]


def arch(id_, focus=None):
    _PI[0] = 0
    fa = f' data-focus="{focus}"' if focus else ""
    g = [f'<div class="arch" id="{id_}"{fa}><svg viewBox="-10 -10 975 655" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{id_}-t">',
         f'<title id="{id_}-t">Energy 4.0 Harness architecture; the number on each box is the developer who owns it</title>',
         '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1c1c1c"/></marker></defs>',
         '<path class="wire" d="M480 84V118"/>', '<path class="wire" d="M370 152H215V218"/>', '<path class="wire" d="M590 152H745V218"/>',
         '<path class="wire plain" d="M480 184V300"/>', '<path class="wire plain" d="M115 300H840"/>',
         '<path class="wire" d="M115 300V328"/>', '<path class="wire" d="M355 300V328"/>', '<path class="wire" d="M595 300V328"/>', '<path class="wire" d="M840 300V328"/>',
         '<path class="wire" d="M115 396V436"/>', '<path class="wire" d="M355 396V436"/>', '<path class="wire" d="M595 396V436"/>', '<path class="wire" d="M840 396V436"/>',
         part(1, 370, 20, 220, 64, "Chat page", "tools/kpi-lab · charts, approve"),
         part(2, 370, 120, 220, 64, "Agent loop + server", "number check · harness/"),
         part(1, 100, 220, 230, 64, "KPI advisor skill", "the model's instructions"),
         part(3, 630, 220, 230, 64, "Model gateway", "Claude Haiku 5.5 · swappable"),
         part(2, 10, 330, 210, 66, "Server", "/api/chat · /api/approve"),
         part(2, 250, 330, 210, 66, "Energy tools", "nine tools · harness/"),
         part(4, 490, 330, 210, 66, "KPI calculator", "mcp/kpi-solar · every number"),
         part(2, 730, 330, 220, 66, "Actions", "propose → approve"),
         part(4, 10, 438, 210, 62, "Day-ahead prices", "daily · synthetic"),
         part(4, 250, 438, 210, 62, "Synthetic portfolio", "2 parks + 1 battery"),
         part(4, 490, 438, 210, 62, "Golden cases", "hand-worked values"),
         part(2, 730, 438, 220, 62, "Audit log", "proposals, approvals, tool calls"),
         '<text class="band" x="10" y="540">Across everything</text>',
         part(3, 10, 552, 225, 62, "Contracts & checks", "schemas · make check"),
         part(3, 245, 552, 225, 62, "Offline replay", "model/recorded"),
         part(2, 480, 552, 225, 62, "Smoke test", "make demo-smoke"),
         part(2, 715, 552, 235, 62, "Demo story", "DEMO.md · screenshots"),
         *[f'<circle class="pulse" r="3"><animateMotion dur="2.4s" begin="{b}s" repeatCount="indefinite" path="{d}"/></circle>' for d, b in PULSES],
         "</svg></div>"]
    return "".join(g)


def legend(target):
    names = {1: "Dev 1 · Skill & chat page", 2: "Dev 2 · Harness & approval", 3: "Dev 3 · Model & contracts", 4: "Dev 4 · Calculator & evals"}
    return (f'<ul class="legend" data-legend="{target}">'
            + "".join(f'<li><button type="button" data-d="{d}" aria-pressed="false"><i>{d}</i>{n}</button></li>' for d, n in names.items())
            + "</ul>")


def loop_svg():
    labels = [("Brief", "one prompt"), ("Build", "Claude, test first"), ("Test", "must be green"), ("Verify", "verifier subagent"),
              ("Pull request", "into main"), ("Merge", "lead merges")]
    gate = {2}
    w, gap, y, h = 135, 22, 70, 58
    xs = [10 + i * (w + gap) for i in range(len(labels))]
    out = ['<div class="loopdiagram"><svg viewBox="0 0 960 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="lt">'
           '<title id="lt">The task loop: brief, build, test, verify, pull request, merge, then the next task</title>'
           '<defs><marker id="la" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#1c1c1c"/></marker></defs>']
    for i, (t, s) in enumerate(labels):
        x = xs[i]
        out.append(f'<g class="{"n g" if i in gate else "n"}" style="--i:{i + 1}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="29"/>'
                   f'<text x="{x + w / 2}" y="{y + 25}" text-anchor="middle">{t}</text><text class="s" x="{x + w / 2}" y="{y + 42}" text-anchor="middle">{s}</text></g>')
        if i:
            out.append(f'<path class="w" d="M{xs[i - 1] + w + 1} {y + h / 2}H{x - 2}"/>')
    tx, bx = xs[2] + w / 2, xs[1] + w / 2
    out.append(f'<path class="w back" d="M{tx} {y + h + 2}V{y + h + 40}H{bx}V{y + h + 4}"/>')
    out.append(f'<text class="lab" x="{tx + 14}" y="{y + h + 44}" text-anchor="start">red: fix the code, run the test again</text>')
    mx, brx = xs[5] + w / 2, xs[0] + w / 2
    out.append(f'<path class="w back" d="M{mx} {y - 2}V{y - 34}H{brx}V{y - 4}"/>')
    out.append(f'<text class="lab" x="{(mx + brx) / 2}" y="{y - 42}" text-anchor="middle">merged: start the next task on a new branch</text>')
    out.append("</svg></div>")
    return "".join(out)


def _defs(mid):
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="9" markerHeight="9" orient="auto-start-reverse">'
            '<path d="M0 0L10 5L0 10z" fill="#1c1c1c"/></marker></defs>')


def _node(i, x, y, w, h, t, sub, fill="var(--green)"):
    return (f'<g class="n" style="--i:{i}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" style="fill:{fill}"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 - 2}" text-anchor="middle">{t}</text>'
            f'<text class="s" x="{x + w / 2}" y="{y + h / 2 + 15}" text-anchor="middle">{sub}</text></g>')


def merge_svg():
    """Four branches fan in to a pull request, then main, then Azure."""
    out = ['<div class="loopdiagram"><svg viewBox="0 0 960 270" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="mt">'
           '<title id="mt">Four developers push branches, open pull requests into main, the lead merges, and main is deployed to Azure</title>', _defs("la")]
    cols = ["var(--d1)", "var(--d2)", "var(--d3)", "var(--d4)"]
    for i in range(4):
        y = 10 + i * 64
        out.append(_node(i + 1, 10, y, 190, 50, f"Dev {i + 1}", f"branch dev{i + 1}/&lt;task&gt;", cols[i]))
        out.append(f'<path class="w plain" d="M200 {y + 25}H260V131"/>')
    out.append('<path class="w" d="M260 131H320"/>')
    out.append(_node(5, 320, 91, 200, 80, "Pull request", "one per task, into main"))
    out.append('<path class="w" d="M520 131H590"/>')
    out.append(_node(6, 590, 91, 150, 80, "main", "the only shared branch", "var(--ink)"))
    out.append('<path class="w" d="M740 131H810"/>')
    out.append(_node(7, 810, 91, 140, 80, "Azure", "container, /health", "var(--lead)"))
    out.append('<text class="lab" x="420" y="193" text-anchor="middle">The lead merges</text>')
    out.append('<text class="lab" x="775" y="193" text-anchor="middle">The lead deploys</text>')
    out.append("</svg></div>")
    return "".join(out)


def deploy_svg():
    items = [("main", "the lead pulls it", "var(--ink)"), ("Build image", "Azure Container Registry", "var(--green)"),
             ("App Service", "pulls the image", "var(--green)"), ("Chat page + API", "GET /health is 200", "var(--lead)")]
    out = ['<div class="loopdiagram"><svg viewBox="0 0 960 130" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="dt">'
           '<title id="dt">Deploy: main, build the image in Azure, App Service pulls it, the chat answers on /health</title>', _defs("la")]
    w, gap = 200, 53
    for i, (t, sub, fill) in enumerate(items):
        x = 10 + i * (w + gap)
        out.append(_node(i + 1, x, 25, w, 80, t, sub, fill))
        if i:
            out.append(f'<path class="w" d="M{x - gap} 65H{x}"/>')
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



REPO_NAME = "TarasNS/energy-agent"


def row(label, body, cls="", sub=None):
    s = f"<small>{sub}</small>" if sub else ""
    c = f' class="{cls}"' if cls else ""
    return f'<li{c}><div class="lbl">{label}{s}</div><div class="body">{body}</div></li>'


def brief(n, slug, own, job):
    """The one prompt that starts a task. Same rules every time, so nobody has to remember them."""
    return (
        "Read INTENT.md and CLAUDE.md first. Then do this task:\n"
        f"{job}\n\n"
        "Rules for this task:\n"
        f"- Work on a new branch called dev{n}/{slug}, created from main.\n"
        f"- Edit only these paths: {own}.\n"
        "- Before you change anything, show me your plan (goal, files, the test, done-when) and wait for my \"go\".\n"
        "- Write the test first. Run it. If it fails, fix the code, never the test, and run it again until it passes. Show me the output."
    )


def finish(n, slug):
    return (
        f"Use the verifier subagent to check this task against docs/developer-{n}.html and report what it finds. "
        "Fix every P0 and P1 it reports. Then run make check and make test and show me the output.\n"
        f"If both are green, commit on branch dev{n}/{slug}, push it and open a pull request into main using "
        f".github/PULL_REQUEST_TEMPLATE.md."
    )


def task(n, title, slug, own, job, see, why="", files=()):
    head = f'<li><span class="t">{title}</span>' + (f"<p>{why}</p>" if why else "")
    if files:
        head += '<p class="files">Files: ' + ", ".join(f(x) if isinstance(x, str) else f(*x) for x in files) + "</p>"
    rows = [
        row("Brief Claude", '<p class="say">Paste into Claude Code</p>' + code(brief(n, slug, own, job)), "", "then reply go"),
        row("Check", f'<p class="see">You should see: {see}</p>', "gate", "must be green"),
        row("Finish", '<p class="say">Paste into Claude Code</p>' + code(finish(n, slug)), "", "verify, test, PR"),
    ]
    return head + '<ol class="loopsteps">' + "".join(rows) + "</ol></li>"


def setup(extra=()):
    return route(
        step("Open the project in Claude Code", "In the Claude desktop app, choose the Code tab and open the folder <code>energy-agent</code>. No folder yet? Ask Claude to clone it in the next step. The repository holds documents and checks only: that is expected."),
        step("Let Claude set it up", "Claude installs the tools and runs the checks. You read the answer.",
             claude=f"Set up this project on my computer. If the code is not here, clone https://github.com/{REPO_NAME}.git. Switch to the main branch, run make setup and make check, and explain any failure in plain words. If make is not installed (common on Windows), run python scripts/dev.py setup and python scripts/dev.py check instead, and from now on read every make X in this project as python scripts/dev.py X. Do not ask me to type my API key in this chat.",
             see="<code>make check passed.</code>"),
        step("Add the key", "Ask the lead for the Anthropic key. Copy <code>.env.example</code> to <code>.env</code>, paste the key after <code>ANTHROPIC_API_KEY=</code> and save. Never commit it.", files=[".env.example"]),
        step("Read the idea and the contract (10 minutes)", "These two files. Claude reads the rest for you. There is no harness code to copy: the team builds it together from the contract.", files=["INTENT.md", "SPEC.md"]),
        *extra,
    )


# ───────────────────────── developer content ─────────────────────────

DEVS = {
    1: dict(title="Skill &amp; Chat Page", own=[".claude/skills/", "tools/kpi-lab/index.html", "tools/kpi-lab/charts.js", "tools/kpi-lab/config.js"],
            what="You write the instructions the model reads and build the chat page a manager uses. You start with the skill, then the page against the server contract in SPEC.md.",
            tasks=[
                task(1, "Write the skill the model reads", "skill", ".claude/skills/ only",
                     "Write .claude/skills/kpi-advisor/SKILL.md, at most 150 lines, from SPEC.md section 10 and the nine tools in section 5. It tells the model: the data is synthetic and every answer must say so; which of the nine tools to use for which kind of question; never calculate, add, average, round or estimate a number; when a tool says a value is unavailable, say so and give the reason; call make_chart at most once; propose an action only when the data clearly justifies it, and never say it is approved; answer in at most 120 words. Put a test next to it (.claude/skills/kpi-advisor/test_skill.py) that fails if any of the nine tool names is missing or the never-calculate rule is gone.",
                     "the test passes, and the skill names all nine tools.",
                     why="No code is needed from anyone else. Dev 2 loads the skill as the system prompt.",
                     files=["SPEC.md", ".claude/skills/README.md"]),
                task(1, "Draw the charts", "charts", "tools/kpi-lab/charts.js and tools/kpi-lab/charts.test.js only",
                     "Write tools/kpi-lab/charts.js with one function renderChart(chart) that returns an SVG or HTML string for the kinds line, bar, area and table. A chart is {id, kind, title, series: [{name, points: [{x, y}]}]} where every y is a decimal string. The code only draws: it never adds, averages or rounds, and it prints each y exactly as given. Use the Nordic Solar colours from .claude/brand-voice-guidelines.md only if it names them, otherwise plain dark and green. Write tools/kpi-lab/charts.test.js, run with node, covering each kind, an empty series and a negative value.",
                     "the node test passes for every chart kind.",
                     why="Independent of the server. The page in the next task calls this function.",
                     files=["SPEC.md"]),
                task(1, "Every state of the chat page", "chat-page", "tools/kpi-lab/index.html and tools/kpi-lab/config.js only",
                     "Build tools/kpi-lab/index.html: one page, no libraries, that posts {question} to /api/chat and renders {text, verified, note, charts, proposals, trace, stopped} as in SPEC.md sections 8 and 9. It must handle loading, a verified answer, a withheld answer (show the note, the charts and the tool results), daily cap reached (429), server not reachable, a proposal waiting, approved, and approval refused. Ask for the approver's name before Approve is sent, then post {proposal_id, approver} to /api/approve. Show SYNTHETIC DATA on screen. The page only renders what the server returns and never calculates. Until Dev 2's server is merged, test against a small stub that returns each state. Check it in the browser at phone width and desktop and show me screenshots.",
                     "all states are visible in the browser at both widths.",
                     why="Needs the chart function from the previous task and the contract in SPEC.md. Dev 2's server arrives later; use a stub.",
                     files=["SPEC.md", "tools/kpi-lab/charts.js"]),
            ],
            done=["The skill names all nine tools, forbids model arithmetic and says the data is synthetic; its test is green.", "Charts draw all four kinds exactly as given; the node test is green.", "Every state of the chat page is clear and checked at phone width.", "The page works against Dev 2's real server once it is merged.", "All tasks merged through green pull requests."]),
    2: dict(title="Harness &amp; Approval", own=["harness/", "mcp/actions/", "tools/kpi-lab/server.py", "scripts/demo-smoke.sh", ".claude/agents/"],
            what="You build the nine tools, the agent loop with the number check, the approval step, the audit log and the server. It is the middle of the harness: Dev 4 gives you data and formulas, Dev 3 the model.",
            tasks=[
                task(2, "The registry and the nine tools", "tools", "harness/ only",
                     "Build harness/registry.py (a ToolRegistry that runs a tool by name and never raises: a bad call becomes {\"error\": ...}) and harness/energy_tools.py with the nine tools in SPEC.md section 5, over the portfolio from data/synthetic/portfolio.py and the KPI functions in mcp/kpi-solar. Every tool returns a JSON string and every money or energy value is a decimal string. Tool descriptions say when to use the tool. Write tests first: each tool on a tiny hand-made portfolio, an unknown kpi, an unknown asset, a date outside June 2026, and a test that no tool called approve exists. Until Dev 4's portfolio and formulas are merged, use a small stand-in with the same shape as in SPEC.md section 2 and section 3.",
                     "the tool tests pass and the registry has exactly nine tools.",
                     why="Needs Dev 4's portfolio and formulas for the real numbers; the shapes are fixed in SPEC.md so you can start now.",
                     files=["SPEC.md", "ARCHITECTURE.md"]),
                task(2, "The agent loop and the number check", "agent-loop", "harness/ only",
                     "Build harness/agent.py: run(question) -> AgentResult(text, verified, note, charts, proposals, trace, stopped) as in SPEC.md section 6. It calls the model only through model.model_gateway.run_turn, runs the tools through the registry, stops after 8 rounds, and calls check_numbers(reply, tool_results, question) before returning text. Withhold the text when any number is unknown. The system prompt is .claude/skills/kpi-advisor/SKILL.md when it exists, otherwise a short built-in fallback. Write the tests first with a scripted model (a function that returns ModelTurns): a correct answer passes, a made-up number is withheld with charts still returned, 12.5 equals 12.50, a year or a count does not raise a false alarm, 9 rounds stop with max_steps. Until Dev 3's gateway is merged, define ModelTurn and ToolCall in a stand-in with the same names.",
                     "the loop tests pass with a scripted model and no network.",
                     why="This is the check that keeps a wrong number off the screen. Dev 4 writes extra tests for it later.",
                     files=["SPEC.md"]),
                task(2, "Propose, approve once, audit", "actions", "mcp/actions/ and the audit part of harness/ only",
                     "Build mcp/actions with propose_action, issue_approval_token and approve_action as in SPEC.md section 7, and write every proposal, approval, refusal and tool call as one JSON line in artifacts/audit.jsonl (path from AUDIT_LOG_PATH). Tokens are one-time, live in memory and never appear in any line. Tests first: approving twice is refused and audited, a wrong token is refused and audited, a token never appears in the file, a scripted run with two tool calls writes two tool_call lines, and the registry holds neither approve_action nor issue_approval_token. Make the agent loop write the tool_call lines.",
                     "the new tests pass and the audit file shows one line per event.",
                     why="Approval is enforced in code, never only in a prompt.",
                     files=["SPEC.md", "INTENT.md"]),
                task(2, "The server and the smoke test", "server-smoke", "tools/kpi-lab/server.py, scripts/demo-smoke.sh",
                     "Build tools/kpi-lab/server.py as in SPEC.md section 8: GET /, POST /api/chat, POST /api/approve, GET /health, a daily cap (KPI_DAILY_CAP, 200, stored in KPI_CAP_FILE), allowed origins and the 429 answer. /api/approve issues the one-time token itself and the browser never sees it. Add tools/kpi-lab/test_server.py. Then make scripts/demo-smoke.sh real: start the server with a scripted model that needs no network, ask the questions in the DEMO.md table (park losses, round-trip efficiency, incident resolution, negative prices), approve one proposal, and check the answer, the chart, the audit lines and the refusal of a second approval. make demo-smoke must pass offline.",
                     "<code>make demo-smoke</code> passes with Wi-Fi off.",
                     why="Needs the loop, the actions and, for the offline version, Dev 3's recorded replay or your own scripted model.",
                     files=["DEMO.md", "SPEC.md"]),
            ],
            done=["Nine tools, no approval tool, and a test says so.", "A made-up number is withheld; charts and tool results still show.", "Every tool call, proposal and approval is one line in the audit log. No token is in it.", "The server answers /api/chat, /api/approve and /health as in SPEC.md.", "<code>make demo-smoke</code> passes offline."]),
    3: dict(title="Model &amp; Contracts", own=["model/", "schemas/", "CLAUDE.md", "Makefile", "scripts/", ".github/", "docs/", "Dockerfile", ".dockerignore"],
            what="You go first: the shared contracts and the model gateway are what the other three build against. Then offline replay and the container.",
            tasks=[
                task(3, "The shared contracts", "contracts", "schemas/ (tests live in schemas/), scripts/verify.py, CLAUDE.md",
                     "Write the JSON schemas in schemas/ for what the parts exchange, from SPEC.md: chat-result.schema.json (text, verified, note, charts, proposals, trace, stopped), chart.schema.json, proposal.schema.json and audit-line.schema.json (events proposed, approved, refused, tool_call). Add schemas/test_schemas.py with one valid and one invalid example for each schema. Make sure make check validates every schema file. Update the Current state line in CLAUDE.md. Dev 4 and Dev 2 review it before the merge, and any later change needs the lead's approval. Merge this one first: everyone waits for it.",
                     "<code>make check</code> and <code>make test</code> are green, and each schema has a failing example.",
                     why="Do this in the first half hour. The other three developers read these files.",
                     files=["SPEC.md", "CLAUDE.md"]),
                task(3, "The model gateway", "gateway", "model/ only",
                     "Build model/model_gateway as in SPEC.md section 4: run_turn(system, messages, tools, max_tokens) returns ModelTurn(text, tool_calls) with ToolCall(id, name, input), and raises ModelUnavailable on a missing key or a failed call. Convert OpenAI-style tool schemas to the provider format. Use the standard library for HTTP so no provider SDK is imported anywhere. Write model/profiles.json with default, fast and offline profiles (Claude Haiku 5.5 for the first two) and read MODEL_PROFILE. Tests first, with no network: tool schema conversion, a text reply, a tool-call reply, a missing key, and a test that no file outside model/model_gateway imports a provider SDK. Update model/README.md to match. Ask me before any live call.",
                     "the gateway tests pass with Wi-Fi off.",
                     why="Dev 2's loop calls this. Publish the names ModelTurn, ToolCall, ModelUnavailable and run_turn early.",
                     files=["SPEC.md", "model/README.md"]),
                task(3, "Offline model replay", "offline-replay", "model/ only",
                     "Add the offline profile. A recorded client replays recorded turns from model/recorded/*.json in order, and run_turn uses it when MODEL_PROFILE=offline. Record the questions in the DEMO.md table once with the real model once Dev 2's loop is merged, but ask me before any live call, and store them as JSON. Add a test that runs the agent loop (harness/agent.py) on a recording with no network and gets the same tool trace and answer twice.",
                     "the test passes with Wi-Fi off, and the answers match the recordings.",
                     why="Without it the demo needs internet. Needs Dev 2's agent loop for the recording.",
                     files=["DEMO.md", "model/README.md"]),
                task(3, "The container files", "container", "Dockerfile, .dockerignore, scripts/test_container.py",
                     "Write a Dockerfile (python:3.11-slim, runtime code only, listens on KPI_LAB_HOST and KPI_LAB_PORT) and an allowlist .dockerignore so .env, tests and docs never enter the image, as described in ARCHITECTURE.md section 7. Add scripts/test_container.py: every path the Dockerfile copies exists. If the settings in ARCHITECTURE.md section 7 need to change, tell the lead. Do not run any Azure command and do not build an image.",
                     "the test passes, and <code>make check</code> is green.",
                     why="The chat is deployed as a container on Azure. Do this last, once the server exists.",
                     files=["ARCHITECTURE.md"]),
            ],
            done=["Schemas match the real chat answer and audit line, with a failing example each.", "Only <code>model/model_gateway/</code> imports a model SDK, and <code>make check</code> proves it.", "<code>MODEL_PROFILE=offline</code> gives the same answers with no network.", "The container files are on <code>main</code> and every path they copy exists.", "<code>make check</code> and <code>make test</code> are green on main."]),
    4: dict(title="Calculator &amp; Evals", own=["mcp/kpi-solar/", "evals/", "tests/", "data/synthetic/", "EVALS.md", "KPI_REVIEW.md"],
            what="You build the data and the numbers, and prove they are right. Everyone else's answers depend on your work, so start with the data and the formulas.",
            tasks=[
                task(4, "The synthetic portfolio", "portfolio", "data/synthetic/ only",
                     "Build data/synthetic/portfolio.py with build(seed=20260601) as in SPEC.md section 2: two parks and a battery, 30 days of June 2026, day-ahead prices, a PPA share of 50 percent, the exact dict shape from the spec, label SYNTHETIC. The same seed must give identical output on every run and no network is used. Write the test first: shape, 30 days, same seed same data, a different seed different data, values inside the ranges in the spec, outage days on the right parks. Add data/synthetic/README.md saying everything is synthetic.",
                     "the tests pass, and two runs print identical data.",
                     why="Dev 2's tools and your golden cases both read this. Merge it early.",
                     files=["SPEC.md"]),
                task(4, "The 13 KPI formulas", "kpi-formulas", "mcp/kpi-solar/ only",
                     "Build mcp/kpi-solar/kpi_solar/metrics.py with the 13 functions in SPEC.md section 3: strings or Decimals in, Decimal or Unavailable(reason) out, never a float, never a division by zero, round half up. incident_resolution_hours is always Unavailable because no tickets are loaded. Do not create mcp/__init__.py. Write the tests first with hand-worked values, at least two per formula (a normal case and a missing or zero input).",
                     "all formula tests pass, with hand-worked values.",
                     why="Every number in the product comes from here. Dev 2's tools call these functions.",
                     files=["SPEC.md", "KPI_REVIEW.md"]),
                task(4, "Golden cases for every KPI", "golden-cases", "evals/, tests/, EVALS.md",
                     "Create evals/cases/golden.json with one case per KPI (the 13 in SPEC.md): the question, the tool, the date window and the expected value worked out by hand from the portfolio in data/synthetic/portfolio.py. Show the working in a note field. Add tests/test_golden.py that runs every case through the tool registry in harness/ with no model and compares exactly as strings. Check at least three expected values by hand before you trust the code output. Update EVALS.md to describe these cases.",
                     "13 golden cases pass exactly, and EVALS.md describes them.",
                     why="A tool that only agrees with itself proves nothing. Hand-worked values are the truth. Needs Dev 2's tools.",
                     files=["EVALS.md", "SPEC.md"]),
                task(4, "Prove a made-up number is withheld", "number-check", "tests/ only",
                     "Write tests/test_number_check.py for check_numbers in harness/agent.py (SPEC.md section 6). Cases: a made-up number is found; the same number written differently (12.5 and 12.50, 85 and 85.0) is accepted; years, dates and counts such as '2 parks' do not cause false alarms; a number that appears only in the question is accepted. If a test shows a real bug, report it to Dev 2 and do not edit harness/.",
                     "the tests pass, or each failure is a written bug report for Dev 2.",
                     why="This check is the one thing that keeps the model from stating a wrong number. Needs Dev 2's loop.",
                     files=["EVALS.md", "SPEC.md"]),
            ],
            done=["The portfolio is the same on every run and matches the ranges in SPEC.md.", "13 formulas pass hand-worked tests and never return a float.", "13 golden cases pass exactly; three were checked by hand.", "A made-up number is withheld, and a test proves it.", "<code>make test</code> is green."]),
}


def dev_page(n, d):
    body = f"""<header class="rolehead"><div class="big" aria-hidden="true">{n}</div><div>
<h1>{d['title']}</h1>
<p>{d['what']}<br>Branches <code>dev{n}/&lt;task&gt;</code><br>Your files: {", ".join(f(x) if (ROOT / x).exists() else C(x) for x in d['own'])}</p></div></header>
{block("Your part", "Highlighted boxes are yours. Arrows show who calls whom.", '<div class="mini">' + arch(f"arch-{n}", focus=n) + "</div>", "part")}
{block("Set up", "Once, before you build", setup(), "setup")}
{block("The loop", "Every task below runs it", LOOP + '<p class="loop-note">One task, one branch, one pull request. Start the next task after the merge.</p>', "loop")}
{block("Tasks", "In this order. Each has one prompt to start and one to finish.", route(*d["tasks"]), "tasks")}
{block("Done when", "Every item has evidence", done(d['done']), "done")}
"""
    return page(f"developer-{n}.html", f"Dev {n} — {html.unescape(d['title'])}", body, COL[n])


# ───────────────────────── lead page ─────────────────────────

def lead_page():
    body = f"""<header class="rolehead lead"><div class="big" aria-hidden="true">L</div><div>
<h1>Lead</h1>
<p>You decide scope and merge to <code>main</code>. You own: {", ".join(f(x) for x in ["INTENT.md", "ARCHITECTURE.md", "TEAM.md", "README.md", "DEMO.md", "scripts/slides.py"])}</p></div></header>
{block("The whole picture", "The number on each box is its developer. Point at a name to see their part.", arch("arch-lead") + legend("arch-lead"), "part")}
{block("Decide first", "Three open questions in INTENT.md, section 10", route(
        step("Pick the first real data source", "Without a validated source no KPI is production-ready. Name one source and one owner, or confirm the POC stays synthetic.", files=[("INTENT.md", "INTENT.md (§10)"), "KPI_REVIEW.md"]),
        step("Confirm who owns the calculator", "<code>mcp/kpi-solar</code> is assigned to Dev 4 in TEAM.md. Say yes or name someone else.", files=["TEAM.md"]),
        step("Choose the demo host", "The Azure container, or the presenter's laptop. Offline replay (Dev 3) is the fallback either way. Make sure you have access to the Azure registry and web app.", files=[("docs/index.html#deploy", "Deploying to Azure")]),
    ), "decide")}
{block("Before the build", "Four prompts, each takes a minute", route(
        step("Add names to the team file", claude="Open TEAM.md and replace Dev 1 to Dev 4 and Lead with these names: <names>. Change nothing else.", files=["TEAM.md"]),
        step("Check the spec with an energy colleague", "15 minutes. Are the KPI definitions right, and are the data ranges plausible?", files=["KPI_REVIEW.md", "SPEC.md"]),
        step("Keep the team off the old build", "The earlier build is kept on tag <code>reference-v1</code> so you can compare at the end. Tell the team not to open it.", claude="Tell me what is on tag reference-v1 and confirm that main has no harness code. Do not change anything."),
        step("Share the key privately", "One Anthropic key for the team. Each developer puts it in their own <code>.env</code>; it is never committed."),
        step("Send each person their page", "Link: <code>docs/developer-N.html</code>. Each person runs the setup prompt on their page before the session."),
    ), "before")}
{block("The loop", "How every task reaches main", LOOP, "loop")}
{block("During the build", None, route(
        step("Merge in build order", "Dev 3 contracts first, then Dev 4 portfolio and formulas, then Dev 2 tools and loop, then the rest. The order is in ARCHITECTURE.md section 6.", files=["ARCHITECTURE.md", "SPEC.md"]),
        step("Check main after every merge", claude="Update main from GitHub, run make verify and tell me in plain words what is red and who owns it."),
        step("Say no to new scope", "If it is not on someone's page, it is after the POC. See INTENT.md section 8.", files=["INTENT.md"]),
        step("Never add an approval tool to the registry", "Nine tools. Approval is never one of them."),
    ), "during")}
{block("Prepare the presentation", "The lead owns the story", route(
        step("Read the five slides", "Open the page and read them aloud once.", files=[("docs/presentation.html", "Presentation")]),
        step("Change the words", "Slide text is in one file. Claude edits it and rebuilds the page.", files=["scripts/slides.py"], claude="Edit the slides in scripts/slides.py. Change: <what to change>. Keep each slide to a headline and at most three short items. Then run make docs and tell me what changed."),
        step("Check the demo story", "The three-minute story and the questions to ask live.", files=["DEMO.md"], claude="Open DEMO.md and run each question in the demo table against the chat page. Tell me which questions give a good answer and which do not, and suggest replacements. Do not change any code."),
    ), "presentation")}
{block("Before presenting", None, route(
        step("Compare with the earlier build", "Only you may open tag <code>reference-v1</code>. Ask the same five questions on the new build and on it, and judge how close they are. Differences are fine; wrong numbers are not.", claude="Run the new harness and the build on tag reference-v1 side by side in separate folders. Ask both: Which park lost most energy in June? / What is our battery round-trip efficiency? / Should we change anything about negative prices? / What was the total revenue of park A in 2031? / Add up the energy of both parks and give me the average. Show a table: tools used, chart yes or no, verified yes or no, and the first 200 characters of each answer. Do not edit any file."),
        step("Run the end-to-end check", claude="Run make demo-smoke and tell me if it passes offline."),
        step("Rehearse twice, once with Wi-Fi off", "Time it. It must be under three minutes. Save one screenshot per step as the fallback.", files=["DEMO.md"]),
        step("Deploy to Azure", "Use the release prompt on the front page.", files=[("docs/index.html#deploy", "Deploying to Azure")]),
    ), "present")}
"""
    return page("lead.html", "Lead", body, "var(--lead)")


# ───────────────────────── start page ─────────────────────────

def sec(title, intro, inner, id_, alt=False):
    i = f'<p class="intro reveal">{intro}</p>' if intro else ""
    a = " alt" if alt else ""
    return f'<section class="sec{a}" id="{id_}"><h2 class="reveal">{title}</h2>{i}<div class="reveal">{inner}</div></section>'


def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def index_page():
    tiles = (tile("lead.html", "L", "Lead", "Decisions, slides &amp; merges")
             + tile("developer-1.html", 1, "Dev 1", "Skill &amp; chat page")
             + tile("developer-2.html", 2, "Dev 2", "Harness, approval &amp; audit")
             + tile("developer-3.html", 3, "Dev 3", "Model, contracts &amp; health")
             + tile("developer-4.html", 4, "Dev 4", "Calculator &amp; evals")
)
    process = route(
        step("The lead settles the idea", "Read " + f("INTENT.md") + " (five minutes). The lead answers its three open questions.", files=[("docs/lead.html", "Lead page")]),
        step("Everyone sets up once", "Open your page from the tiles above and paste the setup prompt. Claude installs the tools and runs the checks."),
        step("Each person takes their tasks", "Four developers, three or four tasks each, in build order. The shared contracts and the data come first: Dev 3 and Dev 4 start, the others read the spec and start the parts that need nothing from anyone."),
        step("Build each task with Claude", "One prompt to start, one to finish. Test first, then the verifier, then a pull request. <a href=\"#loop\">See the loop</a>."),
        step("The parts meet on GitHub", "One pull request per task into <code>main</code>. The lead merges in build order. <a href=\"#combine\">See how</a>."),
        step("The lead prepares the presentation", "Five slides and the three-minute demo.", files=[("docs/presentation.html", "Presentation"), "DEMO.md"]),
        step("Rehearse, merge to main, deploy", "Twice, once with Wi-Fi off. Then the lead deploys <code>main</code> to Azure. <a href=\"#deploy\">See how</a>."),
    )
    body = f"""<section class="hero">
  <div class="hero-l">
    <div>
      <h1>Energy 4.0 Harness</h1>
      <p class="tag">Ask. Check. Approve.</p>
    </div>
    <p class="hero-meta">Managers cannot yet trust AI answers about their portfolio: numbers may be wrong, and an assistant may act alone. This harness gives checked numbers and keeps a person in charge. We build it from scratch, together, from one spec.<span>First proof of concept · synthetic data</span></p>
  </div>
  <div class="hero-r"><div class="tiles">{tiles}</div></div>
</section>

{sec("How we work, start to finish", None, process, "process", True)}

<section class="sec" id="architecture">
  <h2 class="reveal">What we are building</h2>
  <p class="intro reveal">One question flows down through the boxes. The number on each box is its developer. Point at a name to see their part.</p>
  <div class="reveal">{arch("arch-main")}{legend("arch-main")}</div>
</section>

<section class="sec alt" id="combine">
  <h2 class="reveal">How we put our parts together</h2>
  <p class="intro reveal">Nobody sends files by chat or e-mail, and there is no shared folder. GitHub is the one place where our parts meet. Every part arrives as a pull request.</p>
  <div class="reveal">{merge_svg()}</div>
  <div class="reveal">{route(
    step("Work on your own branch", "The brief prompt on your page makes branch <code>devN/&lt;task&gt;</code> from <code>main</code>. You never edit <code>main</code> directly."),
    step("Finish with the finish prompt", "Claude runs <code>make check</code> and <code>make test</code>, pushes your branch and opens a pull request into <code>main</code>. There is no automatic build: the local checks are the gate."),
    step("The lead merges", "The lead merges each pull request into <code>main</code>. One pull request per task. Then tell the lead in the team chat."),
    step("Update before the next task", "Paste this at the start of every task.", claude="Update main from GitHub, create my next branch dev<N>/<task> from it, and tell me in plain words if anything conflicts."),
    step("Two people changed the same file?", "Stop. The ownership table in TEAM.md decides who owns it. Do not resolve it yourself.", files=["TEAM.md"], claude="Show me which files conflict and who owns each one. Explain the conflict in plain words. Do not change anything."),
  )}</div>
</section>

<section class="sec" id="deploy">
  <h2 class="reveal">Deploying to Azure</h2>
  <p class="intro reveal">The chat runs as one container on Azure App Service. Azure builds the image, so nobody needs Docker on a laptop. Dev 3 writes the container files in the last task.</p>
  <div class="reveal">{deploy_svg()}</div>
  <div class="reveal">{tbl(["Part", "How it works"], [
    ["Image", "<code>python:3.11-slim</code> with only the runtime code. <code>.dockerignore</code> is an allowlist, so <code>.env</code>, tests and docs never enter the image."],
    ["Build and run", "<code>az acr build</code> builds in Azure. The web app pulls the image with its managed identity."],
    ["The key", "<code>ANTHROPIC_API_KEY</code> is an App Service setting. It is never in the image or in git."],
    ["Settings", "<code>KPI_DAILY_CAP</code> (default 200 model calls a day), <code>KPI_ALLOWED_ORIGINS</code> (sites allowed to call the API), <code>KPI_LAB_HOST</code>, <code>KPI_LAB_PORT</code>, <code>KPI_CAP_FILE</code>, <code>AUDIT_LOG_PATH</code>."],
    ["Check", "<code>GET /health</code> returns 200 and the calls left today."],
    ["Known limit", "It runs as root because App Service mounts <code>/home</code> writable for root only. Fine for the POC."],
  ])}</div>
  <p class="intro reveal" style="margin-top:1.5rem">Not confirmed yet: the Azure names (registry, web app, resource group) and who has access. They are not in the repo. The lead confirms them before the first release.</p>
  <div class="reveal">{route(
    step("Pull main first", "Only deploy <code>main</code>, after <code>make verify</code> is green."),
    step("Release", "The lead pastes this into Claude Code. Claude asks for the names and for approval before it changes anything in Azure.", claude="Build the container image from main in Azure Container Registry, update the web app to the new image, then call /health and tell me the result. Ask me for the registry, web app and resource group names, and ask before every az command that changes Azure. Never print the API key."),
    step("Check the live page", "Open the page, ask one question, and confirm an answer and a chart come back. Then press Approve on a proposal and check the audit line."),
  )}</div>
</section>

<section class="sec alt" id="loop">
  <h2 class="reveal">How every task flows</h2>
  <p class="intro reveal">One small task, one branch, one pull request. You never type a command: each step is a prompt you paste into Claude Code.</p>
  <div class="reveal">{LOOP}</div>
  <p class="intro reveal">Brief Claude with one prompt and check the plan. Claude builds, tests and fixes until green. A second prompt runs the verifier and the checks, then opens the pull request. The lead merges.</p>
</section>

<section class="sec" id="docs">
  <h2 class="reveal">If something goes wrong</h2>
  <p class="intro reveal">Every project document is built into this guide as a page, and as raw Markdown. Use them when a prompt is unclear or two documents seem to disagree. If they disagree, stop and tell the lead.</p>
  <div class="reveal">{tbl(["Document", "What it answers"], [
    [f("INTENT.md"), "Why we build this, what done means, what is out of scope"],
    [f("SPEC.md"), "Exactly what each part must do: data, KPIs, tools, loop, approval, server, page"],
    [f("ARCHITECTURE.md"), "How the parts connect, and the build order"],
    [f("TEAM.md"), "Who owns which paths"],
    [f("EVALS.md"), "What correct means and how we prove it"],
    [f("DEMO.md"), "The three-minute story the finished harness must run"],
    [f("KPI_REVIEW.md"), "What each KPI means in the real world"],
    [f("CLAUDE.md"), "The rules Claude Code follows in this repository"],
  ])}</div>
</section>

{sec("Who builds what", "Exact tasks are on each page", tbl(["Person", "Builds", "Page"], [
    ["Dev 1", "Skill file for the model, charts, every state of the chat page", '<a href="developer-1.html">developer-1</a>'],
    ["Dev 2", "Nine tools, agent loop and number check, approval and audit, server, smoke test", '<a href="developer-2.html">developer-2</a>'],
    ["Dev 3", "Contracts, model gateway, offline replay, container files", '<a href="developer-3.html">developer-3</a>'],
    ["Dev 4", "Synthetic portfolio, 13 KPI formulas, golden cases, number-check tests", '<a href="developer-4.html">developer-4</a>'],
    ["Lead", "Decisions, the presentation, merges, deploy", '<a href="lead.html">lead</a>'],
]) + f'<p class="files">Files: {f("TEAM.md")}, {f("ARCHITECTURE.md")}</p>', "who", True)}

"""
    return page("index.html", "Energy 4.0 Harness guide", body)


def slides_page():
    n = len(SLIDES)
    out = []
    for i, sl in enumerate(SLIDES, 1):
        items = "".join(f"<li><b>{e(h)}</b><span>{e(t)}</span></li>" for h, t in sl["items"])
        out.append(
            f'<section class="slide {sl["tone"]}" id="slide-{i}"><div class="slide-in">'
            f'<span class="k">{e(sl["kicker"])}</span><h2>{e(sl["title"])}</h2>'
            + (f'<p class="sub">{e(sl["sub"])}</p>' if sl["sub"] else "")
            + (f'<ul class="trio">{items}</ul>' if items else "")
            + (f'<p class="foot">{e(sl["foot"])}</p>' if sl["foot"] else "")
            + f'</div><span class="no">{i} / {n}</span></section>')
    return page("presentation.html", "Presentation", "".join(out), "var(--lead)")


def main():
    (D / "index.html").write_text(index_page(), encoding="utf-8")
    (D / "lead.html").write_text(lead_page(), encoding="utf-8")
    (D / "presentation.html").write_text(slides_page(), encoding="utf-8")
    for n, d in DEVS.items():
        (D / f"developer-{n}.html").write_text(dev_page(n, d), encoding="utf-8")
    ref = D / "reference"
    ref.mkdir(exist_ok=True)
    for src, slug in REFERENCE.items():
        text = (ROOT / src).read_text(encoding="utf-8")
        (ref / f"{slug}.md").write_text(text, encoding="utf-8", newline="\n")
        body = (f'<article class="mdbody"><p class="mdnote"><a href="../index.html">Back to the guide</a> · '
                f'source <code>{e(src)}</code> · <a href="{slug}.md">raw Markdown</a></p>{md_to_html(text)}</article>')
        (ref / f"{slug}.html").write_text(page(f"reference/{slug}.html", slug.replace("_", " "), body, "var(--lead)", base="../"), encoding="utf-8")
    print("docs/ rebuilt: index, lead, presentation, developer-1..4, reference/*")


if __name__ == "__main__":
    main()
