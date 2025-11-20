"""Schwab data source stub used for testing and fallback."""

from __future__ import annotations

import pandas as pd

from qse.exceptions import DataSourceError


class SchwabDataSourceStub:
    """Placeholder adapter that can be swapped once API details are available."""

    def fetch(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        raise DataSourceError("Schwab data source stub does not implement fetch yet")

