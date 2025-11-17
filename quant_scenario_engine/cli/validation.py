"""CLI validation helpers (lightweight stubs)."""

from __future__ import annotations

from quant_scenario_engine.exceptions import ConfigValidationError


def require_positive(name: str, value: int | float) -> None:
    if value <= 0:
        raise ConfigValidationError(f"{name} must be > 0")


def validate_compare_inputs(paths: int, steps: int, seed: int | None) -> None:
    require_positive("paths", paths)
    require_positive("steps", steps)
    if seed is None:
        raise ConfigValidationError("seed is required for reproducibility")

