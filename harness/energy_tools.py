"""The nine read-only tools (SPEC.md section 5) over the synthetic portfolio.

Every number comes from data/synthetic/portfolio.py or kpi_solar.metrics. Tools
only sum daily rows and hand them to the formulas; values leave as decimal
strings. There is no approval tool: approval lives only in the server.
"""
import re
import secrets
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from data.synthetic.portfolio import build
from harness.registry import ToolError, ToolRegistry
from kpi_solar import metrics

ASSETS = ["portfolio", "north", "south", "battery"]
JUNE_START, JUNE_END = "2026-06-01", "2026-06-30"
PRICE_MOVE_EUR_MWH = "10"
ACTIONS = ["enable_negative_price_curtailment", "schedule_inspection", "review_ppa_volume"]
CHART_KINDS = ["line", "bar", "area", "table"]

# metric -> (asset kind, daily field, unit); kind "price" reads the price rows.
METRICS = {
    "actual_mwh": ("pv", "actualMwh", "MWh"),
    "expected_mwh": ("pv", "expectedMwh", "MWh"),
    "availability_hours": ("pv", "availHours", "h"),
    "outage_hours": ("pv", "outageHours", "h"),
    "curtailed_mwh": ("pv", "curtailedMwh", "MWh"),
    "price_eur_mwh": ("price", "meanPrice", "EUR/MWh"),
    "bess_charged_mwh": ("bess", "chargedMwh", "MWh"),
    "bess_discharged_mwh": ("bess", "dischargedMwh", "MWh"),
}


def _sum(rows, field):
    return sum((Decimal(r[field]) for r in rows), Decimal(0))


def _hours(days):
    return Decimal(len(days) * 24)


# --- the 13 KPIs: each takes (assets, days, ctx) and returns (result, inputs) ---
# `assets` is a list of (asset, rows in the chosen days).

def _actual_vs_expected(assets, days, ctx):
    actual = sum((_sum(rows, "actualMwh") for _, rows in assets), Decimal(0))
    expected = sum((_sum(rows, "expectedMwh") for _, rows in assets), Decimal(0))
    return metrics.actual_vs_expected_pct(actual, expected), {"actual_mwh": actual, "expected_mwh": expected}


def _performance_ratio(assets, days, ctx):
    """Per park, then the simple average (SPEC.md section 3)."""
    values, inputs = [], {}
    for asset, rows in assets:
        actual_kwh = _sum(rows, "actualMwh") * 1000
        poa = _sum(rows, "poaKwhM2")
        kwp = Decimal(str(asset["nameplateKwp"]))
        inputs.update({f"{asset['id']}_actual_kwh": actual_kwh, f"{asset['id']}_poa_kwh_m2": poa,
                       f"{asset['id']}_nameplate_kwp": kwp})
        value = metrics.performance_ratio_pct(actual_kwh, poa, kwp)
        if isinstance(value, metrics.Unavailable):
            return value, inputs
        values.append(value)
    average = (sum(values, Decimal(0)) / len(values)).quantize(Decimal("0.1"), ROUND_HALF_UP)
    return average, inputs


def _availability(assets, days, ctx):
    available = sum((_sum(rows, "availHours") for _, rows in assets), Decimal(0))
    period = _hours(days) * len(assets)
    return metrics.availability_pct(available, period), {"available_hours": available, "period_hours": period}


def _capacity_factor(assets, days, ctx):
    energy = sum((_sum(rows, "actualMwh") for _, rows in assets), Decimal(0))
    capacity = sum((Decimal(str(a["capacityMw"])) for a, _ in assets), Decimal(0))
    period = _hours(days)
    return (metrics.capacity_factor_pct(energy, capacity, period),
            {"energy_mwh": energy, "capacity_mw": capacity, "period_hours": period})


def _ppa_delivery(assets, days, ctx):
    share = ctx["ppa_share"]
    delivered = sum((_sum(rows, "actualMwh") for _, rows in assets), Decimal(0)) * share
    contracted = sum((_sum(rows, "expectedMwh") for _, rows in assets), Decimal(0)) * share
    return (metrics.ppa_delivery_pct(delivered, contracted),
            {"delivered_mwh": delivered, "contracted_mwh": contracted, "ppa_share": share})


def _realised_price(assets, days, ctx):
    intervals = []
    for day in days:
        mwh = sum((Decimal(r["actualMwh"]) for _, rows in assets for r in rows if r["date"] == day), Decimal(0))
        intervals.append((mwh, ctx["prices"][day]))
    energy = sum((mwh for mwh, _ in intervals), Decimal(0))
    return metrics.realised_price_eur_mwh(intervals), {"energy_mwh": energy, "days": len(days)}


