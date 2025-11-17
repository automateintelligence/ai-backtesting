"""Validation helpers for distributions."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.exceptions import DistributionFitError


def validate_returns(returns: np.ndarray, min_samples: int) -> None:
    if returns is None or len(returns) < min_samples:
        raise DistributionFitError("Insufficient samples for fit")


def validate_params_bounds(params: dict, bounds: dict) -> None:
    for key, (lower, upper) in bounds.items():
        if key not in params:
            raise DistributionFitError(f"Missing parameter {key}")
        val = params[key]
        if val < lower or val > upper:
            raise DistributionFitError(f"Parameter {key} out of bounds: {val}")


def enforce_convergence(values: dict) -> None:
    for key, val in values.items():
        if val is None or not np.isfinite(val):
            raise DistributionFitError(f"Non-finite parameter {key}: {val}")


def enforce_heavy_tails(excess_kurtosis: float) -> None:
    if excess_kurtosis < 1.0:
        raise DistributionFitError(
            f"Excess kurtosis {excess_kurtosis:.3f} below required heavy-tail threshold (>= 1.0)"
        )


def fallback_to_laplace(returns: np.ndarray):
    from quant_scenario_engine.distributions.laplace import LaplaceDistribution

    lap = LaplaceDistribution()
    lap.fit(returns)
    lap.metadata.fallback_model = "laplace"
    lap.metadata.fit_status = "warn"
    return lap
