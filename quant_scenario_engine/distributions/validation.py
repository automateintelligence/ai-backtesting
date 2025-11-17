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