def _merchant_exposure(assets, days, ctx):
    merchant = sum((_sum(rows, "actualMwh") for _, rows in assets), Decimal(0)) * (1 - ctx["ppa_share"])
    return (metrics.merchant_exposure_eur(merchant, PRICE_MOVE_EUR_MWH),
            {"merchant_mwh": merchant, "price_move_eur_mwh": PRICE_MOVE_EUR_MWH})


def _downtime(assets, days, ctx):
    statuses = []
    for _, rows in assets:
        for r in rows:
            out = int(r["outageHours"])
            statuses += ["OUTAGE"] * out + ["OK"] * (24 - out)
    return metrics.downtime_hours(statuses, "1"), {"hours_checked": len(statuses)}


def _energy_loss(assets, days, ctx):
    expected = sum((_sum(rows, "expectedMwh") for _, rows in assets), Decimal(0))
    actual = sum((_sum(rows, "actualMwh") for _, rows in assets), Decimal(0))
    return metrics.energy_loss_mwh(expected, actual), {"expected_mwh": expected, "actual_mwh": actual}


def _incident_resolution(assets, days, ctx):
    return metrics.incident_resolution_hours([]), {}


def _bess_availability(assets, days, ctx):
    (_, rows), = assets
    available, period = _sum(rows, "availHours"), _hours(days)
    return metrics.bess_availability_pct(available, period), {"available_hours": available, "period_hours": period}


def _bess_round_trip(assets, days, ctx):
    (_, rows), = assets
    discharged, charged = _sum(rows, "dischargedMwh"), _sum(rows, "chargedMwh")
    return (metrics.bess_round_trip_efficiency_pct(discharged, charged),
            {"discharged_mwh": discharged, "charged_mwh": charged})


def _bess_cycle_utilisation(assets, days, ctx):
    (_, rows), = assets
    average = _sum(rows, "throughputMwh") / len(rows)
    usable = Decimal(rows[0]["usableMwh"])
    return (metrics.bess_cycle_utilisation_pct(average, usable),
            {"average_daily_throughput_mwh": average, "usable_mwh": usable})


# kpi -> (title, unit, asset kind, needs, function)
KPIS = {
    "actual_vs_expected": ("Actual vs expected energy", "%", "pv", "actual and expected MWh", _actual_vs_expected),
    "performance_ratio": ("Performance ratio", "%", "pv", "actual kWh, POA irradiation, nameplate kWp",
                          _performance_ratio),
    "availability": ("Availability", "%", "pv", "available hours and period hours", _availability),
    "capacity_factor": ("Capacity factor", "%", "pv", "actual MWh, capacity MW, period hours", _capacity_factor),
    "ppa_delivery": ("PPA delivery (PPA = 50 % of expected, a demo assumption)", "%", "pv",
                     "delivered and contracted MWh", _ppa_delivery),
    "realised_price": ("Realised price", "EUR/MWh", "pv", "daily MWh and daily price", _realised_price),
    "merchant_exposure": ("Merchant exposure to a 10 EUR/MWh price move (a sensitivity, not a forecast)", "EUR",
                          "pv", "merchant MWh and a price move", _merchant_exposure),
    "downtime": ("Downtime", "h", "pv", "hourly outage status", _downtime),
    "energy_loss": ("Energy loss", "MWh", "pv", "expected and actual MWh", _energy_loss),
    "incident_resolution": ("Incident resolution time", "h", "pv", "ticket open-to-close hours (none loaded)",
                            _incident_resolution),
    "bess_availability": ("Battery availability", "%", "bess", "available hours and period hours",
                          _bess_availability),
    "bess_round_trip": ("Battery round-trip efficiency", "%", "bess", "discharged and charged MWh", _bess_round_trip),
    "bess_cycle_utilisation": ("Battery cycle utilisation", "%", "bess", "average daily throughput and usable MWh",
                               _bess_cycle_utilisation),
}


