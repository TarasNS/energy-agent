#!/usr/bin/env python3
"""Seeded generator for the Energy 4.0 Harness demo fixture (owner: Dev 4).

Creates data/synthetic/demo-solar-dk/ for June 2026, DK1, in 15-minute intervals
(the European day-ahead market has used 15-minute MTU since delivery day 1 Oct 2025).

INPUTS ONLY. This script never computes EUR results. Golden EUR values are worked
out by hand (EVALS.md) and must never be produced by an LLM or copied from here.

Usage:
  python data/synthetic/generate.py            # (re)generate the fixture
  python data/synthetic/generate.py --summary  # print what is in it (MWh and counts only)
"""
from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

SEED = 2026
OUT = Path(__file__).resolve().parent / "demo-solar-dk"
PORTFOLIO = "demo-solar-dk"
ZONE = "DK1"
START = datetime(2026, 6, 1, tzinfo=timezone.utc)
DAYS = 30
MTU = 15  # minutes
H = Decimal(MTU) / Decimal(60)

# Fictional assets. Scenario built in:
#   01 self-curtails at negative prices and has two grid-operator limitation days (40 % cap)
#   02 self-curtails at negative prices and has a half-day inverter fault
#   03 has NO negative-price curtailment (fixed feed-in) -> it keeps producing into
#      negative prices. This is the decision the demo should surface.
#   03 rows also omit curtailed_mwh, so the calc must derive it (golden case G-04 path).
ASSETS = [
    {"asset_id": "dk1-solar-01", "name": "Vestmark Solar (demo)", "capacity_mw": "48.000", "self_curtails": True},
    {"asset_id": "dk1-solar-02", "name": "Lindholm Solar (demo)", "capacity_mw": "30.000", "self_curtails": True},
    {"asset_id": "dk1-solar-03", "name": "Engbakke Solar (demo)", "capacity_mw": "12.000", "self_curtails": False},
]
GRID_LIMIT_DAYS = {10, 23}          # asset 01 limited to 40 % of capacity, 10:00-14:00 UTC (sunny weekdays)
FAULT = (17, 7, 13)                  # asset 02, day 17, 07:00-13:00 UTC, 30 % output loss

q3 = lambda d: d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
q2 = lambda d: d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def solar_shape(t: datetime) -> float:
    """0..1 clear-sky shape for Denmark in June, UTC (sun ~02:30-20:00 UTC)."""
    h = t.hour + t.minute / 60 + MTU / 120  # interval midpoint
    rise, set_ = 2.6, 19.9
    if h <= rise or h >= set_:
        return 0.0
    return math.sin(math.pi * (h - rise) / (set_ - rise)) ** 1.35


