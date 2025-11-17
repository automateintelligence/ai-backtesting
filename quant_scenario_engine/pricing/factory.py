"""Factory for option pricers."""

from __future__ import annotations

from quant_scenario_engine.config.factories import FactoryBase
from quant_scenario_engine.exceptions import DependencyError
from quant_scenario_engine.pricing.black_scholes import BlackScholesPricer

_PRICERS = {
    "black_scholes": BlackScholesPricer,
    "black-scholes": BlackScholesPricer,
    "bs": BlackScholesPricer,
}


def get_pricer(name: str):
    normalized = name.lower()
    pricer_cls = _PRICERS.get(normalized)
    if pricer_cls is None:
        raise DependencyError(f"Unknown pricer: {name}")
    return pricer_cls()


def pricer_factory(name: str) -> FactoryBase:
    normalized = name.lower()
    return FactoryBase(name=normalized, builder=lambda: get_pricer(normalized))
