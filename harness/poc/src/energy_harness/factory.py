"""Wire settings into a ready-to-run Agent."""

from __future__ import annotations

import httpx

from .agent import Agent
from .budget import RequestBudget
from .builtin_tools import builtin_tools
from .config import Settings
from .energy import build_energy_tools
from .energy.parks import ParkRegistry
from .energy.sim import Scenario, SimulatedMetered, SimulatedPrices, SimulatedWeather, Simulator
from .llm import OpenRouterClient
from .tools import ToolRegistry


def build_budget(settings: Settings) -> RequestBudget:
    return RequestBudget(
        per_minute=settings.budget.requests_per_minute,
        per_day=settings.budget.requests_per_day,
        state_file=settings.runs_dir / "budget.json",
    )


def build_client(settings: Settings, models: list[str] | None = None, **kwargs) -> OpenRouterClient:
    if not settings.api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key.")
    kwargs.setdefault("budget", build_budget(settings))
    return OpenRouterClient(
        settings.api_key,
        models or settings.models,
        base_url=settings.base_url,
        temperature=settings.temperature,
        timeout_s=settings.timeout_s,
        **kwargs,
    )


def build_simulator(settings: Settings) -> Simulator | None:
    if settings.data_source != "simulation":
        return None
    return Simulator(Scenario.from_file(settings.simulation_file))


def build_registry(settings: Settings, http: httpx.Client | None = None, simulator: Simulator | None = None) -> ToolRegistry:
    if simulator:
        energy = build_energy_tools(
            simulator.parks,
            today=simulator.today,
            weather=SimulatedWeather(simulator),
            prices=SimulatedPrices(simulator),
            metered=SimulatedMetered(simulator),
        )
    else:
        energy = build_energy_tools(ParkRegistry.from_file(settings.parks_file), http)
    return ToolRegistry([*builtin_tools(), *energy])


def build_agent(settings: Settings, *, models: list[str] | None = None, tracer=None, simulator: Simulator | None = None) -> Agent:
    simulator = simulator or build_simulator(settings)
    kwargs = {"today": lambda: simulator.today().isoformat()} if simulator else {}
    return Agent(
        build_client(settings, models),
        build_registry(settings, simulator=simulator),
        max_steps=settings.max_steps,
        tracer=tracer,
        **kwargs,
    )
