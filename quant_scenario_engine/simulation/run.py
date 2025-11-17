"""Simulation orchestrator for compare workflow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quant_scenario_engine.interfaces.distribution import ReturnDistribution
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


def run_compare(
    s0: float,
    distribution: ReturnDistribution,
    n_paths: int,
    n_steps: int,
    seed: Optional[int],
    option_spec,
) -> RunResult:
    price_paths = generate_price_paths(s0=s0, distribution=distribution, n_paths=n_paths, n_steps=n_steps, seed=seed)

    stock_strategy = StockBasicStrategy()
    option_strategy = OptionCallStrategy(option_spec=option_spec)
    signals_stock = stock_strategy.generate_signals(price_paths, features=None, params=StrategyParams(name="stock_basic", kind="stock"))
    signals_option = option_strategy.generate_signals(price_paths, features=None, params=StrategyParams(name="option_call", kind="option"))

    signals = StrategySignals(
        signals_stock=signals_stock.signals_stock,
        signals_option=signals_option.signals_option,
        option_spec=option_spec,
        features_used=[],
    )

    sim = MarketSimulator()
    metrics = sim.run(price_paths, signals)
    return RunResult(metrics=metrics, signals=signals, s0=s0)

