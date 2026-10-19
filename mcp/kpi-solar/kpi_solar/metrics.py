"""Solar, commercial, asset-operations and BESS KPIs: pure functions.

Every function returns a Decimal, or an Unavailable with a reason when an
input is missing. Nothing is estimated, interpolated or defaulted. Inputs are
Decimal (or None when missing); floats are rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Iterable, Sequence

PCT = Decimal("0.1")   # percentages: 1 decimal
HOURS = Decimal("0.01")  # durations: 2 decimals
EUR_MWH = Decimal("0.01")  # prices: 2 decimals
MWH = Decimal("0.001")  # energy: 3 decimals


@dataclass(frozen=True)
class Unavailable:
    """The KPI cannot be computed from the inputs given. Never shown as a number."""

    reason: str


Result = Decimal | Unavailable


def _check_decimal(name: str, value: object) -> None:
    if isinstance(value, float):
        raise TypeError(f"{name} must be Decimal or str, not float")


def _q(value: Decimal, step: Decimal) -> Decimal:
    return value.quantize(step, rounding=ROUND_HALF_UP)


def _need(**inputs: object) -> Unavailable | None:
    missing = [name for name, value in inputs.items() if value is None]
    if missing:
        return Unavailable(f"missing input: {', '.join(missing)}")
    return None


def _dec(name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    _check_decimal(name, value)
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return result


# ── Solar generation ──────────────────────────────────────────────────────


def actual_vs_expected_pct(actual_mwh, expected_mwh) -> Result:
    """Actual ÷ expected × 100. Needs a validated expected baseline."""
    a, e = _dec("actual_mwh", actual_mwh), _dec("expected_mwh", expected_mwh)
    if (u := _need(actual_mwh=a, expected_mwh=e)):
        return u
    if e <= 0:
        return Unavailable("expected_mwh must be > 0")
    return _q(a / e * 100, PCT)


def performance_ratio_pct(actual_kwh, poa_irradiation_kwh_m2, nameplate_kwp) -> Result:
    """IEC 61724 style: E_AC ÷ (H_POA × P_nameplate) × 100. Needs plane-of-array irradiation."""
    e = _dec("actual_kwh", actual_kwh)
    h = _dec("poa_irradiation_kwh_m2", poa_irradiation_kwh_m2)
    p = _dec("nameplate_kwp", nameplate_kwp)
    if (u := _need(actual_kwh=e, poa_irradiation_kwh_m2=h, nameplate_kwp=p)):
        return u
    if h <= 0 or p <= 0:
        return Unavailable("irradiation and nameplate must be > 0")
    return _q(e / (h * p) * 100, PCT)


def availability_pct(available_hours, period_hours) -> Result:
    """Available hours ÷ period hours × 100. The daylight definition must be stated by the caller."""
    a, p = _dec("available_hours", available_hours), _dec("period_hours", period_hours)
    if (u := _need(available_hours=a, period_hours=p)):
        return u
    if p <= 0 or a < 0 or a > p:
        return Unavailable("require 0 <= available_hours <= period_hours and period_hours > 0")
    return _q(a / p * 100, PCT)


def capacity_factor_pct(energy_mwh, capacity_mw, period_hours) -> Result:
    """Metered MWh ÷ (capacity MW × period hours) × 100. State DC or AC basis with the capacity."""
    e, c, h = _dec("energy_mwh", energy_mwh), _dec("capacity_mw", capacity_mw), _dec("period_hours", period_hours)
    if (u := _need(energy_mwh=e, capacity_mw=c, period_hours=h)):
        return u
    if c <= 0 or h <= 0:
        return Unavailable("capacity_mw and period_hours must be > 0")
    return _q(e / (c * h) * 100, PCT)


# ── Energy commercial ─────────────────────────────────────────────────────


def ppa_delivery_pct(delivered_mwh, contracted_mwh) -> Result:
    """Delivered ÷ contracted × 100. Contracted volume must come from the signed agreement."""
    d, c = _dec("delivered_mwh", delivered_mwh), _dec("contracted_mwh", contracted_mwh)
    if (u := _need(delivered_mwh=d, contracted_mwh=c)):
        return u
    if c <= 0:
        return Unavailable("contracted_mwh must be > 0")
    return _q(d / c * 100, PCT)


def realised_price_eur_mwh(intervals: Iterable[tuple[object, object]] | None) -> Result:
    """Σ(MWh_i × price_i) ÷ Σ MWh_i over (mwh, price) pairs.

    Any missing price, or negative energy, makes the result unavailable: no partial price is returned.
    """
    if intervals is None:
        return Unavailable("missing input: intervals")
    total_mwh = Decimal(0)
    total_value = Decimal(0)
    for mwh, price in intervals:
        m, p = _dec("mwh", mwh), _dec("price", price)
        if m is None or p is None:
            return Unavailable("interval with missing energy or price; no partial price")
        if m < 0:
            return Unavailable("negative metered energy in an interval; check the source")
        total_mwh += m
        total_value += m * p
    if total_mwh <= 0:
        return Unavailable("no metered energy in the period")
    return _q(total_value / total_mwh, EUR_MWH)


def merchant_exposure_eur(merchant_mwh, price_move_eur_mwh) -> Result:
    """Merchant MWh × price move (EUR/MWh). A sensitivity, not a forecast: the move is an input."""
    m, p = _dec("merchant_mwh", merchant_mwh), _dec("price_move_eur_mwh", price_move_eur_mwh)
    if (u := _need(merchant_mwh=m, price_move_eur_mwh=p)):
        return u
    return _q(m * p, EUR_MWH)


# ── Asset operations ──────────────────────────────────────────────────────

KNOWN_STATUS = {"OK", "CURTAILED", "OUTAGE", "DATA_GAP"}


def downtime_hours(statuses: Sequence[str] | None, interval_hours) -> Result:
    """Hours of OUTAGE intervals; one interval length is applied to every status.

    DATA_GAP intervals are NOT counted as downtime: missing data is not proof of an outage.
    Unknown status codes raise; they are never counted silently.
    """
    h = _dec("interval_hours", interval_hours)
    if (u := _need(statuses=statuses, interval_hours=h)):
        return u
    if isinstance(statuses, str):
        raise TypeError("statuses must be a sequence of codes, not a string")
    if not statuses:
        return Unavailable("no intervals")
    unknown = {s for s in statuses if s not in KNOWN_STATUS}
    if unknown:
        raise ValueError(f"unknown status codes: {sorted(unknown)}")
    return _q(Decimal(sum(1 for s in statuses if s == "OUTAGE")) * h, HOURS)


def energy_loss_mwh(expected_mwh, actual_mwh) -> Result:
    """Expected − actual. Losses are reported in total; attribution to causes is a separate step."""
    e, a = _dec("expected_mwh", expected_mwh), _dec("actual_mwh", actual_mwh)
    if (u := _need(expected_mwh=e, actual_mwh=a)):
        return u
    return _q(e - a, MWH)


def incident_resolution_hours(open_to_close_hours: Sequence[object] | None) -> Result:
    """Median hours from open to close. Needs ticket data; never inferred from logs."""
    if open_to_close_hours is None or not open_to_close_hours:
        return Unavailable("no incident records; ticket data required")
    if isinstance(open_to_close_hours, str):
        raise TypeError("open_to_close_hours must be a sequence of numbers, not a string")
    values = [_dec("hours", h) for h in open_to_close_hours]
    if any(v is None or v < 0 for v in values):
        return Unavailable("every incident needs a non-negative open-to-close time")
    return _q(Decimal(str(median(values))), HOURS)


# ── Battery energy storage ────────────────────────────────────────────────


def bess_availability_pct(available_hours, period_hours) -> Result:
    """Same definition as plant availability; derated states must be excluded by the caller."""
    return availability_pct(available_hours, period_hours)


def bess_round_trip_efficiency_pct(discharged_mwh, charged_mwh) -> Result:
    """Discharged ÷ charged × 100 over the same period, meters on both sides."""
    d, c = _dec("discharged_mwh", discharged_mwh), _dec("charged_mwh", charged_mwh)
    if (u := _need(discharged_mwh=d, charged_mwh=c)):
        return u
    if c <= 0:
        return Unavailable("charged_mwh must be > 0")
    return _q(d / c * 100, PCT)


def bess_cycle_utilisation_pct(throughput_mwh, usable_mwh) -> Result:
    """Equivalent full cycles: throughput ÷ (2 × usable energy), × 100 for a percentage view."""
    t, u_ = _dec("throughput_mwh", throughput_mwh), _dec("usable_mwh", usable_mwh)
    if (u := _need(throughput_mwh=t, usable_mwh=u_)):
        return u
    if u_ <= 0:
        return Unavailable("usable_mwh must be > 0")
    return _q(t / (2 * u_) * 100, PCT)
