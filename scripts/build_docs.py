#!/usr/bin/env python3
"""Builds the docs/ portal (owner: Dev 1). Run: make docs

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
from flow import BY_NO, FLOW, MERGED, PEOPLE  # noqa: E402
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

COL = {1: "var(--d1)", 2: "var(--d2)", 3: "var(--d3)", 4: "var(--d4)", 5: "var(--lead)", "L": "var(--lead)"}
SUN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="none" stroke="#1a5c00" stroke-width="1.8"/>'
       '<g stroke="#1a5c00" stroke-width="1.6" stroke-linecap="round"><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1"/></g></svg>')
NAV = [("index.html", "Guide", "L"), ("lead.html", "Lead", "L"), ("developer-1.html", "Dev 1 · Model & server", 1),
       ("developer-2.html", "Dev 2 · Calculator & evals", 2), ("developer-3.html", "Dev 3 · Harness & audit", 3),
       ("developer-4.html", "Dev 4 · Approval & release", 4), ("developer-5.html", "Dev 5 · Chat page (lead)", 5),
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
         part(5, 370, 20, 220, 64, "Chat page", "Lovable · energy-agent-ui"),
         part(3, 370, 120, 220, 64, "Agent loop", "number check · harness/"),
         part(4, 100, 220, 230, 64, "KPI advisor skill", "the model's instructions"),
         part(1, 630, 220, 230, 64, "Model gateway", "Claude Haiku 5.5 · swappable"),
         part(1, 10, 330, 210, 66, "Server", "/api/chat · /api/approve"),
         part(3, 250, 330, 210, 66, "Energy tools", "nine tools · harness/"),
         part(2, 490, 330, 210, 66, "KPI calculator", "mcp/kpi-solar · every number"),
         part(4, 730, 330, 220, 66, "Actions", "propose → approve"),
         part(2, 10, 438, 210, 62, "Day-ahead prices", "daily · synthetic"),
         part(2, 250, 438, 210, 62, "Synthetic portfolio", "2 parks + 1 battery"),
         part(2, 490, 438, 210, 62, "Golden cases", "hand-worked values"),
         part(4, 730, 438, 220, 62, "Audit log", "proposals, approvals, tool calls"),
         '<text class="band" x="10" y="540">Across everything</text>',
         part(1, 10, 552, 225, 62, "Contracts & checks", "schemas · make check"),
         part(1, 245, 552, 225, 62, "Offline replay", "model/recorded"),
         part(3, 480, 552, 225, 62, "Smoke test", "make demo-smoke"),
         part(5, 715, 552, 235, 62, "Demo story", "DEMO.md · screenshots"),
         *[f'<circle class="pulse" r="3"><animateMotion dur="2.4s" begin="{b}s" repeatCount="indefinite" path="{d}"/></circle>' for d, b in PULSES],
         "</svg></div>"]
    return "".join(g)


def legend(target):
    names = {1: "Dev 1 · Model & server", 2: "Dev 2 · Calculator & evals", 3: "Dev 3 · Harness & audit", 4: "Dev 4 · Approval & release", 5: "Dev 5 · Chat page"}
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


def flow_svg():
    """The build flow: people as rows, four rounds as columns, an arrow from a task to each task that needs it.
    Arrows are faint until a task is pointed at (docs/js/app.js)."""
    NW, NH, GUT, LBL, HDR, SUB, LH = 198, 44, 68, 124, 40, 56, 128
    PITCH = NW + GUT

    def nx(r): return LBL + (r - 1) * PITCH
    def ny(t): return HDR + (t["dev"] - 1) * LH + t["sub"] * SUB + 10

    edges = [(BY_NO[s], t) for t in FLOW for s in t["needs"]]
    slots, lanes = {}, {}

    def bus(r, key):
        d = slots.setdefault(r, {})
        d.setdefault(key, len(d))
        return nx(r) + NW + 8 + d[key] * 7

    inc = {}
    for s, t in edges:
        inc.setdefault(t["no"], []).append(s)
    port = {}
    for no, srcs in inc.items():
        srcs = sorted(srcs, key=lambda s: (ny(s), s["rnd"]))
        for i, s in enumerate(srcs):
            port[(s["no"], no)] = (i - (len(srcs) - 1) / 2) * 7

    def lane_y(s, t):
        gap = t["dev"] - 1 if s["dev"] <= t["dev"] else t["dev"]
        k = lanes.get(gap, 0)
        lanes[gap] = k + 1
        return HDR + gap * LH - 6 + (k - 1) * 4

    W, H = LBL + 4 * PITCH - GUT + 12, HDR + 5 * LH
    out = [f'<div class="loopdiagram" style="overflow-x:auto"><svg id="flow" viewBox="0 0 {W} {H}" style="min-width:1000px" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="flt">',
           '<title id="flt">The build flow: 17 numbered tasks in four rounds, one row per person. An arrow points from a task to each task that needs it.</title>',
           '<style>#flow .fe{fill:none;stroke:var(--ink);stroke-width:1.3;stroke-linejoin:round;opacity:.55;marker-end:url(#fa)}'
           '#flow .fa{fill:var(--ink)}#flow .fn rect{fill:var(--green)}#flow .fn.d5 rect{fill:var(--lead)}'
           '#flow .fn.res rect{fill:var(--panel);stroke:var(--ink);stroke-dasharray:5 4}#flow .fn text{fill:var(--white);pointer-events:none}'
           '#flow .fn.res text{fill:var(--ink)}#flow .fn{cursor:pointer}#flow .t1{font:600 12.5px var(--font)}#flow .t2{font:400 10.8px var(--font)}'
           '#flow .ch{fill:var(--ink);font:600 12px var(--font);letter-spacing:.05em}#flow .who{fill:var(--ink);font:600 15px var(--font)}'
           '#flow .role{fill:var(--ink);opacity:.7;font:400 11px var(--font)}#flow .sep{stroke:var(--line);stroke-dasharray:4 4}#flow .ln{stroke:var(--line)}'
           '#flow.focus .fe{opacity:.06}#flow.focus .fe.hot{opacity:1;stroke-width:2}#flow.focus .fn{opacity:.28}#flow.focus .fn.hot{opacity:1}'
           '#flow .fn:focus-visible rect{stroke:var(--ink);stroke-width:3}</style>',
           '<defs><marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="8" markerHeight="8" orient="auto"><path class="fa" d="M0 0L10 5L0 10z"/></marker></defs>']
    heads = ["ROUND 1 · START NOW", "ROUND 2 · WIRE UP", "ROUND 3 · PROVE", "ROUND 4 · FINISH"]
    for r in range(1, 5):
        out.append(f'<text class="ch" x="{nx(r) + NW / 2}" y="24" text-anchor="middle">{heads[r - 1]}</text>')
        if r > 1:
            out.append(f'<line class="sep" x1="{nx(r) - GUT / 2}" y1="34" x2="{nx(r) - GUT / 2}" y2="{H - 6}"/>')
    for d, (name, role) in PEOPLE.items():
        y = HDR + (d - 1) * LH
        out.append(f'<line class="ln" x1="4" y1="{y - 4}" x2="{W - 4}" y2="{y - 4}"/>')
        out.append(f'<text class="who" x="6" y="{y + 32}">{name}</text><text class="role" x="6" y="{y + 50}">{role}</text>')
    for s, t in edges:
        sx, sy = nx(s["rnd"]) + NW, ny(s) + NH / 2
        tx, ty = nx(t["rnd"]), ny(t) + NH / 2 + port[(s["no"], t["no"])]
        bx = bus(s["rnd"], s["no"])
        if t["rnd"] == s["rnd"] + 1:
            pts = [(sx, sy), (bx, sy), (bx, ty), (tx - 2, ty)]
        else:
            x2 = tx - 12 - inc[t["no"]].index(s) * 6
            ly = lane_y(s, t)
            pts = [(sx, sy), (bx, sy), (bx, ly), (x2, ly), (x2, ty), (tx - 2, ty)]
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        out.append(f'<path class="fe" data-from="{s["no"]}" data-to="{t["no"]}" d="{d}"/>')
    for t in FLOW:
        x, y = nx(t["rnd"]), ny(t)
        cls = f'fn d{t["dev"]}' + (" res" if t["kind"] == "reserve" else "")
        needs = ", ".join(f'#{n}' for n in t["needs"]) or "nothing"
        out.append(f'<g class="{cls}" data-id="{t["no"]}" tabindex="0" role="button" aria-label="Task {t["no"]}: {e(t["title"])}. Needs {needs}.">'
                   f'<title>#{t["no"]} {e(t["title"])}. Needs: {needs}.</title><rect x="{x}" y="{y}" width="{NW}" height="{NH}" rx="8"/>'
                   f'<text class="t1" x="{x + 10}" y="{y + 19}">#{t["no"]} {e(t["title"])}</text>'
                   f'<text class="t2" x="{x + 10}" y="{y + 35}">{e(t["line2"])}</text></g>')
    out.append("</svg></div>")
    return "".join(out)


def flow_table():
    rows = []
    for t in FLOW:
        name, role = PEOPLE[t["dev"]]
        needs = ", ".join(f"#{n}" for n in t["needs"]) or "nothing"
        kind = {"claude": "Claude Code, pull request", "lovable": "Lovable", "run": "Claude Code, no pull request", "reserve": "reserve"}[t["kind"]]
        rows.append([f'#{t["no"]}', str(t["rnd"]), f'{role.split(" ·")[0]} {name}', e(t["title"]), needs, kind])
    return rows


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


GL = {**GL, 1: GL[3], 2: GL[4], 3: GL[2], 4: GL[1]}  # icons follow the developer numbering: Dev 1 model, 2 calculator, 3 harness, 4 skill


def tile(href, d, k, title):
    cls = "tile lead" if d == "L" else "tile"
    return f'<a class="{cls}" href="{href}" style="background:{COL[d]}"><span class="k">{k}</span>{GL[d]}<b>{title}</b></a>'



REPO_NAME = "TarasNS/energy-agent"


def row(label, body, cls="", sub=None):
    s = f"<small>{sub}</small>" if sub else ""
    c = f' class="{cls}"' if cls else ""
    return f'<li{c}><div class="lbl">{label}{s}</div><div class="body">{body}</div></li>'


def brief(t):
    """The one prompt that starts a task. Same rules every time, so nobody has to remember them."""
    needs = ", ".join(f"#{n} {BY_NO[n]['title']}" for n in t["needs"]) or "nothing, start now"
    return (
        "Read INTENT.md, SPEC.md and CLAUDE.md first. Then do this task:\n"
        f"{t['job']}\n\n"
        "Rules for this task:\n"
        f"- This is task #{t['no']} of {len(FLOW)} (round {t['rnd']}). It needs: {needs}.\n"
        f"- Work on a new branch called dev{t['dev']}/{t['slug']}, created from main.\n"
        f"- Edit only these paths: {t['own']}.\n"
        "- Before you change anything, show me your plan (goal, files, the test, done-when) and wait for my \"go\".\n"
        "- Write the test first. Run it. If it fails, fix the code, never the test, and run it again. Show me the output.\n"
        "- If the test is still red after two fixes, stop and tell me in plain words what fails."
    )


def finish(t):
    return (
        f"Use the verifier subagent to check this task against task #{t['no']} on docs/developer-{t['dev']}.html and report what it finds. "
        "Fix every P0 and P1 it reports. Then run make check and make test and show me the output.\n"
        f"If both are green, commit on branch dev{t['dev']}/{t['slug']}, push it and open a pull request into main named "
        f"\"#{t['no']} {t['title']}\", using .github/PULL_REQUEST_TEMPLATE.md."
    )


def task(no):
    t = BY_NO[no]
    needs = ", ".join(f"#{n} {e(BY_NO[n]['title'])}" for n in t["needs"]) or "nothing, start now"
    head = (f'<li id="task-{no}"><span class="t">#{no} · {e(t["title"])}</span>'
            f'<p class="files"><b>Task #{no} of {len(FLOW)}</b> · round {t["rnd"]} · needs: {needs}'
            + (f' · branch <code>dev{t["dev"]}/{t["slug"]}</code>' if t["kind"] == "claude" else "")
            + ' · <a href="index.html#combine">see the flow</a></p>' + (f"<p>{e(t['why'])}</p>" if t["why"] else ""))
    if t["files"]:
        head += '<p class="files">Files: ' + ", ".join(f(x) if isinstance(x, str) else f(*x) for x in t["files"]) + "</p>"
    if t["kind"] == "reserve":
        return head + f"<p>{e(t['job'])}</p></li>"
    if t["kind"] == "lovable":
        rows = [row("Brief Lovable", '<p class="say">Paste into Lovable</p>' + code(t["job"]), "", "then check the preview"),
                row("Check", f'<p class="see">You should see: {t["see"]}</p>', "gate", "must work"),
                row("Finish", f"<p>{t['finish_text']}</p>", "", "Lovable commits")]
    elif t["kind"] == "run":
        rows = [row("Brief Claude", '<p class="say">Paste into Claude Code</p>' + code(brief(t)), "", "then reply go"),
                row("Check", f'<p class="see">You should see: {t["see"]}</p>', "gate", "must be green"),
                row("Finish", f"<p>{t['finish_text']}</p>", "", "no pull request")]
    else:
        rows = [row("Brief Claude", '<p class="say">Paste into Claude Code</p>' + code(brief(t)), "", "then reply go"),
                row("Check", f'<p class="see">You should see: {t["see"]}</p>', "gate", "must be green"),
                row("Finish", '<p class="say">Paste into Claude Code</p>' + code(finish(t)), "", "verify, test, PR")]
    return head + '<ol class="loopsteps">' + "".join(rows) + "</ol></li>"


def setup(extra=()):
    return route(
        step("Open the project in Claude Code", "In the Claude desktop app, choose the Code tab and open the folder <code>energy-agent</code>. No folder yet? Ask Claude to clone it in the next step. The repository holds documents and checks only: that is expected."),
        step("Let Claude set it up", "Claude installs the tools and runs the checks. You read the answer.",
             claude=f"Set up this project on my computer. If the code is not here, clone https://github.com/{REPO_NAME}.git. Switch to the main branch, run make setup and make check, and explain any failure in plain words. If make is not installed (common on Windows), run python scripts/dev.py setup and python scripts/dev.py check instead, and from now on read every make X in this project as python scripts/dev.py X. Do not ask me to type my API key in this chat.",
             see="<code>make check passed.</code>"),
        step("Choose Haiku 5.5", "In Claude Code, pick Claude Haiku 5.5 in the model menu. It is fast; the tasks are cut small so it can do each one well. If a test stays red after two fixes, stop and ask."),
        step("Add the key", "Ask the lead for the Anthropic key. Copy <code>.env.example</code> to <code>.env</code>, paste the key after <code>ANTHROPIC_API_KEY=</code> and save. Never commit it.", files=[".env.example"]),
        step("Read the idea and the contract (10 minutes)", "These two files. Claude reads the rest for you. There is no harness code to copy: the team builds it together from the contract.", files=["INTENT.md", "SPEC.md"]),
        *extra,
    )


# ───────────────────────── developer content ─────────────────────────

def tasks_of(n):
    return [t["no"] for t in FLOW if t["dev"] == n]


DEVS = {
    1: dict(title="Model &amp; Server", own=["model/", "schemas/", "scripts/", "CLAUDE.md", "Makefile", ".github/", "docs/", "tools/kpi-lab/server.py"],
            what="You built the contracts, the model gateway and the replay. Now you build the server the page and the smoke test talk to, then run the five questions."),
    2: dict(title="Calculator &amp; Evals", own=["mcp/kpi-solar/", "evals/", "tests/", "data/synthetic/", "EVALS.md", "KPI_REVIEW.md"],
            what="You built the portfolio and the formulas. Now you prove the numbers: golden cases, the number check, the same cases through the live server, and the rehearsal."),
    3: dict(title="Harness &amp; Audit", own=["harness/", "model/recorded/", "scripts/demo-smoke.sh", ".claude/agents/"],
            what="You built the tools and the loop. Now you record the demo, write and run the smoke test, and add an audit line for every tool call."),
    4: dict(title="Approval &amp; Release", own=["mcp/actions/", "Dockerfile", ".dockerignore", ".claude/skills/", "tools/kpi-lab/charts.js"],
            what="You built the skill and the charts. As the team's software developer you now build the approval step, the container and the Azure release."),
    5: dict(title="Chat Page (Lovable)", own=["energy-agent-ui (Lovable repository)"],
            what="You are the lead and Dev 5. You approve and merge pull requests, and you build the chat page in Lovable. Lovable commits it to its own repository."),
}
for _n, _d in DEVS.items():
    _d["tasks"] = [task(no) for no in tasks_of(_n)]
    _d["done"] = [f"#{no} {e(BY_NO[no]['title'])}: {BY_NO[no]['see'] or 'done'}" for no in tasks_of(_n) if BY_NO[no]["kind"] != "reserve"]
    _d["merged"] = f'<p class="files">Already merged: {MERGED[_n]}.</p>' if MERGED[_n] else ""
def dev_page(n, d):
    body = f"""<header class="rolehead"><div class="big" aria-hidden="true">{n}</div><div>
