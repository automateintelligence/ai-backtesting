"""Feature computation pipeline for OHLCV data.

Enriches raw bars with SMA, RSI, volume z-score, and gap percentage
features while keeping derived columns separate from source inputs.
"""

from __future__ import annotations

import pandas as pd

from quant_scenario_engine.features.gap import compute_gap_pct
from quant_scenario_engine.features.indicators import (
    compute_rsi,
    compute_sma,
    compute_volume_z,
    ensure_columns_present,
)
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="features.pipeline")


def enrich_ohlcv(
    df: pd.DataFrame,
    *,
    sma_windows: tuple[int, ...] = (20, 50),
    rsi_period: int = 14,
    volume_window: int = 20,
    fillna: bool = True,
) -> pd.DataFrame:
    """Return a copy of df with derived features appended.

    Required columns: open, high, low, close, volume.
    """

    ensure_columns_present(df, ["open", "high", "low", "close", "volume"])
    out = df.copy()

    # Gap percentage (open vs previous close)
    out["gap_pct"] = compute_gap_pct(out["open"], out["close"]).fillna(0.0)

    # SMAs
    for win in sma_windows:
        out[f"sma_{win}"] = compute_sma(out["close"], length=int(win))

    # RSI
    out[f"rsi_{rsi_period}"] = compute_rsi(out["close"], length=int(rsi_period))

    # Volume z-score
    out["volume_z"] = compute_volume_z(out["volume"], window=int(volume_window))

    if fillna:
        out = out.ffill().bfill()

    log.info(
        "Feature pipeline complete",
        extra={"component": "features", "features_added": [c for c in out.columns if c not in df.columns]},
    )

    return out
