"""Clients for free, keyless public data APIs.

- Open-Meteo (https://open-meteo.com/en/docs): hourly irradiance and weather.
  The forecast endpoint covers ~92 days back to 16 days ahead; older dates use
  the archive endpoint (ERA5, available with a ~5 day delay).
- Energy-Charts (https://api.energy-charts.info/, Fraunhofer ISE): day-ahead
  spot prices per bidding zone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import httpx

from ..tools import ToolError

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
PRICE_URL = "https://api.energy-charts.info/price"

FORECAST_PAST_DAYS = 92
FORECAST_AHEAD_DAYS = 15
ARCHIVE_DELAY_DAYS = 6


@dataclass
class WeatherHour:
    time: datetime  # UTC, start of the hour; irradiance values are means over the preceding hour
    ghi_w_m2: float | None
    poa_w_m2: float | None  # plane-of-array (tilted) irradiance, if tilt was requested
    temp_c: float | None
    cloud_pct: float | None


@dataclass
class PricePoint:
    time: datetime  # UTC
    eur_per_mwh: float | None


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


class OpenMeteo:
    def __init__(self, http: httpx.Client, today=utc_today) -> None:
        self.http = http
        self._today = today

    def hourly(
        self,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
        tilt: float | None = None,
        azimuth: float | None = None,
    ) -> list[WeatherHour]:
        today = self._today()
        if end < start:
            raise ToolError("end date is before start date")
        if end > today + timedelta(days=FORECAST_AHEAD_DAYS):
            raise ToolError(f"forecasts only reach {FORECAST_AHEAD_DAYS} days ahead (until {today + timedelta(days=FORECAST_AHEAD_DAYS)})")
        if start >= today - timedelta(days=FORECAST_PAST_DAYS):
            url = FORECAST_URL
        elif end <= today - timedelta(days=ARCHIVE_DELAY_DAYS):
            url = ARCHIVE_URL
        else:
            raise ToolError(
                f"date range spans both archive and recent data; split it at {today - timedelta(days=FORECAST_PAST_DAYS)}"
            )

        variables = ["shortwave_radiation", "temperature_2m", "cloud_cover"]
        params: dict = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": "UTC",
        }
        if tilt is not None:
            variables.append("global_tilted_irradiance")
            params["tilt"] = tilt
            params["azimuth"] = azimuth or 0
        params["hourly"] = ",".join(variables)

        data = _get_json(self.http, url, params, "Open-Meteo")
        hourly = data.get("hourly") or {}
        times = hourly.get("time") or []

        def column(name: str) -> list:
            values = hourly.get(name)
            return values if values is not None else [None] * len(times)

        ghi, temp, cloud, poa = (column(n) for n in ("shortwave_radiation", "temperature_2m", "cloud_cover", "global_tilted_irradiance"))
        return [
            WeatherHour(
                time=datetime.fromisoformat(t).replace(tzinfo=timezone.utc),
                ghi_w_m2=ghi[i],
                poa_w_m2=poa[i],
                temp_c=temp[i],
                cloud_pct=cloud[i],
            )
            for i, t in enumerate(times)
        ]


class EnergyCharts:
    def __init__(self, http: httpx.Client) -> None:
        self.http = http

    def day_ahead(self, bidding_zone: str, start: date, end: date) -> tuple[list[PricePoint], str]:
        params = {"bzn": bidding_zone, "start": start.isoformat(), "end": end.isoformat()}
        data = _get_json(self.http, PRICE_URL, params, "Energy-Charts")
        seconds = data.get("unix_seconds") or []
        prices = data.get("price") or []
        points = [PricePoint(datetime.fromtimestamp(s, timezone.utc), p) for s, p in zip(seconds, prices)]
        return points, data.get("unit") or "EUR / MWh"


def _get_json(http: httpx.Client, url: str, params: dict, source: str) -> dict:
    try:
        resp = http.get(url, params=params, timeout=30)
    except httpx.HTTPError as e:
        raise ToolError(f"{source} request failed: {type(e).__name__}: {e}") from e
    try:
        data = resp.json()
    except ValueError:
        data = None
    if resp.status_code != 200 or not isinstance(data, dict):
        reason = (data.get("reason") or data.get("detail")) if isinstance(data, dict) else None
        raise ToolError(f"{source} returned HTTP {resp.status_code}: {reason or resp.text[:200]}")
    if data.get("error"):
        raise ToolError(f"{source} error: {data.get('reason') or data['error']}")
    return data
