"""Registry of PV parks, loaded from parks.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from ..tools import ToolError


class Park(BaseModel):
    id: str
    name: str
    country: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity_mwp: float = Field(gt=0)
    ac_capacity_mw: float | None = Field(default=None, gt=0)
    tilt: float | None = Field(default=None, ge=0, le=90)
    azimuth: float | None = Field(default=None, ge=-180, le=180)  # Open-Meteo: 0 = south
    bidding_zone: str | None = None


class ParkRegistry:
    def __init__(self, parks: list[Park]) -> None:
        self.parks = parks

    @classmethod
    def from_file(cls, path: Path) -> "ParkRegistry":
        if not Path(path).exists():
            return cls([])
        data = yaml.safe_load(Path(path).read_text()) or {}
        return cls([Park.model_validate(p) for p in data.get("parks") or []])

    def get(self, key: str) -> Park:
        wanted = key.strip().lower()
        for park in self.parks:
            if wanted in (park.id.lower(), park.name.lower()):
                return park
        known = ", ".join(p.id for p in self.parks) or "none configured"
        raise ToolError(f"unknown park '{key}'. Known parks: {known}. Use list_parks.")
