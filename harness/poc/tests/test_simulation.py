import json
from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from conftest import ScriptedLLM, answer, tool_call

from energy_harness.agent import Agent
from energy_harness.config import POC_ROOT
from energy_harness.energy.parks import Park
from energy_harness.energy.sim import Scenario, SimulatedMetered, SimulatedPrices, SimulatedWeather, Simulator
from energy_harness.energy.sim import solar
from energy_harness.evals import EvalSuite, check_case, extract_numbers, run_case
from energy_harness.factory import build_registry
from energy_harness.config import load_settings
from energy_harness.tools import ToolError, ToolRegistry

UTC = timezone.utc
PARK = dict(id="p", name="Park P", latitude=56.0, longitude=10.0, capacity_mwp=50.0, ac_capacity_mw=40.0, tilt=25, azimuth=0, bidding_zone="DK1")


def make_sim(events=(), **kwargs) -> Simulator:
    data = {"seed": 7, "now": "2026-06-20T12:00:00Z", "parks": [PARK], "events": list(events)}
    data.update(kwargs)
    return Simulator(Scenario.model_validate(data))


def day(sim, d: str, park="p"):
    start = datetime.fromisoformat(d).replace(tzinfo=UTC)
    return sim.production(park, start, start + timedelta(days=1))


def energy(samples, field="metered_mw"):
    return sum((getattr(s, field) or 0.0) * 0.25 for s in samples)


# --- solar physics ---------------------------------------------------------------


def test_sun_is_high_at_solar_noon_in_summer_and_below_horizon_at_night():
    noon = datetime(2026, 6, 21, 11, 20, tzinfo=UTC)  # ~solar noon at 10°E
    sin_el, azimuth = solar.sun_position(56.0, 10.0, noon)
    assert 0.82 < sin_el < 0.86  # elevation ≈ 57.5°
    assert 170 < azimuth < 190
    assert solar.sun_position(56.0, 10.0, datetime(2026, 6, 21, 23, 0, tzinfo=UTC))[0] < 0
    assert 800 < solar.clear_sky_ghi(sin_el) < 1000
    assert solar.clear_sky_ghi(-0.1) == 0


def test_tilted_plane_gains_in_winter_sun():
    sin_el, az = solar.sun_position(56.0, 10.0, datetime(2026, 12, 21, 11, 20, tzinfo=UTC))
    ghi = solar.clear_sky_ghi(sin_el)
    assert solar.plane_of_array(ghi, sin_el, az, 40, 0) > 1.5 * ghi
    assert solar.plane_of_array(ghi, sin_el, az, 40, 180) < ghi  # facing north


# --- determinism and plausibility -------------------------------------------------


def test_same_seed_same_data_regardless_of_requested_range():
    a, b = make_sim(), make_sim()
    single = day(a, "2026-06-10")
    within = b.production("p", datetime(2026, 6, 8, tzinfo=UTC), datetime(2026, 6, 12, tzinfo=UTC))
    assert [s.metered_mw for s in single] == [s.metered_mw for s in within if s.time.date() == date(2026, 6, 10)]
    assert make_sim(seed=8).production("p", datetime(2026, 6, 10, tzinfo=UTC), datetime(2026, 6, 11, tzinfo=UTC)) != single


def test_production_is_physically_plausible():
    sim = make_sim()
    for d in ("2026-06-01", "2026-06-02", "2026-06-03"):
        samples = day(sim, d)
        assert len(samples) == 96
        assert all(0 <= s.metered_mw <= 40 * 1.05 for s in samples)  # never above AC limit (+noise)
        assert all(s.metered_mw == 0 for s in samples if s.time.hour in (0, 1, 22, 23))
        assert 0 < energy(samples) / 50 < 8  # 0–8 kWh/kWp per June day
    winter = Simulator(Scenario.model_validate({"seed": 7, "now": "2026-12-20T12:00:00Z", "parks": [PARK]}))
    june = sum(energy(day(sim, f"2026-06-{d:02d}")) for d in range(1, 11))
    december = sum(energy(day(winter, f"2026-12-{d:02d}")) for d in range(1, 11))
    assert june > 3 * december


# --- events ---------------------------------------------------------------------------


