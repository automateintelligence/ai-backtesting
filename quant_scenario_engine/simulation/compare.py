"""Stock vs option comparison orchestration (US1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quant_scenario_engine.interfaces.distribution import ReturnDistribution
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.schema.signals import StrategySignals
from quant_scenario_engine.schema.strategy import StrategyParams
from quant_scenario_engine.simulation.metrics import MetricsReport
from quant_scenario_engine.simulation.simulator import MarketSimulator
from quant_scenario_engine.mc.generator import generate_price_paths
from quant_scenario_engine.strategies.option_call import OptionCallStrategy
from quant_scenario_engine.strategies.stock_basic import StockBasicStrategy


@dataclass
class RunResult:
    metrics: MetricsReport
    signals: StrategySignals
    s0: float


def _build_signals(
    price_paths,
    option_spec: OptionSpec,
) -> StrategySignals:
    stock_strategy = StockBasicStrategy()
    option_strategy = OptionCallStrategy(option_spec=option_spec)

    stock_signals = stock_strategy.generate_signals(
        price_paths,
        features=None,
        params=StrategyParams(name="stock_basic", kind="stock"),
    )
    option_signals = option_strategy.generate_signals(
        price_paths,
        features=None,
        params=StrategyParams(name="option_call", kind="option"),
    )

    return StrategySignals(
        signals_stock=stock_signals.signals_stock,
        signals_option=option_signals.signals_option,
        option_spec=option_spec,
        features_used=[],
    )


def run_compare(
    *,
    s0: float,
    distribution: ReturnDistribution,
    n_paths: int,
    n_steps: int,
    seed: Optional[int],
    option_spec: OptionSpec,
    var_method: str = "historical",
    covariance_estimator: str = "sample",
    lookback_window: int | None = None,
) -> RunResult:
    """Generate MC paths, run baseline stock vs option strategies, and return metrics.

    The function expects a fitted ``ReturnDistribution``; seeding is applied in the
    generator to keep runs reproducible.
    """

    price_paths = generate_price_paths(
        s0=s0, distribution=distribution, n_paths=n_paths, n_steps=n_steps, seed=seed
    )

    signals = _build_signals(price_paths, option_spec)
    simulator = MarketSimulator()
    metrics = simulator.run(
        price_paths,
        signals,
        var_method=var_method,
        covariance_estimator=covariance_estimator,
        lookback_window=lookback_window,
    )
    return RunResult(metrics=metrics, signals=signals, s0=s0)
