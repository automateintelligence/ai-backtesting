"""Baseline stock strategy using dual moving averages."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.interfaces.strategy import Strategy, StrategySignals
from quant_scenario_engine.schema.strategy import StrategyParams


class StockBasicStrategy(Strategy):
    def __init__(self, short_window: int = 5, long_window: int = 20) -> None:
        if short_window <= 0 or long_window <= 0:
            raise ValueError("window sizes must be positive")
        self.short_window = short_window
        self.long_window = long_window

    def _rolling_mean(self, path: np.ndarray, window: int) -> np.ndarray:
        window = max(1, min(window, len(path)))
        kernel = np.ones(window) / window
        result = np.convolve(path, kernel, mode="same")
        # np.convolve preserves length when kernel <= path length; clipping guards
        return result[: len(path)]

    def generate_signals(self, price_paths, features, params: StrategyParams) -> StrategySignals:
        closes = np.asarray(price_paths, dtype=float)
        short_w = int(params.params.get("short_window", self.short_window))
        long_w = int(params.params.get("long_window", self.long_window))
        if short_w <= 0 or long_w <= 0:
            raise ValueError("window sizes must be positive")
        if short_w >= long_w:
            # Avoid degenerate crossover definitions
            long_w = short_w + 5
        long_w = min(long_w, closes.shape[1])
        short_w = min(short_w, closes.shape[1])

        short_ma = np.vstack([self._rolling_mean(row, short_w) for row in closes])
        long_ma = np.vstack([self._rolling_mean(row, long_w) for row in closes])

        raw_signal = np.where(short_ma > long_ma, 1, -1).astype(np.int8)
        signals_stock = raw_signal
        signals_option = np.zeros_like(signals_stock, dtype=np.int8)

        return StrategySignals(
            signals_stock=signals_stock,
            signals_option=signals_option,
            option_spec=None,
            features_used=list(features.keys()) if isinstance(features, dict) else [],
        )
