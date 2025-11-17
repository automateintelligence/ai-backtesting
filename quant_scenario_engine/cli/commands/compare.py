"""Compare CLI command wiring."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from quant_scenario_engine.cli.validation import validate_compare_inputs
from quant_scenario_engine.config.loader import load_config_with_precedence
from quant_scenario_engine.distributions.factory import get_distribution
from quant_scenario_engine.exceptions import ConfigValidationError
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.simulation.run import run_compare
from quant_scenario_engine.utils.logging import get_logger
from quant_scenario_engine.utils.progress import ProgressReporter

log = get_logger(__name__, component="cli_compare")


def compare(
    config: Optional[Path] = typer.Option(
        None, "--config", help="Optional YAML/JSON config path"
    ),
    symbol: Optional[str] = typer.Option(None, help="Ticker symbol"),
    s0: Optional[float] = typer.Option(None, help="Starting price"),
    paths: Optional[int] = typer.Option(None, help="Number of MC paths"),
    steps: Optional[int] = typer.Option(None, help="Steps per path"),
    seed: Optional[int] = typer.Option(None, help="Random seed"),
    distribution: Optional[str] = typer.Option(None, help="Return distribution"),
    strategy: Optional[str] = typer.Option(None, "--strategy", help="Stock strategy name (e.g., stock_basic)"),
    option_strategy: Optional[str] = typer.Option(None, "--option-strategy", help="Option strategy name (e.g., call_basic)"),
    strike: Optional[float] = typer.Option(None, help="Option strike"),
    maturity_days: Optional[int] = typer.Option(None, help="Option maturity in days"),
    iv: Optional[float] = typer.Option(None, help="Implied volatility"),
    rfr: Optional[float] = typer.Option(None, help="Risk-free rate"),
) -> None:
    defaults = {
        "symbol": None,
        "s0": 100.0,
        "paths": 1000,
        "steps": 60,
        "seed": 42,
        "distribution": "laplace",
        "strategy": "stock_basic",
        "option_strategy": "call_basic",
        "strike": 100.0,
        "maturity_days": 30,
        "iv": 0.2,
        "rfr": 0.01,
    }
    cli_values = {
        "symbol": symbol,
        "s0": s0,
        "paths": paths,
        "steps": steps,
        "seed": seed,
        "distribution": distribution,
        "strategy": strategy,
        "option_strategy": option_strategy,
        "strike": strike,
        "maturity_days": maturity_days,
        "iv": iv,
        "rfr": rfr,
    }
    casters = {
        "symbol": str,
        "s0": float,
        "paths": int,
        "steps": int,
        "seed": int,
        "distribution": str,
        "strategy": str,
        "option_strategy": str,
        "strike": float,
        "maturity_days": int,
        "iv": float,
        "rfr": float,
    }

    cfg = load_config_with_precedence(
        config_path=config,
        env_prefix="QSE_",
        cli_values=cli_values,
        defaults=defaults,
        casters=casters,
    )

    if not cfg.get("symbol"):
        raise ConfigValidationError("symbol is required (CLI > ENV > YAML)")

    validate_compare_inputs(
        cfg["paths"],
        cfg["steps"],
        cfg["seed"],
        symbol=cfg["symbol"],
        strike=cfg["strike"],
        maturity_days=cfg["maturity_days"],
        implied_vol=cfg["iv"],
        distribution=cfg["distribution"],
    )

    progress = ProgressReporter(total=3, log=log, component="compare")
    log.info("Starting compare run", extra={"symbol": cfg["symbol"]})
    dist = get_distribution(cfg["distribution"])
    import numpy as np

    dist.fit(np.random.laplace(0, 0.01, size=500))
    progress.tick("Distribution fit complete")

    option_spec = OptionSpec(
        option_type="call",
        strike=cfg["strike"],
        maturity_days=cfg["maturity_days"],
        implied_vol=cfg["iv"],
        risk_free_rate=cfg["rfr"],
        contracts=1,
    )
    result = run_compare(
        s0=cfg["s0"],
        distribution=dist,
        n_paths=cfg["paths"],
        n_steps=cfg["steps"],
        seed=cfg["seed"],
        stock_strategy=cfg["strategy"],
        option_strategy=cfg["option_strategy"],
        option_spec=option_spec,
    )
    progress.tick("Simulation finished")
    typer.echo(result.metrics)
    progress.tick("Compare completed")
