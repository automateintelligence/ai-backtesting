"""Black-Scholes option pricer."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from quant_scenario_engine.exceptions import PricingError
from quant_scenario_engine.models.options import OptionSpec


@dataclass
class BlackScholesResult:
    prices: np.ndarray
    d1: np.ndarray
    d2: np.ndarray


def _compute_ttm(days: int) -> float:
    return max(days, 1) / 252.0


def black_scholes_price(path_slice: np.ndarray, option_spec: OptionSpec) -> BlackScholesResult:
    s = np.asarray(path_slice, dtype=float)
    k = option_spec.strike if isinstance(option_spec.strike, (int, float)) else s[0]
    t = _compute_ttm(option_spec.maturity_days)
    sigma = option_spec.implied_vol
    r = option_spec.risk_free_rate
    if sigma <= 0 or sigma > 5:
        raise PricingError("Invalid implied volatility")
    if k <= 0:
        raise PricingError("Invalid strike")

    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(s / k) + (r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
        d2 = d1 - sigma * math.sqrt(t)
        if option_spec.option_type == "call":
            prices = s * norm.cdf(d1) - k * math.exp(-r * t) * norm.cdf(d2)
        else:
            prices = k * math.exp(-r * t) * norm.cdf(-d2) - s * norm.cdf(-d1)

    if not np.all(np.isfinite(prices)):
        raise PricingError("Non-finite Black-Scholes prices")

    return BlackScholesResult(prices=prices, d1=d1, d2=d2)


class BlackScholesPricer:
    def price(self, path_slice: np.ndarray, option_spec: OptionSpec) -> np.ndarray:
        return black_scholes_price(path_slice, option_spec).prices

