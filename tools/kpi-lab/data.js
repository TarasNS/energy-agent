// SYNTHETIC dataset for the KPI chat. Not Nordic Solar data.
// Deterministic: the same seed gives the same numbers every time, so answers can be checked.
(function (root) {
  function rng(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  function dates(n) {
    const out = [];
    const start = Date.UTC(2026, 5, 1); // synthetic month: June 2026
    for (let i = 0; i < n; i++) out.push(new Date(start + i * 86400000).toISOString().slice(0, 10));
    return out;
  }

  function build(seed = 20260601) {
    const r = rng(seed);
    const days = dates(30);
    const pv = [
      { id: "north", name: "Park North (synthetic)", capacityMw: 10, nameplateKwp: 10000, outageDays: [6, 7, 19] },
      { id: "south", name: "Park South (synthetic)", capacityMw: 8, nameplateKwp: 8000, outageDays: [12] },
    ];
    const assets = pv.map((p) => {
      const daily = days.map((date, i) => {
        const poa = 4.2 + r() * 2.2; // kWh/m² per day, plausible June range
        const expectedMwh = (p.nameplateKwp * poa * 0.82) / 1000; // expected yield baseline (synthetic model)
        const factor = 0.9 + r() * 0.16;
        let actualMwh = expectedMwh * factor;
        let outageHours = r() < 0.08 ? 1 + Math.floor(r() * 3) : 0;
        if (p.outageDays.includes(i)) outageHours = 10 + Math.floor(r() * 4);
        if (p.outageDays.includes(i)) actualMwh *= 0.35;
        const curtailedMwh = r() < 0.2 ? 0.3 + r() * 0.9 : 0;
        return {
          date,
          poaKwhM2: round(poa, 2),
          expectedMwh: round(expectedMwh, 3),
          actualMwh: round(actualMwh, 3),
          availHours: 24 - outageHours,
          outageHours,
          curtailedMwh: round(curtailedMwh, 3),
        };
      });
      return { ...p, kind: "pv", daily };
    });

    const prices = days.map((date) => {
      const base = 38 + r() * 30;
      const negative = r() < 0.15;
      return { date, meanPrice: round(negative ? -4 - r() * 12 : base, 2) };
    });

    const bessDaily = days.map((date) => {
      const usable = 20;
      const charged = 8 + r() * 4;
      const rte = 0.84 + r() * 0.07;
      const discharged = charged * rte;
      return {
        date,
        chargedMwh: round(charged, 3),
        dischargedMwh: round(discharged, 3),
        throughputMwh: round(charged + discharged, 3),
        usableMwh: usable,
        availHours: r() < 0.9 ? 24 : 24 - 2,
      };
    });

    return {
      label: "SYNTHETIC: not Nordic Solar data",
      period: { start: days[0], end: days[days.length - 1], days: days.length },
      days,
      assets: [...assets, { id: "battery", name: "Battery (synthetic)", kind: "bess", capacityMw: 5, daily: bessDaily }],
      prices,
      ppa: { shareOfExpected: 0.5 }, // ASSUMPTION for the demo: half of expected volume is under a PPA
    };
  }

  function round(v, d) {
    const f = Math.pow(10, d);
    return Math.round(v * f) / f;
  }

  const api = { build };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.KPI_DATA = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
