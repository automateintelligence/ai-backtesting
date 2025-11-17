from pathlib import Path
import sys
import types

import pandas as pd

# Provide a lightweight yfinance stub before importing cache
fake_yf = types.SimpleNamespace()


class _FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, start, end, interval, auto_adjust=True):  # pragma: no cover - used in fallback
        raise RuntimeError("network fetch not allowed in tests")


fake_yf.Ticker = _FakeTicker
sys.modules.setdefault("yfinance", fake_yf)

from quant_scenario_engine.data import cache


def test_parse_symbol_list_variants():
    assert cache.parse_symbol_list("AAPL,MSFT") == ["AAPL", "MSFT"]
    assert cache.parse_symbol_list("['AAPL','MSFT']") == ["AAPL", "MSFT"]
    assert cache.parse_symbol_list("[]") == []


def test_load_or_fetch_uses_existing_slice(tmp_path):
    path = tmp_path / "historical/interval=1d/symbol=AAPL/_v1"
    path.mkdir(parents=True)
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    df_existing = pd.DataFrame({
        "date": dates,
        "open": [1, 2, 3, 4, 5],
        "high": [1, 2, 3, 4, 5],
        "low": [1, 2, 3, 4, 5],
        "close": [1, 2, 3, 4, 5],
        "volume": [10, 10, 10, 10, 10],
    })
    # Ensure file exists; actual parquet read is mocked
    (path / "data.parquet").write_text("")

    called = False

    def _fake_fetch(symbol, start, end, interval, target):
        nonlocal called
        called = True
        raise AssertionError("fetch_symbol should not be called when cache covers window")

    original_fetch = cache.fetch_symbol
    original_read = cache.pd.read_parquet
    cache.fetch_symbol = _fake_fetch  # type: ignore
    cache.pd.read_parquet = lambda *args, **kwargs: df_existing  # type: ignore
    try:
        out = cache.load_or_fetch("AAPL", start="2024-01-02", end="2024-01-04", interval="1d", target=tmp_path)
    finally:
        cache.fetch_symbol = original_fetch  # type: ignore
        cache.pd.read_parquet = original_read  # type: ignore

    assert not called
    assert len(out) == 3
    assert out["close"].tolist() == [2, 3, 4]


def test_load_or_fetch_extends_when_needed(tmp_path):
    path = tmp_path / "historical/interval=1d/symbol=AAPL/_v1"
    path.mkdir(parents=True)
    dates = pd.date_range("2024-01-01", periods=2, freq="D")
    df_existing = pd.DataFrame({
        "date": dates,
        "open": [1, 2],
        "high": [1, 2],
        "low": [1, 2],
        "close": [1, 2],
        "volume": [10, 10],
    })
    (path / "data.parquet").write_text("")

    called = False

    def _fake_fetch(symbol, start, end, interval, target):
        nonlocal called
        called = True
        dates_new = pd.date_range("2024-01-01", periods=4, freq="D")
        df_new = pd.DataFrame({
            "date": dates_new,
            "open": [1, 2, 3, 4],
            "high": [1, 2, 3, 4],
            "low": [1, 2, 3, 4],
            "close": [1, 2, 3, 4],
            "volume": [10, 10, 10, 10],
        })
        return df_new

    original_fetch = cache.fetch_symbol
    original_read = cache.pd.read_parquet
    cache.fetch_symbol = _fake_fetch  # type: ignore
    cache.pd.read_parquet = lambda *args, **kwargs: df_existing  # type: ignore
    try:
        out = cache.load_or_fetch("AAPL", start="2024-01-01", end="2024-01-04", interval="1d", target=tmp_path)
    finally:
        cache.fetch_symbol = original_fetch  # type: ignore
        cache.pd.read_parquet = original_read  # type: ignore

    assert called
    assert len(out) == 4
    assert out["close"].tolist() == [1, 2, 3, 4]
