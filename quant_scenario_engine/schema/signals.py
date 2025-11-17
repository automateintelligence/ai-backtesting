"""StrategySignals schema."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from quant_scenario_engine.models.options import OptionSpec


@dataclass
class StrategySignals:
    signals_stock: np.ndarray
    signals_option: np.ndarray
    option_spec: OptionSpec | None
    features_used: list[str]

    def __post_init__(self) -> None:
        if self.signals_stock.shape != self.signals_option.shape:
            raise ValueError("signals_stock and signals_option must have the same shape")
        if self.signals_stock.dtype != np.int8:
            self.signals_stock = self.signals_stock.astype(np.int8)
        if self.signals_option.dtype != np.int8:
            self.signals_option = self.signals_option.astype(np.int8)
        if self.signals_stock.ndim != 2:
            raise ValueError("signals must be 2-D array [n_paths, n_steps]")
        # De-duplicate feature list while preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for f in self.features_used:
            if f not in seen:
                seen.add(f)
                deduped.append(f)
        self.features_used = deduped
