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
        closes = np.asarray(price_paths)
        # Simple momentum: positive returns -> long call, else flat
        rets = np.diff(closes, axis=1, prepend=closes[:, :1])
        signal = np.where(rets >= 0, 1, 0).astype(np.int8)
        return StrategySignals(
            signals_stock=np.zeros_like(signal, dtype=np.int8),
            signals_option=signal,
            option_spec=self.option_spec,
            features_used=[],
        )

