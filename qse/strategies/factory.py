"""Factory for trading strategies."""

from __future__ import annotations

from qse.exceptions import DependencyError
from qse.interfaces.strategy import Strategy
from qse.models.options import OptionSpec
from qse.strategies.option_atm_call_momentum import OptionAtmCallMomentumStrategy
from qse.strategies.option_atm_put_rsi import OptionAtmPutRsiStrategy
from qse.strategies.option_call import OptionCallStrategy
from qse.strategies.stock_basic import StockBasicStrategy
from qse.strategies.stock_bollinger_reversion import (
    StockBollingerReversionStrategy,
)
from qse.strategies.stock_donchian_breakout import StockDonchianBreakoutStrategy
from qse.strategies.stock_rsi_reversion import StockRsiReversionStrategy
from qse.strategies.stock_sma_trend import StockSmaTrendStrategy


def get_strategy(name: str, kind: str, option_spec: OptionSpec | None = None) -> Strategy:
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

    if name == "stock_bollinger_reversion":
        return StockBollingerReversionStrategy()

    if name == "stock_donchian_breakout":
        return StockDonchianBreakoutStrategy()

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
