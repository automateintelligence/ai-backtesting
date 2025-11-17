"""Baseline call option strategy mirroring stock signal."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.interfaces.strategy import Strategy, StrategySignals
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.schema.strategy import StrategyParams


class OptionCallStrategy(Strategy):
    def __init__(self, option_spec: OptionSpec) -> None:
        self.option_spec = option_spec

    def generate_signals(self, price_paths, features, params: StrategyParams) -> StrategySignals:
        closes = np.asarray(price_paths, dtype=float)
        momentum_window = int(params.params.get("momentum_window", 3))
        if momentum_window <= 0:
            momentum_window = 1

        # Rolling momentum: price above rolling mean -> long call else flat
        kernel = np.ones(momentum_window) / momentum_window
        rolling = np.vstack([np.convolve(row, kernel, mode="same") for row in closes])
        signal = np.where(closes >= rolling, 1, 0).astype(np.int8)

        features_used = list(features.keys()) if isinstance(features, dict) else []
        return StrategySignals(
            signals_stock=np.zeros_like(signal, dtype=np.int8),
            signals_option=signal,
            option_spec=self.option_spec,
            features_used=features_used,
        )
