"""Hand-worked tests for the 13 KPI formulas (SPEC.md section 3).

Every expected value below was worked by hand, not copied from the code.
"""
from decimal import Decimal

import pytest

from kpi_solar import metrics
from kpi_solar.metrics import Unavailable


def D(s):
    return Decimal(s)


def assert_unavailable(result):
    assert isinstance(result, Unavailable)
    assert isinstance(result.reason, str) and result.reason


# --- actual_vs_expected_pct -------------------------------------------------

def test_actual_vs_expected_normal():
    assert metrics.actual_vs_expected_pct("95.000", "100.000") == D("95.0")


def test_actual_vs_expected_rounds_half_up():
    # 0.0625 / 1 * 100 = 6.25 -> 6.3 (banker's rounding would give 6.2)
    assert metrics.actual_vs_expected_pct("0.0625", "1") == D("6.3")


def test_actual_vs_expected_zero_expected():
    assert_unavailable(metrics.actual_vs_expected_pct("50", "0"))


def test_actual_vs_expected_missing():
    assert_unavailable(metrics.actual_vs_expected_pct(None, "100"))
    assert_unavailable(metrics.actual_vs_expected_pct("", "100"))


def test_actual_vs_expected_zero_actual_is_valid():
    assert metrics.actual_vs_expected_pct("0", "100") == D("0.0")


# --- performance_ratio_pct --------------------------------------------------

def test_performance_ratio_normal():
    # 40 000 kWh / (5.0 kWh/m2 * 10 000 kWp) = 0.8
    assert metrics.performance_ratio_pct("40000", "5.0", "10000") == D("80.0")


def test_performance_ratio_zero_irradiation():
    assert_unavailable(metrics.performance_ratio_pct("40000", "0", "10000"))


def test_performance_ratio_zero_nameplate():
    assert_unavailable(metrics.performance_ratio_pct("40000", "5.0", "0"))


# --- availability_pct -------------------------------------------------------

def test_availability_normal():
    # 696 / 720 = 96.666... -> 96.7
    assert metrics.availability_pct("696", "720") == D("96.7")


def test_availability_zero_period():
    assert_unavailable(metrics.availability_pct("696", "0"))


def test_availability_missing_hours():
    assert_unavailable(metrics.availability_pct(None, "720"))


# --- capacity_factor_pct ----------------------------------------------------

def test_capacity_factor_normal():
    # 1800 / (10 * 720) = 0.25
    assert metrics.capacity_factor_pct("1800", "10", "720") == D("25.0")


def test_capacity_factor_zero_capacity():
    assert_unavailable(metrics.capacity_factor_pct("1800", "0", "720"))


def test_capacity_factor_zero_period():
    assert_unavailable(metrics.capacity_factor_pct("1800", "10", "0"))


# --- ppa_delivery_pct -------------------------------------------------------

def test_ppa_delivery_normal():
    assert metrics.ppa_delivery_pct("45", "50") == D("90.0")


def test_ppa_delivery_zero_contracted():
    assert_unavailable(metrics.ppa_delivery_pct("45", "0"))


def test_ppa_delivery_over_delivery_not_capped():
    assert metrics.ppa_delivery_pct("55", "50") == D("110.0")


# --- realised_price_eur_mwh -------------------------------------------------

def test_realised_price_normal():
    # (10*40 + 30*60) / 40 = 2200 / 40 = 55
    assert metrics.realised_price_eur_mwh([("10", "40"), ("30", "60")]) == D("55.00")


def test_realised_price_negative_price_is_valid():
    # (100*50 + 100*-10) / 200 = 4000 / 200 = 20
    assert metrics.realised_price_eur_mwh([("100", "50"), ("100", "-10")]) == D("20.00")


def test_realised_price_rounds_half_up():
    # 1 * 0.005 / 1 = 0.005 -> 0.01 (half up)
    assert metrics.realised_price_eur_mwh([("1", "0.005")]) == D("0.01")


