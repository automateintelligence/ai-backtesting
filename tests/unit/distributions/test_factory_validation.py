import numpy as np
import pytest

from qse.distributions.factory import distribution_factory, get_distribution
from qse.distributions.validation import (
    heavy_tail_status,
    validate_params_bounds,
    validate_returns,
)
from qse.exceptions import DependencyError, DistributionFitError


def test_distribution_factory_creates():
    dist = get_distribution("laplace")
    assert dist is not None
    factory = distribution_factory("student_t")
    assert factory.create().__class__.__name__ == "StudentTDistribution"
    with pytest.raises(DependencyError):
        get_distribution("unknown")


def test_validate_returns_and_bounds():
    validate_returns(np.ones(10), min_samples=5)
    with pytest.raises(DistributionFitError):
        validate_returns(np.ones(2), min_samples=5)

    bounds = {"scale": (0.0, 10.0)}
    validate_params_bounds({"scale": 1.0}, bounds)
    with pytest.raises(DistributionFitError):
        validate_params_bounds({"scale": -1.0}, bounds)

    ok, warn = heavy_tail_status(1.2)
    assert ok and not warn
    ok, warn = heavy_tail_status(0.7)
    assert ok and warn
    ok, warn = heavy_tail_status(0.3)
    assert not ok and warn


def test_enforce_convergence_and_bounds_in_models(monkeypatch):
    from qse.distributions.laplace import LaplaceDistribution
    from qse.distributions.student_t import StudentTDistribution

    lap = LaplaceDistribution()

    def bad_fit(*args, **kwargs):
        return (0.0, np.nan)

    monkeypatch.setattr("qse.distributions.laplace.laplace.fit", bad_fit)
    with pytest.raises(DistributionFitError):
        lap.fit(np.ones(100))

    tdist = StudentTDistribution()

    def bad_t_fit(*args, **kwargs):
        return (1.0, 0.0, -1.0)  # df too low, scale negative

    monkeypatch.setattr("qse.distributions.student_t.stats.t.fit", bad_t_fit)
    with pytest.raises(DistributionFitError):
        tdist.fit(np.ones(200))
