import pandas as pd
import pytest

from quant_scenario_engine.data.validation import (
    REQUIRED_COLUMNS,
    compute_fingerprint,
    enforce_missing_tolerance,
    fingerprints_match,
    validate_ohlcv,
)
from quant_scenario_engine.exceptions import SchemaError, TimestampAnomalyError


def _frame():
    return pd.DataFrame(
        {
            "open": [1, 2],
            "high": [2, 3],
            "low": [0, 1],
            "close": [1, 2],
            "volume": [10, 10],
        },
        index=pd.date_range("2023-01-01", periods=2, freq="D"),
    )


def test_validate_ohlcv_missing_columns():
    df = _frame().drop(columns=["volume"])
    with pytest.raises(SchemaError):
        validate_ohlcv(df)


def test_validate_ohlcv_future_timestamp():
    df = _frame()
    df.index = pd.date_range(pd.Timestamp.utcnow() + pd.Timedelta(days=1), periods=2, freq="D")
    with pytest.raises(TimestampAnomalyError):
        validate_ohlcv(df)


def test_validate_ohlcv_passes_and_fingerprint_changes_on_data_change():
    df = _frame()
    validate_ohlcv(df)  # no raise
    fp1 = compute_fingerprint(df)
    df2 = df.copy()
    df2.loc[df2.index[-1], "close"] = 99
    fp2 = compute_fingerprint(df2)
    assert fp1 != fp2
    assert fingerprints_match(fp1, fp1)


def test_enforce_missing_tolerance_detects_gap():
    df = _frame()
    df.loc[df.index[0], "close"] = None
    with pytest.raises(TimestampAnomalyError):
        enforce_missing_tolerance(df, max_gap=0, max_ratio=0.1)


def test_enforce_missing_tolerance_passes_within_threshold():
    df = _frame()
    gap, ratio = enforce_missing_tolerance(df, max_gap=2, max_ratio=0.6)
    assert gap == 0
    assert ratio == 0.0