def build():
    rnd = random.Random(SEED)
    day_kind, clear = {}, {}
    for d in range(1, DAYS + 1):
        k = rnd.choices(["sunny", "mixed", "overcast"], weights=[5, 3, 2])[0]
        if d in GRID_LIMIT_DAYS or d == FAULT[0]:
            k = "sunny"  # make the scripted events visible
        day_kind[d] = k
        clear[d] = {"sunny": rnd.uniform(0.86, 1.0), "mixed": rnd.uniform(0.5, 0.78), "overcast": rnd.uniform(0.15, 0.4)}[k]

    prices, rows = [], []
    t = START
    while t < START + timedelta(days=DAYS):
        d = t.day
        weekend = t.weekday() >= 5
        local_h = (t.hour + 2) + t.minute / 60  # CEST
        shape = solar_shape(t)
        cloud = clear[d] * (rnd.uniform(0.75, 1.1) if day_kind[d] == "mixed" else rnd.uniform(0.95, 1.03))
        cloud = max(0.0, min(cloud, 1.0))

        # Day-ahead price: morning and evening peaks, solar-driven midday dip.
        base = 74 - (12 if weekend else 0)
        peak = 38 * math.exp(-((local_h - 8) ** 2) / 3) + 70 * math.exp(-((local_h - 20.5) ** 2) / 3.5)
        dip = (92 if weekend else 70) * shape * clear[d] ** 2
        p = base + peak - dip + rnd.gauss(0, 4)
        prices.append({"price_zone": ZONE, "interval_start": iso(t), "interval_minutes": MTU,
                       "day_ahead_price_eur_mwh": str(q2(Decimal(str(p)))), "source": "fixture"})
        price = Decimal(prices[-1]["day_ahead_price_eur_mwh"])

        for a in ASSETS:
            cap = Decimal(a["capacity_mw"])
            avail = q3(cap * Decimal("0.74") * Decimal(str(shape * cloud)) * H)
            curt, reason = Decimal("0.000"), None
            if avail > 0:
                if a["self_curtails"] and price < 0:
                    curt, reason = q3(avail * Decimal("0.95")), "negative_price"
                elif a["asset_id"] == "dk1-solar-01" and d in GRID_LIMIT_DAYS and 10 <= t.hour < 14:
                    limit = q3(cap * Decimal("0.40") * H)
                    if avail > limit:
                        curt, reason = avail - limit, "grid_operator"
                elif a["asset_id"] == "dk1-solar-02" and d == FAULT[0] and FAULT[1] <= t.hour < FAULT[2]:
                    curt, reason = q3(avail * Decimal("0.30")), "technical"
            row = {"asset_id": a["asset_id"], "interval_start": iso(t), "interval_minutes": MTU,
                   "price_zone": ZONE, "available_mwh": str(avail), "actual_mwh": str(avail - curt)}
            if a["self_curtails"]:  # asset 03 omits curtailed_mwh on purpose (derivation path)
                row["curtailed_mwh"] = str(curt)
            if reason:
                row["curtailment_reason"] = reason
            rows.append(row)
        t += timedelta(minutes=MTU)

    assets = [{"asset_id": a["asset_id"], "portfolio_id": PORTFOLIO, "name": a["name"], "technology": "solar_pv",
               "price_zone": ZONE, "capacity_mw": a["capacity_mw"], "data_class": "synthetic"} for a in ASSETS]
    return assets, rows, prices


def write():
    assets, rows, prices = build()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets.json").write_text(json.dumps(assets, indent=2) + "\n")
    with open(OUT / "production-2026-06.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    with open(OUT / "prices-DK1-2026-06.jsonl", "w") as f:
        f.writelines(json.dumps(p) + "\n" for p in prices)
    print(f"wrote {OUT}: {len(assets)} assets, {len(rows)} production rows, {len(prices)} price rows")


def summary():
    rows = [json.loads(l) for l in open(OUT / "production-2026-06.jsonl")]
    prices = {p["interval_start"]: Decimal(p["day_ahead_price_eur_mwh"]) for p in map(json.loads, open(OUT / "prices-DK1-2026-06.jsonl"))}
    neg = sum(1 for v in prices.values() if v < 0)
    print(f"price intervals: {len(prices)} · negative: {neg} · min {min(prices.values())} · max {max(prices.values())} EUR/MWh")
    for aid in sorted({r["asset_id"] for r in rows}):
        rs = [r for r in rows if r["asset_id"] == aid]
        av = sum(Decimal(r["available_mwh"]) for r in rs)
        ac = sum(Decimal(r["actual_mwh"]) for r in rs)
        by = {}
        for r in rs:
            if "curtailment_reason" in r:
                by[r["curtailment_reason"]] = by.get(r["curtailment_reason"], Decimal(0)) + Decimal(r["available_mwh"]) - Decimal(r["actual_mwh"])
        at_neg = sum(Decimal(r["actual_mwh"]) for r in rs if prices[r["interval_start"]] < 0)
        print(f"{aid}: available {av} MWh · actual {ac} MWh · curtailed {av - ac} MWh {dict((k, str(v)) for k, v in by.items())} · produced at negative prices {at_neg} MWh")
    print("MWh and counts only. EUR values come from energy-calc and hand-worked golden cases.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    summary() if args.summary else write()
