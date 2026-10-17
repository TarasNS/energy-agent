"""Energy tools against fixture responses shaped like the public APIs' documented formats."""

import json
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from energy_harness.config import POC_ROOT
from energy_harness.energy import build_energy_tools, pv
from energy_harness.energy.parks import Park, ParkRegistry
from energy_harness.energy.sources import ARCHIVE_URL, FORECAST_URL, PRICE_URL, OpenMeteo
from energy_harness.tools import ToolError, ToolRegistry

TODAY = date(2026, 10, 17)
PARK = Park(
    id="test-park", name="Test Park", latitude=56.0, longitude=9.5,
    capacity_mwp=100.0, ac_capacity_mw=50.0, tilt=25, azimuth=0, bidding_zone="DK1",
)
FLAT = Park(id="flat", name="Flat Park", latitude=54.0, longitude=17.0, capacity_mwp=10.0)


@pytest.fixture
def registry():
    tools = build_energy_tools(ParkRegistry([PARK, FLAT]), httpx.Client(), today=lambda: TODAY)
    return ToolRegistry(tools)


def run(registry, name, **args):
    result = registry.execute(name, json.dumps(args))
    return result.ok, (json.loads(result.content) if result.ok else result.content)


def open_meteo_response(request):
    """Hourly series for the requested dates: bell-shaped irradiance peaking at 12:00 UTC."""
    q = request.url.params
    start, end = date.fromisoformat(q["start_date"]), date.fromisoformat(q["end_date"])
    times, ghi = [], []
    day = start
    while day <= end:
        for h in range(24):
            times.append(f"{day.isoformat()}T{h:02d}:00")
            ghi.append(round(max(0.0, 600 * math.sin(math.pi * (h - 6) / 12)), 1) if 6 <= h <= 18 else 0.0)
        day += timedelta(days=1)
    hourly = {
        "time": times,
        "shortwave_radiation": ghi,
        "temperature_2m": [10.0] * len(times),
        "cloud_cover": [40] * len(times),
    }
    if "global_tilted_irradiance" in q["hourly"]:
        hourly["global_tilted_irradiance"] = [round(g * 1.2, 1) for g in ghi]
    return httpx.Response(200, json={"latitude": float(q["latitude"]), "hourly_units": {}, "hourly": hourly})


def prices_response(day: date, resolution_min: int = 15):
    berlin = ZoneInfo("Europe/Berlin")
    start = datetime(day.year, day.month, day.day, tzinfo=berlin)
    n = 24 * 60 // resolution_min
    # include one interval from the previous and next market day, which must be filtered out
    stamps = [start + timedelta(minutes=resolution_min * i) for i in range(-1, n + 1)]
    prices = [50.0 + (i % 8) * 10 for i in range(len(stamps))]
    prices[10] = -5.0
    return {
        "license_info": "CC BY 4.0",
        "unix_seconds": [int(s.astimezone(timezone.utc).timestamp()) for s in stamps],
        "price": prices,
        "unit": "EUR / MWh",
        "deprecated": False,
    }


# --- PV model -----------------------------------------------------------------


def test_pv_power_math():
    assert pv.ac_power_mw(60, 0, 20) == 0.0
    assert pv.ac_power_mw(60, None, 20) == 0.0
    # 1000 W/m², 25 °C air → cell 56.25 °C → derate 1 - 0.0035 × 31.25
    assert pv.ac_power_mw(60, 1000, 25) == pytest.approx(60 * 0.85 * (1 - 0.0035 * 31.25))
    assert pv.ac_power_mw(100, 1000, 25, ac_capacity_mw=50) == 50
    assert pv.ac_power_mw(60, 500, None) > 0


# --- parks --------------------------------------------------------------------


def test_shipped_parks_file_loads():
    parks = ParkRegistry.from_file(POC_ROOT / "parks.yaml")
    assert len(parks.parks) >= 1
    assert parks.get(parks.parks[0].name.upper()).id == parks.parks[0].id


def test_list_parks_and_unknown_park(registry):
    ok, parks = run(registry, "list_parks")
    assert ok and [p["id"] for p in parks] == ["test-park", "flat"]
    ok, msg = run(registry, "estimate_pv_production", park="nowhere")
    assert not ok and "unknown park" in msg and "test-park" in msg


# --- PV production --------------------------------------------------------------


@respx.mock
def test_estimate_pv_production_single_day(registry):
    route = respx.get(FORECAST_URL).mock(side_effect=open_meteo_response)
    ok, result = run(registry, "estimate_pv_production", park="Test Park")
    assert ok, result

    params = route.calls[0].request.url.params
    assert params["start_date"] == params["end_date"] == "2026-10-17"
    assert float(params["tilt"]) == 25 and "global_tilted_irradiance" in params["hourly"]

    assert [d["date"] for d in result["daily"]] == ["2026-10-17"]
    day = result["daily"][0]
    assert 0 < day["energy_mwh"] < 100 * 24
    assert day["peak_mw"] <= 50  # clipped at AC capacity
    assert day["energy_mwh"] == pytest.approx(sum(h["mw"] for h in result["hourly"]), abs=0.2)
    assert result["total_energy_mwh"] == day["energy_mwh"]
    assert "tilted" in result["method"]


@respx.mock
def test_flat_park_uses_ghi_and_multi_day_has_no_hourly(registry):
    route = respx.get(FORECAST_URL).mock(side_effect=open_meteo_response)
    ok, result = run(registry, "estimate_pv_production", park="flat", start_date="2026-10-17", end_date="2026-10-20")
    assert ok, result
    assert "tilt" not in route.calls[0].request.url.params
    assert "horizontal" in result["method"]
    assert len(result["daily"]) == 4 and "hourly" not in result


