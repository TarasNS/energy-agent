"""The nine tools the agent may call, over the synthetic portfolio (harness/dataset.py).

Every KPI goes through mcp/kpi-solar (kpi_solar.metrics). The sums and the rounding mirror
tools/kpi-lab/engine.js, so the numbers match the chat that shipped before this port.
Money and energy cross the tool boundary as strings. No tool approves anything.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Callable, Literal

from pydantic import Field

from harness.registry import ToolError, ToolRegistry, tool
from kpi_solar import metrics as K
from kpi_solar.metrics import Unavailable

ChartKind = Literal["line", "bar", "area", "table"]
ActionName = Literal["enable_negative_price_curtailment", "schedule_inspection", "review_ppa_volume"]
MetricName = Literal[
    "actual_mwh", "expected_mwh", "availability_hours", "outage_hours",
    "curtailed_mwh", "price_eur_mwh", "bess_charged_mwh", "bess_discharged_mwh",
]
CompareBy = Literal["asset", "week"]


def _fixed(value: float | int, places: int) -> str:
    """Format like JavaScript toFixed: half away from zero, on the exact binary value."""
    quantum = Decimal(1).scaleb(-places)
    return format(Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP), "f")


def _rows(asset: dict, days: list[str]) -> list[dict]:
    wanted = set(days)
    return [row for row in asset["daily"] if row["date"] in wanted]


def _total(assets: list[dict], days: list[str], key: str) -> float:
    # Same order as engine.js: per asset, then per day, starting from 0.
    return sum(sum(row[key] for row in _rows(a, days)) for a in assets)


# ── KPI computations: (assets, days, data) -> (Decimal | Unavailable, inputs) ──


def _actual_vs_expected(parks, days, data):
    a, e = _fixed(_total(parks, days, "actualMwh"), 3), _fixed(_total(parks, days, "expectedMwh"), 3)
    return K.actual_vs_expected_pct(a, e), {"actual_mwh": a, "expected_mwh": e}


def _performance_ratio(parks, days, data):
    inputs, values = {}, []
    for park in parks:
        e = _total([park], days, "actualMwh") * 1000  # kWh
        h = sum(row["poaKwhM2"] for row in _rows(park, days))  # kWh/m2 over the period
        r = K.performance_ratio_pct(_fixed(e, 1), _fixed(h, 2), str(park["nameplateKwp"]))
        inputs[park["id"]] = "unavailable" if isinstance(r, Unavailable) else format(r, "f") + " %"
        if not isinstance(r, Unavailable):
            values.append(r)
    if not values:
        return Unavailable("no park has all inputs"), inputs
    average = sum(values) / len(values)
    inputs["basis"] = "simple average of the park ratios"
    return average.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), inputs


def _availability(parks, days, data):
    available = sum(sum(row["availHours"] for row in _rows(p, days)) for p in parks)
    period = len(days) * 24 * len(parks)
    return K.availability_pct(str(available), str(period)), {
        "available_hours": str(available), "period_hours": str(period), "parks": str(len(parks)),
    }


def _capacity_factor(parks, days, data):
    mwh = _fixed(_total(parks, days, "actualMwh"), 3)
    capacity = sum(p["capacityMw"] for p in parks)
    hours = len(days) * 24
    return K.capacity_factor_pct(mwh, str(capacity), str(hours)), {
        "energy_mwh": mwh, "capacity_mw": str(capacity), "period_hours": str(hours),
    }


def _ppa_delivery(parks, days, data):
    share = data["ppa"]["shareOfExpected"]
    delivered = _fixed(_total(parks, days, "actualMwh") * share, 3)
    contracted = _fixed(_total(parks, days, "expectedMwh") * share, 3)
    return K.ppa_delivery_pct(delivered, contracted), {
        "delivered_mwh": delivered,
        "contracted_mwh": contracted,
        "contract_share": f"{share * 100:g} % of expected output (demo ASSUMPTION)",
    }


def _realised_price(parks, days, data):
    prices = {p["date"]: p["meanPrice"] for p in data["prices"]}
    intervals = []
    for day in days:
        mwh = sum(row["actualMwh"] for p in parks for row in _rows(p, [day]))
        intervals.append((_fixed(mwh, 3), _fixed(prices[day], 2)))
    return K.realised_price_eur_mwh(intervals), {"daily_intervals": str(len(intervals)), "basis": "daily, not 15-minute"}


def _merchant_exposure(parks, days, data):
    share = data["ppa"]["shareOfExpected"]
    merchant = _fixed(_total(parks, days, "actualMwh") * (1 - share), 3)
    move = "10"  # EUR/MWh sensitivity: an input for the demo, not a forecast
    return K.merchant_exposure_eur(merchant, move), {
        "merchant_mwh": merchant, "price_move_eur_mwh": move, "note": "sensitivity, not a forecast",
    }


def _downtime(parks, days, data):
    statuses = []
    for p in parks:
        for row in _rows(p, days):
            statuses.extend("OUTAGE" if hour < row["outageHours"] else "OK" for hour in range(24))
    return K.downtime_hours(statuses, "1"), {"hourly_intervals": str(len(statuses)), "interval_hours": "1"}


def _energy_loss(parks, days, data):
    expected = _fixed(_total(parks, days, "expectedMwh"), 3)
    actual = _fixed(_total(parks, days, "actualMwh"), 3)
    return K.energy_loss_mwh(expected, actual), {"expected_mwh": expected, "actual_mwh": actual}


def _incident_resolution(parks, days, data):
    return K.incident_resolution_hours([]), {"tickets_loaded": "0"}


def _bess_availability(parks, days, data):
    battery = parks[0]
    available = sum(row["availHours"] for row in _rows(battery, days))
    hours = len(days) * 24
    return K.bess_availability_pct(str(available), str(hours)), {
        "available_hours": str(available), "period_hours": str(hours),
    }


def _bess_round_trip(parks, days, data):
    battery = parks[0]
    charged = _fixed(sum(row["chargedMwh"] for row in _rows(battery, days)), 3)
    discharged = _fixed(sum(row["dischargedMwh"] for row in _rows(battery, days)), 3)
    return K.bess_round_trip_efficiency_pct(discharged, charged), {
        "charged_mwh": charged, "discharged_mwh": discharged,
    }


def _bess_cycle_utilisation(parks, days, data):
    battery = parks[0]
    rows = _rows(battery, days)
    average = _fixed(sum(row["throughputMwh"] for row in rows) / len(days), 3)
    usable = rows[0]["usableMwh"]
    return K.bess_cycle_utilisation_pct(average, str(usable)), {
        "average_daily_throughput_mwh": average, "usable_mwh": str(usable),
    }


@dataclass(frozen=True)
class _Kpi:
    title: str
    unit: str
    scope: str  # "pv" or "bess"
    needs: str
    compute: Callable


KPIS: dict[str, _Kpi] = {
    "actual_vs_expected": _Kpi("Actual vs expected generation", "%", "pv", "actual and expected MWh", _actual_vs_expected),
    "performance_ratio": _Kpi("Performance ratio", "%", "pv", "POA irradiation, nameplate kWp, actual kWh", _performance_ratio),
    "availability": _Kpi("Availability", "%", "pv", "available hours per park", _availability),
    "capacity_factor": _Kpi("Capacity factor", "%", "pv", "actual MWh and capacity MW", _capacity_factor),
    "ppa_delivery": _Kpi("PPA delivery vs contract", "%", "pv", "actual and expected MWh, PPA share (demo assumption)", _ppa_delivery),
    "realised_price": _Kpi("Realised (capture) price", "EUR/MWh", "pv", "daily PV MWh and day-ahead price", _realised_price),
    "merchant_exposure": _Kpi("Merchant price exposure", "EUR", "pv", "merchant MWh and a 10 EUR/MWh move (sensitivity)", _merchant_exposure),
    "downtime": _Kpi("Downtime", "h", "pv", "hourly outage status per park", _downtime),
    "energy_loss": _Kpi("Energy losses", "MWh", "pv", "expected and actual MWh", _energy_loss),
    "incident_resolution": _Kpi("Incident resolution (median)", "h", "pv", "ticket open and close times (not loaded)", _incident_resolution),
    "bess_availability": _Kpi("BESS availability", "%", "bess", "battery available hours", _bess_availability),
    "bess_round_trip": _Kpi("Round-trip efficiency", "%", "bess", "battery charged and discharged MWh", _bess_round_trip),
    "bess_cycle_utilisation": _Kpi("Cycle utilisation", "%", "bess", "battery throughput and usable MWh", _bess_cycle_utilisation),
}

# metric -> (unit, scope, daily key, decimals)
METRICS: dict[str, tuple[str, str, str, int]] = {
    "actual_mwh": ("MWh", "pv", "actualMwh", 3),
    "expected_mwh": ("MWh", "pv", "expectedMwh", 3),
    "availability_hours": ("h", "any", "availHours", 0),
    "outage_hours": ("h", "pv", "outageHours", 0),
    "curtailed_mwh": ("MWh", "pv", "curtailedMwh", 3),
    "bess_charged_mwh": ("MWh", "bess", "chargedMwh", 3),
    "bess_discharged_mwh": ("MWh", "bess", "dischargedMwh", 3),
}


def _period(data: dict, start: str | None, end: str | None) -> tuple[list[str], str, str]:
    days = data["days"]
    first, last = days[0], days[-1]
    s, e = start or first, end or last
    for label, value in (("start", s), ("end", e)):
        if value not in days:
            raise ToolError(f"{label} must be a day in the period, {first} to {last}, written YYYY-MM-DD")
    if s > e:
        raise ToolError("start is after end")
    return [d for d in days if s <= d <= e], s, e


def _assets_for(data: dict, scope: str, asset: str) -> list[dict]:
    if asset == "portfolio":
        kind = "bess" if scope == "bess" else "pv"
        return [a for a in data["assets"] if a["kind"] == kind]
    match = [a for a in data["assets"] if a["id"] == asset]
    if not match:
        raise ToolError(f"unknown asset '{asset}'. Use one of: portfolio, {', '.join(a['id'] for a in data['assets'])}.")
    if scope != "any" and match[0]["kind"] != scope:
        raise ToolError(f"'{asset}' has no {scope} data for this. Use 'portfolio' or another asset.")
    return match


def _daily_series(data: dict, metric: str, asset: str, start: str | None, end: str | None) -> dict:
    days, s, e = _period(data, start, end)
    if metric == "price_eur_mwh":
        prices = {p["date"]: p["meanPrice"] for p in data["prices"]}
        points = [{"date": d, "value": _fixed(prices[d], 2)} for d in days]
        return {"metric": metric, "unit": "EUR/MWh", "start": s, "end": e, "points": points}
    unit, scope, key, places = METRICS[metric]
    assets = _assets_for(data, scope, asset)
    points = [
        {"date": d, "value": _fixed(sum(row[key] for a in assets for row in _rows(a, [d])), places)}
        for d in days
    ]
    return {"metric": metric, "unit": unit, "asset": asset, "start": s, "end": e, "points": points}


def _kpi_row(data: dict, kpi: str, asset: str, start: str | None, end: str | None) -> dict:
    if kpi not in KPIS:
        raise ToolError(f"unknown kpi '{kpi}'. Use one of: {', '.join(KPIS)}.")
    spec = KPIS[kpi]
    assets = _assets_for(data, spec.scope, asset)
    days, s, e = _period(data, start, end)
    result, inputs = spec.compute(assets, days, data)
    unavailable = isinstance(result, Unavailable)
    return {
        "kpi": kpi,
        "title": spec.title,
        "asset": asset,
        "start": s,
        "end": e,
        "value": None if unavailable else format(result, "f"),
        "unit": spec.unit,
        "unavailable": result.reason if unavailable else None,
        "inputs": inputs,
    }


def build_energy_tools(data: dict, proposals: Callable[[str, str, str], str]) -> ToolRegistry:
    """The nine tools over one dataset. `proposals(action, asset, reason)` records a proposal and returns its id."""
    chart_ids = itertools.count(1)
    asset_ids = [a["id"] for a in data["assets"]]

    def _compare_rows(kpi: str, by: str) -> list[dict]:
        if kpi not in KPIS:
            raise ToolError(f"unknown kpi '{kpi}'. Use one of: {', '.join(KPIS)}.")
        if by == "asset":
            names = ["battery"] if KPIS[kpi].scope == "bess" else [a["id"] for a in data["assets"] if a["kind"] == "pv"]
            return [_kpi_row(data, kpi, name, None, None) for name in names]
        days = data["days"]
        return [
            _kpi_row(data, kpi, "portfolio", block[0], block[-1])
            for block in (days[i:i + 7] for i in range(0, len(days), 7))
        ]

    @tool
    def list_assets() -> list[dict]:
        """List the parks and the battery in the portfolio. Use it when the question does not name an asset."""
        return [
            {"id": a["id"], "name": a["name"], "kind": a["kind"], "capacity_mw": str(a["capacityMw"])}
            for a in data["assets"]
        ]

    @tool
    def list_kpis() -> list[dict]:
        """List the KPI ids with titles, units and inputs. Use it to find the right kpi id before get_kpi or compare_kpi."""
        return [{"kpi": k, "title": s.title, "unit": s.unit, "needs": s.needs} for k, s in KPIS.items()]

    @tool
    def get_kpi(
        kpi: Annotated[str, Field(description="A kpi id from list_kpis, for example availability.")],
        asset: Annotated[str, Field(description="'portfolio' (default), 'north', 'south' or 'battery'.")] = "portfolio",
        start: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Default: first day of the period.")] = None,
        end: Annotated[str | None, Field(description="Last day, YYYY-MM-DD. Default: last day of the period.")] = None,
    ) -> dict:
        """Calculate one KPI for the portfolio or one asset over a date range. Use it for any single KPI value."""
        return _kpi_row(data, kpi, asset, start, end)

    @tool
    def compare_kpi(
        kpi: Annotated[str, Field(description="A kpi id from list_kpis.")],
        by: Annotated[CompareBy, Field(description="'asset' compares the parks or the battery; 'week' splits the period into 7-day blocks.")],
    ) -> dict:
        """Compare one KPI across the assets or across weeks of the period. Use it for 'which park' or 'by week' questions."""
        rows = _compare_rows(kpi, by)
        return {"kpi": kpi, "by": by, "rows": rows, "chart_hint": f'make_chart(kind="bar", kpi="{kpi}", by="{by}", title=...)'}

    @tool
    def get_series(
        metric: Annotated[MetricName, Field(description="The daily series to read.")],
        asset: Annotated[str, Field(description="'portfolio' (default), 'north', 'south' or 'battery'. Ignored for price_eur_mwh.")] = "portfolio",
        start: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Default: first day of the period.")] = None,
        end: Annotated[str | None, Field(description="Last day, YYYY-MM-DD. Default: last day of the period.")] = None,
    ) -> dict:
        """Read a daily series, one point per day. Use it for trends and for values to feed make_chart."""
        return _daily_series(data, metric, asset, start, end)

    @tool
    def get_prices(
        start: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Default: first day of the period.")] = None,
        end: Annotated[str | None, Field(description="Last day, YYYY-MM-DD. Default: last day of the period.")] = None,
    ) -> dict:
        """List the daily mean day-ahead price and whether it was negative. Use it for any price question."""
        days, s, e = _period(data, start, end)
        wanted = set(days)
        points = [
            {"date": p["date"], "mean_eur_mwh": _fixed(p["meanPrice"], 2), "negative": p["meanPrice"] < 0}
            for p in data["prices"] if p["date"] in wanted
        ]
        return {"start": s, "end": e, "points": points}

    @tool
    def get_events(
        asset: Annotated[str, Field(description="'portfolio' (default), 'north', 'south' or 'battery'.")] = "portfolio",
        start: Annotated[str | None, Field(description="First day, YYYY-MM-DD. Default: first day of the period.")] = None,
        end: Annotated[str | None, Field(description="Last day, YYYY-MM-DD. Default: last day of the period.")] = None,
    ) -> dict:
        """List outage days and curtailment days in a date range. Use it to explain what happened on which day."""
        days, s, e = _period(data, start, end)
        events = []
        for a in _assets_for(data, "any", asset):
            for row in _rows(a, days):
                if row.get("outageHours", 0) > 0:
                    events.append({"date": row["date"], "asset": a["id"], "type": "outage", "hours": str(row["outageHours"])})
                if row.get("curtailedMwh", 0) > 0:
                    events.append({"date": row["date"], "asset": a["id"], "type": "curtailment", "mwh": _fixed(row["curtailedMwh"], 3)})
        events.sort(key=lambda ev: (ev["date"], ev["asset"]))
        return {"start": s, "end": e, "events": events}

    @tool
    def make_chart(
        kind: Annotated[ChartKind, Field(description="line for trends, bar for comparing parks or weeks, area for cumulative shape, table for exact values.")],
        title: Annotated[str, Field(description="Short chart title.")],
        metric: Annotated[MetricName | None, Field(description="A daily series to chart, the same ids as get_series. Use this or kpi.")] = None,
        kpi: Annotated[str | None, Field(description="A kpi id from list_kpis, charted across parks or weeks. Use this or metric.")] = None,
        by: Annotated[CompareBy, Field(description="With kpi: 'asset' (default) for one bar per park, 'week' for 7-day blocks.")] = "asset",
        kpis: Annotated[list[str] | None, Field(description="Several kpi ids for the portfolio, one row each. Use with kind='table' for headline questions.")] = None,
        assets: Annotated[list[str] | None, Field(description="With metric: one series per asset, 'portfolio' (default), 'north', 'south' or 'battery'.")] = None,
        start: Annotated[str | None, Field(description="With metric: first day, YYYY-MM-DD. Default: first day of the period.")] = None,
        end: Annotated[str | None, Field(description="With metric: last day, YYYY-MM-DD. Default: last day of the period.")] = None,
    ) -> dict:
        """Chart values straight from the calculator: a daily series (metric), one KPI across parks or weeks (kpi), or several portfolio KPIs (kpis). Pass ids, never numbers. Call it at most once per answer."""
        if sum(x is not None for x in (metric, kpi, kpis)) != 1:
            raise ToolError("pass exactly one of metric (a daily series), kpi (a KPI across parks or weeks) or kpis (several portfolio KPIs).")
        if kpis is not None:
            if not kpis or assets or start or end:
                raise ToolError("kpis needs at least one kpi id; assets, start and end apply to metric.")
            rows = [_kpi_row(data, k, "portfolio", None, None) for k in kpis]
            points = [{"x": f"{r['title']} ({r['unit']})", "y": r["value"]} for r in rows]
            return {"chart_id": f"chart-{next(chart_ids)}", "kind": kind, "title": title,
                    "series": [{"name": "Portfolio", "points": points}]}
        if kpi is not None:
            if assets or start or end:
                raise ToolError("with kpi, use by only; assets, start and end apply to metric.")
            rows = _compare_rows(kpi, by)
            points = [
                {"x": r["asset"] if by == "asset" else f"{r['start']} to {r['end']}", "y": r["value"]}
                for r in rows
            ]
            series = [{"name": rows[0]["unit"] if rows else "", "points": points}]
            return {"chart_id": f"chart-{next(chart_ids)}", "kind": kind, "title": title, "series": series}
        names = assets or ["portfolio"]
        for name in names:
            if name != "portfolio" and name not in asset_ids:
                raise ToolError(f"unknown asset '{name}'. Use one of: portfolio, {', '.join(asset_ids)}.")
        series = []
        for name in names:
            read = _daily_series(data, metric, name, start, end)
            series.append({
                "name": name if len(names) > 1 else read["unit"],
                "points": [{"x": p["date"], "y": p["value"]} for p in read["points"]],
            })
        return {"chart_id": f"chart-{next(chart_ids)}", "kind": kind, "title": title, "series": series}

    @tool
    def propose_action(
        action: Annotated[ActionName, Field(description="The action to propose.")],
        asset: Annotated[str, Field(description="'north', 'south' or 'battery'.")],
        reason: Annotated[str, Field(description="One sentence that cites the KPI values behind the proposal.")],
    ) -> dict:
        """Propose an action for a person to approve. Use it only when the data clearly justifies it; you cannot approve or run it."""
        if asset not in asset_ids:
            raise ToolError(f"unknown asset '{asset}'. Use one of: {', '.join(asset_ids)}.")
        return {"proposal_id": proposals(action, asset, reason), "status": "proposed"}

    return ToolRegistry([
        list_assets, list_kpis, get_kpi, compare_kpi, get_series,
        get_prices, get_events, make_chart, propose_action,
    ])
