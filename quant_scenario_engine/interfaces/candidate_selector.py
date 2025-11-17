"""Candidate selector interface per FR-CAND-001."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from quant_scenario_engine.schema.episode import CandidateEpisode
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="selectors.interface")


class CandidateSelector(ABC):
    """Base selector for identifying candidate episodes."""

    def __init__(
        self,
        *,
        name: str = "candidate_selector",
        feature_requirements: Iterable[str] | None = None,
        min_episodes: int = 30,
    ) -> None:
        self.name = name
        self.feature_requirements = list(feature_requirements or [])
        self.min_episodes = int(min_episodes)

    @abstractmethod
    def score(self, row: dict) -> float:
        """Score a row of features for ranking."""

    @abstractmethod
    def select(self, data) -> list[CandidateEpisode]:
        """Return a ranked list of candidate episodes from provided data."""

    def select_candidates(self, data) -> list[CandidateEpisode]:
        """Compatibility alias, defers to select()."""

        results = self.select(data)
        if self.min_episodes and len(results) < self.min_episodes:
            log.warning(
                "selector produced fewer episodes than min_episodes",
                extra={"min_episodes": self.min_episodes, "produced": len(results)},
            )
        return results

