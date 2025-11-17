"""Screen CLI command wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from quant_scenario_engine.cli.validation import validate_screen_inputs
from quant_scenario_engine.features.pipeline import enrich_ohlcv
from quant_scenario_engine.selectors.gap_volume import GapVolumeSelector
from quant_scenario_engine.simulation.screen import screen_universe
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="cli_screen")


def screen(
    universe: Path = typer.Option(..., exists=True, help="CSV with columns: symbol,date,open,high,low,close,volume"),
    gap_min: float = typer.Option(0.03, help="Minimum absolute gap percentage"),
    volume_z_min: float = typer.Option(1.5, help="Minimum volume z-score"),
    horizon: int = typer.Option(10, help="Episode horizon (bars)"),
    top: int | None = typer.Option(None, help="Top N candidates to keep"),
    max_workers: int = typer.Option(4, help="Max workers for screening"),
) -> None:
    validate_screen_inputs(horizon=horizon, max_workers=max_workers)

    df = pd.read_csv(universe)
    required = {"symbol", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise typer.Exit(code=1)

    df["date"] = pd.to_datetime(df["date"])
    grouped = {sym: g.set_index("date").sort_index() for sym, g in df.groupby("symbol")}

    # Enrich each symbol's data with features
    enriched = {sym: enrich_ohlcv(g) for sym, g in grouped.items()}

    selector = GapVolumeSelector(gap_min=gap_min, volume_z_min=volume_z_min, horizon=horizon)
    candidates = screen_universe(universe=enriched, selector=selector, max_workers=max_workers, top_n=top)

    payload = [
        {
            "symbol": c.symbol,
            "t0": c.t0.isoformat(),
            "horizon": c.horizon,
            "selector": c.selector_name,
            "state_features": c.state_features,
            "score": c.score,
        }
        for c in candidates
    ]

    typer.echo(json.dumps({"candidates": payload}, indent=2))
    log.info("screen command completed", extra={"candidates": len(payload)})

