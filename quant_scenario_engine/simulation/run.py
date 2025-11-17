"""Simulation orchestrator entry points.

This module wraps the compare workflow for backwards compatibility while the
core logic lives in :mod:`quant_scenario_engine.simulation.compare`.
"""

from __future__ import annotations

from quant_scenario_engine.simulation.compare import RunResult, run_compare  # re-export

__all__ = ["RunResult", "run_compare"]
