"""Scenario file: simulated fleet, clock and scripted incidents."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from ..parks import Park

EventType = Literal["outage", "curtailment", "degradation", "data_gap", "price"]


class SimEvent(BaseModel):
    """A scripted incident, active on [start, end).

    outage       park loses `fraction` of its inverters (1.0 = everything down)
    curtailment  park output capped at `limit_mw` (grid operator / setpoint)
    degradation  park output reduced by `fraction` (soiling, snow, string faults); not visible in availability
    data_gap     no metered values recorded
    price        day-ahead price in `zone` fixed at `price` EUR/MWh
    """

    type: EventType
    start: datetime
    end: datetime
    park: str | None = None
    zone: str | None = None
    fraction: float | None = Field(default=None, gt=0, le=1)
    limit_mw: float | None = Field(default=None, ge=0)
    price: float | None = None
    note: str | None = None

    @field_validator("start", "end")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _check(self) -> "SimEvent":
        if self.end <= self.start:
            raise ValueError("event end must be after start")
        needs = {
            "outage": ("park", "fraction"),
            "degradation": ("park", "fraction"),
            "curtailment": ("park", "limit_mw"),
            "data_gap": ("park",),
            "price": ("zone", "price"),
        }[self.type]
        missing = [f for f in needs if getattr(self, f) is None]
        if missing:
            raise ValueError(f"{self.type} event needs {', '.join(missing)}")
        if self.zone:
            self.zone = self.zone.upper()
        return self

    def active(self, t: datetime) -> bool:
        return self.start <= t < self.end


class Scenario(BaseModel):
    seed: int = 42
    now: datetime | None = None  # simulated clock; None = real time
    history_days: int = Field(default=90, ge=1)
    curtail_on_negative_prices: bool = True
    parks: list[Park] = Field(min_length=1)
    events: list[SimEvent] = []

    @field_validator("now")
    @classmethod
    def _utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _check_parks(self) -> "Scenario":
        ids = {p.id for p in self.parks}
        unknown = sorted({e.park for e in self.events if e.park and e.park not in ids})
        if unknown:
            raise ValueError(f"events reference unknown parks: {', '.join(unknown)}")
        return self

    @classmethod
    def from_file(cls, path: Path) -> "Scenario":
        return cls.model_validate(yaml.safe_load(Path(path).read_text()) or {})
