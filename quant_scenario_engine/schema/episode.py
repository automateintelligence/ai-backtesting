"""Candidate episode schema per data-model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CandidateEpisode:
    symbol: str
    t0: datetime
    horizon: int
    state_features: dict[str, float] = field(default_factory=dict)
    selector_name: str = ""
    score: float | None = None

    def __post_init__(self) -> None:
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        if not isinstance(self.t0, datetime):
            raise ValueError("t0 must be a datetime")
        # Ensure numeric features
        cleaned: dict[str, float] = {}
        for k, v in self.state_features.items():
            try:
                cleaned[k] = float(v)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"state feature {k} is not numeric") from exc
        self.state_features = cleaned


__all__ = ["CandidateEpisode"]

