"""Settings loaded from config.yaml plus environment variables / .env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Mapping

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

POC_ROOT = Path(__file__).resolve().parents[2]


class BudgetConfig(BaseModel):
    requests_per_minute: int | None = 20
    requests_per_day: int | None = 50


class Settings(BaseModel):
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    models: list[str] = Field(min_length=1)
    temperature: float = 0.2
    max_steps: int = 8
    timeout_s: float = 90
    budget: BudgetConfig = BudgetConfig()
    parks_file: Path
    runs_dir: Path
    data_source: Literal["live", "simulation"] = "live"
    simulation_file: Path


def find_config(explicit: str | Path | None = None, env: Mapping[str, str] = os.environ) -> Path:
    candidates = [explicit, env.get("ENERGY_HARNESS_CONFIG"), Path.cwd() / "config.yaml", POC_ROOT / "config.yaml"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError("config.yaml not found; pass --config or set ENERGY_HARNESS_CONFIG")


def load_settings(config_path: str | Path | None = None, env: Mapping[str, str] | None = None) -> Settings:
    if env is None:
        load_dotenv(Path.cwd() / ".env")
        load_dotenv(POC_ROOT / ".env")
        env = os.environ
    path = find_config(config_path, env)
    data = yaml.safe_load(path.read_text()) or {}

    defaults = {"parks_file": "parks.yaml", "runs_dir": "runs", "simulation_file": "simulation.yaml"}
    for key, default in defaults.items():
        value = Path(data.get(key, default))
        data[key] = value if value.is_absolute() else path.parent / value

    data["api_key"] = env.get("OPENROUTER_API_KEY") or None
    if env.get("ENERGY_HARNESS_DATA_SOURCE"):
        data["data_source"] = env["ENERGY_HARNESS_DATA_SOURCE"]
    if env.get("ENERGY_HARNESS_MODELS"):
        data["models"] = [m.strip() for m in env["ENERGY_HARNESS_MODELS"].split(",") if m.strip()]
    return Settings.model_validate(data)
