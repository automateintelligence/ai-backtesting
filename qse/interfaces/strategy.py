"""Strategy interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from qse.models.options import OptionSpec
from qse.schema.strategy import StrategyParams


@dataclass
class StrategySignals:
    signals_stock: np.ndarray
    signals_option: np.ndarray
    option_spec: OptionSpec | None
    features_used: list[str]


class Strategy(ABC):
    """Base strategy for generating signals over price paths and features."""

    @abstractmethod
    def generate_signals(
        self,
        price_paths: np.ndarray,
        features,
        params: StrategyParams,
    ) -> StrategySignals:
        """Return strategy signals for stock and option legs."""

