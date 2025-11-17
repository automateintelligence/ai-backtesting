"""Compare CLI command wiring."""

from __future__ import annotations

import typer

from quant_scenario_engine.cli.validation import validate_compare_inputs
from quant_scenario_engine.distributions.factory import get_distribution
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.simulation.run import run_compare


def compare(
    symbol: str = typer.Option(..., help="Ticker symbol"),
    s0: float = typer.Option(100.0, help="Starting price"),
    paths: int = typer.Option(1000, help="Number of MC paths"),
    steps: int = typer.Option(60, help="Steps per path"),
    seed: int = typer.Option(42, help="Random seed"),
    distribution: str = typer.Option("laplace", help="Return distribution"),
    strike: float = typer.Option(100.0, help="Option strike"),
    maturity_days: int = typer.Option(30, help="Option maturity in days"),
    iv: float = typer.Option(0.2, help="Implied volatility"),
    rfr: float = typer.Option(0.01, help="Risk-free rate"),
) -> None:
    validate_compare_inputs(paths, steps, seed)
    dist = get_distribution(distribution)
    # fit dummy distribution to proceed; in practice supply real returns
    import numpy as np

    dist.fit(np.random.laplace(0, 0.01, size=500))
    option_spec = OptionSpec(
        option_type="call",
        strike=strike,
        maturity_days=maturity_days,
        implied_vol=iv,
        risk_free_rate=rfr,
        contracts=1,
    )
    result = run_compare(
        s0=s0,
        distribution=dist,
        n_paths=paths,
        n_steps=steps,
        seed=seed,
        option_spec=option_spec,
    )
    typer.echo(result.metrics)

