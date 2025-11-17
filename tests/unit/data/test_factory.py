import pytest

from quant_scenario_engine.data.factory import data_source_factory, get_data_source
from quant_scenario_engine.data.schwab_stub import SchwabDataSourceStub
from quant_scenario_engine.data.yfinance import YFinanceDataSource
from quant_scenario_engine.exceptions import DataSourceError, DependencyError


def test_get_data_source_returns_providers():
    assert isinstance(get_data_source("yfinance"), YFinanceDataSource)
    assert isinstance(get_data_source("schwab_stub"), SchwabDataSourceStub)
    with pytest.raises(DependencyError):
        get_data_source("unknown")


def test_schwab_stub_fetch_raises():
    stub = SchwabDataSourceStub()
    with pytest.raises(DataSourceError):
        stub.fetch("AAPL", "2023-01-01", "2023-01-02")


def test_factory_creates_instances():
    factory = data_source_factory("yfinance")
    inst = factory.create()
    assert isinstance(inst, YFinanceDataSource)
