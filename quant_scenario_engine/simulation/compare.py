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
from quant_scenario_engine.strategies.factory import get_strategy


@dataclass
class RunResult:
    metrics: MetricsReport
    signals: StrategySignals
    s0: float


def _build_signals(
    price_paths,
    stock_strategy_name: str,
    option_strategy_name: str,
    option_spec: OptionSpec,
    stock_params: Optional[dict] = None,
    option_params: Optional[dict] = None,
) -> StrategySignals:
    """
    Build combined signals from stock and option strategies.

    Args:
        price_paths: MC price paths [n_paths, n_steps]
        stock_strategy_name: Name of stock strategy (e.g., 'stock_basic')
        option_strategy_name: Name of option strategy (e.g., 'call_basic')
        option_spec: Option specification with strike/IV/maturity
        stock_params: Optional strategy-specific parameters for stock strategy
        option_params: Optional strategy-specific parameters for option strategy

    Returns:
        Combined StrategySignals with both stock and option positions
    """
    # Load strategies dynamically from factory
    stock_strategy = get_strategy(stock_strategy_name, kind="stock")
    option_strategy = get_strategy(
        option_strategy_name, kind="option", option_spec=option_spec
    )

    # Generate signals using provided parameters
    stock_signals = stock_strategy.generate_signals(
        price_paths,
        features={},
        params=StrategyParams(
            name=stock_strategy_name, kind="stock", params=stock_params or {}
        ),
    )
    option_signals = option_strategy.generate_signals(
        price_paths,
        features={},
        params=StrategyParams(
            name=option_strategy_name, kind="option", params=option_params or {}
        ),
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
    stock_strategy: str,
    option_strategy: str,
    option_spec: OptionSpec,
    stock_params: Optional[dict] = None,
    option_params: Optional[dict] = None,
    var_method: str = "historical",
    covariance_estimator: str = "sample",
    lookback_window: int | None = None,
) -> RunResult:
    """
    Generate MC paths, run stock vs option strategies, and return comparative metrics.

    Args:
        s0: Initial stock price
        distribution: Fitted return distribution for MC sampling
        n_paths: Number of Monte Carlo paths
        n_steps: Steps per path
        seed: Random seed for reproducibility
        stock_strategy: Name of stock strategy (e.g., 'stock_basic')
        option_strategy: Name of option strategy (e.g., 'call_basic')
        option_spec: Option specification (strike, IV, maturity, etc.)
        stock_params: Optional strategy-specific parameters for stock strategy
        option_params: Optional strategy-specific parameters for option strategy
        var_method: VaR calculation method ('parametric' or 'historical')
        covariance_estimator: Covariance estimation method
        lookback_window: Window for historical metrics calculation

    Returns:
        RunResult with metrics, signals, and starting price

    Note:
        The distribution should already be fitted. Seeding is applied in the
        generator to ensure reproducible runs.
    """
    price_paths = generate_price_paths(
        s0=s0, distribution=distribution, n_paths=n_paths, n_steps=n_steps, seed=seed
    )

    signals = _build_signals(
        price_paths,
        stock_strategy_name=stock_strategy,
        option_strategy_name=option_strategy,
        option_spec=option_spec,
        stock_params=stock_params,
        option_params=option_params,
    )
    simulator = MarketSimulator()
    metrics = simulator.run(
        price_paths,
        signals,
        var_method=var_method,
        covariance_estimator=covariance_estimator,
        lookback_window=lookback_window,
    )
    return RunResult(metrics=metrics, signals=signals, s0=s0)
