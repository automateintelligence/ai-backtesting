"""Utilities for building candidate episodes."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

import pandas as pd

from qse.schema.episode import CandidateEpisode


def build_candidate_episodes(
    *,
    symbol: str,
    selector_name: str,
    df: pd.DataFrame,
    horizon: int,
    feature_fields: Iterable[str] | None = None,
    score_field: str | None = None,
    maturity_days: int | None = None,
) -> list[CandidateEpisode]:
    """Create CandidateEpisode objects from a filtered DataFrame.

    Args:
        symbol: Ticker symbol
        selector_name: Name of selector producing episodes
        df: Filtered dataframe containing event rows (index must be datetime-like)
        horizon: Episode horizon (bars)
        feature_fields: Subset of columns to persist as state features
        score_field: Optional column with precomputed score
        maturity_days: When provided, must be >= horizon (FR-035)
    """

    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if maturity_days is not None and maturity_days < horizon:
        raise ValueError("maturity_days must be >= horizon for candidate episodes")

    feature_fields = list(feature_fields or [])
    episodes: list[CandidateEpisode] = []

    for idx, row in df.iterrows():
        t0 = idx
        if not isinstance(t0, datetime):
            t0 = pd.to_datetime(t0).to_pydatetime()
        state = {field: float(row[field]) for field in feature_fields if field in row}
        score_val = None
        if score_field and score_field in row:
            try:
                score_val = float(row[score_field])
            except (TypeError, ValueError):
                score_val = None
        episode = CandidateEpisode(
            symbol=symbol,
            t0=t0,
            horizon=horizon,
            state_features=state,
            selector_name=selector_name,
            score=score_val,
        )
        episodes.append(episode)

    return episodes

