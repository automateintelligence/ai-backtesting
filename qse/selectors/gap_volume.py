"""Gap + volume based candidate selector (default MVP selector)."""

from __future__ import annotations

import pandas as pd

from qse.interfaces.candidate_selector import CandidateSelector
from qse.selectors.episodes import build_candidate_episodes
from qse.utils.logging import get_logger

log = get_logger(__name__, component="selector.gap_volume")


class GapVolumeSelector(CandidateSelector):
    """Selects episodes where price gaps significantly with confirming volume."""

    def __init__(
        self,
        *,
        gap_min: float = 0.03,
        volume_z_min: float = 1.5,
        horizon: int = 10,
        name: str = "gap_volume",
        min_episodes: int = 30,
    ) -> None:
        super().__init__(name=name, feature_requirements=["gap_pct", "volume_z"], min_episodes=min_episodes)
        self.gap_min = gap_min
        self.volume_z_min = volume_z_min
        self.horizon = horizon

    def score(self, row: dict) -> float:
        gap = abs(float(row.get("gap_pct", 0.0)))
        vol = float(row.get("volume_z", 0.0))
        return gap + max(vol, 0)

    def select(self, data: pd.DataFrame) -> list:
        if not isinstance(data, pd.DataFrame):
            raise TypeError("GapVolumeSelector expects a pandas DataFrame")

        missing = [c for c in self.feature_requirements if c not in data.columns]
        if missing:
            log.warning("missing required features", extra={"missing": missing})
            return []

        filtered = data[(data["gap_pct"].abs() >= self.gap_min) & (data["volume_z"] >= self.volume_z_min)].copy()
        if filtered.empty:
            log.info("no candidates after filtering", extra={"component": self.name})
            return []

        filtered["score"] = filtered.apply(lambda row: self.score(row), axis=1)
        filtered.sort_values("score", ascending=False, inplace=True)

        episodes = build_candidate_episodes(
            symbol=str(filtered.get("symbol", ["unknown"]).iloc[0]) if "symbol" in filtered else "unknown",
            selector_name=self.name,
            df=filtered,
            horizon=self.horizon,
            feature_fields=["gap_pct", "volume_z"],
            score_field="score",
        )

        if len(episodes) < self.min_episodes:
            log.warning(
                "selector produced fewer episodes than min_episodes",
                extra={"min_episodes": self.min_episodes, "produced": len(episodes)},
            )

        return episodes

