"""Small Markdown to HTML converter for the document pages in docs/reference/ (owner: Dev 1).

Handles what our documents use: headings, paragraphs, tables, lists, fenced code, quotes,
bold, italics, inline code and links. Standard library only.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

# Every spec document is built as a page in docs/reference/, so it stays readable even if GitHub is not.
REFERENCE = {
    "INTENT.md": "INTENT", "SPEC.md": "SPEC", "ARCHITECTURE.md": "ARCHITECTURE", "TEAM.md": "TEAM",
    "EVALS.md": "EVALS", "DEMO.md": "DEMO", "KPI_REVIEW.md": "KPI_REVIEW", "CLAUDE.md": "CLAUDE", "README.md": "README",
    ".claude/brand-voice-guidelines.md": "brand-voice-guidelines",
}
BY_NAME = {Path(k).name: v for k, v in REFERENCE.items()}

e = html.escape


def link(label: str, href: str) -> str:
    href = html.unescape(href)
    if re.match(r"^(https?:|mailto:|#)", href):
        return f'<a href="{href}">{label}</a>'
    path, _, frag = href.partition("#")
    frag = f"#{frag}" if frag else ""
    name = Path(path).name
    if name in BY_NAME and not path.startswith("docs/"):
        return f'<a href="{BY_NAME[name]}.html{frag}">{label}</a>'
    if path.startswith("docs/"):
        return f'<a href="../{path[5:]}{frag}">{label}</a>'
    return f"<code>{label}</code>"


def inline(s: str) -> str:
    spans: list[str] = []

    def keep(m):
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = e(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: link(m.group(1), m.group(2)), s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{e(spans[int(m.group(1))], quote=False)}</code>", s)


LIST = re.compile(r"^(\d+\.|-) ")


def md_to_html(md: str) -> str:
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>" + e("\n".join(buf)) + "</code></pre>")
        elif re.match(r"^#{1,4} ", ln):
            n = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{n}>{inline(ln[n + 1:])}</h{n}>")
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            i -= 1
            head, body = rows[0], rows[2:]
            out.append('<div class="tbl"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
                       + "</tbody></table></div>")
        elif LIST.match(ln):
            tag = "ol" if ln[0].isdigit() else "ul"
            items = []
            while i < len(lines) and LIST.match(lines[i]):
                items.append(LIST.sub("", lines[i]))
                i += 1
            i -= 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        elif ln.startswith(">"):
            out.append(f"<blockquote>{inline(ln.lstrip('> '))}</blockquote>")
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.strip():
            buf = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|>)", lines[i + 1]) and not LIST.match(lines[i + 1]):
                i += 1
                buf.append(lines[i])
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        i += 1
    return "\n".join(out)
