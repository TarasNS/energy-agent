// Engine tests on the synthetic dataset. Run: node --test tools/kpi-lab/engine.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const K = require("./kpi.js");
const D = require("./data.js");
const E = require("./engine.js");

const data = D.build();

test("dataset is deterministic and labelled synthetic", () => {
  assert.equal(D.build().assets[0].daily[0].actualMwh, data.assets[0].daily[0].actualMwh);
  assert.match(data.label, /SYNTHETIC/);
  assert.equal(data.days.length, 30);
});

test("PPA delivery counts only the PPA share of output", () => {
  assert.match(E.ask("ppa delivery", data, K).text, /PPA delivery vs contract: 92\.6 %/);
});

test("cycle utilisation averages per day", () => {
  assert.match(E.ask("battery", data, K).text, /Cycle utilisation: 46\.1 %/);
});

test("incident resolution is unavailable, not estimated", () => {
  const r = E.ask("incident resolution", data, K);
  assert.match(r.text, /Incident resolution \(median\): unavailable\. no incident records/);
  assert.equal(r.kpis[0].value, null);
});

test("every answer carries a calculator trace", () => {
  const r = E.ask("availability", data, K);
  assert.ok(r.trace.length > 0);
  assert.match(r.trace[0], /availability_pct\(/);
});

test("unknown question falls back to the headline", () => {
  const r = E.ask("xyzzy", data, K);
  assert.match(r.text, /headline/);
  assert.equal(r.kpis.length, 3);
});

test("help lists the topics", () => {
  assert.match(E.ask("help", data, K).text, /actual vs expected/);
});

// Every standard tag must route to the KPI it names.
const TAG_CHECKS = [
  ["What is the actual vs expected generation for this period?", /Actual vs expected/],
  ["What is the performance ratio of each park?", /Performance ratio/],
  ["What is the availability of the parks this period?", /Availability/],
  ["What is the capacity factor of the portfolio?", /Capacity factor/],
  ["What is the PPA delivery against the contract?", /PPA delivery/],
  ["What is the realised (capture) price for the period?", /Realised/],
  ["What is the merchant price exposure?", /Merchant price exposure/],
  ["How many hours of downtime did the parks have?", /Downtime/],
  ["What are the energy losses against expected output?", /Energy losses/],
  ["What is the median incident resolution time?", /Incident resolution/],
  ["What are the battery availability, round-trip efficiency and cycle utilisation?", /BESS availability[\s\S]*Round-trip[\s\S]*Cycle utilisation/],
];
for (const [request, expected] of TAG_CHECKS) {
  test(`standard request routes correctly: ${request}`, () => {
    assert.match(E.ask(request, data, K).text, expected);
  });
}
