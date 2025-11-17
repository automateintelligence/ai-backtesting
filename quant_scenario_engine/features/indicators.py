"""Lightweight technical indicator wrappers with pandas-ta fallback.

Implements SMA, RSI, and volume z-score utilities. If pandas-ta is not
installed, falls back to numpy/pandas computations and logs a warning.
"""

from __future__ import annotations

import warnings
from typing import Iterable

import numpy as np
import pandas as pd

try:  # Optional dependency
    import pandas_ta as ta  # type: ignore
except Exception:  # pragma: no cover - presence is environment-specific
    ta = None

from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="features.indicators")


def _warn_once(message: str, _emitted: set[str] = set()) -> None:
    if message in _emitted:
        return
    warnings.warn(message)
    log.warning(message)
    _emitted.add(message)


def compute_sma(series: pd.Series, length: int) -> pd.Series:
    """Compute simple moving average.

    Uses pandas-ta when available; otherwise uses rolling mean.
    """

    if length <= 0:
        raise ValueError("length must be positive")

    if ta is not None:
        return ta.sma(series, length=length).bfill().fillna(series)

    _warn_once("pandas-ta not installed, falling back to pandas rolling mean for SMA")
    return series.rolling(window=length, min_periods=1).mean()


def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Compute Relative Strength Index.

    Falls back to a simple implementation if pandas-ta is unavailable.
    """

    if length <= 0:
        raise ValueError("length must be positive")

    if ta is not None:
        return ta.rsi(series, length=length).fillna(50.0)

    _warn_once("pandas-ta not installed, using fallback RSI computation")
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(length, min_periods=length).mean()
    avg_loss = loss.rolling(length, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def compute_volume_z(volume: pd.Series, window: int = 20) -> pd.Series:
    """Compute volume z-score over a rolling window."""

    if window <= 1:
        raise ValueError("window must be > 1 for z-score")

    rolling_mean = volume.rolling(window=window, min_periods=2).mean()
    rolling_std = volume.rolling(window=window, min_periods=2).std(ddof=1)
    z = (volume - rolling_mean) / rolling_std.replace(0, np.nan)
    return z.fillna(0.0)


def ensure_columns_present(df: pd.DataFrame, required: Iterable[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