class _Tools:
    def __init__(self, portfolio):
        self.p = portfolio
        self.assets = {a["id"]: a for a in portfolio["assets"]}
        self.ctx = {"ppa_share": Decimal(str(portfolio["ppa"]["shareOfExpected"])),
                    "prices": {r["date"]: r["meanPrice"] for r in portfolio["prices"]}}
        self.charts = 0

    # --- checks ---

    def _days(self, start, end):
        start = self.p["period"]["start"] if start is None else start
        end = self.p["period"]["end"] if end is None else end
        for value in (start, end):
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ToolError(f"date {value!r} must be YYYY-MM-DD")
            try:
                date.fromisoformat(value)
            except ValueError:
                raise ToolError(f"date {value!r} does not exist") from None
            if not JUNE_START <= value <= JUNE_END:
                raise ToolError(f"date {value} is outside June 2026; use {JUNE_START} to {JUNE_END}")
        if start > end:
            raise ToolError(f"start {start} is after end {end}")
        days = [d for d in self.p["days"] if start <= d <= end]
        if not days:
            raise ToolError(f"no data from {start} to {end}")
        return days

    def _assets(self, asset, kind):
        """The assets of `kind` behind `asset`. For a battery KPI, portfolio means the battery."""
        if asset not in ASSETS:
            raise ToolError(f"unknown asset {asset!r}; use one of {', '.join(ASSETS)}")
        if asset == "portfolio":
            found = [a for a in self.assets.values() if a["kind"] == kind]
        else:
            found = [self.assets[asset]] if asset in self.assets and self.assets[asset]["kind"] == kind else []
        if not found:
            raise ToolError(f"asset {asset!r} has no {'PV' if kind == 'pv' else 'battery'} data")
        return found

    def _kpi(self, kpi):
        if kpi not in KPIS:
            raise ToolError(f"unknown kpi {kpi!r}; call list_kpis for the 13 names")
        return KPIS[kpi]

    def _row(self, kpi, asset, days):
        title, unit, kind, _, fn = self._kpi(kpi)
        chosen = [(a, [r for r in a["daily"] if r["date"] in days]) for a in self._assets(asset, kind)]
        result, inputs = fn(chosen, days, self.ctx)
        unavailable = result.reason if isinstance(result, metrics.Unavailable) else None
        return {"kpi": kpi, "title": title, "asset": asset, "start": days[0], "end": days[-1],
                "value": None if unavailable is not None else str(result), "unit": unit, "unavailable": unavailable,
                "inputs": {k: str(v) for k, v in inputs.items()}}

    # --- the nine tools ---

    def list_assets(self):
        return {"label": self.p["label"],
                "assets": [{"id": a["id"], "name": a["name"], "kind": a["kind"],
                            "capacity_mw": str(a["capacityMw"])} for a in self.p["assets"]]}

    def list_kpis(self):
        return [{"kpi": k, "title": t, "unit": u, "needs": n} for k, (t, u, _, n, _) in KPIS.items()]

    def get_kpi(self, kpi, asset="portfolio", start=None, end=None):
        self._kpi(kpi)
        return self._row(kpi, asset, self._days(start, end))

    def compare_kpi(self, kpi, by, asset="portfolio", start=None, end=None):
        _, _, kind, _, _ = self._kpi(kpi)
        days = self._days(start, end)
        if by == "asset":
            rows = [self._row(kpi, a["id"], days) for a in self._assets("portfolio", kind)]
        elif by == "week":
            rows = [self._row(kpi, asset, days[i:i + 7]) for i in range(0, len(days), 7)]
        else:
            raise ToolError("by must be 'asset' or 'week'")
        return {"kpi": kpi, "by": by, "rows": rows}

    def get_series(self, metric, asset="portfolio", start=None, end=None):
        if metric not in METRICS:
            raise ToolError(f"unknown metric {metric!r}; use one of {', '.join(METRICS)}")
        kind, field, unit = METRICS[metric]
        if asset not in ASSETS:
            raise ToolError(f"unknown asset {asset!r}; use one of {', '.join(ASSETS)}")
        days = self._days(start, end)
        if kind == "price":
            points = [{"date": d, "value": self.ctx["prices"][d]} for d in days]
        else:
            if asset == "battery" and metric == "availability_hours":
                kind = "bess"
            chosen = self._assets(asset, kind)
            points = [{"date": d, "value": str(sum((Decimal(r[field]) for a in chosen for r in a["daily"]
                                                    if r["date"] == d), Decimal(0)))} for d in days]
        return {"metric": metric, "unit": unit, "start": days[0], "end": days[-1], "points": points}

    def get_prices(self, start=None, end=None):
        days = self._days(start, end)
        prices = self.ctx["prices"]
        return {"start": days[0], "end": days[-1], "unit": "EUR/MWh",
                "points": [{"date": d, "value": prices[d], "negative": Decimal(prices[d]) < 0} for d in days]}

    def get_events(self, asset="portfolio", start=None, end=None):
        days = self._days(start, end)
        if asset not in ASSETS:
            raise ToolError(f"unknown asset {asset!r}; use one of {', '.join(ASSETS)}")
        parks = [] if asset == "battery" else self._assets(asset, "pv")
        events = []
        for park in parks:
            for r in park["daily"]:
                if r["date"] not in days:
                    continue
                if Decimal(r["outageHours"]) > 0:
                    events.append({"date": r["date"], "asset": park["id"], "kind": "outage", "value": r["outageHours"]})
                if Decimal(r["curtailedMwh"]) > 0:
                    events.append({"date": r["date"], "asset": park["id"], "kind": "curtailment",
                                   "value": r["curtailedMwh"]})
        events.sort(key=lambda e: (e["date"], e["asset"], e["kind"]))
        return {"start": days[0], "end": days[-1], "events": events}

    def make_chart(self, kind, title, series):
        if kind not in CHART_KINDS:
            raise ToolError(f"kind must be one of {', '.join(CHART_KINDS)}")
        if not isinstance(title, str) or not isinstance(series, list):
            raise ToolError("title must be a string and series a list")
        clean = []
        for s in series:
            if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not isinstance(s.get("points"), list):
                raise ToolError("each series needs a name and a list of points")
            points = []
            for p in s["points"]:
                if not isinstance(p, dict) or not isinstance(p.get("x"), str) or not isinstance(p.get("y"), str):
                    raise ToolError("each point needs x and y as strings; copy y from a tool result")
                points.append({"x": p["x"], "y": p["y"]})
            clean.append({"name": s["name"], "points": points})
        self.charts += 1
        return {"id": f"chart_{self.charts}", "kind": kind, "title": title, "series": clean}

    def propose_action(self, action, asset, reason):
        if action not in ACTIONS:
            raise ToolError(f"action must be one of {', '.join(ACTIONS)}")
        if asset not in ASSETS:
            raise ToolError(f"unknown asset {asset!r}; use one of {', '.join(ASSETS)}")
        if not isinstance(reason, str) or not reason.strip():
            raise ToolError("reason must say which tool values justify the action")
        return {"id": f"prop_{secrets.token_hex(6)}", "action": action, "asset": asset, "reason": reason,
                "status": "pending"}


