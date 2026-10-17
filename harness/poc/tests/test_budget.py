import pytest

from energy_harness.budget import BudgetExceeded, RequestBudget


def test_waits_when_minute_window_is_full(clock):
    budget = RequestBudget(per_minute=3, per_day=None, clock=clock, sleep=clock.sleep)
    for _ in range(3):
        budget.acquire()
    assert clock.sleeps == []
    budget.acquire()
    assert len(clock.sleeps) == 1 and 59 < clock.sleeps[0] <= 60.1


def test_blocks_at_daily_cap(clock):
    budget = RequestBudget(per_minute=None, per_day=2, clock=clock, sleep=clock.sleep)
    budget.acquire()
    budget.acquire()
    assert budget.remaining_today == 0
    with pytest.raises(BudgetExceeded):
        budget.acquire()


def test_daily_count_resets_at_utc_midnight(clock):
    budget = RequestBudget(per_minute=None, per_day=1, clock=clock, sleep=clock.sleep)
    budget.acquire()
    clock.now += 86_400
    budget.acquire()
    assert budget.used_today == 1


def test_daily_count_persists_across_instances(clock, tmp_path):
    state = tmp_path / "budget.json"
    RequestBudget(per_minute=None, per_day=5, state_file=state, clock=clock).acquire()
    again = RequestBudget(per_minute=None, per_day=5, state_file=state, clock=clock)
    assert again.used_today == 1


def test_corrupt_state_file_is_ignored(clock, tmp_path):
    state = tmp_path / "budget.json"
    state.write_text("not json")
    assert RequestBudget(per_day=5, state_file=state, clock=clock).used_today == 0