def test_realised_price_empty():
    assert_unavailable(metrics.realised_price_eur_mwh([]))


def test_realised_price_zero_volume():
    assert_unavailable(metrics.realised_price_eur_mwh([("0", "50"), ("0", "40")]))


def test_realised_price_missing_value():
    assert_unavailable(metrics.realised_price_eur_mwh([("10", None)]))


# --- merchant_exposure_eur --------------------------------------------------

def test_merchant_exposure_normal():
    assert metrics.merchant_exposure_eur("100", "10") == D("1000.00")


def test_merchant_exposure_zero_volume_is_zero():
    assert metrics.merchant_exposure_eur("0", "10") == D("0.00")


def test_merchant_exposure_missing():
    assert_unavailable(metrics.merchant_exposure_eur(None, "10"))


def test_merchant_exposure_negative_move_allowed():
    assert metrics.merchant_exposure_eur("100", "-10") == D("-1000.00")


# --- downtime_hours ---------------------------------------------------------

def test_downtime_normal():
    statuses = ["OUTAGE"] * 3 + ["OK"] * 21
    assert metrics.downtime_hours(statuses, "1") == D("3")


def test_downtime_rounds_half_up():
    # 1 OUTAGE interval of 0.5 h = 0.5 h -> 1
    assert metrics.downtime_hours(["OUTAGE", "OK"], "0.5") == D("1")


def test_downtime_no_outage_is_zero():
    assert metrics.downtime_hours(["OK"] * 24, "1") == D("0")


def test_downtime_empty_statuses():
    assert_unavailable(metrics.downtime_hours([], "1"))


def test_downtime_unknown_status():
    assert_unavailable(metrics.downtime_hours(["OK", "BROKEN"], "1"))


def test_downtime_zero_interval():
    assert_unavailable(metrics.downtime_hours(["OUTAGE"], "0"))


# --- energy_loss_mwh --------------------------------------------------------

def test_energy_loss_normal():
    assert metrics.energy_loss_mwh("130.000", "125.592") == D("4.408")


def test_energy_loss_zero_loss():
    assert metrics.energy_loss_mwh("100", "100") == D("0.000")


def test_energy_loss_missing():
    assert_unavailable(metrics.energy_loss_mwh("130", None))


# --- incident_resolution_hours ----------------------------------------------

def test_incident_resolution_always_unavailable():
    result = metrics.incident_resolution_hours(["2", "4", "9"])
    assert_unavailable(result)
    assert "ticket" in result.reason.lower()


def test_incident_resolution_empty_also_unavailable():
    assert_unavailable(metrics.incident_resolution_hours([]))
    assert_unavailable(metrics.incident_resolution_hours(None))


# --- bess_availability_pct --------------------------------------------------

def test_bess_availability_normal():
    # 710 / 720 = 98.611 -> 98.6
    assert metrics.bess_availability_pct("710", "720") == D("98.6")


def test_bess_availability_zero_period():
    assert_unavailable(metrics.bess_availability_pct("710", "0"))


# --- bess_round_trip_efficiency_pct -----------------------------------------

def test_bess_round_trip_normal():
    assert metrics.bess_round_trip_efficiency_pct("88", "100") == D("88.0")


def test_bess_round_trip_zero_charged():
    assert_unavailable(metrics.bess_round_trip_efficiency_pct("88", "0"))


def test_bess_round_trip_missing():
    assert_unavailable(metrics.bess_round_trip_efficiency_pct(None, "100"))


# --- bess_cycle_utilisation_pct ---------------------------------------------

def test_bess_cycle_utilisation_normal():
    # 19 / (2 * 20) = 0.475
    assert metrics.bess_cycle_utilisation_pct("19", "20") == D("47.5")


def test_bess_cycle_utilisation_zero_usable():
    assert_unavailable(metrics.bess_cycle_utilisation_pct("19", "0"))


# --- cross-cutting rules ----------------------------------------------------

def test_decimal_inputs_are_accepted():
    assert metrics.availability_pct(D("696"), D("720")) == D("96.7")