def test_outage_degradation_curtailment_and_gap():
    events = [
        {"type": "outage", "park": "p", "start": "2026-06-10T00:00:00Z", "end": "2026-06-11T00:00:00Z", "fraction": 1.0},
        {"type": "outage", "park": "p", "start": "2026-06-11T00:00:00Z", "end": "2026-06-12T00:00:00Z", "fraction": 0.5},
        {"type": "degradation", "park": "p", "start": "2026-06-12T00:00:00Z", "end": "2026-06-13T00:00:00Z", "fraction": 0.2},
        {"type": "curtailment", "park": "p", "start": "2026-06-13T00:00:00Z", "end": "2026-06-14T00:00:00Z", "limit_mw": 5},
        {"type": "data_gap", "park": "p", "start": "2026-06-14T10:00:00Z", "end": "2026-06-14T12:00:00Z"},
    ]
    sim = make_sim(events, curtail_on_negative_prices=False)

    full = day(sim, "2026-06-10")
    assert energy(full) == 0 and all(s.availability == 0 for s in full)

    half = day(sim, "2026-06-11")
    assert energy(half) == pytest.approx(0.5 * energy(half, "expected_mw"), rel=0.02)

    soiled = day(sim, "2026-06-12")
    assert energy(soiled) == pytest.approx(0.8 * energy(soiled, "expected_mw"), rel=0.02)
    assert all(s.availability == 1 for s in soiled)

    capped = day(sim, "2026-06-13")
    assert max(s.metered_mw for s in capped) <= 5 * 1.05
    assert sum(s.curtailed for s in capped) > 10

    gap = day(sim, "2026-06-14")
    assert sum(s.metered_mw is None for s in gap) == 8


def test_negative_price_event_curtails_park_in_that_zone():
    event = {"type": "price", "zone": "dk1", "start": "2026-06-14T10:00:00Z", "end": "2026-06-14T12:00:00Z", "price": -20}
    sim = make_sim([event])
    prices = sim.prices("DK1", date(2026, 6, 14), date(2026, 6, 14))
    assert sum(p.eur_per_mwh == -20 for p in prices) == 8
    samples = day(sim, "2026-06-14")
    window = [s for s in samples if 10 <= s.time.hour < 12]
    assert all(s.metered_mw == 0 and s.curtailed for s in window)
    assert not any(s.curtailed for s in samples if s.time.hour == 9)


def test_prices_cover_market_days_including_dst_change():
    sim = make_sim()
    assert len(sim.prices("SE3", date(2026, 6, 14), date(2026, 6, 14))) == 96
    assert len(sim.prices("SE3", date(2026, 10, 25), date(2026, 10, 25))) == 100  # clocks go back
    with pytest.raises(ToolError, match="unknown bidding zone"):
        sim.prices("XX", date(2026, 6, 14), date(2026, 6, 14))


def test_scenario_validation():
    with pytest.raises(ValidationError, match="unknown parks"):
        make_sim([{"type": "outage", "park": "nope", "start": "2026-06-10T00:00:00Z", "end": "2026-06-11T00:00:00Z", "fraction": 1}])
    with pytest.raises(ValidationError, match="needs limit_mw"):
        make_sim([{"type": "curtailment", "park": "p", "start": "2026-06-10T00:00:00Z", "end": "2026-06-11T00:00:00Z"}])
    with pytest.raises(ValidationError, match="after start"):
        make_sim([{"type": "data_gap", "park": "p", "start": "2026-06-11T00:00:00Z", "end": "2026-06-10T00:00:00Z"}])


# --- adapters -----------------------------------------------------------------------


def test_metered_stops_at_now_and_refuses_the_future():
    sim = make_sim()
    site = Park.model_validate(PARK)
    today = SimulatedMetered(sim).production(site, date(2026, 6, 20), date(2026, 6, 20))
    assert len(today) == 48 and today[-1].time == datetime(2026, 6, 20, 11, 45, tzinfo=UTC)
    with pytest.raises(ToolError, match="future"):
        SimulatedMetered(sim).production(site, date(2026, 6, 21), date(2026, 6, 21))


def test_tomorrows_prices_appear_after_the_auction():
    morning = SimulatedPrices(make_sim(now="2026-06-20T08:00:00Z"))
    afternoon = SimulatedPrices(make_sim(now="2026-06-20T12:00:00Z"))
    assert morning.day_ahead("DK1", date(2026, 6, 21), date(2026, 6, 21))[0] == []
    assert len(afternoon.day_ahead("DK1", date(2026, 6, 21), date(2026, 6, 21))[0]) == 96


