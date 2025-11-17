import numpy as np
import pytest

from quant_scenario_engine.distributions.laplace import LaplaceDistribution
from quant_scenario_engine.exceptions import DistributionFitError


def test_laplace_fit_and_sample_reproducible():
    returns = np.random.normal(0, 0.01, size=100)
    dist = LaplaceDistribution()
    dist.fit(returns)
    sample1 = dist.sample(10, 5, seed=42)
    sample2 = dist.sample(10, 5, seed=42)
    assert np.array_equal(sample1, sample2)


def test_laplace_fit_insufficient_samples():
    dist = LaplaceDistribution()
    with pytest.raises(DistributionFitError):
        dist.fit(np.array([0.1]), min_samples=5)
