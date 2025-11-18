"""Episode bootstrap distribution for conditional Monte Carlo."""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
from numpy.random import Generator, PCG64

from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import DistributionMetadata, ReturnDistribution


class EpisodeBootstrapDistribution(ReturnDistribution):
    """Non-parametric sampler that bootstraps historical episode returns."""

    def __init__(self, *, min_episodes: int = 5, min_samples: int = 60) -> None:
        super().__init__()
        self.min_episodes = min_episodes
        self.min_samples = min_samples
        self._episodes: List[np.ndarray] = []

    def fit(self, episode_returns: Iterable[np.ndarray], min_samples: int | None = None) -> None:
        """Store episode return sequences after validation."""

        min_samples = min_samples or self.min_samples
        cleaned: list[np.ndarray] = []
        for seq in episode_returns:
            arr = np.asarray(seq, dtype=float).flatten()
            if arr.size == 0:
                continue
            cleaned.append(arr)

        if len(cleaned) < self.min_episodes:
            raise DistributionFitError(f"Insufficient episodes for bootstrap (got {len(cleaned)}, need {self.min_episodes})")

        total_samples = int(sum(arr.size for arr in cleaned))
        if total_samples < min_samples:
            raise DistributionFitError(f"Insufficient samples for bootstrap (got {total_samples}, need {min_samples})")

        self._episodes = cleaned
        self.metadata = DistributionMetadata(fit_status="success", min_samples=min_samples, fallback_model=None)

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None) -> np.ndarray:
        if not self._episodes:
            raise DistributionFitError("Bootstrap distribution not fit")

        rng: Generator = Generator(PCG64(seed)) if seed is not None else np.random.default_rng()
        samples = np.zeros((n_paths, n_steps), dtype=float)

        for i in range(n_paths):
            seq = rng.choice(self._episodes)
            if seq.size >= n_steps:
                # Preserve local structure by sampling a contiguous slice
                start = rng.integers(0, seq.size - n_steps + 1) if seq.size > n_steps else 0
                samples[i] = seq[start : start + n_steps]
            else:
                # Repeat sequence to fill requested steps
                reps = int(np.ceil(n_steps / seq.size))
                tiled = np.tile(seq, reps)[:n_steps]
                samples[i] = tiled

        return samples


__all__ = ["EpisodeBootstrapDistribution"]
