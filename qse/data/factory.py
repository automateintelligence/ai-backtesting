"""Factory for data sources."""

from __future__ import annotations

from qse.config.factories import FactoryBase
from qse.data.schwab_stub import SchwabDataSourceStub
from qse.data.yfinance import YFinanceDataSource
from qse.exceptions import DependencyError


def get_data_source(name: str):
    name = name.lower()
    if name == "yfinance":
        return YFinanceDataSource()
    if name == "schwab_stub":
        return SchwabDataSourceStub()
    raise DependencyError(f"Unknown data source: {name}")


def data_source_factory(name: str) -> FactoryBase:
    return FactoryBase(name=name, builder=lambda: get_data_source(name))
