"""Factory for data sources."""

from __future__ import annotations

from quant_scenario_engine.config.factories import FactoryBase
from quant_scenario_engine.data.schwab_stub import SchwabDataSourceStub
from quant_scenario_engine.data.yfinance import YFinanceDataSource
from quant_scenario_engine.exceptions import DependencyError


def get_data_source(name: str):
    name = name.lower()
    if name == "yfinance":
        return YFinanceDataSource()
    if name == "schwab_stub":
        return SchwabDataSourceStub()
    raise DependencyError(f"Unknown data source: {name}")


def data_source_factory(name: str) -> FactoryBase:
    return FactoryBase(name=name, builder=lambda: get_data_source(name))
