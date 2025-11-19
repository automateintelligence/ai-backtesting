"""CLI command for running distribution audits (US6a)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer

from quant_scenario_engine.cli.formatters.audit_formatter import format_audit_result
from quant_scenario_engine.data.cache import load_or_fetch
from quant_scenario_engine.distributions.distribution_audit import audit_distributions_for_symbol
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="cli_audit_distributions")


def audit_distributions(
    symbol: str = typer.Option(..., "--symbol", help="Ticker symbol to audit"),
    lookback_days: int = typer.Option(756, "--lookback-days", help="Historical days to audit"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date YYYY-MM-DD"),
    interval: str = typer.Option("1d", "--interval", help="Data interval for historical fetch"),
    target: Path = typer.Option(Path("data"), "--target", help="Data cache directory"),
    force_refit: bool = typer.Option(False, "--force-refit/--use-cache", help="Bypass cached audit results"),
    plot_fit: bool = typer.Option(False, "--plot-fit/--no-plot-fit", help="Emit diagnostic fit plot"),
) -> None:
    try:
        end_ts = pd.Timestamp(end_date) if end_date else pd.Timestamp.utcnow().normalize()
    except Exception:
        log.error("invalid end date", extra={"end_date": end_date})
        raise typer.Exit(code=1)

    start_ts = end_ts - pd.Timedelta(days=lookback_days)
    log.info(
        "Fetching historical data for audit",
        extra={"symbol": symbol, "start": start_ts.date().isoformat(), "end": end_ts.date().isoformat(), "interval": interval},
    )

    df = load_or_fetch(
        symbol,
        start=start_ts.date().isoformat(),
        end=end_ts.date().isoformat(),
        interval=interval,
        target=target,
    )
    if df.empty:
        log.error("No data returned for audit", extra={"symbol": symbol})
        raise typer.Exit(code=2)

    price_series = df.sort_values("date")["close"]

    result = audit_distributions_for_symbol(
        symbol=symbol,
        price_series=price_series,
        lookback_days=lookback_days,
        end_date=end_ts.date().isoformat(),
        data_source=f"yfinance:{interval}",
        force_refit=force_refit,
        plot_fit=plot_fit,
    )

    typer.echo(format_audit_result(result))
    log.info("distribution audit complete", extra={"symbol": symbol, "best_model": result.best_model.name if result.best_model else None})


__all__ = ["audit_distributions"]
