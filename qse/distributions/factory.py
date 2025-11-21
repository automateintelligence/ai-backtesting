"""Factory for return distributions."""

from __future__ import annotations

from qse.config.factories import FactoryBase
from qse.distributions.laplace import LaplaceDistribution
from qse.distributions.student_t import StudentTDistribution
from qse.distributions.normal import NormalDistribution
from qse.exceptions import DependencyError


def get_distribution(name: str):
    name = name.lower()
    if name == "laplace":
        return LaplaceDistribution()
    if name in {"student_t", "student-t", "t"}:
        return StudentTDistribution()
    if name in {"normal", "gaussian"}:
        return NormalDistribution()
    raise DependencyError(f"Unknown distribution: {name}")


def distribution_factory(name: str) -> FactoryBase:
    return FactoryBase(name=name, builder=lambda: get_distribution(name))
