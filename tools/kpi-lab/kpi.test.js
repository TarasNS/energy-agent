// Parity test: the same hand-worked values as mcp/kpi-solar/tests/test_metrics.py.
// Run: node --test tools/kpi-lab/
const test = require("node:test");
const assert = require("node:assert/strict");
const K = require("./kpi.js");

test("actual vs expected", () => assert.equal(K.actualVsExpectedPct("90", "100"), 90.0));
test("actual vs expected needs baseline", () => assert.ok(K.isUnavailable(K.actualVsExpectedPct("90", ""))));
test("performance ratio", () => assert.equal(K.performanceRatioPct("800", "200", "5"), 80.0));
test("availability", () => assert.equal(K.availabilityPct("690", "720"), 95.8));
test("availability rejects available > period", () => assert.ok(K.isUnavailable(K.availabilityPct("800", "720"))));
test("capacity factor", () => assert.equal(K.capacityFactorPct("30", "10", "100"), 3.0));
test("PPA delivery", () => assert.equal(K.ppaDeliveryPct("95", "100"), 95.0));
test("realised price is volume weighted", () => assert.equal(K.realisedPriceEurMwh([["10", "40"], ["30", "20"]]), 25.0));
test("realised price refuses partial", () => assert.ok(K.isUnavailable(K.realisedPriceEurMwh([["10", "40"], ["30", ""]]))));
test("realised price refuses negative energy", () => assert.ok(K.isUnavailable(K.realisedPriceEurMwh([["-1", "40"], ["10", "20"]]))));
test("merchant exposure", () => assert.equal(K.merchantExposureEur("200", "5"), 1000.0));
test("downtime counts outages only", () =>
  assert.equal(K.downtimeHours(["OK", "OUTAGE", "OK", "OUTAGE", "CURTAILED"], "0.25"), 0.5));
test("downtime keeps two decimals", () =>
  assert.equal(K.downtimeHours(["OUTAGE", "OUTAGE"], "0.0833"), 0.17));
test("data gap is not downtime", () => assert.equal(K.downtimeHours(["DATA_GAP", "DATA_GAP"], "0.25"), 0));
test("downtime rejects unknown status", () => assert.throws(() => K.downtimeHours(["OK", "MAYBE"], "0.25")));
test("energy loss", () => assert.equal(K.energyLossMwh("120", "100"), 20.0));
test("incident resolution median", () => assert.equal(K.incidentResolutionHours(["2", "4", "9"]), 4.0));
test("incident needs tickets", () => assert.ok(K.isUnavailable(K.incidentResolutionHours([]))));
test("BESS availability", () => assert.equal(K.bessAvailabilityPct("90", "100"), 90.0));
test("BESS round trip", () => assert.equal(K.bessRoundTripPct("88", "100"), 88.0));
test("BESS cycle utilisation", () => assert.equal(K.bessCycleUtilisationPct("400", "200"), 100.0));
test("JS numbers are refused, as Python floats are", () => assert.throws(() => K.availabilityPct(690.0, 720)));
test("NaN is refused", () => assert.throws(() => K.availabilityPct("NaN", "720")));