def _date(what):
    return {"type": "string", "description": f"{what} day, YYYY-MM-DD inside June 2026. Default: whole month."}


ASSET_PARAM = {"type": "string", "enum": ASSETS, "description": "Default portfolio."}
PERIOD = {"start": _date("First"), "end": _date("Last")}

SPECS = [
    ("list_assets", "Use to see which parks and the battery exist and their capacity in MW.", {}, []),
    ("list_kpis", "Use to see the 13 KPI names, their units and what each needs, when unsure which KPI fits.",
     {}, []),
    ("get_kpi", "Use for one KPI value for one asset or the portfolio over a period. Unavailable values come "
                "with a reason.",
     {"kpi": {"type": "string", "enum": list(KPIS)}, "asset": ASSET_PARAM, **PERIOD}, ["kpi"]),
    ("compare_kpi", "Use to rank assets (by=asset) or see a KPI change week by week (by=week).",
     {"kpi": {"type": "string", "enum": list(KPIS)}, "by": {"type": "string", "enum": ["asset", "week"]},
      "asset": ASSET_PARAM, **PERIOD}, ["kpi", "by"]),
    ("get_series", "Use for a daily curve: energy, availability, outage or curtailment, price, battery charge.",
     {"metric": {"type": "string", "enum": list(METRICS)}, "asset": ASSET_PARAM, **PERIOD}, ["metric"]),
    ("get_prices", "Use for daily mean day-ahead prices and which days were negative.", PERIOD, []),
    ("get_events", "Use to list outage and curtailment days for an asset.", {"asset": ASSET_PARAM, **PERIOD}, []),
    ("make_chart", "Use at most once, to chart values you already have. Every y is a string copied from a tool "
                   "result.",
     {"kind": {"type": "string", "enum": CHART_KINDS}, "title": {"type": "string"},
      "series": {"type": "array", "items": {"type": "object", "required": ["name", "points"], "properties": {
          "name": {"type": "string"},
          "points": {"type": "array", "items": {"type": "object", "required": ["x", "y"], "properties": {
              "x": {"type": "string"}, "y": {"type": "string"}}}}}}}},
     ["kind", "title", "series"]),
    ("propose_action", "Use only when tool values clearly justify an action. It records a proposal for a person "
                       "to approve; it runs nothing.",
     {"action": {"type": "string", "enum": ACTIONS}, "asset": ASSET_PARAM,
      "reason": {"type": "string", "description": "The tool values that justify it."}},
     ["action", "asset", "reason"]),
]


def build_registry(portfolio=None):
    """The nine tools over `portfolio` (default: the synthetic portfolio). One registry per question."""
    tools = _Tools(portfolio if portfolio is not None else build())
    registry = ToolRegistry()
    for name, description, properties, required in SPECS:
        registry.register(name, getattr(tools, name), description,
                          {"type": "object", "properties": properties, "required": required})
    return registry
