"""CLI command for fetching historical market data via yfinance."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import typer
import yfinance as yf
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from quant_scenario_engine.utils.logging import get_logger

console = Console()
log = get_logger(__name__, component="cli.fetch")


def fetch(
    symbol: str = typer.Option(..., "--symbol", help="Stock ticker symbol (e.g., AAPL)"),
    start: str = typer.Option(
        ..., "--start", help="Start date in YYYY-MM-DD format (e.g., 2018-01-01)"
    ),
    end: str = typer.Option(
        ..., "--end", help="End date in YYYY-MM-DD format (e.g., 2024-12-31)"
    ),
    interval: str = typer.Option(
        "1d", "--interval", help="Data interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo"
    ),
    target: Path = typer.Option(
        Path("data"), "--target", help="Target directory for parquet output"
    ),
) -> None:
    """
    Fetch historical market data and save as Parquet.

    Downloads OHLCV data via yfinance and stores in partitioned Parquet format:
    target/historical/interval={interval}/symbol={symbol}/_v1/data.parquet

    Example:
        python -m quant_scenario_engine.cli.fetch --symbol AAPL --start 2018-01-01 --end 2024-12-31 --interval 1d --target data/
    """
    # Validate dates
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        if start_dt >= end_dt:
            console.print("[red]Error: Start date must be before end date[/red]")
            raise typer.Exit(code=1)
    except ValueError as exc:
        console.print(f"[red]Error: Invalid date format - {exc}[/red]")
        raise typer.Exit(code=1)

    # Validate interval
    valid_intervals = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]
    if interval not in valid_intervals:
        console.print(
            f"[red]Error: Invalid interval '{interval}'. Must be one of: {', '.join(valid_intervals)}[/red]"
        )
        raise typer.Exit(code=1)

    # Setup output directory
    output_dir = (
        target / "historical" / f"interval={interval}" / f"symbol={symbol}" / "_v1"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "data.parquet"

    console.print(f"[bold cyan]Fetching {symbol} data[/bold cyan]")
    console.print(f"  Period: {start} to {end}")
    console.print(f"  Interval: {interval}")
    console.print(f"  Output: {output_file}")

    # Fetch data with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Downloading {symbol} data...", total=None)

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval=interval, auto_adjust=True)

            if df.empty:
                progress.stop()
                console.print(
                    f"[red]Error: No data returned for {symbol}. Check symbol and date range.[/red]"
                )
                raise typer.Exit(code=2)

            progress.update(task, description=f"Processing {len(df)} rows...")

            # Standardize column names and add metadata
            df = df.reset_index()
            df.columns = df.columns.str.lower()
            df["symbol"] = symbol
            df["interval"] = interval

            # Save as Parquet
            progress.update(task, description=f"Writing {output_file.name}...")
            df.to_parquet(output_file, index=False, engine="pyarrow", compression="snappy")

            progress.stop()
            console.print(f"[green]✓[/green] Successfully saved {len(df)} rows to {output_file}")
            log.info(
                f"Fetched {symbol} data: {len(df)} rows from {start} to {end} (interval={interval})"
            )

        except Exception as exc:
            progress.stop()
            console.print(f"[red]Error during fetch: {exc}[/red]")
            log.exception(f"Failed to fetch data for {symbol}")
            raise typer.Exit(code=3)
