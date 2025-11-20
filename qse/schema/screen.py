"""ScreenResponse serialization helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, List

from qse.schema.episode import CandidateEpisode


@dataclass
class ScreenResponse:
    candidates: List[CandidateEpisode]

    def to_dict(self) -> dict:
        return {
            "candidates": [
                {
                    "symbol": c.symbol,
                    "t0": c.t0.isoformat(),
                    "horizon": c.horizon,
                    "selector": c.selector_name,
                    "state_features": c.state_features,
                    "score": c.score,
                }
                for c in self.candidates
            ]
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

