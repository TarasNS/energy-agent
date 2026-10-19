"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { renderChart } = require("./charts.js");

const spec = (kind) => ({
  chart_id: "c1",
  kind,
  title: "Availability by park",
  series: [{ name: "Availability %", points: [{ x: "north", y: "96.5" }, { x: "south", y: "97.1" }] }],
});

test("every kind renders the title", () => {
  for (const k of ["line", "bar", "area", "table"]) {
    assert.ok(renderChart(spec(k)).includes("Availability by park"), `kind ${k}`);
  }
});

test("labels are the spec strings, never recomputed", () => {
  assert.ok(renderChart(spec("bar")).includes(">96.5<"));
  assert.ok(renderChart(spec("table")).includes(">96.5<"));
});

test("animation is on, and off for reduced motion", () => {
  const html = renderChart(spec("line"));
  assert.ok(html.includes("@keyframes") && html.includes("prefers-reduced-motion: reduce"));
});

test("no border lines on the figure", () => {
  assert.ok(!/border\s*:\s*[^0n]/.test(renderChart(spec("table"))));
});

test("empty or malformed series does not throw", () => {
  assert.ok(renderChart({ kind: "bar", title: "t", series: [] }).includes("No data"));
  assert.ok(renderChart({ kind: "line", title: "t" }).includes("No data"));
  assert.ok(renderChart({ kind: "area", title: "t", series: [null, { name: "x" }] }).includes("No data"));
});

test("text from the spec is escaped", () => {
  const html = renderChart({ ...spec("bar"), title: "<img onerror=x>" });
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("&lt;img"));
  const table = renderChart({
    kind: "table",
    title: "t",
    series: [{ name: "<script>", points: [{ x: "<b>north</b>", y: "1" }] }],
  });
  assert.ok(!table.includes("<script>") && !table.includes("<b>"));
});
