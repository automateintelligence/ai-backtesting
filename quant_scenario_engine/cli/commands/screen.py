"""Screen CLI command wiring."""

from __future__ import annotations

import json
from pathlib import Path
import ast

import pandas as pd
import typer
import yfinance as yf

from quant_scenario_engine.cli.validation import validate_screen_inputs
from quant_scenario_engine.features.pipeline import enrich_ohlcv
from quant_scenario_engine.selectors.gap_volume import GapVolumeSelector
from quant_scenario_engine.simulation.screen import screen_universe
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="cli_screen")


def _fetch_symbol(symbol: str, start: str, end: str, interval: str, target: Path) -> pd.DataFrame:
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, interval=interval, auto_adjust=True)
    if df.empty:
        raise typer.Exit(code=2)
    df = df.reset_index()
    df.columns = df.columns.str.lower()
    df["symbol"] = symbol
    df["interval"] = interval

    output_dir = target / "historical" / f"interval={interval}" / f"symbol={symbol}" / "_v1"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "data.parquet"
    df.to_parquet(output_file, index=False, engine="pyarrow", compression="snappy")
    return df


def _load_or_fetch(symbol: str, start: str, end: str, interval: str, target: Path) -> pd.DataFrame:
    path = target / "historical" / f"interval={interval}" / f"symbol={symbol}" / "_v1" / "data.parquet"
    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    if path.exists():
        df = pd.read_parquet(path, engine="pyarrow")
        df["date"] = pd.to_datetime(df["date"])
        min_date, max_date = df["date"].min(), df["date"].max()
        if start_ts < min_date or end_ts > max_date:
            # Need to extend data range
            df = _fetch_symbol(symbol, start, end, interval, target)
        else:
            # Serve slice from parquet for shorter interval
            mask = (df["date"] >= start_ts) & (df["date"] <= end_ts)
            df = df.loc[mask].copy()
    else:
        df = _fetch_symbol(symbol, start, end, interval, target)

    return df


def _parse_symbol_list(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw:
        return []
    # Try Python literal list
    try:
        val = ast.literal_eval(raw)
        if isinstance(val, (list, tuple)):
            return [str(v).strip("'\" ") for v in val if str(v).strip()]
    except Exception:
        pass
    # Fallback: comma-delimited string
    cleaned = raw.strip("[]")
    return [s.strip().strip("'\"") for s in cleaned.split(",") if s.strip().strip("'\"")]


def screen(
    universe: str = typer.Option("", help="CSV path or list of symbols (e.g., ['AAPL','MSFT'])"),
    symbols: str = typer.Option("", help="Comma-delimited symbols (alternative to --universe)"),
    start: str = typer.Option(None, help="Start date YYYY-MM-DD when using symbols input"),
    end: str = typer.Option(None, help="End date YYYY-MM-DD when using symbols input"),
    interval: str = typer.Option("1d", help="Data interval"),
    target: Path = typer.Option(Path("data"), help="Target directory for parquet caching"),
    gap_min: float = typer.Option(0.03, help="Minimum absolute gap percentage"),
    volume_z_min: float = typer.Option(1.5, help="Minimum volume z-score"),
    horizon: int = typer.Option(10, help="Episode horizon (bars)"),
    top: int | None = typer.Option(None, help="Top N candidates to keep"),
    max_workers: int = typer.Option(4, help="Max workers for screening"),
) -> None:
    validate_screen_inputs(horizon=horizon, max_workers=max_workers)
    valid_intervals = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
    if interval not in valid_intervals:
        raise typer.Exit(code=1)

    grouped: dict[str, pd.DataFrame] = {}

    if universe:
        # Universe can be a CSV path or inline list of tickers
        path = Path(universe)
        if path.exists():
            df = pd.read_csv(path)
            required = {"symbol", "date", "open", "high", "low", "close", "volume"}
            missing = required - set(df.columns)
            if missing:
                raise typer.Exit(code=1)
            df["date"] = pd.to_datetime(df["date"])
            grouped = {sym: g.set_index("date").sort_index() for sym, g in df.groupby("symbol")}
        else:
            symbols = universe

    if not grouped:
        symbol_list = _parse_symbol_list(symbols)
        if not symbol_list:
            raise typer.Exit(code=1)
        if not start or not end:
            raise typer.Exit(code=1)
        for sym in symbol_list:
            df = _load_or_fetch(sym, start=start, end=end, interval=interval, target=target)
            df = df.sort_values("date")
            grouped[sym] = df.set_index("date")

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
