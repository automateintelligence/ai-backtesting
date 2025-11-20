"""Distribution interface for return models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Estimator = Literal["mle", "gmm"]
FitStatus = Literal["success", "warn", "fail"]


@dataclass
class DistributionMetadata:
    estimator: Estimator | None = None
    loglik: float | None = None
    aic: float | None = None
    bic: float | None = None
    fit_status: FitStatus = "warn"
    min_samples: int = 60
    excess_kurtosis: float | None = None
    heavy_tail_warning: bool = False
    fallback_model: str | None = None


class ReturnDistribution(ABC):
    """Base class for all unconditional or state-conditioned return models."""

    metadata: DistributionMetadata

    def __init__(self) -> None:
        self.metadata = DistributionMetadata()

    @abstractmethod
    def fit(self, returns) -> None:
        """Fit parameters from 1D array of log returns."""

    @abstractmethod
    def sample(self, n_paths: int, n_steps: int, seed: int | None = None):
        """Produce log-return matrix of shape (n_paths, n_steps)."""
