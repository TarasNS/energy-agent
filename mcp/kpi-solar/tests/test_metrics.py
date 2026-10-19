"""KPI formula tests. Expected values are worked by hand in the comments.

No company data is used. Every input is a made-up round number chosen to make
the arithmetic checkable by hand.
"""

from decimal import Decimal

import pytest

from kpi_solar.metrics import (
    Unavailable,
    actual_vs_expected_pct,
    availability_pct,
    bess_availability_pct,
    bess_cycle_utilisation_pct,
    bess_round_trip_efficiency_pct,
    capacity_factor_pct,
    downtime_hours,
    energy_loss_mwh,
    incident_resolution_hours,
    merchant_exposure_eur,
    performance_ratio_pct,
    ppa_delivery_pct,
    realised_price_eur_mwh,
)


# ── Solar generation ──────────────────────────────────────────────────────

def test_actual_vs_expected():
    # 90 / 100 × 100 = 90.0
    assert actual_vs_expected_pct("90", "100") == Decimal("90.0")


def test_actual_vs_expected_needs_baseline():
    assert isinstance(actual_vs_expected_pct("90", None), Unavailable)


def test_performance_ratio():
    # 800 kWh / (200 kWh/m² × 5 kWp) × 100 = 800 / 1000 × 100 = 80.0
    assert performance_ratio_pct("800", "200", "5") == Decimal("80.0")


def test_performance_ratio_needs_irradiation():
    assert "poa_irradiation_kwh_m2" in performance_ratio_pct("800", None, "5").reason


def test_availability():
    # 690 / 720 × 100 = 95.833… → 95.8
    assert availability_pct("690", "720") == Decimal("95.8")


def test_availability_rejects_available_above_period():
    assert isinstance(availability_pct("800", "720"), Unavailable)


def test_capacity_factor():
    # 30 MWh / (10 MW × 100 h) × 100 = 3.0
    assert capacity_factor_pct("30", "10", "100") == Decimal("3.0")


# ── Energy commercial ─────────────────────────────────────────────────────

def test_ppa_delivery():
    # 95 / 100 × 100 = 95.0
    assert ppa_delivery_pct("95", "100") == Decimal("95.0")


def test_realised_price_is_volume_weighted():
    # (10 × 40 + 30 × 20) / (10 + 30) = (400 + 600) / 40 = 25.00
    assert realised_price_eur_mwh([("10", "40"), ("30", "20")]) == Decimal("25.00")


def test_realised_price_refuses_partial_result():
    result = realised_price_eur_mwh([("10", "40"), ("30", None)])
    assert isinstance(result, Unavailable)


def test_realised_price_needs_energy():
    assert isinstance(realised_price_eur_mwh([("0", "40")]), Unavailable)


def test_merchant_exposure():
    # 200 MWh × 5 EUR/MWh = 1000.00
    assert merchant_exposure_eur("200", "5") == Decimal("1000.00")


# ── Asset operations ──────────────────────────────────────────────────────

def test_downtime_counts_only_outage_intervals():
    # 2 OUTAGE intervals × 0.25 h = 0.5 h
    statuses = ["OK", "OUTAGE", "OK", "OUTAGE", "CURTAILED"]
    assert downtime_hours(statuses, "0.25") == Decimal("0.5")


def test_downtime_rejects_unknown_status():
    with pytest.raises(ValueError):
        downtime_hours(["OK", "MAYBE"], "0.25")


def test_energy_loss():
    # 120.000 − 100.000 = 20.000
    assert energy_loss_mwh("120", "100") == Decimal("20.000")


def test_incident_resolution_median():
    # median of 2, 4, 9 = 4
    assert incident_resolution_hours(["2", "4", "9"]) == Decimal("4.0")


def test_incident_resolution_needs_tickets():
    assert isinstance(incident_resolution_hours([]), Unavailable)


# ── Battery storage ───────────────────────────────────────────────────────

def test_bess_availability_matches_plant_definition():
    assert bess_availability_pct("90", "100") == Decimal("90.0")


def test_bess_round_trip():
    # 88 / 100 × 100 = 88.0
    assert bess_round_trip_efficiency_pct("88", "100") == Decimal("88.0")


def test_bess_cycle_utilisation():
    # 400 MWh throughput / (2 × 200 MWh usable) × 100 = 100.0 (one equivalent full cycle)
    assert bess_cycle_utilisation_pct("400", "200") == Decimal("100.0")


def test_no_float_input_is_accepted():
    with pytest.raises(TypeError):
        availability_pct(690.0, 720)


# ── Regression tests from the independent check ──────────────────────────

def test_hours_keep_two_decimals():
    # 2 OUTAGE × 0.0833 h = 0.1666 → 0.17 (not rounded to 0.2)
    assert downtime_hours(["OUTAGE", "OUTAGE"], "0.0833") == Decimal("0.17")


def test_data_gap_is_not_downtime():
    assert downtime_hours(["DATA_GAP", "DATA_GAP"], "0.25") == Decimal("0.00")


def test_downtime_none_statuses_is_unavailable():
    assert isinstance(downtime_hours(None, "0.25"), Unavailable)


def test_downtime_rejects_string_as_sequence():
    with pytest.raises(TypeError):
        downtime_hours("OUTAGE", "0.25")


def test_incident_rejects_string_as_sequence():
    with pytest.raises(TypeError):
        incident_resolution_hours("24")


def test_incident_none_is_unavailable():
    assert isinstance(incident_resolution_hours(None), Unavailable)


def test_nan_is_rejected():
    with pytest.raises(ValueError):
        availability_pct("NaN", "720")


def test_infinity_is_rejected():
    with pytest.raises(ValueError):
        capacity_factor_pct("Infinity", "10", "100")


def test_realised_price_none_intervals_is_unavailable():
    assert isinstance(realised_price_eur_mwh(None), Unavailable)


def test_realised_price_refuses_negative_energy():
    assert isinstance(realised_price_eur_mwh([("-1", "40"), ("10", "20")]), Unavailable)
