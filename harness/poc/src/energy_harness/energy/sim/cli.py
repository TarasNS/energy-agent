"""`energy-harness-sim`: look at the simulated ground truth.

    energy-harness-sim events
    energy-harness-sim production sim-dk-west 2026-10-09 [--end 2026-10-11] [--csv out.csv]
    energy-harness-sim prices DK1 2026-10-11 [--csv out.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from ...config import load_settings
from .scenario import Scenario
from .simulator import Simulator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="energy-harness-sim", description="Inspect or export simulated data.")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("events", help="list parks and scripted incidents")
    prod = sub.add_parser("production", help="15-min production for a park")
    prod.add_argument("park")
    prod.add_argument("start", type=date.fromisoformat)
    prod.add_argument("--end", type=date.fromisoformat)
    prod.add_argument("--csv")
    price = sub.add_parser("prices", help="15-min day-ahead prices for a zone (CET/CEST market days)")
    price.add_argument("zone")
    price.add_argument("start", type=date.fromisoformat)
    price.add_argument("--end", type=date.fromisoformat)
    price.add_argument("--csv")
    args = parser.parse_args(argv)

    settings = load_settings(args.config)
    sim = Simulator(Scenario.from_file(settings.simulation_file))

    if args.command == "events":
        print(f"seed {sim.scenario.seed} · simulated now {sim.now():%Y-%m-%d %H:%M} UTC\n")
        for p in sim.parks.parks:
            print(f"  {p.id:14} {p.name:30} {p.capacity_mwp:5.1f} MWp  {p.bidding_zone}")
        print()
        for e in sim.scenario.events:
            what = e.park or e.zone
            print(f"  {e.start:%Y-%m-%d %H:%M} → {e.end:%Y-%m-%d %H:%M}  {e.type:12} {what:12} {e.note or ''}")
        return 0

    end = args.end or args.start
    if args.command == "production":
        start_dt = datetime.combine(args.start, time(), timezone.utc)
        samples = sim.production(args.park, start_dt, start_dt + timedelta(days=(end - args.start).days + 1))
        header = ["time_utc", "expected_mw", "metered_mw", "availability", "curtailed"]
        rows = [[s.time.isoformat(), s.expected_mw, s.metered_mw, s.availability, s.curtailed] for s in samples]
        daily = defaultdict(lambda: [0.0, 0.0])
        for s in samples:
            daily[s.time.date()][0] += s.expected_mw * 0.25
            daily[s.time.date()][1] += (s.metered_mw or 0.0) * 0.25
        print(f"{'date':12} {'expected MWh':>13} {'metered MWh':>12}")
        for day, (expected, metered) in sorted(daily.items()):
            print(f"{day!s:12} {expected:13.1f} {metered:12.1f}")
    else:
        points = sim.prices(args.zone, args.start, end)
        header = ["time_utc", "eur_per_mwh"]
        rows = [[p.time.isoformat(), p.eur_per_mwh] for p in points]
        values = [p.eur_per_mwh for p in points]
        print(f"{args.zone.upper()} {args.start}..{end}: mean {sum(values) / len(values):.2f}, min {min(values)}, max {max(values)} EUR/MWh")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
