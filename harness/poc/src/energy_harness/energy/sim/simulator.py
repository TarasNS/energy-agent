"""The simulation engine: weather, prices and metered production at 15-minute resolution.

Every random draw is seeded by (scenario seed, what, where, which day), so a
given day always comes out the same no matter which date range is requested.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from ...tools import ToolError
from .. import pv
from ..parks import Park, ParkRegistry
from ..sources import PricePoint
from . import solar
from .scenario import Scenario

STEP = timedelta(minutes=15)
MARKET_TZ = ZoneInfo("Europe/Berlin")

# Representative location and price level (EUR/MWh) per bidding zone.
ZONES: dict[str, tuple[float, float, float]] = {
    "DK1": (56.2, 9.0, 82.0),
    "DK2": (55.5, 12.0, 88.0),
    "SE3": (59.0, 15.0, 48.0),
    "SE4": (56.0, 14.0, 70.0),
    "NO1": (60.0, 10.5, 45.0),
    "FI": (62.0, 25.0, 42.0),
    "DE-LU": (51.0, 10.0, 86.0),
    "NL": (52.2, 5.5, 84.0),
    "PL": (52.0, 19.0, 102.0),
}


@dataclass
class WeatherSample:
    time: datetime  # interval start, UTC
    ghi_w_m2: float
    poa_w_m2: float | None
    temp_c: float
    cloud_pct: float


@dataclass
class ProductionSample:
    time: datetime  # interval start, UTC
    expected_mw: float  # output with no incidents and no metering noise (ground truth, not shown to the agent)
    metered_mw: float | None  # None = data gap
    availability: float  # inverter availability 0..1
    curtailed: bool


class Simulator:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.parks = ParkRegistry(scenario.parks)
        self._cache: dict[tuple, list] = {}

    # --- clock -------------------------------------------------------------

    def now(self) -> datetime:
        return self.scenario.now or datetime.now(timezone.utc)

    def today(self) -> date:
        return self.now().date()

    # --- weather -------------------------------------------------------------

    def weather(
        self, lat: float, lon: float, start: datetime, end: datetime, tilt: float | None = None, azimuth: float | None = None
    ) -> list[WeatherSample]:
        """15-minute weather samples on [start, end)."""
        out = []
        t = _align(start)
        while t < end:
            csi = self._clear_sky_index(lat, lon, t.date())[_slot(t)]
            sin_el, sun_az = solar.sun_position(lat, lon, t + STEP / 2)
            ghi = solar.clear_sky_ghi(sin_el) * csi
            poa = solar.plane_of_array(ghi, sin_el, sun_az, tilt, azimuth or 0.0) if tilt is not None else None
            out.append(
                WeatherSample(
                    time=t,
                    ghi_w_m2=round(ghi, 1),
                    poa_w_m2=None if poa is None else round(poa, 1),
                    temp_c=round(self._temperature(lat, lon, t, csi), 1),
                    cloud_pct=round(min(100.0, max(0.0, (1.05 - csi) / 0.95 * 100)), 0),
                )
            )
            t += STEP
        return out

    def _clear_sky_index(self, lat: float, lon: float, day: date) -> list[float]:
        """96 clear-sky-index values (1 = cloudless) for one UTC day. Nearby parks share weather."""
        key = ("sky", round(lat), round(lon), day)
        if key not in self._cache:
            rng = self._rng(*key)
            regime = rng.choices([0.95, 0.65, 0.3], weights=_season_weights(day))[0]
            x, values = 0.0, []
            for _ in range(96):
                x = 0.85 * x + rng.gauss(0.0, 0.07)
                values.append(min(1.05, max(0.05, regime + x)))
            self._cache[key] = values
        return self._cache[key]

    def _temperature(self, lat: float, lon: float, t: datetime, csi: float) -> float:
        doy = t.timetuple().tm_yday
        seasonal = 8.5 - 8.5 * math.cos(2 * math.pi * (doy - 20) / 365) - 0.4 * (lat - 56)
        daily_offset = self._rng("temp", round(lat), round(lon), t.date()).uniform(-2.5, 2.5)
        solar_hour = t.hour + t.minute / 60 + lon / 15
        diurnal = (1.5 + 3.5 * csi) * math.sin(2 * math.pi * (solar_hour - 9) / 24)
        return seasonal + daily_offset + diurnal

    # --- prices ------------------------------------------------------------------

    def prices(self, zone: str, start: date, end: date) -> list[PricePoint]:
        """15-minute day-ahead prices for market (CET/CEST) days start..end."""
        points: list[PricePoint] = []
        day = start
        while day <= end:
            points += self._market_day_prices(zone.upper(), day)
            day += timedelta(days=1)
        return points

    def price_at(self, zone: str, t: datetime) -> float | None:
        day = t.astimezone(MARKET_TZ).date()
        for point in self._market_day_prices(zone.upper(), day):
            if point.time == t:
                return point.eur_per_mwh
        return None

    def _market_day_prices(self, zone: str, day: date) -> list[PricePoint]:
        key = ("price", zone, day)
        if key in self._cache:
            return self._cache[key]
        if zone not in ZONES:
            raise ToolError(f"unknown bidding zone '{zone}'. Simulated zones: {', '.join(ZONES)}")
        lat, lon, base = ZONES[zone]
        rng = self._rng(*key)
        weekend = day.weekday() >= 5
        level = base * rng.uniform(0.7, 1.3) * (0.85 if weekend else 1.0)
        depth = rng.uniform(0.5, 1.2) * (1.25 if weekend else 1.0)  # how hard solar pushes midday prices down

        points = []
        t = datetime.combine(day, time(), MARKET_TZ).astimezone(timezone.utc)
        stop = datetime.combine(day + timedelta(days=1), time(), MARKET_TZ).astimezone(timezone.utc)
        while t < stop:
            h = t.astimezone(MARKET_TZ).hour + t.astimezone(MARKET_TZ).minute / 60
            demand = 0.72 + 0.28 * _bump(h, 8.0, 1.8) + 0.48 * _bump(h, 18.5, 2.0)
            sin_el, _ = solar.sun_position(lat, lon, t + STEP / 2)
            solar_share = solar.clear_sky_ghi(sin_el) * self._clear_sky_index(lat, lon, t.date())[_slot(t)] / 1000
            price = level * (demand - depth * solar_share) + rng.gauss(0.0, 0.03 * base)
            for event in self.scenario.events:
                if event.type == "price" and event.zone == zone and event.active(t):
                    price = event.price
            points.append(PricePoint(t, round(price, 2)))
            t += STEP
        self._cache[key] = points
        return points

    # --- production -------------------------------------------------------------

    def production(self, park: str | Park, start: datetime, end: datetime) -> list[ProductionSample]:
        """Metered production samples on [start, end)."""
        site = park if isinstance(park, Park) else self.parks.get(park)
        events = [e for e in self.scenario.events if e.park == site.id]
        out = []
        for w in self.weather(site.latitude, site.longitude, start, end, site.tilt, site.azimuth):
            irradiance = w.poa_w_m2 if site.tilt is not None else w.ghi_w_m2
            expected = pv.ac_power_mw(site.capacity_mwp, irradiance, w.temp_c, site.ac_capacity_mw)
            active = [e for e in events if e.active(w.time)]

            availability = max(0.0, 1.0 - sum(e.fraction for e in active if e.type == "outage"))
            mw = expected * availability
            for e in active:
                if e.type == "degradation":
                    mw *= 1.0 - e.fraction
            limits = [e.limit_mw for e in active if e.type == "curtailment"]
            if self.scenario.curtail_on_negative_prices and site.bidding_zone in ZONES:
                price = self.price_at(site.bidding_zone, w.time)
                if price is not None and price < 0:
                    limits.append(0.0)
            curtailed = bool(limits) and expected > 0 and mw > min(limits)
            if curtailed:
                mw = min(limits)
            if mw > 0:
                mw *= 1.0 + self._rng("meter", site.id, w.time.isoformat()).gauss(0.0, 0.01)

            gap = any(e.type == "data_gap" for e in active)
            out.append(ProductionSample(w.time, round(expected, 3), None if gap else round(mw, 3), availability, curtailed))
        return out

    def _rng(self, *key) -> random.Random:
        return random.Random(":".join(str(k) for k in (self.scenario.seed, *key)))


def _align(t: datetime) -> datetime:
    t = t.astimezone(timezone.utc)
    return t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)


def _slot(t: datetime) -> int:
    return t.hour * 4 + t.minute // 15


def _bump(h: float, centre: float, width: float) -> float:
    return math.exp(-(((h - centre) / width) ** 2))


def _season_weights(day: date) -> tuple[float, float, float]:
    """(sunny, mixed, overcast) odds by month, roughly southern Scandinavia."""
    if day.month in (5, 6, 7, 8):
        return (0.5, 0.35, 0.15)
    if day.month in (11, 12, 1, 2):
        return (0.15, 0.3, 0.55)
    return (0.3, 0.35, 0.35)
