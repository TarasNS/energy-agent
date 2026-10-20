'use strict';
// Draws charts. It never adds, averages or rounds: every y is printed exactly as given.
// Number() is used only to place marks on the page, never to produce text.

const INK = '#1f2933';
const GREEN = '#2e7d32';
const GRID = '#d5dbd6';
const PALETTE = [GREEN, INK, '#66a06a', '#7b8794', '#1b4d1f', '#a5c9a8'];

const W = 640;
const H = 320;
const M = { top: 40, right: 20, bottom: 50, left: 20 };

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

function f(n) {
  return String(Math.round(n * 10) / 10); // pixel coordinates only
}

function hasPoints(chart) {
  return Array.isArray(chart.series) && chart.series.some((s) => s.points && s.points.length > 0);
}

function frame(chart, body) {
  return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" '
    + 'aria-label="' + esc(chart.title) + '" data-chart-id="' + esc(chart.id) + '" '
    + 'font-family="sans-serif" font-size="11">'
    + '<text x="' + M.left + '" y="22" font-size="14" font-weight="bold" fill="' + INK + '">'
    + esc(chart.title) + '</text>' + body + '</svg>';
}

function empty(chart) {
  return frame(chart, '<text x="' + M.left + '" y="' + (H / 2) + '" fill="' + INK + '">No data</text>');
}

function scales(chart) {
  const ys = [0];
  let n = 0;
  chart.series.forEach((s) => {
    n = Math.max(n, s.points.length);
    s.points.forEach((p) => ys.push(Number(p.y)));
  });
  const lo = Math.min.apply(null, ys);
  const hi = Math.max.apply(null, ys);
  const span = hi - lo || 1;
  const plotH = H - M.top - M.bottom;
  const plotW = W - M.left - M.right;
  return {
    n,
    yPos: (v) => M.top + plotH - ((Number(v) - lo) / span) * plotH,
    xPos: (i) => M.left + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW),
    slot: plotW / Math.max(n, 1),
    zero: M.top + plotH - ((0 - lo) / span) * plotH,
  };
}

function axis(chart, sc) {
  const first = chart.series.find((s) => s.points.length) || { points: [] };
  let out = '<line x1="' + M.left + '" x2="' + (W - M.right) + '" y1="' + f(sc.zero) + '" y2="' + f(sc.zero)
    + '" stroke="' + GRID + '"/>';
  first.points.forEach((p, i) => {
    out += '<text x="' + f(sc.xPos(i)) + '" y="' + (H - M.bottom + 16) + '" text-anchor="middle" fill="' + INK + '">'
      + esc(p.x) + '</text>';
  });
  return out;
}

function legend(chart) {
  return chart.series.map((s, i) => '<text x="' + (M.left + i * 130) + '" y="' + (H - 8)
    + '" fill="' + PALETTE[i % PALETTE.length] + '">&#9632; ' + esc(s.name) + '</text>').join('');
}

function labels(s, i, sc, dy) {
  return s.points.map((p, j) => '<text x="' + f(sc.xPos(j)) + '" y="' + f(sc.yPos(p.y) + dy)
    + '" text-anchor="middle" fill="' + PALETTE[i % PALETTE.length] + '">' + esc(p.y) + '</text>').join('');
}

function line(chart) {
  const sc = scales(chart);
  let body = axis(chart, sc);
  chart.series.forEach((s, i) => {
    const c = PALETTE[i % PALETTE.length];
    const pts = s.points.map((p, j) => f(sc.xPos(j)) + ',' + f(sc.yPos(p.y))).join(' ');
    body += '<polyline fill="none" stroke="' + c + '" stroke-width="2" points="' + pts + '"/>';
    s.points.forEach((p, j) => {
      body += '<circle cx="' + f(sc.xPos(j)) + '" cy="' + f(sc.yPos(p.y)) + '" r="3" fill="' + c + '"/>';
    });
    body += labels(s, i, sc, -8);
  });
  return frame(chart, body + legend(chart));
}

function area(chart) {
  const sc = scales(chart);
  let body = axis(chart, sc);
  chart.series.forEach((s, i) => {
    if (!s.points.length) return;
    const c = PALETTE[i % PALETTE.length];
    const top = s.points.map((p, j) => (j ? 'L' : 'M') + f(sc.xPos(j)) + ' ' + f(sc.yPos(p.y))).join(' ');
    const last = s.points.length - 1;
    body += '<path fill="' + c + '" fill-opacity="0.2" stroke="' + c + '" stroke-width="2" d="'
      + top + ' L' + f(sc.xPos(last)) + ' ' + f(sc.zero) + ' L' + f(sc.xPos(0)) + ' ' + f(sc.zero) + ' Z"/>';
    body += labels(s, i, sc, -8);
  });
  return frame(chart, body + legend(chart));
}

function bar(chart) {
  const sc = scales(chart);
  const k = chart.series.length;
  const bw = (sc.slot * 0.7) / k;
  let body = axis(chart, sc);
  chart.series.forEach((s, i) => {
    const c = PALETTE[i % PALETTE.length];
    s.points.forEach((p, j) => {
      const cx = M.left + sc.slot * (j + 0.5);
      const x = cx - (bw * k) / 2 + bw * i;
      const y = sc.yPos(p.y);
      const neg = Number(p.y) < 0;
      body += '<rect x="' + f(x) + '" y="' + f(Math.min(y, sc.zero)) + '" width="' + f(bw)
        + '" height="' + f(Math.abs(sc.zero - y)) + '" fill="' + c + '"/>';
      body += '<text x="' + f(x + bw / 2) + '" y="' + f(neg ? y + 12 : y - 4)
        + '" text-anchor="middle" fill="' + c + '">' + esc(p.y) + '</text>';
    });
  });
  return frame(chart, body + legend(chart));
}

function table(chart) {
  const th = 'style="text-align:left;padding:4px 8px;border-bottom:2px solid ' + GREEN + ';color:' + INK + '"';
  const td = 'style="padding:4px 8px;border-bottom:1px solid ' + GRID + ';color:' + INK + '"';
  const xs = [];
  chart.series.forEach((s) => s.points.forEach((p) => { if (!xs.includes(p.x)) xs.push(p.x); }));
  let out = '<div data-chart-id="' + esc(chart.id) + '"><strong style="color:' + INK + '">' + esc(chart.title)
    + '</strong><table style="border-collapse:collapse;font-family:sans-serif"><thead><tr><th ' + th + '></th>'
    + chart.series.map((s) => '<th ' + th + '>' + esc(s.name) + '</th>').join('') + '</tr></thead><tbody>';
  xs.forEach((x) => {
    out += '<tr><td ' + td + '>' + esc(x) + '</td>';
    chart.series.forEach((s) => {
      const p = s.points.find((q) => q.x === x);
      out += '<td ' + td + '>' + (p ? esc(p.y) : '') + '</td>';
    });
    out += '</tr>';
  });
  return out + '</tbody></table></div>';
}

const KINDS = { line, bar, area, table };

function renderChart(chart) {
  const draw = KINDS[chart && chart.kind];
  if (!draw) throw new Error('Unknown chart kind: ' + (chart && chart.kind));
  if (!hasPoints(chart)) {
    return chart.kind === 'table'
      ? '<div data-chart-id="' + esc(chart.id) + '"><strong style="color:' + INK + '">' + esc(chart.title)
        + '</strong><p style="color:' + INK + '">No data</p></div>'
      : empty(chart);
  }
  return draw(chart);
}

if (typeof module !== 'undefined' && module.exports) module.exports = { renderChart };
if (typeof window !== 'undefined') window.renderChart = renderChart;
