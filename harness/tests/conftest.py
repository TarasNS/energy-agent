"""Shared test helpers for the harness. No network, no real API key: the model is always scripted."""

from __future__ import annotations

from harness.dataset import build
from harness.energy_tools import build_energy_tools


def fake_propose(action: str, asset: str, reason: str) -> str:
    return "P-1"


def registry_for_tests():
    return build_energy_tools(build(), fake_propose)
