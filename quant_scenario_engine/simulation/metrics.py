"""Metrics computation utilities."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal, Optional

import numpy as np
from scipy.stats import norm

VarMethod = Literal["parametric", "historical"]
CovarianceEstimator = Literal["sample", "ledoit_wolf", "shrinkage_delta"]


def max_drawdown(equity_curve: np.ndarray) -> float:
    cum_max = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - cum_max) / cum_max
    return float(drawdowns.min())


def sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float:
    excess = returns - risk_free / 252
    denom = np.std(excess)
    return float(excess.mean() / denom) if denom != 0 else 0.0


def sortino_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float:
    downside = returns[returns < 0]
    denom = np.std(downside) if len(downside) else 0
    return float((returns.mean() - risk_free / 252) / denom) if denom != 0 else 0.0


def _parametric_var(returns: np.ndarray, alpha: float, covariance_estimator: CovarianceEstimator) -> float:
    mean = returns.mean()
    std = returns.std()
    if covariance_estimator == "shrinkage_delta":
        # Light shrinkage toward zero variance to stabilize outliers
        std = math.sqrt(0.9 * std**2 + 0.1 * (returns.mean() ** 2))
    # ledtoit_wolf not implemented fully; treat same as sample but callable for interface completeness
    z = norm.ppf(alpha)
    return float(mean + std * z)


def var_cvar(
    returns: np.ndarray,
    alpha: float = 0.05,
    method: VarMethod = "historical",
    covariance_estimator: CovarianceEstimator = "sample",
) -> tuple[float, float]:
    if method == "historical":
        var = np.percentile(returns, alpha * 100)
    else:
        var = _parametric_var(returns, alpha, covariance_estimator)
    tail = returns[returns <= var]
    cvar = tail.mean() if tail.size else var
    return float(var), float(cvar)


@dataclass
class MetricsReport:
    mean_pnl: float
    median_pnl: float
    max_drawdown: float
    sharpe: float
    sortino: float
    var: float
    cvar: float
    var_method: VarMethod
    lookback_window: Optional[int]
    covariance_estimator: CovarianceEstimator
    bankruptcy_rate: float
    early_exercise_events: int

    def _unit_label(self, field: str) -> str:
        unit_map = {
            "mean_pnl": "$",
            "median_pnl": "$",
            "max_drawdown": "%",
            "var": "%",
            "cvar": "%",
            "bankruptcy_rate": "%",
        }
        return f"{field}{unit_map.get(field, '')}"

    def to_formatted_dict(self, include_units: bool = True) -> dict[str, object]:
        formatted: dict[str, object] = {}
        for key, value in asdict(self).items():
            label = self._unit_label(key) if include_units else key
            if isinstance(value, float):
                formatted[label] = round(value, 2)
            else:
                formatted[label] = value
        return formatted

    def __str__(self) -> str:  # pragma: no cover - presentation only
        pairs = [f"{k}={v}" for k, v in self.to_formatted_dict(include_units=True).items()]
        return ", ".join(pairs)

    __repr__ = __str__


def compute_metrics(
    pnl: np.ndarray,
    equity_curve: np.ndarray,
    *,
    var_method: VarMethod = "historical",
    lookback_window: Optional[int] = None,
    covariance_estimator: CovarianceEstimator = "sample",
    bankruptcy_rate: float = 0.0,
    early_exercise_events: int = 0,
    alpha: float = 0.05,
    risk_free: float = 0.0,
) -> MetricsReport:
    if equity_curve.ndim != 1:
        equity_curve = np.asarray(equity_curve).reshape(-1)
    returns = np.diff(equity_curve, prepend=equity_curve[:1]) / equity_curve[:1]
    if lookback_window:
        returns = returns[-lookback_window:]
    var, cvar = var_cvar(returns, alpha=alpha, method=var_method, covariance_estimator=covariance_estimator)
    return MetricsReport(
        mean_pnl=float(np.mean(pnl)),
        median_pnl=float(np.median(pnl)),
        max_drawdown=max_drawdown(equity_curve),
        sharpe=sharpe_ratio(returns, risk_free=risk_free),
        sortino=sortino_ratio(returns, risk_free=risk_free),
        var=var,
        cvar=cvar,
        var_method=var_method,
        lookback_window=lookback_window,
        covariance_estimator=covariance_estimator,
        bankruptcy_rate=float(bankruptcy_rate),
        early_exercise_events=int(early_exercise_events),
    )
