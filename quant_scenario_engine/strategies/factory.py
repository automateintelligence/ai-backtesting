"""Factory for trading strategies."""

from __future__ import annotations

from typing import Optional

from quant_scenario_engine.exceptions import DependencyError
from quant_scenario_engine.interfaces.strategy import Strategy
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.strategies.option_call import OptionCallStrategy
from quant_scenario_engine.strategies.stock_basic import StockBasicStrategy
from quant_scenario_engine.strategies.stock_sma_trend import StockSmaTrendStrategy
from quant_scenario_engine.strategies.stock_rsi_reversion import StockRsiReversionStrategy
from quant_scenario_engine.strategies.option_atm_call_momentum import OptionAtmCallMomentumStrategy
from quant_scenario_engine.strategies.option_atm_put_rsi import OptionAtmPutRsiStrategy


def get_strategy(name: str, kind: str, option_spec: Optional[OptionSpec] = None) -> Strategy:
    """
    Create a strategy instance by name.

    Args:
        name: Strategy identifier (e.g., 'stock_basic', 'call_basic')
        kind: Strategy kind enum ('stock' or 'option')
        option_spec: Required for option strategies, defines strike/IV/maturity

    Returns:
        Strategy instance ready to generate signals

    Raises:
        DependencyError: Unknown strategy name
        ValueError: Missing option_spec for option strategy
    """
    name = name.lower()

    # Stock strategies
    if name == "stock_basic":
        return StockBasicStrategy()

    if name == "stock_sma_trend":
        return StockSmaTrendStrategy()

    if name == "stock_rsi_reversion":
        return StockRsiReversionStrategy()

    # Option strategies
    if name in {"call_basic", "option_call"}:
        if option_spec is None:
            raise ValueError(f"Strategy '{name}' requires option_spec parameter")
        return OptionCallStrategy(option_spec=option_spec)

    if name == "option_atm_call_momentum":
        if option_spec is None:
            raise ValueError(f"Strategy '{name}' requires option_spec parameter")
        return OptionAtmCallMomentumStrategy(option_spec=option_spec)

    if name == "option_atm_put_rsi":
        if option_spec is None:
            raise ValueError(f"Strategy '{name}' requires option_spec parameter")
        return OptionAtmPutRsiStrategy(option_spec=option_spec)

    raise DependencyError(f"Unknown strategy: {name} (kind={kind})")


__all__ = ["get_strategy"]
