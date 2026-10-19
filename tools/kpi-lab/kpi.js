// KPI formulas for the test page. Mirrors mcp/kpi-solar/kpi_solar/metrics.py.
// Same rules: a value, or {unavailable: reason}. Nothing is estimated or defaulted.
// Decimal arithmetic is approximated with Number; rounding is half-up to the step.
(function (root) {
  const UNAVAILABLE = (reason) => ({ unavailable: reason });
  const isUnavailable = (r) => r !== null && typeof r === "object" && "unavailable" in r;

  function num(name, v) {
    if (v === null || v === undefined || v === "") return null;
    if (typeof v === "number") throw new TypeError(`${name} must be a string or Decimal-like, not a JS number`);
    const n = Number(v);
    if (!Number.isFinite(n)) throw new RangeError(`${name} must be a finite number, got ${v}`);
    return n;
  }
  function round(value, step) {
    const k = Math.round(Math.abs(value) / step) * step; // half-up on magnitude
    const r = Math.sign(value) * k;
    return Number(r.toFixed(decimalsOf(step)));
  }
  function decimalsOf(step) {
    return (String(step).split(".")[1] || "").length;
  }
  const PCT = 0.1, HOURS = 0.01, EUR_MWH = 0.01, MWH = 0.001;

  function need(obj) {
    const missing = Object.entries(obj).filter(([, v]) => v === null).map(([k]) => k);
    return missing.length ? UNAVAILABLE(`missing input: ${missing.join(", ")}`) : null;
  }

  function actualVsExpectedPct(actual, expected) {
    const a = num("actual_mwh", actual), e = num("expected_mwh", expected);
    const u = need({ actual_mwh: a, expected_mwh: e }); if (u) return u;
    if (e <= 0) return UNAVAILABLE("expected_mwh must be > 0");
    return round((a / e) * 100, PCT);
  }
  function performanceRatioPct(actualKwh, poaKwhM2, nameplateKwp) {
    const e = num("actual_kwh", actualKwh), h = num("poa_irradiation_kwh_m2", poaKwhM2), p = num("nameplate_kwp", nameplateKwp);
    const u = need({ actual_kwh: e, poa_irradiation_kwh_m2: h, nameplate_kwp: p }); if (u) return u;
    if (h <= 0 || p <= 0) return UNAVAILABLE("irradiation and nameplate must be > 0");
    return round((e / (h * p)) * 100, PCT);
  }
  function availabilityPct(avail, period) {
    const a = num("available_hours", avail), p = num("period_hours", period);
    const u = need({ available_hours: a, period_hours: p }); if (u) return u;
    if (p <= 0 || a < 0 || a > p) return UNAVAILABLE("require 0 <= available_hours <= period_hours and period_hours > 0");
    return round((a / p) * 100, PCT);
  }
  function capacityFactorPct(energy, capacity, period) {
    const e = num("energy_mwh", energy), c = num("capacity_mw", capacity), h = num("period_hours", period);
    const u = need({ energy_mwh: e, capacity_mw: c, period_hours: h }); if (u) return u;
    if (c <= 0 || h <= 0) return UNAVAILABLE("capacity_mw and period_hours must be > 0");
    return round((e / (c * h)) * 100, PCT);
  }
  function ppaDeliveryPct(delivered, contracted) {
    const d = num("delivered_mwh", delivered), c = num("contracted_mwh", contracted);
    const u = need({ delivered_mwh: d, contracted_mwh: c }); if (u) return u;
    if (c <= 0) return UNAVAILABLE("contracted_mwh must be > 0");
    return round((d / c) * 100, PCT);
  }
  // intervals: array of [mwh, price]
  function realisedPriceEurMwh(intervals) {
    if (!intervals || intervals.length === 0) return UNAVAILABLE("missing input: intervals");
    let totalMwh = 0, totalValue = 0;
    for (const [mwhRaw, priceRaw] of intervals) {
      const m = num("mwh", mwhRaw), p = num("price", priceRaw);
      if (m === null || p === null) return UNAVAILABLE("interval with missing energy or price; no partial price");
      if (m < 0) return UNAVAILABLE("negative metered energy in an interval; check the source");
      totalMwh += m; totalValue += m * p;
    }
    if (totalMwh <= 0) return UNAVAILABLE("no metered energy in the period");
    return round(totalValue / totalMwh, EUR_MWH);
  }
  function merchantExposureEur(mwh, move) {
    const m = num("merchant_mwh", mwh), p = num("price_move_eur_mwh", move);
    const u = need({ merchant_mwh: m, price_move_eur_mwh: p }); if (u) return u;
    return round(m * p, EUR_MWH);
  }
  const KNOWN = new Set(["OK", "CURTAILED", "OUTAGE", "DATA_GAP"]);
  function downtimeHours(statuses, intervalHours) {
    const h = num("interval_hours", intervalHours);
    const u = need({ statuses: statuses && statuses.length !== undefined ? statuses : null, interval_hours: h }); if (u) return u;
    if (statuses.length === 0) return UNAVAILABLE("no intervals");
    const unknown = [...new Set(statuses.filter((s) => !KNOWN.has(s)))];
    if (unknown.length) throw new RangeError(`unknown status codes: ${unknown.sort().join(", ")}`);
    const outages = statuses.filter((s) => s === "OUTAGE").length;
    return round(outages * h, HOURS);
  }
  function energyLossMwh(expected, actual) {
    const e = num("expected_mwh", expected), a = num("actual_mwh", actual);
    const u = need({ expected_mwh: e, actual_mwh: a }); if (u) return u;
    return round(e - a, MWH);
  }
  function incidentResolutionHours(hours) {
    if (!hours || hours.length === 0) return UNAVAILABLE("no incident records; ticket data required");
    const vals = hours.map((h) => num("hours", h));
    if (vals.some((v) => v === null || v < 0)) return UNAVAILABLE("every incident needs a non-negative open-to-close time");
    const s = [...vals].sort((a, b) => a - b), n = s.length;
    const med = n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
    return round(med, HOURS);
  }
  function bessAvailabilityPct(avail, period) { return availabilityPct(avail, period); }
  function bessRoundTripPct(discharged, charged) {
    const d = num("discharged_mwh", discharged), c = num("charged_mwh", charged);
    const u = need({ discharged_mwh: d, charged_mwh: c }); if (u) return u;
    if (c <= 0) return UNAVAILABLE("charged_mwh must be > 0");
    return round((d / c) * 100, PCT);
  }
  function bessCycleUtilisationPct(throughput, usable) {
    const t = num("throughput_mwh", throughput), u_ = num("usable_mwh", usable);
    const u = need({ throughput_mwh: t, usable_mwh: u_ }); if (u) return u;
    if (u_ <= 0) return UNAVAILABLE("usable_mwh must be > 0");
    return round((t / (2 * u_)) * 100, PCT);
  }

  const api = {
    isUnavailable, actualVsExpectedPct, performanceRatioPct, availabilityPct, capacityFactorPct,
    ppaDeliveryPct, realisedPriceEurMwh, merchantExposureEur, downtimeHours, energyLossMwh,
    incidentResolutionHours, bessAvailabilityPct, bessRoundTripPct, bessCycleUtilisationPct,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.KPI = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
