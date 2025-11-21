"""Lightweight configuration schema and validation (US7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from qse.exceptions import ConfigValidationError, ConfigConflictError


DistributionName = Literal["laplace", "student_t", "normal", "garch_t"]
DataSourceName = Literal["yfinance", "schwab_stub"]
PricerName = Literal["black_scholes", "py_vollib", "quantlib"]


@dataclass
class MCConfig:
    paths: int = 1000
    steps: int = 60
    seed: int = 42

    def validate(self) -> None:
        if self.paths <= 0:
            raise ConfigValidationError("mc.paths must be > 0")
        if self.steps <= 0:
            raise ConfigValidationError("mc.steps must be > 0")


@dataclass
class RunConfigSchema:
    symbol: str
    data_source: DataSourceName = "yfinance"
    distribution: DistributionName = "laplace"
    pricer: PricerName = "black_scholes"
    mc: MCConfig = field(default_factory=MCConfig)

    def validate(self) -> None:
        if not self.symbol:
            raise ConfigValidationError("symbol is required")
        if self.data_source not in {"yfinance", "schwab_stub"}:
            raise ConfigValidationError("data_source must be yfinance or schwab_stub")
        if self.distribution not in {"laplace", "student_t", "normal", "garch_t"}:
            raise ConfigValidationError("distribution must be one of laplace, student_t, normal, garch_t")
        if self.pricer not in {"black_scholes", "py_vollib", "quantlib"}:
            raise ConfigValidationError("pricer must be one of black_scholes, py_vollib, quantlib")
        self.mc.validate()


def validate_config(config: dict[str, Any]) -> RunConfigSchema:
    """Fail-fast validation for CLI configs."""
    mc_cfg = config.get("mc", {})
    mc = MCConfig(
        paths=int(mc_cfg.get("paths", 1000)),
        steps=int(mc_cfg.get("steps", 60)),
        seed=int(mc_cfg.get("seed", 42)),
    )

    schema = RunConfigSchema(
        symbol=str(config.get("symbol", "")).strip(),
        data_source=config.get("data_source", "yfinance"),
        distribution=config.get("distribution", "laplace"),
        pricer=config.get("pricer", "black_scholes"),
        mc=mc,
    )
    schema.validate()

    # Conflicts
    if schema.pricer == "quantlib":
        raise ConfigConflictError("QuantLib pricer is a stub; choose black_scholes or py_vollib")

    return schema
