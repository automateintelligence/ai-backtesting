import pytest

from quant_scenario_engine.exceptions import ConfigValidationError
from quant_scenario_engine.schema.strategy import StrategyParams


def test_strategy_params_valid():
    params = StrategyParams(name="sma", kind="stock")
    assert params.name == "sma"
    assert params.fees == 0.0005


def test_strategy_params_validation_errors():
    with pytest.raises(ConfigValidationError):
        StrategyParams(name="", kind="stock")
    with pytest.raises(ConfigValidationError):
        StrategyParams(name="sma", kind="invalid")  # type: ignore
    with pytest.raises(ConfigValidationError):
        StrategyParams(name="sma", kind="stock", fees=-0.1)