<h1>{d['title']}</h1>
<p>{d['what']}<br>Branches <code>dev{n}/&lt;task&gt;</code><br>Your files: {", ".join(f(x) if (ROOT / x).exists() else C(x) for x in d['own'])}</p></div></header>
{block("Your part", "Highlighted boxes are yours. Arrows show who calls whom.", '<div class="mini">' + arch(f"arch-{n}", focus=n) + "</div>", "part")}
{block("Set up", "Once, before you build", setup(), "setup")}
{block("The loop", "Every task below runs it", LOOP + '<p class="loop-note">One task, one branch, one pull request. Start the next task after the merge.</p>', "loop")}
{block("Tasks", "In this order. The number is the place of the task in the flow on the front page.", d["merged"] + route(*d["tasks"]), "tasks")}
{block("Done when", "Every item has evidence", done(d['done']), "done")}
"""
    return page(f"developer-{n}.html", f"Dev {n} — {html.unescape(d['title'])}", body, COL[n])


# ───────────────────────── lead page ─────────────────────────

def lead_page():
    body = f"""<header class="rolehead lead"><div class="big" aria-hidden="true">L</div><div>
<h1>Lead</h1>
<p>You decide scope, approve and merge pull requests, and build the chat page in Lovable as Dev 5 (<a href="developer-5.html">your Dev 5 page</a>). You own: {", ".join(f(x) for x in ["INTENT.md", "ARCHITECTURE.md", "TEAM.md", "README.md", "DEMO.md", "scripts/slides.py"])}</p></div></header>
{block("The whole picture", "The number on each box is its developer. Point at a name to see their part.", arch("arch-lead") + legend("arch-lead"), "part")}
{block("Decide first", "Two open questions in INTENT.md, section 10", route(
        step("Pick the first real data source", "Without a validated source no KPI is production-ready. Name one source and one owner, or confirm the POC stays synthetic.", files=[("INTENT.md", "INTENT.md (§10)"), "KPI_REVIEW.md"]),
        step("Choose the demo host", "The Azure container, or the presenter's laptop. Offline replay (Dev 1) is the fallback either way. Make sure you have access to the Azure registry and web app.", files=[("docs/index.html#deploy", "Deploying to Azure")]),
    ), "decide")}
{block("Before the build", "Four prompts, each takes a minute", route(
                step("Check the spec with an energy colleague", "15 minutes. Are the KPI definitions right, and are the data ranges plausible?", files=["KPI_REVIEW.md", "SPEC.md"]),
        step("Keep the team off the old build", "The earlier build is kept on tag <code>reference-v1</code> so you can compare at the end. Tell the team not to open it.", claude="Tell me what is on tag reference-v1 and confirm that main has no harness code. Do not change anything."),
        step("Share the key privately", "One Anthropic key for the team. Each developer puts it in their own <code>.env</code>; it is never committed."),
        step("Send each person their page", "Link: <code>docs/developer-N.html</code>, Dev 1 to Dev 5. Each person runs the setup prompt on their page before the session and picks Haiku 5.5."),
    ), "before")}
{block("The loop", "How every task reaches main", LOOP, "loop")}
{block("During the build", None, route(
        step("Merge as soon as a task is green", "Each pull request is named with its task number. Merge it when the checks are green: the flow on the front page shows what may start after it. Do not wait to merge in number order.", files=[("docs/index.html#combine", "The flow")]),
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
        step("Check the smoke test", "Dev 3 runs it in task #14. Ask for the output before you approve the release."),
        step("Rehearse twice, once with Wi-Fi off", "Time it. It must be under three minutes. Save one screenshot per step as the fallback.", files=["DEMO.md"]),
        step("Approve the release", "Dev 4 runs the release (task #15) and asks you before every change in Azure.", files=[("docs/index.html#deploy", "Deploying to Azure")]),
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
    tiles = (tile("lead.html", "L", "Lead", "Decisions, approvals &amp; merges")
             + tile("developer-1.html", 1, "Dev 1", "Model &amp; server")
             + tile("developer-2.html", 2, "Dev 2", "Calculator &amp; evals")
             + tile("developer-3.html", 3, "Dev 3", "Harness &amp; audit")
             + tile("developer-4.html", 4, "Dev 4", "Approval &amp; release")
             + tile("developer-5.html", 5, "Dev 5", "Chat page in Lovable")
)
    process = route(
        step("The lead settles the idea", "Read " + f("INTENT.md") + " (five minutes). The lead answers its two open questions.", files=[("docs/lead.html", "Lead page")]),
        step("Everyone sets up once", "Open your page from the tiles above and paste the setup prompt. Claude installs the tools and runs the checks."),
        step("Each person takes their tasks", "Five people, seventeen numbered tasks in four rounds. Every task in round 1 needs nothing, so everyone starts at once. <a href=\"#combine\">See the flow</a>."),
        step("Build each task with Claude", "One prompt to start, one to finish. Test first, then the verifier, then a pull request. <a href=\"#loop\">See the loop</a>."),
        step("The parts meet on GitHub", "One pull request per task into <code>main</code>, named with its task number. The lead merges each one as soon as it is green. <a href=\"#combine\">See how</a>."),
        step("The lead prepares the presentation", "Five slides and the three-minute demo.", files=[("docs/presentation.html", "Presentation"), "DEMO.md"]),
        step("Rehearse, merge to main, deploy", "Twice, once with the server offline. Then Dev 4 releases <code>main</code> to Azure, and the lead approves each change. <a href=\"#deploy\">See how</a>."),
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
  <p class="intro reveal">Nobody sends files by chat or e-mail, and there is no shared folder. GitHub is the one place where our parts meet. Every part arrives as a pull request, and the lead merges each one as soon as it is green. The flow below has 17 numbered tasks in four rounds, one row per person; an arrow points from a task to each task that needs it. Point at or tap a task to light up its chain.</p>
  <div class="reveal">{flow_svg()}<p class="files">The number on a task is the same on its developer page and in its pull request name. Dashed grey boxes are reserve time. Everyone builds with Claude Haiku 5.5 in Claude Code; Dev 5 builds the chat page in Lovable.</p></div>
  <div class="reveal">{route(
    step("Work on your own branch", "The brief prompt on your page makes branch <code>devN/&lt;task&gt;</code> from <code>main</code>. You never edit <code>main</code> directly."),
    step("Finish with the finish prompt", "Claude runs <code>make check</code> and <code>make test</code>, pushes your branch and opens a pull request into <code>main</code>. There is no automatic build: the local checks are the gate."),
    step("The lead merges", "The lead merges each pull request into <code>main</code>. One pull request per task. Then tell the lead in the team chat."),
    step("Update before the next task", "Paste this at the start of every task.", claude="Update main from GitHub, create my next branch dev<N>/<task> from it, and tell me in plain words if anything conflicts."),
    step("Two people changed the same file?", "Stop. The ownership table in TEAM.md decides who owns it. Do not resolve it yourself.", files=["TEAM.md"], claude="Show me which files conflict and who owns each one. Explain the conflict in plain words. Do not change anything."),
  )}</div>
</section>

<section class="sec alt" id="order">
  <h2 class="reveal">Every task, as a list</h2>
  <p class="intro reveal">The same tasks as the flow above. Already merged before this flow: contracts, model gateway, offline replay, portfolio, KPI formulas, skill, charts, nine tools and the agent loop.</p>
  <div class="reveal">{tbl(["Task", "Round", "Who", "What", "Needs", "How"], flow_table())}</div>
  <p class="intro reveal" style="margin-top:1.5rem">After every merge the lead runs <code>make check</code> and <code>make test</code> on <code>main</code>, and the next developer updates from <code>main</code> before the next task.</p>
</section>

<section class="sec" id="deploy">
  <h2 class="reveal">Deploying to Azure</h2>
  <p class="intro reveal">The chat runs as one container on Azure App Service. Azure builds the image, so nobody needs Docker on a laptop. Dev 4 writes the container files (task #2) and releases (task #15). The chat page is not in the container: Dev 5 builds it in Lovable, and its address goes into <code>KPI_ALLOWED_ORIGINS</code>.</p>
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
    step("Release", "Dev 4 pastes this into Claude Code (task #15). Claude asks for the names, and the lead approves each change in Azure.", claude="Build the container image from main in Azure Container Registry, update the web app to the new image, then call /health and tell me the result. Ask me for the registry, web app and resource group names, and ask before every az command that changes Azure. Never print the API key."),
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

{sec("Who builds what", "Exact tasks are on each page", tbl(["Person", "Builds now", "Page"], [
    ["Dev 1 Anna", "Server routes, server on the real loop, the five-question run (#1, #9, #13)", '<a href="developer-1.html">developer-1</a>'],
    ["Dev 2 Huiling", "Golden cases, number-check tests, golden through the server, rehearsal (#3, #4, #12, #17)", '<a href="developer-2.html">developer-2</a>'],
    ["Dev 3 Raul", "Demo recordings, smoke script, tool-call audit, smoke run, fixes (#5, #6, #10, #14, #16)", '<a href="developer-3.html">developer-3</a>'],
    ["Dev 4 Søren", "Container files, actions and approval, release to Azure (#2, #7, #15)", '<a href="developer-4.html">developer-4</a>'],
    ["Dev 5 Taras (lead)", "Chat page in Lovable, page on the server (#8, #11); approves and merges", '<a href="developer-5.html">developer-5</a>'],
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
    print("docs/ rebuilt: index, lead, presentation, developer-1..5, reference/*")


if __name__ == "__main__":
    main()
