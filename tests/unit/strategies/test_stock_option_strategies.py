import numpy as np

from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.schema.strategy import StrategyParams
from quant_scenario_engine.strategies.option_call import OptionCallStrategy
from quant_scenario_engine.strategies.stock_basic import StockBasicStrategy


def _paths():
    return np.array([[1, 2, 3, 4], [2, 2, 2, 2]], dtype=float)


def test_stock_basic_generates_signals():
    strategy = StockBasicStrategy()
    signals = strategy.generate_signals(_paths(), None, StrategyParams(name="sma", kind="stock"))
    assert signals.signals_stock.shape == (2, 4)
    assert signals.option_spec is None


def test_option_call_generates_signals():
    spec = OptionSpec(
        option_type="call",
        strike=1.0,
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.01,
        contracts=1,
    )
    strategy = OptionCallStrategy(option_spec=spec)
    signals = strategy.generate_signals(_paths(), None, StrategyParams(name="call", kind="option"))
    assert signals.option_spec == spec
    assert signals.signals_option.shape == (2, 4)
