"""Factory for option pricers."""

from __future__ import annotations

from quant_scenario_engine.config.factories import FactoryBase
from quant_scenario_engine.exceptions import DependencyError
from quant_scenario_engine.pricing.black_scholes import BlackScholesPricer


def get_pricer(name: str):
    name = name.lower()
    if name in {"black_scholes", "black-scholes", "bs"}:
        return BlackScholesPricer()
    raise DependencyError(f"Unknown pricer: {name}")


def pricer_factory(name: str) -> FactoryBase:
    return FactoryBase(name=name, builder=lambda: get_pricer(name))

