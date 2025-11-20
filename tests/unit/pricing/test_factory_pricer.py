import pytest

from qse.exceptions import DependencyError
from qse.pricing.factory import get_pricer, pricer_factory


def test_pricer_factory_creates():
    pricer = get_pricer("black_scholes")
    assert pricer is not None
    factory = pricer_factory("bs")
    assert factory.create().__class__.__name__ == "BlackScholesPricer"
    with pytest.raises(DependencyError):
        get_pricer("unknown")
