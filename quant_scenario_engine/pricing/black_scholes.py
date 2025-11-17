"""Black-Scholes option pricer.

Implements basic European pricing with light guards for IV/strike edge cases
and horizon vs. maturity handling. The intent is robustness for simulation
workloads rather than full market-calibration fidelity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from scipy.stats import norm

from quant_scenario_engine.exceptions import PricingError
from quant_scenario_engine.models.options import OptionSpec


@dataclass
class BlackScholesResult:
    prices: np.ndarray
    d1: np.ndarray
    d2: np.ndarray
def _resolve_strike(option_spec: OptionSpec, spot: float) -> float:
    strike = option_spec.strike
    if isinstance(strike, str):
        if strike.lower() in {"atm", "spot"}:
            return float(spot)
        raise PricingError(f"Unsupported strike spec: {strike}")
    return float(strike)


def _compute_ttm(maturity_days: int, horizon_steps: int | None = None) -> float:
    """Convert maturity to years while acknowledging simulation horizon.

    - Clamp to at least one trading day to avoid divide-by-zero
    - If a horizon is provided (number of bars in the path), cap maturity to
      that horizon to avoid negative time deltas after expiry.
    """

    days = max(maturity_days, 1)
    if horizon_steps is not None:
        days = min(days, max(int(horizon_steps), 1))
    return days / 252.0


def _validate_inputs(path_slice: np.ndarray, option_spec: OptionSpec) -> Tuple[np.ndarray, float, float, float, float]:
    s = np.asarray(path_slice, dtype=float)
    if s.ndim != 1:
        raise PricingError("path_slice must be 1-D for a single path")
    if s.size == 0:
        raise PricingError("path_slice is empty")
    if np.any(s <= 0):
        raise PricingError("Non-positive spot path encountered")

    k = _resolve_strike(option_spec, spot=s[0])
    if not math.isfinite(k) or k <= 0:
        raise PricingError("Invalid strike")

    t = _compute_ttm(option_spec.maturity_days, horizon_steps=s.size)
    sigma = float(option_spec.implied_vol)
    r = float(option_spec.risk_free_rate)
    if sigma <= 0 or sigma > 5:
        raise PricingError("Invalid implied volatility")
    if t <= 0:
        raise PricingError("Invalid time to maturity")

    return s, k, t, sigma, r


def black_scholes_price(path_slice: np.ndarray, option_spec: OptionSpec) -> BlackScholesResult:
    s, k, t, sigma, r = _validate_inputs(path_slice, option_spec)

    # Add a small epsilon around ATM to reduce numerical noise
    eps = 1e-12
    k_safe = max(k, eps)
    sqrt_t = math.sqrt(t)

    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(s / k_safe) + (r + 0.5 * sigma**2) * t) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t
        if option_spec.option_type == "call":
            prices = s * norm.cdf(d1) - k_safe * math.exp(-r * t) * norm.cdf(d2)
        elif option_spec.option_type == "put":
            prices = k_safe * math.exp(-r * t) * norm.cdf(-d2) - s * norm.cdf(-d1)
        else:
            raise PricingError(f"Unsupported option_type: {option_spec.option_type}")

    if not np.all(np.isfinite(prices)):
        raise PricingError("Non-finite Black-Scholes prices")

    return BlackScholesResult(prices=prices * option_spec.contracts, d1=d1, d2=d2)


class BlackScholesPricer:
    """Lightweight European option pricer.

    Early exercise for American options is intentionally not modelled; callers
    should set ``early_exercise=False`` or provide an alternate pricer.
    """

    def price(self, path_slice: np.ndarray, option_spec: OptionSpec) -> np.ndarray:
        result = black_scholes_price(path_slice, option_spec)
        return result.prices