@respx.mock
def test_old_dates_use_archive(registry):
    archive = respx.get(ARCHIVE_URL).mock(side_effect=open_meteo_response)
    ok, result = run(registry, "estimate_pv_production", park="flat", start_date="2026-03-01", end_date="2026-03-02")
    assert ok and archive.called and len(result["daily"]) == 2


def test_pv_range_validation(registry):
    assert "end_date is before" in run(registry, "estimate_pv_production", park="flat", start_date="2026-10-17", end_date="2026-10-16")[1]
    assert "max 31 days" in run(registry, "estimate_pv_production", park="flat", start_date="2026-08-01", end_date="2026-10-01")[1]
    assert "15 days ahead" in run(registry, "estimate_pv_production", park="flat", start_date="2026-11-10")[1]


def test_open_meteo_rejects_ranges_spanning_archive_and_recent():
    weather = OpenMeteo(httpx.Client(), today=lambda: TODAY)
    with pytest.raises(ToolError, match="split it"):
        weather.hourly(56, 9, date(2026, 7, 1), date(2026, 10, 15))


@respx.mock
def test_open_meteo_error_is_reported(registry):
    respx.get(FORECAST_URL).mock(return_value=httpx.Response(400, json={"error": True, "reason": "Latitude must be in range"}))
    ok, msg = run(registry, "estimate_pv_production", park="flat")
    assert not ok and "Latitude must be in range" in msg


# --- irradiance -------------------------------------------------------------------


@respx.mock
def test_irradiance_forecast_by_park(registry):
    route = respx.get(FORECAST_URL).mock(side_effect=open_meteo_response)
    ok, result = run(registry, "get_irradiance_forecast", park="test-park", days=2)
    assert ok, result
    assert route.calls[0].request.url.params["end_date"] == "2026-10-18"
    assert [d["date"] for d in result["daily"]] == ["2026-10-17", "2026-10-18"]
    assert result["daily"][0]["peak_ghi_w_m2"] == 600
    assert result["daily"][0]["mean_cloud_cover_pct"] == 40
    assert all(h["ghi_w_m2"] > 0 for h in result["hourly_utc"])


@respx.mock
def test_irradiance_by_coordinates_long_range_has_no_hourly(registry):
    respx.get(FORECAST_URL).mock(side_effect=open_meteo_response)
    ok, result = run(registry, "get_irradiance_forecast", latitude=60.1, longitude=24.9, days=7)
    assert ok and result["location"] == "60.100,24.900" and len(result["daily"]) == 7 and "hourly_utc" not in result


def test_irradiance_needs_a_location(registry):
    ok, msg = run(registry, "get_irradiance_forecast", latitude=60.1)
    assert not ok and "latitude and longitude" in msg
    ok, msg = run(registry, "get_irradiance_forecast", park="flat", days=30)
    assert not ok and "days" in msg


# --- prices -----------------------------------------------------------------------


@respx.mock
def test_day_ahead_prices_single_day(registry):
    route = respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json=prices_response(TODAY)))
    ok, result = run(registry, "get_day_ahead_prices", bidding_zone="dk1")
    assert ok, result
    assert route.calls[0].request.url.params["bzn"] == "DK1"

    day = result["daily"][0]
    assert day["date"] == "2026-10-17"
    assert day["intervals"] == 96 and day["resolution_min"] == 15  # neighbours filtered out
    assert day["min"] == -5.0 and day["negative_intervals"] == 1
    assert day["max"] == 120.0
    assert len(result["prices"]) == 96 and result["prices"][0][0] == "00:00"


@respx.mock
def test_day_ahead_prices_multi_day_hourly(registry):
    data = prices_response(date(2026, 10, 15), resolution_min=60)
    second = prices_response(date(2026, 10, 16), resolution_min=60)
    merged = dict(zip(data["unix_seconds"], data["price"])) | dict(zip(second["unix_seconds"], second["price"]))
    data["unix_seconds"], data["price"] = list(merged), list(merged.values())
    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json=data))
    ok, result = run(registry, "get_day_ahead_prices", bidding_zone="SE3", start_date="2026-10-15", end_date="2026-10-16")
    assert ok, result
    assert [d["date"] for d in result["daily"]] == ["2026-10-15", "2026-10-16"]
    assert all(d["intervals"] == 24 and d["resolution_min"] == 60 for d in result["daily"])
    assert "prices" not in result


@respx.mock
def test_day_ahead_prices_errors(registry):
    respx.get(PRICE_URL).mock(return_value=httpx.Response(404, json={"detail": "Bidding zone XX not found"}))
    ok, msg = run(registry, "get_day_ahead_prices", bidding_zone="XX")
    assert not ok and "not found" in msg

    respx.get(PRICE_URL).mock(return_value=httpx.Response(200, json={"unix_seconds": [], "price": []}))
    ok, msg = run(registry, "get_day_ahead_prices", bidding_zone="DK1", start_date="2026-10-18")
    assert not ok and "not published yet" in msg


@respx.mock
def test_network_failure_becomes_tool_error(registry):
    respx.get(PRICE_URL).mock(side_effect=httpx.ConnectError("blocked"))
    ok, msg = run(registry, "get_day_ahead_prices", bidding_zone="DK1")
    assert not ok and "Energy-Charts request failed" in msg
