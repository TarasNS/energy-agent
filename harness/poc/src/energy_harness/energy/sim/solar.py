"""Just enough solar geometry and irradiance modelling for plausible synthetic data.

Sun position from the Cooper declination and solar hour angle (no equation of
time), Haurwitz clear-sky GHI, Erbs diffuse split, isotropic-sky transposition.
"""

from __future__ import annotations

import math
from datetime import datetime

SOLAR_CONSTANT = 1367.0
ALBEDO = 0.2


def sun_position(lat: float, lon: float, t: datetime) -> tuple[float, float]:
    """Return (sin of elevation, azimuth in degrees clockwise from north) for a UTC time."""
    doy = t.timetuple().tm_yday
    decl = math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (284 + doy))))
    solar_hours = t.hour + t.minute / 60.0 + t.second / 3600.0 + lon / 15.0
    hour_angle = math.radians(15.0 * (solar_hours - 12.0))
    phi = math.radians(lat)

    sin_el = math.sin(phi) * math.sin(decl) + math.cos(phi) * math.cos(decl) * math.cos(hour_angle)
    cos_el = math.sqrt(max(0.0, 1.0 - sin_el**2))
    if cos_el < 1e-6 or abs(math.cos(phi)) < 1e-6:
        return sin_el, 180.0
    cos_az = (math.sin(decl) - sin_el * math.sin(phi)) / (cos_el * math.cos(phi))
    azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))
    if hour_angle > 0:  # afternoon: sun in the west
        azimuth = 360.0 - azimuth
    return sin_el, azimuth


def clear_sky_ghi(sin_el: float) -> float:
    """Haurwitz clear-sky global horizontal irradiance, W/m²."""
    if sin_el <= 0:
        return 0.0
    return 1098.0 * sin_el * math.exp(-0.057 / sin_el)


def diffuse_fraction(kt: float) -> float:
    """Erbs correlation: diffuse share of GHI from the clearness index."""
    if kt <= 0.22:
        return 1.0 - 0.09 * kt
    if kt <= 0.80:
        return 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    return 0.165


def plane_of_array(ghi: float, sin_el: float, sun_azimuth: float, tilt: float, azimuth: float) -> float:
    """Irradiance on a tilted plane, W/m². `azimuth` uses the Open-Meteo convention (0 = south, 90 = west)."""
    if ghi <= 0 or sin_el <= 0.02:
        return max(ghi, 0.0) * (1 + math.cos(math.radians(tilt))) / 2
    kt = min(1.0, ghi / (SOLAR_CONSTANT * sin_el))
    dhi = ghi * diffuse_fraction(kt)
    dni = min((ghi - dhi) / sin_el, 1000.0)

    zenith = math.acos(max(-1.0, min(1.0, sin_el)))
    beta = math.radians(tilt)
    panel_az = math.radians(180.0 + azimuth)  # from north
    cos_aoi = math.cos(zenith) * math.cos(beta) + math.sin(zenith) * math.sin(beta) * math.cos(math.radians(sun_azimuth) - panel_az)
    return max(0.0, dni * max(cos_aoi, 0.0) + dhi * (1 + math.cos(beta)) / 2 + ghi * ALBEDO * (1 - math.cos(beta)) / 2)
