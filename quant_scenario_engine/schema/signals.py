"""StrategySignals schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from quant_scenario_engine.models.options import OptionSpec


@dataclass
class StrategySignals:
    signals_stock: np.ndarray
    signals_option: np.ndarray
    option_spec: Optional[OptionSpec]
    features_used: List[str]

