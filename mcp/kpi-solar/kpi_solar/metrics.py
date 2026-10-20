"""The 13 KPI formulas (SPEC.md section 3).

Pure functions: strings or Decimals in, Decimal or Unavailable(reason) out.
Never a float, never a division by zero, round half up (ties go away from zero).
Rounding places follow SPEC.md section 2: % 1, MWh 3, EUR and EUR/MWh 2, hours 0.

Every function runs in its own fixed decimal context, so the caller's context
cannot change a result, and any arithmetic error becomes Unavailable.
"""
import re
from dataclasses import dataclass
from decimal import (
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)
from functools import wraps

_CONTEXT = Context(
    prec=60,
    rounding=ROUND_HALF_UP,
    traps=[InvalidOperation, DivisionByZero, Overflow],
)
_MAX_EXPONENT = 30  # refuses values like 1e999999 that no real input needs
_MAX_TEXT_LENGTH = 64
_PLAIN_DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


@dataclass(frozen=True)
class Unavailable:
    """A KPI that cannot be calculated, with the reason in plain words."""

    reason: str


def _safe(function):
    """Run in the fixed context; an arithmetic error becomes Unavailable."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        with localcontext(_CONTEXT):
            try:
                return function(*args, **kwargs)
            except ArithmeticError:
                return Unavailable("result out of range")

    return wrapper


def _num(value, name, *, allow_negative=False):
    """Parse one input to a finite Decimal, or return Unavailable."""
    if value is None or isinstance(value, (bool, float)):
        return Unavailable(f"{name}: missing or not a string/Decimal")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return Unavailable(f"{name}: empty")
        if len(text) > _MAX_TEXT_LENGTH or not _PLAIN_DECIMAL.fullmatch(text):
            return Unavailable(f"{name}: not a plain decimal number")
        number = Decimal(text)
    elif isinstance(value, Decimal):
        number = value
    else:
        return Unavailable(f"{name}: unsupported type {type(value).__name__}")
    if not number.is_finite():
        return Unavailable(f"{name}: not finite")
    if number != 0 and abs(number.adjusted()) > _MAX_EXPONENT:
        return Unavailable(f"{name}: out of range")
    if number < 0 and not allow_negative:
        return Unavailable(f"{name}: negative")
    return number


def _first_unavailable(*values):
    for value in values:
        if isinstance(value, Unavailable):
            return value
    return None


def _round(number, places):
    """Round half up; a result that rounds to zero is plain zero, never -0."""
    rounded = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return rounded.copy_abs() if rounded.is_zero() else rounded


def _ratio_pct(numerator, denominator, denominator_name):
    """numerator / denominator * 100, 1 place, denominator must be above zero."""
    if denominator == 0:
        return Unavailable(f"{denominator_name} is zero")
    return _round(numerator / denominator * 100, 1)


def _as_sequence(value, name):
    """Accept only a list or tuple: not a generator, set, dict, string or number."""
    if not isinstance(value, (list, tuple)):
        return Unavailable(f"{name}: expected a list or tuple")
    if not value:
        return Unavailable(f"no {name}")
    return value


@_safe
def actual_vs_expected_pct(actual_mwh, expected_mwh):
    actual = _num(actual_mwh, "actual_mwh")
    expected = _num(expected_mwh, "expected_mwh")
    bad = _first_unavailable(actual, expected)
    return bad or _ratio_pct(actual, expected, "expected_mwh")


@_safe
def performance_ratio_pct(actual_kwh, poa_irradiation_kwh_m2, nameplate_kwp):
    actual = _num(actual_kwh, "actual_kwh")
    poa = _num(poa_irradiation_kwh_m2, "poa_irradiation_kwh_m2")
    kwp = _num(nameplate_kwp, "nameplate_kwp")
    bad = _first_unavailable(actual, poa, kwp)
    if bad:
        return bad
    if poa == 0:
        return Unavailable("poa_irradiation_kwh_m2 is zero")
    if kwp == 0:
        return Unavailable("nameplate_kwp is zero")
    return _ratio_pct(actual, poa * kwp, "reference energy")


@_safe
def availability_pct(available_hours, period_hours):
    available = _num(available_hours, "available_hours")
    period = _num(period_hours, "period_hours")
    bad = _first_unavailable(available, period)
    return bad or _ratio_pct(available, period, "period_hours")


@_safe
def capacity_factor_pct(energy_mwh, capacity_mw, period_hours):
    energy = _num(energy_mwh, "energy_mwh")
    capacity = _num(capacity_mw, "capacity_mw")
    period = _num(period_hours, "period_hours")
    bad = _first_unavailable(energy, capacity, period)
    if bad:
        return bad
    if capacity == 0:
        return Unavailable("capacity_mw is zero")
    if period == 0:
        return Unavailable("period_hours is zero")
    return _ratio_pct(energy, capacity * period, "possible energy")


@_safe
def ppa_delivery_pct(delivered_mwh, contracted_mwh):
    delivered = _num(delivered_mwh, "delivered_mwh")
    contracted = _num(contracted_mwh, "contracted_mwh")
    bad = _first_unavailable(delivered, contracted)
    return bad or _ratio_pct(delivered, contracted, "contracted_mwh")


@_safe
def realised_price_eur_mwh(intervals):
    """intervals: a list or tuple of (mwh, price). Prices may be negative, volumes may not."""
    intervals = _as_sequence(intervals, "intervals")
    if isinstance(intervals, Unavailable):
        return intervals
    total_value = Decimal(0)
    total_mwh = Decimal(0)
    for pair in intervals:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return Unavailable("interval is not a (mwh, price) pair")
        mwh = _num(pair[0], "mwh")
        price = _num(pair[1], "price", allow_negative=True)
        bad = _first_unavailable(mwh, price)
        if bad:
            return bad
        total_value += mwh * price
        total_mwh += mwh
    if total_mwh == 0:
        return Unavailable("total volume is zero")
    return _round(total_value / total_mwh, 2)


@_safe
def merchant_exposure_eur(merchant_mwh, price_move_eur_mwh):
    merchant = _num(merchant_mwh, "merchant_mwh")
    move = _num(price_move_eur_mwh, "price_move_eur_mwh", allow_negative=True)
    bad = _first_unavailable(merchant, move)
    return bad or _round(merchant * move, 2)


@_safe
def downtime_hours(statuses, interval_hours):
    """statuses: a list or tuple with one "OK" or "OUTAGE" per interval."""
    interval = _num(interval_hours, "interval_hours")
    if isinstance(interval, Unavailable):
        return interval
    if interval == 0:
        return Unavailable("interval_hours is zero")
    statuses = _as_sequence(statuses, "statuses")
    if isinstance(statuses, Unavailable):
        return statuses
    outages = 0
    for status in statuses:
        if status == "OUTAGE":
            outages += 1
        elif status != "OK":
            return Unavailable('statuses: each must be "OK" or "OUTAGE"')
    return _round(Decimal(outages) * interval, 0)


@_safe
def energy_loss_mwh(expected_mwh, actual_mwh):
    """expected - actual. The sign is kept: negative when actual exceeds expected."""
    expected = _num(expected_mwh, "expected_mwh")
    actual = _num(actual_mwh, "actual_mwh")
    bad = _first_unavailable(expected, actual)
    return bad or _round(expected - actual, 3)


@_safe
def incident_resolution_hours(open_to_close_hours):
    """No tickets are loaded in the POC, so this is always Unavailable."""
    return Unavailable("no tickets loaded")


@_safe
def bess_availability_pct(available_hours, period_hours):
    return availability_pct(available_hours, period_hours)


@_safe
def bess_round_trip_efficiency_pct(discharged_mwh, charged_mwh):
    discharged = _num(discharged_mwh, "discharged_mwh")
    charged = _num(charged_mwh, "charged_mwh")
    bad = _first_unavailable(discharged, charged)
    return bad or _ratio_pct(discharged, charged, "charged_mwh")


@_safe
def bess_cycle_utilisation_pct(throughput_mwh, usable_mwh):
    """throughput_mwh is the average daily throughput (charged + discharged)."""
    throughput = _num(throughput_mwh, "throughput_mwh")
    usable = _num(usable_mwh, "usable_mwh")
    bad = _first_unavailable(throughput, usable)
    if bad:
        return bad
    if usable == 0:
        return Unavailable("usable_mwh is zero")
    return _ratio_pct(throughput, 2 * usable, "cycle capacity")
