"""Energy tools exposed to the agent.

Outputs are daily summaries, with hourly/interval detail only for short ranges,
to keep token use (and free-tier latency) down.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from statistics import fmean
from typing import Annotated, Callable
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field

from ..tools import Tool, ToolError, tool
from . import pv
from .parks import ParkRegistry
from .sources import EnergyCharts, OpenMeteo, WeatherHour, utc_today

MARKET_TZ = ZoneInfo("Europe/Berlin")  # day-ahead delivery days are CET/CEST for DK, SE, NO, DE, PL
MAX_RANGE_DAYS = 31
DETAIL_MAX_DAYS = 2

DateArg = Annotated[date | None, Field(description="ISO date YYYY-MM-DD; defaults to today (UTC)")]
ParkArg = Annotated[str, Field(description="Park id or name from list_parks")]


def build_energy_tools(
    parks: ParkRegistry,
    http: httpx.Client | None = None,
    today: Callable[[], date] | None = None,
    *,
    weather=None,
    prices=None,
    metered=None,
) -> list[Tool]:
    """Build the energy tools. Live sources (Open-Meteo, Energy-Charts) are used unless `weather`/`prices`
    are given; `get_metered_production` is only offered when a `metered` source is given."""
    today = today or utc_today
    if weather is None or prices is None:
        http = http or httpx.Client(headers={"User-Agent": "energy-agent-harness/0.1"})
    weather = weather or OpenMeteo(http, today=today)
    prices = prices or EnergyCharts(http)

    def date_range(start: date | None, end: date | None) -> tuple[date, date]:
        start = start or today()
        end = end or start
        if end < start:
            raise ToolError("end_date is before start_date")
        if (end - start).days + 1 > MAX_RANGE_DAYS:
            raise ToolError(f"range too long; max {MAX_RANGE_DAYS} days per call")
        return start, end

    @tool
    def list_parks() -> list[dict]:
        """List the PV parks the agent knows about, with location, DC/AC capacity, orientation and bidding zone."""
        return [p.model_dump(exclude_none=True) for p in parks.parks]

    @tool
    def get_irradiance_forecast(
        park: Annotated[str | None, Field(description="Park id or name; alternative to latitude/longitude")] = None,
        latitude: Annotated[float | None, Field(ge=-90, le=90)] = None,
        longitude: Annotated[float | None, Field(ge=-180, le=180)] = None,
        days: Annotated[int, Field(ge=1, le=16, description="Number of days from today")] = 3,
    ) -> dict:
        """Solar irradiance and weather forecast (Open-Meteo) for a park or a coordinate:
        daily GHI energy (kWh/m²), peak GHI, mean cloud cover and temperature; hourly detail for 1–2 days."""
        if park:
            site = parks.get(park)
            latitude, longitude, label = site.latitude, site.longitude, site.id
        elif latitude is not None and longitude is not None:
            label = f"{latitude:.3f},{longitude:.3f}"
        else:
            raise ToolError("give either park or both latitude and longitude")
        start = today()
        end = start + timedelta(days=days - 1)
        hours = weather.hourly(latitude, longitude, start, end)

        daily = []
        for day, rows in _group_by_day(hours):
            if not start <= day <= end:
                continue
            ghi = [r.ghi_w_m2 or 0.0 for r in rows]
            daily.append(
                {
                    "date": day.isoformat(),
                    "ghi_kwh_m2": round(sum(ghi) / 1000.0, 2),
                    "peak_ghi_w_m2": round(max(ghi), 0),
                    "mean_cloud_cover_pct": _mean(r.cloud_pct for r in rows),
                    "mean_temp_c": _mean(r.temp_c for r in rows),
                }
            )
        result: dict = {"location": label, "source": weather.name, "daily": daily}
        if days <= DETAIL_MAX_DAYS:
            result["hourly_utc"] = [
                {"time": r.time.strftime("%Y-%m-%d %H:%M"), "ghi_w_m2": r.ghi_w_m2, "cloud_pct": r.cloud_pct, "temp_c": r.temp_c}
                for r in hours
                if r.ghi_w_m2
            ]
        return result

    @tool
    def estimate_pv_production(park: ParkArg, start_date: DateArg = None, end_date: DateArg = None) -> dict:
        """Estimate a park's PV production (MWh per day, peak MW, capacity factor) from Open-Meteo irradiance
        and the park's capacity. Works for forecasts (up to 15 days ahead) and past dates. These are model
        estimates, not metered production."""
        site = parks.get(park)
        start, end = date_range(start_date, end_date)
        hours = weather.hourly(site.latitude, site.longitude, start, end, site.tilt, site.azimuth)
        use_poa = site.tilt is not None

        daily, detail = [], []
        for day, rows in _group_by_day(hours):
            if not start <= day <= end:
                continue
            power = [
                pv.ac_power_mw(site.capacity_mwp, r.poa_w_m2 if use_poa else r.ghi_w_m2, r.temp_c, site.ac_capacity_mw)
                for r in rows
            ]
            energy = sum(power)  # hourly mean MW × 1 h
            daily.append(
                {
                    "date": day.isoformat(),
                    "energy_mwh": round(energy, 1),
                    "peak_mw": round(max(power, default=0.0), 2),
                    "capacity_factor_pct": round(100 * energy / (site.capacity_mwp * 24), 1),
                }
            )
            detail += [{"hour_ending_utc": r.time.strftime("%Y-%m-%d %H:%M"), "mw": round(p, 2)} for r, p in zip(rows, power) if p > 0]

        result: dict = {
            "park": site.id,
            "capacity_mwp": site.capacity_mwp,
            "ac_capacity_mw": site.ac_capacity_mw,
            "method": f"estimate from {weather.name} {'tilted' if use_poa else 'horizontal'} irradiance, PR {pv.PERFORMANCE_RATIO}, temperature-derated",
            "daily": daily,
            "total_energy_mwh": round(sum(d["energy_mwh"] for d in daily), 1),
        }
        if (end - start).days + 1 <= DETAIL_MAX_DAYS:
            result["hourly"] = detail
        return result

    @tool
    def get_day_ahead_prices(
        bidding_zone: Annotated[str, Field(description="Bidding zone code, e.g. DK1, DK2, SE3, SE4, NO1, FI, DE-LU, PL, NL")],
        start_date: DateArg = None,
        end_date: DateArg = None,
    ) -> dict:
        """Day-ahead spot prices (EUR/MWh) for a bidding zone from Energy-Charts: daily mean/min/max, cheapest and
        most expensive interval, count of negative-price intervals; all intervals for a single day. Delivery days
        and interval times are in CET/CEST. Tomorrow's prices are published around 13:00 CET."""
        start, end = date_range(start_date, end_date)
        points, unit = prices.day_ahead(bidding_zone.strip().upper(), start, end)

        by_day: dict[date, list] = defaultdict(list)
        for point in points:
            local = point.time.astimezone(MARKET_TZ)
            if start <= local.date() <= end and point.eur_per_mwh is not None:
                by_day[local.date()].append((local, point.eur_per_mwh))
        if not by_day:
            raise ToolError(f"no prices for {bidding_zone} between {start} and {end} (not published yet, or unknown zone)")

        daily = []
        for day in sorted(by_day):
            rows = by_day[day]
            low, high = min(rows, key=lambda r: r[1]), max(rows, key=lambda r: r[1])
            resolution = int((rows[1][0] - rows[0][0]).total_seconds() // 60) if len(rows) > 1 else None
            daily.append(
                {
                    "date": day.isoformat(),
                    "mean": round(fmean(r[1] for r in rows), 2),
                    "min": round(low[1], 2),
                    "min_at": low[0].strftime("%H:%M"),
                    "max": round(high[1], 2),
                    "max_at": high[0].strftime("%H:%M"),
                    "negative_intervals": sum(1 for r in rows if r[1] < 0),
                    "intervals": len(rows),
                    "resolution_min": resolution,
                }
            )
        result: dict = {"bidding_zone": bidding_zone.upper(), "unit": unit, "timezone": "CET/CEST", "source": prices.name, "daily": daily}
        if start == end:
            result["prices"] = [[t.strftime("%H:%M"), round(p, 2)] for t, p in by_day[start]] if start in by_day else []
        return result

    @tool
    def get_metered_production(park: ParkArg, start_date: DateArg = None, end_date: DateArg = None) -> dict:
        """Measured production of a park from the monitoring system (15-minute meter data): per day the energy
        (MWh), peak MW, inverter availability (% of daylight), number of curtailed 15-min intervals and data
        completeness (%); hourly MWh for a single day. Today's data runs up to the current time. Compare with
        estimate_pv_production to spot underperformance that availability alone doesn't explain."""
        site = parks.get(park)
        start, end = date_range(start_date, end_date)
        samples = metered.production(site, start, end)
        if not samples:
            raise ToolError(f"no metered data for {site.id} between {start} and {end}")

        by_day: dict[date, list] = defaultdict(list)
        for s in samples:
            by_day[s.time.date()].append(s)
        daily, hourly = [], defaultdict(float)
        for day in sorted(by_day):
            rows = by_day[day]
            present = [s for s in rows if s.metered_mw is not None]
            daylight = [s for s in rows if s.expected_mw > 0]
            daily.append(
                {
                    "date": day.isoformat(),
                    "energy_mwh": round(sum(s.metered_mw for s in present) * 0.25, 1),
                    "peak_mw": round(max((s.metered_mw for s in present), default=0.0), 2),
                    "availability_pct": round(100 * fmean(s.availability for s in daylight), 1) if daylight else 100.0,
                    "curtailed_intervals": sum(s.curtailed for s in rows),
                    "data_completeness_pct": round(100 * len(present) / len(rows), 1),
                    "intervals": len(rows),
                }
            )
            for s in present:
                hourly[s.time.strftime("%Y-%m-%d %H:00")] += s.metered_mw * 0.25

        result: dict = {
            "park": site.id,
            "capacity_mwp": site.capacity_mwp,
            "source": metered.name,
            "data_until_utc": (samples[-1].time + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M"),
            "daily": daily,
            "total_energy_mwh": round(sum(d["energy_mwh"] for d in daily), 1),
        }
        if start == end:
            result["hourly_mwh_utc"] = {hour: round(mwh, 2) for hour, mwh in hourly.items() if mwh > 0}
        return result

    tools = [list_parks, get_irradiance_forecast, estimate_pv_production, get_day_ahead_prices]
    return tools + [get_metered_production] if metered is not None else tools


def _group_by_day(hours: list[WeatherHour]) -> list[tuple[date, list[WeatherHour]]]:
    """Group by the UTC day each hourly interval falls in. Open-Meteo irradiance at hour t is the mean over
    the preceding hour, so 00:00 belongs to the previous day and the last interval of the range (night) is cut."""
    groups: dict[date, list[WeatherHour]] = defaultdict(list)
    for row in hours:
        groups[(row.time - timedelta(hours=1)).date()].append(row)
    return sorted(groups.items())


def _mean(values) -> float | None:
    present = [v for v in values if v is not None]
    return round(fmean(present), 1) if present else None
