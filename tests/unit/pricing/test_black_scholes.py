import numpy as np
import pytest

from quant_scenario_engine.exceptions import PricingError
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.pricing.black_scholes import BlackScholesPricer


def _spec():
    return OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.01,
        contracts=1,
    )


def test_black_scholes_prices_non_negative():
    pricer = BlackScholesPricer()
    path = np.linspace(90, 110, num=10)
    prices = pricer.price(path, _spec())
    assert (prices >= 0).all()


def test_black_scholes_invalid_iv():
    pricer = BlackScholesPricer()
    bad_spec = _spec()
    bad_spec.implied_vol = 0
    with pytest.raises(PricingError):
        pricer.price(np.array([100, 101]), bad_spec)
