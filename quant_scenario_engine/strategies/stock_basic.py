"""Baseline stock strategy using dual moving averages."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.interfaces.strategy import Strategy, StrategySignals
from quant_scenario_engine.schema.strategy import StrategyParams


class StockBasicStrategy(Strategy):
    def __init__(self, short_window: int = 5, long_window: int = 20) -> None:
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, price_paths, features, params: StrategyParams) -> StrategySignals:
        closes = np.asarray(price_paths)
        short_ma = closes.mean(axis=1, keepdims=True)
        long_ma = closes.mean(axis=1, keepdims=True)
        # Simplified: long vs short average of full path
        signal = np.where(short_ma > long_ma, 1, -1).astype(np.int8)
        signals_stock = np.repeat(signal, closes.shape[1], axis=1)
        signals_option = np.zeros_like(signals_stock, dtype=np.int8)
        return StrategySignals(
            signals_stock=signals_stock,
            signals_option=signals_option,
            option_spec=None,
            features_used=[],
        )

