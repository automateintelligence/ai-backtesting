"""Student-T distribution model."""

from __future__ import annotations

import numpy as np
from numpy.random import Generator, PCG64
from scipy import stats

from quant_scenario_engine.distributions.ar_detection import detect_ar_process
from quant_scenario_engine.distributions.stationarity import check_stationarity
from quant_scenario_engine.distributions.validation import (
    enforce_convergence,
    fallback_to_laplace,
    heavy_tail_status,
    validate_params_bounds,
    validate_returns,
)
from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import DistributionMetadata, ReturnDistribution


class StudentTDistribution(ReturnDistribution):
    def __init__(self) -> None:
        super().__init__()
        self.df: float | None = None
        self.loc: float | None = None
        self.scale: float | None = None

    def fit(self, returns: np.ndarray, min_samples: int = 60) -> None:
        validate_returns(returns, min_samples)

        stationarity = check_stationarity(returns)
        if stationarity.recommendation.startswith("difference"):
            returns = np.diff(returns)

        ar_result = detect_ar_process(returns)
        if ar_result.order_suggestion > 0:
            raise DistributionFitError("AR structure detected; unsupported for IID Student-T")

        try:
            df, loc, scale = stats.t.fit(returns)
            self.df, self.loc, self.scale = float(df), float(loc), float(scale)
            enforce_convergence({"df": self.df, "loc": self.loc, "scale": self.scale})
            validate_params_bounds(
                {"df": self.df, "scale": self.scale},
                {"df": (2.0, 1000.0), "scale": (1e-9, 10.0)},
            )
            excess_kurt = float(stats.kurtosis(returns, fisher=True))
            ok, warn = heavy_tail_status(excess_kurt)
            if not ok:
                raise DistributionFitError(
                    f"Excess kurtosis {excess_kurt:.3f} below required heavy-tail threshold"
                )
            logpdf = stats.t.logpdf(returns, df=df, loc=loc, scale=scale).sum()
            self.metadata = DistributionMetadata(
                estimator="mle",
                loglik=float(logpdf),
                aic=float(2 * 3 - 2 * logpdf),
                bic=float(len(returns) * np.log(len(returns)) - 2 * logpdf),
                fit_status="success",
                min_samples=min_samples,
                excess_kurtosis=excess_kurt,
                heavy_tail_warning=warn,
            )
        except DistributionFitError:
            fallback = fallback_to_laplace(returns)
            self.df = None
            self.loc = fallback.loc
            self.scale = fallback.scale
            self.metadata = fallback.metadata

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None) -> np.ndarray:
        if self.df is None or self.loc is None or self.scale is None:
            raise DistributionFitError("Model not fit")
        rng = Generator(PCG64(seed)) if seed is not None else np.random.default_rng()
        return rng.standard_t(self.df, size=(n_paths, n_steps)) * self.scale + self.loc