def test_float_input_is_refused():
    assert_unavailable(metrics.availability_pct(696.0, "720"))
    assert_unavailable(metrics.energy_loss_mwh("130", 125.5))


def test_bool_input_is_refused():
    assert_unavailable(metrics.availability_pct(True, "720"))


@pytest.mark.parametrize("bad", ["abc", "NaN", "Infinity", "-Infinity", " ", "1e999999"])
def test_garbage_strings_are_refused(bad):
    assert_unavailable(metrics.availability_pct(bad, "720"))


@pytest.mark.parametrize(
    "call",
    [
        lambda: metrics.availability_pct("-1", "720"),
        lambda: metrics.energy_loss_mwh("-1", "5"),
        lambda: metrics.capacity_factor_pct("10", "-5", "720"),
        lambda: metrics.performance_ratio_pct("100", "-5", "10"),
        lambda: metrics.bess_round_trip_efficiency_pct("-1", "100"),
    ],
)
def test_negative_physical_quantities_are_refused(call):
    assert_unavailable(call())


CALLS = [
    lambda: metrics.actual_vs_expected_pct("95", "100"),
    lambda: metrics.performance_ratio_pct("40000", "5", "10000"),
    lambda: metrics.availability_pct("696", "720"),
    lambda: metrics.capacity_factor_pct("1800", "10", "720"),
    lambda: metrics.ppa_delivery_pct("45", "50"),
    lambda: metrics.realised_price_eur_mwh([("10", "40"), ("30", "60")]),
    lambda: metrics.merchant_exposure_eur("100", "10"),
    lambda: metrics.downtime_hours(["OUTAGE", "OK"], "1"),
    lambda: metrics.energy_loss_mwh("130", "125"),
    lambda: metrics.incident_resolution_hours(["1"]),
    lambda: metrics.bess_availability_pct("710", "720"),
    lambda: metrics.bess_round_trip_efficiency_pct("88", "100"),
    lambda: metrics.bess_cycle_utilisation_pct("19", "20"),
]


@pytest.mark.parametrize("call", CALLS)
def test_never_returns_a_float(call):
    result = call()
    assert not isinstance(result, float)
    assert isinstance(result, (Decimal, Unavailable))


def test_all_thirteen_functions_exist():
    names = [
        "actual_vs_expected_pct", "performance_ratio_pct", "availability_pct",
        "capacity_factor_pct", "ppa_delivery_pct", "realised_price_eur_mwh",
        "merchant_exposure_eur", "downtime_hours", "energy_loss_mwh",
        "incident_resolution_hours", "bess_availability_pct",
        "bess_round_trip_efficiency_pct", "bess_cycle_utilisation_pct",
    ]
    assert len(names) == 13
    for name in names:
        assert callable(getattr(metrics, name))


# --- robustness (verifier P2 items) -----------------------------------------

@pytest.mark.parametrize(
    "call",
    [
        lambda: metrics.availability_pct("1e30", "1e-30"),
        lambda: metrics.capacity_factor_pct("1e30", "1e-30", "1e-30"),
        lambda: metrics.performance_ratio_pct("1e30", "1e-30", "1e-30"),
        lambda: metrics.bess_cycle_utilisation_pct("1e30", "1e-30"),
        lambda: metrics.merchant_exposure_eur("1e30", "1e30"),
        lambda: metrics.energy_loss_mwh("1e30", "0"),
        lambda: metrics.realised_price_eur_mwh([("1e30", "1e30")]),
    ],
)
def test_extreme_values_give_unavailable_not_an_exception(call):
    result = call()
    assert isinstance(result, (Decimal, Unavailable))


def test_extreme_overflow_is_unavailable():
    assert_unavailable(metrics.availability_pct("1e30", "1e-30"))


