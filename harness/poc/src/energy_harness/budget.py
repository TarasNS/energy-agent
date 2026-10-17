"""Local request guard mirroring OpenRouter's free-tier limits.

OpenRouter enforces the real limits account-wide; this guard only stops the
harness from burning the daily quota (failed requests count too) and spaces
requests to stay under the per-minute limit.
"""

from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class BudgetExceeded(Exception):
    """The local daily request budget is used up."""


class RequestBudget:
    def __init__(
        self,
        per_minute: int | None = 20,
        per_day: int | None = 50,
        state_file: Path | None = None,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self.state_file = state_file
        self._clock = clock
        self._sleep = sleep
        self._recent: deque[float] = deque()
        self._date, self._count = self._load()

    def acquire(self) -> None:
        """Reserve one request; sleeps if the per-minute window is full."""
        self._roll_day()
        if self.per_day is not None and self._count >= self.per_day:
            raise BudgetExceeded(
                f"Local daily budget of {self.per_day} requests is used up "
                f"(resets at 00:00 UTC). Raise budget.requests_per_day in config.yaml "
                f"if your OpenRouter account allows more."
            )
        if self.per_minute:
            self._drop_old()
            if len(self._recent) >= self.per_minute:
                self._sleep(max(0.0, 60.0 - (self._clock() - self._recent[0])) + 0.05)
                self._drop_old()
        self._recent.append(self._clock())
        self._count += 1
        self._save()

    @property
    def used_today(self) -> int:
        self._roll_day()
        return self._count

    @property
    def remaining_today(self) -> int | None:
        return None if self.per_day is None else max(0, self.per_day - self.used_today)

    def _today(self) -> str:
        return datetime.fromtimestamp(self._clock(), timezone.utc).date().isoformat()

    def _roll_day(self) -> None:
        if self._date != self._today():
            self._date, self._count = self._today(), 0

    def _drop_old(self) -> None:
        cutoff = self._clock() - 60.0
        while self._recent and self._recent[0] <= cutoff:
            self._recent.popleft()

    def _load(self) -> tuple[str, int]:
        today = self._today()
        if self.state_file and self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                if data.get("date") == today:
                    return today, int(data.get("count", 0))
            except (ValueError, OSError):
                pass
        return today, 0

    def _save(self) -> None:
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"date": self._date, "count": self._count}))
