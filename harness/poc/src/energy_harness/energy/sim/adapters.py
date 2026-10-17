"""Adapters that give the simulator the same interfaces as the live data sources,
so the agent tools run unchanged on simulated data."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from statistics import fmean

from ...tools import ToolError
from ..parks import Park
from ..sources import FORECAST_AHEAD_DAYS, PricePoint, WeatherHour
from .simulator import ProductionSample, Simulator

PRICE_PUBLICATION_HOUR_UTC = 11  # ~13:00 CEST / 12:00 CET


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time(), timezone.utc)


class SimulatedWeather:
    """Replaces OpenMeteo. Forecasts are 'perfect': they equal the simulated actuals."""

    name = "SIMULATED weather"

    def __init__(self, sim: Simulator) -> None:
        self.sim = sim

    def hourly(self, latitude, longitude, start: date, end: date, tilt=None, azimuth=None) -> list[WeatherHour]:
        today = self.sim.today()
        if end < start:
            raise ToolError("end date is before start date")
        if end > today + timedelta(days=FORECAST_AHEAD_DAYS):
            raise ToolError(f"forecasts only reach {FORECAST_AHEAD_DAYS} days ahead (until {today + timedelta(days=FORECAST_AHEAD_DAYS)})")
        if start < today - timedelta(days=self.sim.scenario.history_days):
            raise ToolError(f"simulated weather only goes back {self.sim.scenario.history_days} days")

        # Match Open-Meteo: value at hour T is the mean over the preceding hour.
        samples = self.sim.weather(latitude, longitude, _midnight(start) - timedelta(hours=1), _midnight(end) + timedelta(hours=23), tilt, azimuth)
        hours = []
        for i in range(0, len(samples), 4):
            block = samples[i : i + 4]
            hours.append(
                WeatherHour(
                    time=block[0].time + timedelta(hours=1),
                    ghi_w_m2=round(fmean(s.ghi_w_m2 for s in block), 1),
                    poa_w_m2=None if block[0].poa_w_m2 is None else round(fmean(s.poa_w_m2 for s in block), 1),
                    temp_c=round(fmean(s.temp_c for s in block), 1),
                    cloud_pct=round(fmean(s.cloud_pct for s in block), 0),
                )
            )
        return hours


class SimulatedPrices:
    """Replaces EnergyCharts. Tomorrow's prices appear after the daily auction (~11:00 UTC)."""

    name = "SIMULATED day-ahead market"

    def __init__(self, sim: Simulator) -> None:
        self.sim = sim

    def day_ahead(self, bidding_zone: str, start: date, end: date) -> tuple[list[PricePoint], str]:
        now = self.sim.now()
        last_published = now.date() + timedelta(days=1 if now.hour >= PRICE_PUBLICATION_HOUR_UTC else 0)
        oldest = now.date() - timedelta(days=self.sim.scenario.history_days)
        start, end = max(start, oldest), min(end, last_published)
        if start > end:
            return [], "EUR / MWh"
        return self.sim.prices(bidding_zone, start, end), "EUR / MWh"


class SimulatedMetered:
    """Simulated monitoring/SCADA system: metered 15-minute production up to 'now'."""

    name = "SIMULATED SCADA"

    def __init__(self, sim: Simulator) -> None:
        self.sim = sim

    def production(self, park: Park, start: date, end: date) -> list[ProductionSample]:
        now = self.sim.now()
        if start > now.date():
            raise ToolError(f"no metered data for future dates (today is {now.date()}); use estimate_pv_production for forecasts")
        oldest = now.date() - timedelta(days=self.sim.scenario.history_days)
        if start < oldest:
            raise ToolError(f"metered data only goes back to {oldest}")
        stop = min(_midnight(end + timedelta(days=1)), now.replace(minute=now.minute - now.minute % 15, second=0, microsecond=0))
        return self.sim.production(park, _midnight(start), stop)