@pytest.mark.parametrize(
    "result",
    [
        metrics.availability_pct("-0", "720"),
        metrics.merchant_exposure_eur("0", "-10"),
        metrics.energy_loss_mwh("100", "100.0004"),
        metrics.realised_price_eur_mwh([("10", "-0.001")]),
        metrics.energy_loss_mwh("0", "0.0004"),
    ],
)
def test_negative_zero_is_normalised(result):
    assert result.is_zero()
    assert not result.is_signed()
    assert not str(result).startswith("-")


def test_small_negative_value_that_rounds_to_zero_has_no_sign():
    assert str(metrics.merchant_exposure_eur("0", "-10")) == "0.00"
    assert str(metrics.energy_loss_mwh("100", "100.0004")) == "0.000"


def test_empty_generator_statuses_are_refused_like_an_empty_list():
    assert_unavailable(metrics.downtime_hours((s for s in []), "1"))


@pytest.mark.parametrize("bad", [(s for s in ["OUTAGE"]), {"OUTAGE"}, 5, "OUTAGE", {"OUTAGE": 1}])
def test_downtime_refuses_anything_but_a_list_or_tuple(bad):
    assert_unavailable(metrics.downtime_hours(bad, "1"))


def test_downtime_accepts_list_and_tuple_alike():
    assert metrics.downtime_hours(["OUTAGE", "OK"], "1") == D("1")
    assert metrics.downtime_hours(("OUTAGE", "OK"), "1") == D("1")


@pytest.mark.parametrize(
    "bad",
    [5, {"10": "40"}, ["12"], "12", {("10", "40")}, (p for p in [("10", "40")]), [("10", "40", "1")], [5]],
)
def test_realised_price_refuses_odd_containers(bad):
    assert_unavailable(metrics.realised_price_eur_mwh(bad))


def test_realised_price_accepts_list_and_tuple_alike():
    assert metrics.realised_price_eur_mwh([("10", "40"), ("30", "60")]) == D("55.00")
    assert metrics.realised_price_eur_mwh((["10", "40"], ["30", "60"])) == D("55.00")


@pytest.mark.parametrize("bad", ["1_000", "\uff11\uff12", "\u0661\u0662", "LONG", "1 2", "0x10", "--1", "1.2.3"])
def test_lenient_decimal_strings_are_refused(bad):
    if bad == "LONG":
        bad = "0." + "1" * 100000  # too long to use as a parameter id on Windows
    assert_unavailable(metrics.availability_pct(bad, "720"))


@pytest.mark.parametrize("good", ["85", "85.00", "+85.5", ".5", "5.", " 85 ", "1.5e2", "125.592"])
def test_plain_decimal_strings_still_work(good):
    assert isinstance(metrics.availability_pct(good, "720"), Decimal)


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_non_finite_decimal_objects_are_refused(bad):
    assert_unavailable(metrics.availability_pct(bad, "720"))
    assert_unavailable(metrics.merchant_exposure_eur("1", bad))


def test_callers_decimal_context_does_not_matter():
    import decimal

    with decimal.localcontext() as ctx:
        ctx.traps[decimal.Inexact] = True
        ctx.prec = 3
        ctx.rounding = decimal.ROUND_DOWN
        assert metrics.availability_pct("696", "720") == D("96.7")
        assert metrics.realised_price_eur_mwh([("10", "40"), ("30", "60")]) == D("55.00")
        assert metrics.energy_loss_mwh("130.000", "125.592") == D("4.408")


def test_energy_loss_is_negative_when_actual_exceeds_expected():
    # documented behaviour: the sign is kept, the caller decides what to say
    assert metrics.energy_loss_mwh("100", "110") == D("-10.000")


def test_unavailable_reason_does_not_echo_the_bad_status():
    huge = metrics.downtime_hours(["OK", "X" * 1_000_000], "1")
    assert_unavailable(huge)
    assert len(huge.reason) < 100


def test_deeply_nested_status_does_not_blow_the_stack():
    nested = []
    for _ in range(100_000):
        nested = [nested]
    assert_unavailable(metrics.downtime_hours([nested], "1"))
