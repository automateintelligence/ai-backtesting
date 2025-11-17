"""Metrics computation utilities."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Literal

from quant_scenario_engine.exceptions import ResourceLimitError

VarMethod = Literal["parametric", "historical"]


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


def var_cvar(returns: np.ndarray, alpha: float = 0.05, method: VarMethod = "historical") -> tuple[float, float]:
    if method == "historical":
        var = np.percentile(returns, alpha * 100)
    else:
        mean, std = returns.mean(), returns.std()
        var = mean + std * np.sqrt(252) * (-1.65)
    cvar = returns[returns <= var].mean() if (returns <= var).any() else var
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


def compute_metrics(pnl: np.ndarray, equity_curve: np.ndarray, var_method: VarMethod = "historical") -> MetricsReport:
    returns = np.diff(equity_curve, prepend=equity_curve[:1]) / equity_curve[:1]
    var, cvar = var_cvar(returns, method=var_method)
    return MetricsReport(
        mean_pnl=float(pnl.mean()),
        median_pnl=float(np.median(pnl)),
        max_drawdown=max_drawdown(equity_curve),
        sharpe=sharpe_ratio(returns),
        sortino=sortino_ratio(returns),
        var=var,
        cvar=cvar,
        var_method=var_method,
    )

