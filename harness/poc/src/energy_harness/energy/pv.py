"""Simple PV output estimate from irradiance.

P_ac = capacity_mwp × (G / 1000) × PR × (1 + γ × (T_cell − 25)), clipped at AC capacity,
with T_cell from the NOCT model: T_cell = T_air + (NOCT − 20) / 800 × G.

Good enough for daily energy within roughly ±10–20 % on typical fixed-tilt
parks; not a substitute for metered data or a full PVsyst-style model.
"""

from __future__ import annotations

PERFORMANCE_RATIO = 0.85  # losses excluding temperature: inverter, soiling, wiring, mismatch, availability
TEMP_COEFF_PER_C = -0.0035
NOCT_C = 45.0
DEFAULT_AIR_TEMP_C = 15.0


def cell_temperature(air_temp_c: float, irradiance_w_m2: float) -> float:
    return air_temp_c + (NOCT_C - 20.0) / 800.0 * irradiance_w_m2


def ac_power_mw(
    capacity_mwp: float,
    irradiance_w_m2: float | None,
    air_temp_c: float | None,
    ac_capacity_mw: float | None = None,
    performance_ratio: float = PERFORMANCE_RATIO,
) -> float:
    if not irradiance_w_m2 or irradiance_w_m2 <= 0:
        return 0.0
    t_cell = cell_temperature(DEFAULT_AIR_TEMP_C if air_temp_c is None else air_temp_c, irradiance_w_m2)
    power = capacity_mwp * irradiance_w_m2 / 1000.0 * performance_ratio * (1 + TEMP_COEFF_PER_C * (t_cell - 25.0))
    power = max(power, 0.0)
    return min(power, ac_capacity_mw) if ac_capacity_mw else power
