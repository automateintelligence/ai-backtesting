import numpy as np
import pytest

from qse.distributions.student_t import StudentTDistribution
from qse.exceptions import DistributionFitError


def test_student_t_fit_and_sample_reproducible():
    returns = np.random.standard_t(df=5, size=500) * 0.01
    dist = StudentTDistribution()
    dist.fit(returns)
    sample1 = dist.sample(10, 5, seed=123)
    sample2 = dist.sample(10, 5, seed=123)
    assert np.array_equal(sample1, sample2)


def test_student_t_fit_insufficient_samples():
    dist = StudentTDistribution()
    with pytest.raises(DistributionFitError):
        dist.fit(np.array([0.1]), min_samples=50)
