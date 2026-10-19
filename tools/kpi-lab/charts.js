/* Animated chart renderer for the KPI lab chat.
 * renderChart(spec) -> HTML string for one <figure>. Pure: no DOM, no network.
 * Browser: window.renderChart. Node: module.exports = { renderChart }.
 *
 * spec: { chart_id, kind: "line" | "bar" | "area" | "table", title,
 *         series: [{ name, points: [{ x, y }] }] }
 * x and y are the strings from the make_chart result. y is parsed only for
 * geometry; every label shown is the spec string as given (never rounded or
 * recomputed). Unknown kinds render as a table. Empty data renders "No data".
 */
(function (root) {
  "use strict";

  var VB_W = 480;
  var VB_H = 240;
  var PAD_L = 14;
  var PAD_R = 14;
  var PAD_T = 30;
  var PAD_B = 40;
  var PLOT_W = VB_W - PAD_L - PAD_R;
  var PLOT_T = PAD_T;
  var PLOT_B = VB_H - PAD_B;
  var KINDS = ["line", "bar", "area", "table"];

  // Brand tokens only (ns-web-brand). Light is the default; dark swaps the ink and series colours.
  // Tints are color-mix() of an approved token. Nothing here uses a border.
  var CSS = [
    "@keyframes ns-draw { to { stroke-dashoffset: 0; } }",
    "@keyframes ns-grow { from { transform: scaleY(0); } to { transform: scaleY(1); } }",
    "@keyframes ns-fade { from { opacity: 0; } to { opacity: 1; } }",
    "@keyframes ns-rise { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }",
    ".ns-chart {",
    "  --ns-green: #1A5C00; --ns-almost-black: #1C1C1C; --ns-off-white: #F4F2EB; --ns-white: #FFFFFF;",
    "  --ns-ink: var(--ns-almost-black);",
    "  --ns-card: color-mix(in srgb, var(--ns-almost-black) 4%, var(--ns-off-white));",
    "  --ns-grid: color-mix(in srgb, var(--ns-ink) 10%, transparent);",
    "  --ns-axis: color-mix(in srgb, var(--ns-ink) 30%, transparent);",
    "  --ns-tint: color-mix(in srgb, var(--ns-ink) 6%, transparent);",
    "  --ns-tint-strong: color-mix(in srgb, var(--ns-ink) 11%, transparent);",
    "  --ns-s0: var(--ns-green); --ns-s1: var(--ns-almost-black);",
    "  --ns-s2: color-mix(in srgb, var(--ns-green) 55%, var(--ns-off-white));",
    "  --ns-s3: color-mix(in srgb, var(--ns-green) 30%, var(--ns-off-white));",
    "  margin: 0; padding: 16px; border-radius: 12px; background: var(--ns-card); color: var(--ns-ink);",
    "  font-family: Aptos, \"Segoe UI\", system-ui, -apple-system, Roboto, \"Helvetica Neue\", Arial, sans-serif;",
    "}",
    ":root[data-theme=\"dark\"] .ns-chart {",
    "  --ns-ink: var(--ns-white);",
    "  --ns-card: color-mix(in srgb, var(--ns-white) 6%, var(--ns-almost-black));",
    "  --ns-s0: var(--ns-white); --ns-s1: var(--ns-off-white);",
    "  --ns-s2: color-mix(in srgb, var(--ns-white) 55%, var(--ns-almost-black));",
    "  --ns-s3: color-mix(in srgb, var(--ns-white) 30%, var(--ns-almost-black));",
    "}",
    "@media (prefers-color-scheme: dark) {",
    "  :root:not([data-theme=\"light\"]) .ns-chart {",
    "    --ns-ink: var(--ns-white);",
    "    --ns-card: color-mix(in srgb, var(--ns-white) 6%, var(--ns-almost-black));",
    "    --ns-s0: var(--ns-white); --ns-s1: var(--ns-off-white);",
    "    --ns-s2: color-mix(in srgb, var(--ns-white) 55%, var(--ns-almost-black));",
    "    --ns-s3: color-mix(in srgb, var(--ns-white) 30%, var(--ns-almost-black));",
    "  }",
    "}",
    ".ns-chart figcaption { font-weight: 700; font-size: 1rem; line-height: 1.3; margin-bottom: 8px; }",
    ".ns-chart .k0 { --sc: var(--ns-s0); } .ns-chart .k1 { --sc: var(--ns-s1); }",
    ".ns-chart .k2 { --sc: var(--ns-s2); } .ns-chart .k3 { --sc: var(--ns-s3); }",
    ".ns-chart .ns-legend { list-style: none; margin: 0 0 8px; padding: 0; display: flex; flex-wrap: wrap; gap: 6px; font-size: 0.875rem; font-weight: 600; }",
    ".ns-chart .ns-legend li { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; background: var(--ns-tint); }",
    ".ns-chart .ns-sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; background: var(--sc); }",
    ".ns-chart svg { display: block; width: 100%; height: auto; overflow: visible; font-size: 14px; }",
    ".ns-chart svg text { fill: var(--ns-ink); font-family: inherit; }",
    ".ns-chart .ns-grid { stroke: var(--ns-grid); stroke-width: 1; }",
    ".ns-chart .ns-axis { stroke: var(--ns-axis); stroke-width: 1.5; }",
    ".ns-chart .ns-line { fill: none; stroke: var(--sc); stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }",
    ".ns-chart .ns-area { fill: var(--sc); fill-opacity: 0.16; }",
    ".ns-chart .ns-dot { fill: var(--sc); }",
    ".ns-chart .ns-bar.pos { fill: var(--sc); }",
    ".ns-chart .ns-bar.neg { fill: none; stroke: var(--sc); stroke-width: 2; stroke-dasharray: 5 4; stroke-linejoin: round; }",
    ".ns-chart .ns-lbl { font-weight: 600; }",
    ".ns-chart .ns-empty { margin: 8px 0 0; font-weight: 600; }",
    ".ns-chart .ns-table-wrap { overflow-x: auto; }",
    ".ns-chart .ns-table { width: 100%; font-size: 0.9375rem; font-variant-numeric: tabular-nums; border-spacing: 0; }",
    ".ns-chart .ns-table th, .ns-chart .ns-table td { padding: 8px 10px; text-align: right; font-weight: 400; }",
    ".ns-chart .ns-table th { font-weight: 600; }",
    ".ns-chart .ns-table th:first-child, .ns-chart .ns-table td:first-child { text-align: left; }",
    ".ns-chart .ns-table thead th { background: var(--ns-tint-strong); }",
    ".ns-chart .ns-table tbody tr:nth-child(odd) > * { background: var(--ns-tint); }",
    "@media (prefers-reduced-motion: no-preference) {",
    "  .ns-chart .ns-line { stroke-dasharray: 1; stroke-dashoffset: 1; animation: ns-draw 600ms ease-out var(--d, 0ms) forwards; }",
    "  .ns-chart .ns-area { opacity: 0; animation: ns-fade 300ms ease-out var(--d, 0ms) forwards; }",
    "  .ns-chart .ns-dot, .ns-chart .ns-lbl { opacity: 0; animation: ns-fade 200ms ease-out var(--d, 0ms) forwards; }",
    "  .ns-chart .ns-bar { transform-box: fill-box; animation: ns-grow 350ms ease-out var(--d, 0ms) both; }",
    "  .ns-chart .ns-bar-up { transform-origin: 50% 100%; }",
    "  .ns-chart .ns-bar-down { transform-origin: 50% 0; }",
    "  .ns-chart .ns-row { opacity: 0; animation: ns-rise 250ms ease-out var(--d, 0ms) forwards; }",
    "}",
    "@media (prefers-reduced-motion: reduce) {",
    "  .ns-chart, .ns-chart * { animation: none !important; transition: none !important; }",
    "}"
  ].join("\n");

  function esc(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  // Labels are the spec strings as given; a missing value says n/a instead of a number.
  function labelOf(value) {
    return value === undefined || value === null || value === "" ? "n/a" : String(value);
  }

  // Geometry only.
  function numberOf(value) {
    return value === undefined || value === null || value === "" ? NaN : Number(value);
  }

  function f1(n) { return Number(n).toFixed(1); }

  function slotsFor(width) { return Math.max(2, Math.floor(width / 80)); }

  function everyNth(count, slots) { return Math.max(1, Math.ceil(count / slots)); }

  function readSeries(spec) {
    var raw = spec && Array.isArray(spec.series) ? spec.series : [];
    var out = [];
    raw.forEach(function (s) {
      if (!s || typeof s !== "object") return;
      var pts = Array.isArray(s.points) ? s.points : [];
      out.push({
        name: s.name === undefined || s.name === null ? "" : String(s.name),
        points: pts
          .filter(function (p) { return p && typeof p === "object"; })
          .map(function (p) {
            return { x: p.x === undefined || p.x === null ? "" : String(p.x), y: p.y };
          })
      });
    });
    return out;
  }

  // Categories in first-seen order across all series.
  function categoriesOf(series) {
    var seen = {};
    var list = [];
    series.forEach(function (s) {
      s.points.forEach(function (p) {
        if (!Object.prototype.hasOwnProperty.call(seen, p.x)) {
          seen[p.x] = true;
          list.push(p.x);
        }
      });
    });
    return list;
  }

  function valueAt(s, x) {
    for (var i = 0; i < s.points.length; i++) {
      if (s.points[i].x === x) return s.points[i].y;
    }
    return undefined;
  }

  // Linear y scale that always includes zero, with 12% headroom above the largest value.
  function scaleOf(values) {
    var finite = values.filter(function (v) { return isFinite(v); });
    var lo = Math.min.apply(null, [0].concat(finite));
    var hi = Math.max.apply(null, [0].concat(finite));
    if (hi - lo <= 0) hi = lo + 1;
    hi += (hi - lo) * 0.12;
    return function (v) { return PLOT_B - ((v - lo) / (hi - lo)) * (PLOT_B - PLOT_T); };
  }

  function gridSvg(zeroY) {
    var out = "";
    for (var g = 1; g <= 3; g++) {
      var gy = f1(PLOT_T + ((PLOT_B - PLOT_T) * g) / 4);
      out += "<line class=\"ns-grid\" x1=\"" + PAD_L + "\" x2=\"" + (VB_W - PAD_R) + "\" y1=\"" + gy + "\" y2=\"" + gy + "\"/>";
    }
    out += "<line class=\"ns-axis\" x1=\"" + PAD_L + "\" x2=\"" + (VB_W - PAD_R) + "\" y1=\"" + f1(zeroY) + "\" y2=\"" + f1(zeroY) + "\"/>";
    return out;
  }

  function xLabels(cats, centers, edgeAnchors) {
    var step = everyNth(cats.length, slotsFor(PLOT_W));
    var out = "";
    cats.forEach(function (c, i) {
      if (i % step !== 0) return;
      var anchor = "middle";
      if (edgeAnchors && i === 0) anchor = "start";
      if (edgeAnchors && i === cats.length - 1 && cats.length > 1) anchor = "end";
      out += "<text x=\"" + f1(centers[i]) + "\" y=\"" + (VB_H - 12) + "\" text-anchor=\"" + anchor + "\">" + esc(c) + "</text>";
    });
    return out;
  }

  function lineSvg(series, cats, area) {
    var n = cats.length;
    var centers = cats.map(function (_, i) {
      return n <= 1 ? PAD_L + PLOT_W / 2 : PAD_L + 8 + (i / (n - 1)) * (PLOT_W - 16);
    });
    var all = [];
    series.forEach(function (s) { cats.forEach(function (c) { all.push(numberOf(valueAt(s, c))); }); });
    var y = scaleOf(all);
    var zeroY = y(0);
    var showValues = n <= 10;
    var showDots = n <= 12;
    var body = gridSvg(zeroY);

    series.forEach(function (s, k) {
      var pts = [];
      cats.forEach(function (c, i) {
        var raw = valueAt(s, c);
        var v = numberOf(raw);
        if (isFinite(v)) pts.push({ x: centers[i], y: y(v), v: v, raw: labelOf(raw) });
      });
      if (!pts.length) return;
      var d = pts.map(function (p, j) { return (j ? "L" : "M") + f1(p.x) + "," + f1(p.y); }).join(" ");
      var g = "<g class=\"k" + (k % 4) + "\">";
      if (area) {
        var first = pts[0];
        var last = pts[pts.length - 1];
        var fillD = d + " L" + f1(last.x) + "," + f1(zeroY) + " L" + f1(first.x) + "," + f1(zeroY) + " Z";
        g += "<path class=\"ns-area\" style=\"--d:450ms\" d=\"" + fillD + "\"/>";
      }
      g += "<path class=\"ns-line\" pathLength=\"1\" style=\"--d:0ms\" d=\"" + d + "\"/>";
      pts.forEach(function (p) {
        if (showDots) {
          g += "<circle class=\"ns-dot\" r=\"4\" cx=\"" + f1(p.x) + "\" cy=\"" + f1(p.y) + "\" style=\"--d:600ms\"/>";
        }
        if (showValues) {
          // Later series and falling values put their label under the point, so labels do not stack.
          var below = k % 2 === 1 || p.v < 0;
          var ly = below ? p.y + 20 : p.y - 10;
          g += "<text class=\"ns-lbl\" style=\"--d:600ms\" x=\"" + f1(p.x) + "\" y=\"" + f1(ly) + "\" text-anchor=\"middle\">" + esc(p.raw) + "</text>";
        }
      });
      body += g + "</g>";
    });

    return body + xLabels(cats, centers, true);
  }

  // Rounded top for a bar that rises from the zero line; rounded bottom for one that falls.
  function barPath(x, top, w, h, up) {
    var r = Math.max(0, Math.min(4, w / 2, h));
    if (up) {
      return "M" + f1(x) + "," + f1(top + h) + " V" + f1(top + r) +
        " Q" + f1(x) + "," + f1(top) + " " + f1(x + r) + "," + f1(top) +
        " H" + f1(x + w - r) +
        " Q" + f1(x + w) + "," + f1(top) + " " + f1(x + w) + "," + f1(top + r) +
        " V" + f1(top + h) + " Z";
    }
    var bottom = top + h;
    return "M" + f1(x) + "," + f1(top) + " V" + f1(bottom - r) +
      " Q" + f1(x) + "," + f1(bottom) + " " + f1(x + r) + "," + f1(bottom) +
      " H" + f1(x + w - r) +
      " Q" + f1(x + w) + "," + f1(bottom) + " " + f1(x + w) + "," + f1(bottom - r) +
      " V" + f1(top) + " Z";
  }

  function barSvg(series, cats) {
    var n = cats.length;
    var S = series.length;
    var all = [];
    series.forEach(function (s) { cats.forEach(function (c) { all.push(numberOf(valueAt(s, c))); }); });
    var y = scaleOf(all);
    var zeroY = y(0);
    var band = PLOT_W / n;
    var group = band * 0.72;
    var barW = group / S;
    var gap = Math.min(6, barW * 0.2);
    var total = n * S;
    var stagger = Math.min(40, 350 / Math.max(1, total - 1));
    var showValues = total <= 16;
    var centers = [];
    var body = gridSvg(zeroY);
    var j = 0;

    cats.forEach(function (c, i) {
      var left = PAD_L + i * band + (band - group) / 2;
      centers.push(PAD_L + i * band + band / 2);
      series.forEach(function (s, k) {
        var raw = valueAt(s, c);
        var v = numberOf(raw);
        var x = left + k * barW + gap / 2;
        var w = Math.max(barW - gap, 2);
        var delay = Math.round(j * stagger);
        j += 1;
        var cx = x + w / 2;
        var labelY = zeroY - 8;
        if (isFinite(v) && v !== 0) {
          var yv = y(v);
          var up = v > 0;
          var top = Math.min(yv, zeroY);
          var h = Math.abs(yv - zeroY);
          var cls = "ns-bar " + (up ? "pos ns-bar-up" : "neg ns-bar-down") + " k" + (k % 4);
          body += "<path class=\"" + cls + "\" style=\"--d:" + delay + "ms\" d=\"" + barPath(x, top, w, h, up) + "\"/>";
          labelY = up ? top - 8 : top + h + 16;
        }
        if (showValues) {
          body += "<text class=\"ns-lbl\" style=\"--d:600ms\" x=\"" + f1(cx) + "\" y=\"" + f1(labelY) + "\" text-anchor=\"middle\">" + esc(labelOf(raw)) + "</text>";
        }
      });
    });

    return body + xLabels(cats, centers, false);
  }

  function tableHtml(series, cats) {
    var n = cats.length;
    var stagger = Math.min(30, 300 / Math.max(1, n - 1));
    var head = "<tr><th scope=\"col\"></th>" + series.map(function (s) {
      return "<th scope=\"col\">" + esc(s.name) + "</th>";
    }).join("") + "</tr>";
    var rows = cats.map(function (c, i) {
      var cells = series.map(function (s) {
        return "<td>" + esc(labelOf(valueAt(s, c))) + "</td>";
      }).join("");
      return "<tr class=\"ns-row\" style=\"--d:" + Math.round(i * stagger) + "ms\"><th scope=\"row\">" + esc(c) + "</th>" + cells + "</tr>";
    }).join("");
    return "<div class=\"ns-table-wrap\"><table class=\"ns-table\"><thead>" + head +
      "</thead><tbody>" + rows + "</tbody></table></div>";
  }

  function figure(kind, title, inner) {
    return "<figure class=\"ns-chart ns-chart-" + kind + "\"><figcaption>" + esc(title) + "</figcaption>" +
      "<style>" + CSS + "</style>" + inner + "</figure>";
  }

  function renderChart(spec) {
    var s = spec || {};
    var title = s.title === undefined || s.title === null ? "" : String(s.title);
    var kind = KINDS.indexOf(s.kind) >= 0 ? s.kind : "table";
    var series = readSeries(s);
    var cats = categoriesOf(series);

    if (!cats.length) return figure(kind, title, "<p class=\"ns-empty\">No data</p>");
    if (kind === "table") return figure(kind, title, tableHtml(series, cats));

    var legend = "<ul class=\"ns-legend\">" + series.map(function (sr, k) {
      return "<li class=\"k" + (k % 4) + "\"><span class=\"ns-sw\"></span>" + esc(sr.name) + "</li>";
    }).join("") + "</ul>";
    var plot = kind === "bar" ? barSvg(series, cats) : lineSvg(series, cats, kind === "area");
    var svg = "<svg viewBox=\"0 0 " + VB_W + " " + VB_H + "\" role=\"img\" aria-label=\"" + esc(title) + "\">" + plot + "</svg>";
    return figure(kind, title, legend + svg);
  }

  var api = { renderChart: renderChart };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.renderChart = renderChart;
})(typeof window !== "undefined" ? window : null);
