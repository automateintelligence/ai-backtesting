"""Gap-related feature utilities."""

from __future__ import annotations

import pandas as pd


def compute_gap_pct(open_series: pd.Series, prev_close_series: pd.Series) -> pd.Series:
    """Compute gap percentage between today's open and previous close.

    gap_pct = (open_t - close_{t-1}) / close_{t-1}
    """

    prev_close = prev_close_series.shift(1)
    gap = (open_series - prev_close) / prev_close
    return gap

