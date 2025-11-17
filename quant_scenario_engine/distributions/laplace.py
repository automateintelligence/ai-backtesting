"""Laplace distribution model."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator, PCG64
from scipy.stats import laplace

from quant_scenario_engine.distributions.stationarity import check_stationarity
from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import DistributionMetadata, ReturnDistribution


class LaplaceDistribution(ReturnDistribution):
    def __init__(self) -> None:
        super().__init__()
        self.loc: float | None = None
        self.scale: float | None = None

    def fit(self, returns: np.ndarray, min_samples: int = 60) -> None:
        if returns is None or len(returns) < min_samples:
            raise DistributionFitError("Insufficient samples for Laplace fit")

        stationarity = check_stationarity(returns)
        if stationarity.recommendation.startswith("difference"):
            returns = np.diff(returns)

        loc, scale = laplace.fit(returns)
        self.loc, self.scale = float(loc), float(scale)
        self.metadata = DistributionMetadata(
            estimator="mle",
            loglik=float(laplace.logpdf(returns, loc=loc, scale=scale).sum()),
            aic=float(2 * 2 - 2 * laplace.logpdf(returns, loc=loc, scale=scale).sum()),
            bic=float(len(returns) * np.log(len(returns)) - 2 * laplace.logpdf(returns, loc=loc, scale=scale).sum()),
            fit_status="success",
            min_samples=min_samples,
        )

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None) -> np.ndarray:
        if self.loc is None or self.scale is None:
            raise DistributionFitError("Model not fit")
        rng = Generator(PCG64(seed)) if seed is not None else np.random.default_rng()
        return rng.laplace(self.loc, self.scale, size=(n_paths, n_steps))

