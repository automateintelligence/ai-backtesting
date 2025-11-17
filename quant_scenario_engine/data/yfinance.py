"""YFinance data adapter with retry and column normalization."""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd

from quant_scenario_engine.exceptions import DataSourceError


class YFinanceDataSource:
    def __init__(self, max_retries: int = 3, backoff_seconds: Optional[list[int]] = None) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds or [1, 2, 4]
        if len(self.backoff_seconds) < self.max_retries:
            self.backoff_seconds.extend([self.backoff_seconds[-1]] * (self.max_retries - len(self.backoff_seconds)))

    def fetch(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                df = self._download(symbol, start, end, interval, progress=False)
                if df is None or df.empty:
                    raise DataSourceError("Empty data returned from yfinance")
                df = self._normalize_columns(df)
                return df
            except Exception as exc:  # pragma: no cover - exercised via tests with retries
                last_exc = exc
                if attempt == self.max_retries - 1:
                    raise DataSourceError(f"Failed to fetch {symbol} after retries") from exc
                time.sleep(self.backoff_seconds[attempt])
        raise DataSourceError("Unknown fetch failure") from last_exc

    def _download(self, symbol: str, start: str, end: str, interval: str, progress: bool = False) -> pd.DataFrame:
        try:
            import yfinance as yf  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise DataSourceError("yfinance not installed") from exc

        return yf.download(symbol, start=start, end=end, interval=interval, progress=progress)

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {col: col.lower() for col in df.columns}
        df = df.rename(columns=rename_map)
        # yfinance provides "adj close"; drop if present
        df = df.drop(columns=[c for c in df.columns if c.startswith("adj")], errors="ignore")
        df.index = pd.to_datetime(df.index)
        return df
