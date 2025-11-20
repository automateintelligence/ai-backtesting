import pytest

from qse.data.resolution import select_resolution
from qse.data.universe import UniverseConfig
from qse.exceptions import ConfigValidationError


def test_select_resolution_defaults():
    assert select_resolution("distribution") == "1d"
    assert select_resolution("backtest") == "5m"
    assert select_resolution("live") == "1m"
    assert select_resolution("unknown") == "1d"


def test_universe_config_duplicates():
    with pytest.raises(ConfigValidationError):
        UniverseConfig(universe=["AAPL", "AAPL"])

    cfg = UniverseConfig(universe=["AAPL"], watchlist=["MSFT"], live=[])
    assert cfg.watchlist == ["MSFT"]
