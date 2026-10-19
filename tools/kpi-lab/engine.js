// Chat engine: question -> KPI(s) -> calculator -> answer, tiles, chart, trace.
// The calculator is kpi.js (mirrors mcp/kpi-solar). The matching is keyword rules, not a language model.
(function (root) {
  const isU = (r) => r !== null && typeof r === "object" && "unavailable" in r;
  const fmt = (v, d, unit) => (typeof v === "number" ? `${v.toFixed(d)}${unit ? " " + unit : ""}` : "n/a");

  function sum(arr, f) { return arr.reduce((a, x) => a + f(x), 0); }

  function pvAssets(data) { return data.assets.filter((a) => a.kind === "pv"); }
  function bess(data) { return data.assets.find((a) => a.kind === "bess"); }

  function periodHours(data) { return data.period.days * 24; }

  // ── KPI computations. Each returns { title, result, unit, decimals, trace, chart? } ──

  function actualVsExpected(K, data) {
    const pv = pvAssets(data);
    const actual = sum(pv, (a) => sum(a.daily, (d) => d.actualMwh));
    const expected = sum(pv, (a) => sum(a.daily, (d) => d.expectedMwh));
    const r = K.actualVsExpectedPct(actual.toFixed(3), expected.toFixed(3));
    const days = data.days;
    return {
      title: "Actual vs expected generation", result: r, unit: "%", decimals: 1,
      trace: `actual_vs_expected_pct(actual=${actual.toFixed(3)} MWh, expected=${expected.toFixed(3)} MWh)`,
      chart: {
        kind: "line", title: "Daily actual vs expected, all PV parks (MWh)",
        labels: days.map((d) => d.slice(8)),
        series: [
          { name: "Actual", values: days.map((_, i) => sum(pv, (a) => a.daily[i].actualMwh)) },
          { name: "Expected", values: days.map((_, i) => sum(pv, (a) => a.daily[i].expectedMwh)) },
        ],
      },
    };
  }

  function performanceRatio(K, data) {
    const perAsset = pvAssets(data).map((a) => {
      const e = sum(a.daily, (d) => d.actualMwh) * 1000;   // kWh
      const h = sum(a.daily, (d) => d.poaKwhM2);            // kWh/m² over period
      const r = K.performanceRatioPct(e.toFixed(1), h.toFixed(2), String(a.nameplateKwp));
      return { name: a.name, value: isU(r) ? null : r, reason: isU(r) ? r.unavailable : "" };
    });
    const ok = perAsset.filter((x) => x.value !== null);
    const avg = ok.length ? ok.reduce((s, x) => s + x.value, 0) / ok.length : null;
    return {
      title: "Performance ratio", result: avg === null ? { unavailable: "no park has all inputs" } : Number(avg.toFixed(1)),
      unit: "%", decimals: 1,
      trace: perAsset.map((x) => `performance_ratio_pct(${x.name}) = ${x.value === null ? "unavailable" : x.value.toFixed(1) + " %"}`).join("; "),
      chart: { kind: "bar", title: "Performance ratio by park (%)", bars: perAsset.map((x) => ({ label: x.name.replace(" (synthetic)", ""), value: x.value })) },
    };
  }

  function availability(K, data) {
    const pv = pvAssets(data);
    const hours = periodHours(data);
    const perAsset = pv.map((a) => {
      const avail = sum(a.daily, (d) => d.availHours);
      const r = K.availabilityPct(String(avail), String(hours));
      return { name: a.name, value: isU(r) ? null : r };
    });
    const availAll = sum(pv, (a) => sum(a.daily, (d) => d.availHours));
    const total = K.availabilityPct(String(availAll), String(hours * pv.length));
    return {
      title: "Availability", result: total, unit: "%", decimals: 1,
      trace: `availability_pct(available_hours=${availAll}, period_hours=${hours * pv.length} across ${pv.length} parks)`,
      chart: { kind: "bar", title: "Availability by park (%)", bars: perAsset.map((x) => ({ label: x.name.replace(" (synthetic)", ""), value: x.value })) },
    };
  }

  function capacityFactor(K, data) {
    const pv = pvAssets(data);
    const mwh = sum(pv, (a) => sum(a.daily, (d) => d.actualMwh));
    const capacity = sum(pv, (a) => a.capacityMw);
    const r = K.capacityFactorPct(mwh.toFixed(3), String(capacity), String(periodHours(data)));
    return { title: "Capacity factor", result: r, unit: "%", decimals: 1,
      trace: `capacity_factor_pct(energy=${mwh.toFixed(3)} MWh, capacity=${capacity} MW, hours=${periodHours(data)})` };
  }

  function ppaDelivery(K, data) {
    const pv = pvAssets(data);
    const actual = sum(pv, (a) => sum(a.daily, (d) => d.actualMwh));
    const expected = sum(pv, (a) => sum(a.daily, (d) => d.expectedMwh));
    const delivered = actual * data.ppa.shareOfExpected;   // share of output sold under the PPA
    const contracted = expected * data.ppa.shareOfExpected;
    const r = K.ppaDeliveryPct(delivered.toFixed(3), contracted.toFixed(3));
    return { title: "PPA delivery vs contract", result: r, unit: "%", decimals: 1,
      trace: `ppa_delivery_pct(delivered=${delivered.toFixed(3)}, contracted=${contracted.toFixed(3)}) · contracted = ${data.ppa.shareOfExpected * 100}% of expected (demo ASSUMPTION)` };
  }

  function realisedPrice(K, data) {
    const pv = pvAssets(data);
    const intervals = data.days.map((date, i) => [
      sum(pv, (a) => a.daily[i].actualMwh).toFixed(3),
      data.prices[i].meanPrice.toFixed(2),
    ]);
    const r = K.realisedPriceEurMwh(intervals);
    return { title: "Realised (capture) price", result: r, unit: "EUR/MWh", decimals: 2,
      trace: `realised_price_eur_mwh(${intervals.length} daily intervals; day-level, not 15-minute)`,
      chart: { kind: "bar", title: "Daily day-ahead price, EUR/MWh (negative days in red)", bars: data.days.map((d, i) => ({ label: d.slice(8), value: data.prices[i].meanPrice })) } };
  }

  function merchantExposure(K, data) {
    const pv = pvAssets(data);
    const actual = sum(pv, (a) => sum(a.daily, (d) => d.actualMwh));
    const merchant = actual * (1 - data.ppa.shareOfExpected);
    const move = 10; // EUR/MWh sensitivity: an input for the demo, not a forecast
    const r = K.merchantExposureEur(merchant.toFixed(3), String(move));
    return { title: "Merchant price exposure", result: r, unit: "EUR", decimals: 2,
      trace: `merchant_exposure_eur(merchant=${merchant.toFixed(3)} MWh, price_move=${move} EUR/MWh) · sensitivity, not a forecast` };
  }

  function downtime(K, data) {
    const pv = pvAssets(data);
    let outageHours = 0;
    const statuses = [];
    pv.forEach((a) => a.daily.forEach((d) => {
      for (let h = 0; h < 24; h++) statuses.push(h < d.outageHours ? "OUTAGE" : "OK");
    }));
    outageHours = statuses.filter((s) => s === "OUTAGE").length;
    const r = K.downtimeHours(statuses, "1");
    return { title: "Downtime", result: r, unit: "h", decimals: 2,
      trace: `downtime_hours(${statuses.length} hourly statuses across ${pv.length} parks, interval=1 h) · DATA_GAP not counted` ,
      chart: { kind: "bar", title: "Outage hours by park", bars: pv.map((a) => ({ label: a.name.replace(" (synthetic)", ""), value: sum(a.daily, (d) => d.outageHours) })) } };
  }

  function energyLoss(K, data) {
    const pv = pvAssets(data);
    const exp = sum(pv, (a) => sum(a.daily, (d) => d.expectedMwh));
    const act = sum(pv, (a) => sum(a.daily, (d) => d.actualMwh));
    const r = K.energyLossMwh(exp.toFixed(3), act.toFixed(3));
    return { title: "Energy losses", result: r, unit: "MWh", decimals: 3,
      trace: `energy_loss_mwh(expected=${exp.toFixed(3)}, actual=${act.toFixed(3)})` };
  }

  function incidents(K) {
    const r = K.incidentResolutionHours([]);
    return { title: "Incident resolution (median)", result: r, unit: "h", decimals: 2,
      trace: "incident_resolution_hours(no tickets loaded)" };
  }

  function bessKpis(K, data) {
    const b = bess(data);
    const hours = data.days.length * 24;
    const avail = sum(b.daily, (d) => d.availHours);
    const charged = sum(b.daily, (d) => d.chargedMwh);
    const discharged = sum(b.daily, (d) => d.dischargedMwh);
    const throughput = sum(b.daily, (d) => d.throughputMwh);
    const usable = b.daily[0].usableMwh;
    return [
      { title: "BESS availability", result: K.bessAvailabilityPct(String(avail), String(hours)), unit: "%", decimals: 1,
        trace: `bess_availability_pct(available_hours=${avail}, period_hours=${hours})` },
      { title: "Round-trip efficiency", result: K.bessRoundTripPct(discharged.toFixed(3), charged.toFixed(3)), unit: "%", decimals: 1,
        trace: `bess_round_trip_pct(discharged=${discharged.toFixed(3)}, charged=${charged.toFixed(3)})` },
      { title: "Cycle utilisation", result: K.bessCycleUtilisationPct((throughput / data.days.length).toFixed(3), String(usable)), unit: "%", decimals: 1,
        trace: `bess_cycle_utilisation_pct(average daily throughput=${(throughput / data.days.length).toFixed(3)} MWh, usable=${usable} MWh)` },
    ];
  }

  // ── Routing: keywords -> which KPIs to answer ──

  const ROUTES = [
    { match: /actual vs|expected|vs expected|baseline/, run: actualVsExpected },
    { match: /performance ratio|\bpr\b/, run: performanceRatio },
    { match: /availab/, run: availability, bessToo: true },
    { match: /capacity factor|\bcf\b/, run: capacityFactor },
    { match: /ppa|contract|delivery/, run: ppaDelivery },
    { match: /realis|capture/, run: realisedPrice },
    { match: /merchant|exposure|price risk/, run: merchantExposure },
    { match: /downtime|outage/, run: downtime },
    { match: /loss/, run: energyLoss },
    { match: /incident|resolution|ticket/, run: incidents },
    { match: /bess|battery|storage|round.?trip|cycle/, run: null, bess: true },
  ];

  const HELP = "Try: “actual vs expected”, “performance ratio”, “availability”, “capacity factor”, “PPA delivery”, “realised price”, “merchant exposure”, “downtime”, “energy losses”, “incident resolution”, or “battery”.";

  function ask(question, data, K) {
    const q = (question || "").toLowerCase().trim();
    if (!q) return { text: HELP, kpis: [], chart: null, trace: [] };
    if (/^(help|\?|what can)/.test(q)) return { text: HELP, kpis: [], chart: null, trace: [] };

    const results = [];
    let wantsBess = false;
    for (const route of ROUTES) {
      if (!route.match.test(q)) continue;
      if (route.bess) { wantsBess = true; continue; }
      results.push(route.run(K, data));
      if (route.bessToo && /battery|bess|storage/.test(q)) wantsBess = true;
    }
    if (wantsBess) results.push(...bessKpis(K, data));

    if (results.length === 0) {
      // default summary: the headline KPIs
      results.push(actualVsExpected(K, data), availability(K, data), performanceRatio(K, data));
      return buildAnswer(results, data, "Here is the headline for the period. " + HELP);
    }
    return buildAnswer(results, data, null);
  }

  function describe(r) {
    if (isU(r.result)) return `${r.title}: unavailable. ${r.result.unavailable}.`;
    return `${r.title}: ${fmt(r.result, r.decimals, r.unit)}.`;
  }

  function buildAnswer(results, data, lead) {
    const lines = results.map(describe);
    const unavailable = results.filter((r) => isU(r.result)).length;
    const text = (lead ? lead + "\n" : "") + lines.join("\n") +
      (unavailable ? `\n\n${unavailable} KPI(s) need data that is not loaded, so they are shown as unavailable rather than estimated.` : "");
    const kpis = results.map((r) => ({
      title: r.title,
      value: isU(r.result) ? null : r.result,
      unavailable: isU(r.result) ? r.result.unavailable : null,
      unit: r.unit, decimals: r.decimals,
    }));
    const chart = results.find((r) => r.chart) ? results.find((r) => r.chart).chart : null;
    const trace = results.map((r) => r.trace);
    return { text, kpis, chart, trace, label: data.label };
  }

  const api = { ask, HELP };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.KPI_ENGINE = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
