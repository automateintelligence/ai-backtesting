"""CLI command for parameter grid execution (US2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import typer

from qse.cli.validation import validate_grid_request
from qse.config.loader import load_config_with_precedence
from qse.distributions.factory import get_distribution
from qse.exceptions import ConfigValidationError
from qse.models.options import OptionSpec
from qse.simulation.grid import StrategyGridDefinition, run_grid
from qse.utils.logging import get_logger

log = get_logger(__name__, component="cli.grid")


def _build_option_spec(raw: dict[str, Any] | None) -> OptionSpec:
    if raw is None:
        raise ConfigValidationError("option_spec is required for option strategies")
    payload = {**{"strike": raw.get("strike", "atm")}, **raw}
    return OptionSpec(**payload)


def _parse_strategy_grids(raw: list[dict[str, Any]]) -> list[StrategyGridDefinition]:
    grids: list[StrategyGridDefinition] = []
    for entry in raw:
        shared = entry.get("shared") or {}
        option_spec = None
        if entry.get("kind") == "option":
            option_spec = _build_option_spec(shared.get("option_spec"))
        grids.append(
            StrategyGridDefinition(
                name=str(entry.get("name", "")),
                kind=str(entry.get("kind", "")),
                grid=entry.get("grid") or {},
                shared=shared,
                option_spec=option_spec,
            )
        )
    return grids


def grid(
    config: Path = typer.Option(..., "--config", help="YAML/JSON GridRequest file"),
    max_workers: int | None = typer.Option(None, "--max-workers", help="Override worker count"),
) -> None:
    defaults = {
        "paths": 1000,
        "steps": 60,
        "seed": 42,
        "distribution": "laplace",
        "objective_weights": {"w1": 0.3, "w2": 0.3, "w3": 0.2, "w4": 0.2},
        "s0": 100.0,
    }
    cli_values = {"max_workers": max_workers}
    casters = {
        "symbol": str,
        "paths": int,
        "steps": int,
        "seed": int,
        "distribution": str,
        "s0": float,
        "max_workers": int,
    }

    cfg = load_config_with_precedence(
        config_path=config,
        env_prefix="QSE_GRID_",
        cli_values=cli_values,
        defaults=defaults,
        casters=casters,
    )
    validate_grid_request(cfg)

    strategy_grids = _parse_strategy_grids(cfg["grid"])
    distribution = get_distribution(cfg["distribution"])
    distribution.fit(np.random.laplace(0, 0.01, size=500))

    results = run_grid(
        strategy_grids=strategy_grids,
        distribution=distribution,
        s0=float(cfg.get("s0", 100.0)),
        n_paths=cfg["paths"],
        n_steps=cfg["steps"],
        seed=cfg["seed"],
        objective_weights=cfg.get("objective_weights"),
        max_workers=cfg.get("max_workers"),
    )

    payload = [
        {
            "index": r.index,
            "status": r.status,
            "objective_score": r.objective_score,
            "normalized_metrics": r.normalized_metrics,
            "error": r.error,
        }
        for r in results
    ]
    typer.echo(json.dumps(payload, indent=2))
    log.info("Grid run completed", extra={"configs": len(results)})


__all__ = ["grid"]
