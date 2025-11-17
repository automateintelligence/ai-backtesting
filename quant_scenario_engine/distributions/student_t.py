"""Student-T distribution model."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator, PCG64
from scipy import stats

from quant_scenario_engine.distributions.ar_detection import detect_ar_process
from quant_scenario_engine.distributions.stationarity import check_stationarity
from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import DistributionMetadata, ReturnDistribution


class StudentTDistribution(ReturnDistribution):
    def __init__(self) -> None:
        super().__init__()
        self.df: float | None = None
        self.loc: float | None = None
        self.scale: float | None = None

    def fit(self, returns: np.ndarray, min_samples: int = 60) -> None:
        if returns is None or len(returns) < min_samples:
            raise DistributionFitError("Insufficient samples for Student-T fit")

        stationarity = check_stationarity(returns)
        if stationarity.recommendation.startswith("difference"):
            returns = np.diff(returns)

        ar_result = detect_ar_process(returns)
        if ar_result.order_suggestion > 0:
            raise DistributionFitError("AR structure detected; unsupported for IID Student-T")

        df, loc, scale = stats.t.fit(returns)
        self.df, self.loc, self.scale = float(df), float(loc), float(scale)
        logpdf = stats.t.logpdf(returns, df=df, loc=loc, scale=scale).sum()
        self.metadata = DistributionMetadata(
            estimator="mle",
            loglik=float(logpdf),
            aic=float(2 * 3 - 2 * logpdf),
            bic=float(len(returns) * np.log(len(returns)) - 2 * logpdf),
            fit_status="success",
            min_samples=min_samples,
        )

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None) -> np.ndarray:
        if self.df is None or self.loc is None or self.scale is None:
            raise DistributionFitError("Model not fit")
        rng = Generator(PCG64(seed)) if seed is not None else np.random.default_rng()
        return rng.standard_t(self.df, size=(n_paths, n_steps)) * self.scale + self.loc