def test_weather_matches_open_meteo_hour_ending_layout():
    hours = SimulatedWeather(make_sim()).hourly(56.0, 10.0, date(2026, 6, 20), date(2026, 6, 21), tilt=25, azimuth=0)
    assert len(hours) == 48
    assert hours[0].time == datetime(2026, 6, 20, 0, 0, tzinfo=UTC)
    assert hours[-1].time == datetime(2026, 6, 21, 23, 0, tzinfo=UTC)
    assert max(h.poa_w_m2 for h in hours) > 0


# --- shipped scenario through the real tools -----------------------------------------------


@pytest.fixture(scope="module")
def shipped():
    settings = load_settings(POC_ROOT / "config.yaml", env={"ENERGY_HARNESS_DATA_SOURCE": "simulation"})
    sim = Simulator(Scenario.from_file(settings.simulation_file))
    return sim, build_registry(settings, simulator=sim)


def run_tool(registry, name, **args):
    result = registry.execute(name, json.dumps(args))
    assert result.ok, result.content
    return json.loads(result.content)


def test_shipped_scenario_incidents_are_visible_in_tools(shipped):
    _, reg = shipped
    assert "get_metered_production" in reg.names()
    east = run_tool(reg, "get_metered_production", park="sim-dk-east", start_date="2026-10-14")["daily"][0]
    assert east["energy_mwh"] == 0 and east["availability_pct"] == 0
    west = run_tool(reg, "get_metered_production", park="sim-dk-west", start_date="2026-10-09")["daily"][0]
    assert 50 < west["availability_pct"] < 90
    assert run_tool(reg, "get_metered_production", park="sim-dk-west", start_date="2026-10-11")["daily"][0]["curtailed_intervals"] == 12
    assert run_tool(reg, "get_metered_production", park="sim-pl", start_date="2026-10-12")["daily"][0]["data_completeness_pct"] < 90
    dk1 = run_tool(reg, "get_day_ahead_prices", bidding_zone="DK1", start_date="2026-10-11")["daily"][0]
    assert dk1["min"] == -18.5 and dk1["min_at"] == "12:00" and dk1["negative_intervals"] == 12

    metered = run_tool(reg, "get_metered_production", park="sim-pl", start_date="2026-10-13", end_date="2026-10-16")["total_energy_mwh"]
    estimated = run_tool(reg, "estimate_pv_production", park="sim-pl", start_date="2026-10-13", end_date="2026-10-16")["total_energy_mwh"]
    assert metered / estimated == pytest.approx(0.85, abs=0.02)  # soiling


# --- evals --------------------------------------------------------------------------------


def test_extract_numbers():
    assert extract_numbers("1,234.5 MWh, −18.5 EUR at 12:00 on 2026-10-11") == [1234.5, -18.5, 12, 0, 2026, 10, 11]  # date parts stay positive
    assert extract_numbers("about 183.5MWh") == [183.5]


def test_shipped_eval_suite_parses_and_ground_truth_resolves(shipped):
    _, reg = shipped
    suite = EvalSuite.from_file(POC_ROOT / "evals.yaml")
    assert len({c.id for c in suite.cases}) == len(suite.cases)
    from energy_harness.evals import expected_number

    for case in suite.cases:
        if case.expect.number:
            expected_number(case.expect.number, reg)  # raises if a tool call fails
        assert set(case.expect.tools_called) <= set(reg.names())


def test_run_case_scores_scripted_agents(shipped):
    sim, reg = shipped
    case = next(c for c in EvalSuite.from_file(POC_ROOT / "evals.yaml").cases if c.id == "metered-energy")
    truth = run_tool(reg, "get_metered_production", park="sim-dk-west", start_date="2026-10-10")["daily"][0]["energy_mwh"]

    def agent(final_text):
        llm = ScriptedLLM(tool_call("get_metered_production", '{"park": "sim-dk-west", "start_date": "2026-10-10"}'), answer(final_text))
        return Agent(llm, reg, today=lambda: sim.today().isoformat())

    good = run_case(agent(f"Jutland produced {truth} MWh on 2026-10-10."), case, reg)
    assert good.passed and good.tools == ["get_metered_production"]
    bad = run_case(agent("It produced about 12 MWh."), case, reg)
    assert not bad.passed and "no match" in [c for c in bad.checks if c.name == "number"][0].detail

    lazy = run_case(Agent(ScriptedLLM(answer(f"{truth} MWh")), reg), case, reg)
    assert not lazy.passed  # right number but never looked at the meter
