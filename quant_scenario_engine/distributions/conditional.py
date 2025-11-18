"""State-conditioned parametric refit distribution."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.distributions.factory import get_distribution
from quant_scenario_engine.distributions.validation import validate_returns
from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import DistributionMetadata, ReturnDistribution


class ConditionalRefitDistribution(ReturnDistribution):
    """Refits a base distribution on conditioned returns."""

    def __init__(self, base_distribution: str | ReturnDistribution = "laplace") -> None:
        super().__init__()
        self.base_distribution = base_distribution if isinstance(base_distribution, ReturnDistribution) else get_distribution(str(base_distribution))

    def fit(self, returns: np.ndarray, min_samples: int = 60) -> None:
        validate_returns(returns, min_samples)
        self.base_distribution.fit(returns)
        meta = getattr(self.base_distribution, "metadata", DistributionMetadata())
        self.metadata = meta

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None) -> np.ndarray:
        if not hasattr(self.base_distribution, "sample"):
            raise DistributionFitError("Base distribution missing sample()")
        return self.base_distribution.sample(n_paths=n_paths, n_steps=n_steps, seed=seed)


__all__ = ["ConditionalRefitDistribution"]
