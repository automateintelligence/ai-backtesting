"""CLI command for optimize-strategy - discover optimal option structures (US1/FR-059)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from qse.config.loader import load_config_with_precedence
from qse.data.factory import FallbackDataSource, get_data_source
from qse.exceptions import ConfigValidationError
from qse.utils.logging import get_logger

console = Console()
log = get_logger(__name__, component="cli.optimize")


def optimize_strategy(
    ticker: str = typer.Option(..., "--ticker", help="Stock ticker symbol (e.g., NVDA)"),
    regime: str = typer.Option(..., "--regime", help="Regime label (e.g., strong-bullish, neutral)"),
    trade_horizon: int = typer.Option(1, "--trade-horizon", help="Trade horizon in days (default: 1)"),
    config: Optional[Path] = typer.Option(None, "--config", help="Path to config.yml file"),
    override: list[str] = typer.Option(
        [], "--override", help="Override config values: --override 'mc.num_paths=10000'"
    ),
    data_source: str = typer.Option(
        "schwab", "--data-source", help="Primary data provider (schwab|yfinance|schwab_stub)"
    ),
    allow_fallback: bool = typer.Option(
        True, "--allow-fallback/--no-fallback", help="Fallback to yfinance on Schwab errors"
    ),
    access_token: Optional[str] = typer.Option(None, "--access-token", envvar="SCHWAB_ACCESS_TOKEN"),
    timeout: float = typer.Option(10.0, "--timeout", help="HTTP timeout seconds for data provider"),
    output: Optional[Path] = typer.Option(None, "--output", help="Output JSON file for results"),
    retest: Optional[Path] = typer.Option(
        None, "--retest", help="Retest existing Top-10 list with fresh market data (<30s mode)"
    ),
) -> None:
    """
    Optimize option strategies from ticker + regime + horizon.

    Returns Top-10 ranked option structures with complete risk/reward analysis.
    Full universe sweep may take up to 1 hour; retest mode completes in <30 seconds.

    Example (full sweep):
        qse optimize-strategy --ticker NVDA --regime strong-bullish --trade-horizon 1

    Example (retest with overrides):
        qse optimize-strategy --ticker NVDA --regime strong-bullish --trade-horizon 1 \\
            --retest top10.json \\
            --override "mc.num_paths=10000" \\
            --override "filters.max_capital=20000"

    Spec References: FR-001, FR-004, FR-059, FR-061
    """
    # Validate ticker
    if not ticker or len(ticker) > 10:
        console.print("[red]Error: Invalid ticker symbol[/red]")
        raise typer.Exit(code=1)

    # Validate trade horizon
    if trade_horizon < 1 or trade_horizon > 30:
        console.print("[red]Error: Trade horizon must be between 1 and 30 days[/red]")
        raise typer.Exit(code=1)

    # Parse CLI overrides (FR-058: --override "path.to.param=value")
    cli_overrides: dict[str, any] = {}
    for override_str in override:
        try:
            if "=" not in override_str:
                raise ValueError(f"Override must be in format 'key=value', got: {override_str}")
            key, value = override_str.split("=", 1)
            # Nested path support: "mc.num_paths" -> {"mc": {"num_paths": ...}}
            _set_nested_value(cli_overrides, key, _parse_value(value))
        except Exception as exc:
            console.print(f"[red]Error parsing override '{override_str}': {exc}[/red]")
            raise typer.Exit(code=1)

    # Load config with precedence: CLI > ENV > YAML > defaults (FR-056, FR-058)
    try:
        merged_config = load_config_with_precedence(
            config_path=config,
            env_prefix="QSE_",
            cli_values=cli_overrides,
            defaults=_get_default_config(),
            casters=_get_config_casters(),
        )
    except ConfigValidationError as exc:
        console.print(f"[red]Config validation failed: {exc}[/red]")
        raise typer.Exit(code=1)

    # Validate regime label (FR-002, FR-060)
    available_regimes = merged_config.get("regimes", {}).keys()
    if regime not in available_regimes and not cli_overrides.get("regime"):
        console.print(
            f"[red]Error: Unknown regime '{regime}'. Available: {', '.join(available_regimes)}[/red]"
        )
        console.print("[yellow]Hint: Use --override to provide explicit regime parameters[/yellow]")
        raise typer.Exit(code=1)

    # Display operation summary
    mode = "retest" if retest else "full sweep"
    console.print(f"[bold cyan]Optimize Strategy ({mode})[/bold cyan]")
    console.print(f"  Ticker: {ticker}")
    console.print(f"  Regime: {regime}")
    console.print(f"  Trade Horizon: {trade_horizon} days")
    console.print(f"  Data Provider: {data_source}")
    if cli_overrides:
        console.print(f"  Overrides: {len(cli_overrides)} parameter(s) set")

    # Initialize data provider with fallback (FR-004, FR-005)
    try:
        primary = get_data_source(
            data_source, access_token=access_token, timeout=timeout, max_retries=3
        )
        provider = (
            FallbackDataSource(primary, get_data_source("yfinance", max_retries=3), logger=log)
            if allow_fallback and data_source != "yfinance"
            else primary
        )
    except Exception as exc:
        console.print(f"[red]Error initializing data provider: {exc}[/red]")
        raise typer.Exit(code=3)

    # Run optimization with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Optimizing {ticker} strategies...", total=None)

        try:
            # Import here to avoid circular dependencies
            from qse.optimizers.strategy_optimizer import StrategyOptimizer

            optimizer = StrategyOptimizer(
                config=merged_config,
                data_provider=provider,
                logger=log,
            )

            # FR-061: Two runtime modes (full sweep vs retest)
            if retest:
                # Retest mode: <30s target by reusing cached structures
                console.print(f"[yellow]Loading cached Top-10 from {retest}...[/yellow]")
                cached_top10 = json.loads(retest.read_text())
                result = optimizer.retest_top10(
                    ticker=ticker,
                    regime=regime,
                    trade_horizon=trade_horizon,
                    cached_top10=cached_top10,
                )
            else:
                # Full sweep mode: Up to 1 hour for broad candidate search
                result = optimizer.optimize(
                    ticker=ticker,
                    regime=regime,
                    trade_horizon=trade_horizon,
                )

            progress.stop()

            # Display results summary (FR-048 to FR-055)
            _display_results(result)

            # Save output if requested
            if output:
                output.write_text(json.dumps(result, indent=2))
                console.print(f"\n[green]✓[/green] Results saved to {output}")

            log.info(
                f"Optimization complete: {ticker} regime={regime} horizon={trade_horizon}d "
                f"top10_count={len(result.get('top10', []))}"
            )

        except Exception as exc:
            progress.stop()
            console.print(f"[red]Optimization failed: {exc}[/red]")
            log.exception(f"Failed to optimize {ticker}")
            raise typer.Exit(code=3)


def _set_nested_value(d: dict, path: str, value: any) -> None:
    """Set nested dictionary value from dot-separated path."""
    keys = path.split(".")
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _parse_value(value_str: str) -> any:
    """Parse string value to appropriate type (int, float, bool, str)."""
    # Boolean
    if value_str.lower() in ("true", "yes", "1"):
        return True
    if value_str.lower() in ("false", "no", "0"):
        return False
    # Number
    try:
        if "." in value_str:
            return float(value_str)
        return int(value_str)
    except ValueError:
        pass
    # String (strip quotes if present)
    return value_str.strip("\"'")


def _get_default_config() -> dict:
    """Default configuration (FR-056: config sections)."""
    return {
        "regimes": {
            "neutral": {"mean_daily_return": 0.0, "daily_vol": 0.01, "skew": 0.0, "kurtosis_excess": 1.0},
            "strong-bullish": {"mean_daily_return": 0.02, "daily_vol": 0.03, "skew": 0.5, "kurtosis_excess": 2.0},
            "mild-bullish": {"mean_daily_return": 0.01, "daily_vol": 0.02, "skew": 0.3, "kurtosis_excess": 1.5},
            "strong-bearish": {"mean_daily_return": -0.02, "daily_vol": 0.03, "skew": -0.5, "kurtosis_excess": 2.0},
            "mild-bearish": {"mean_daily_return": -0.01, "daily_vol": 0.02, "skew": -0.3, "kurtosis_excess": 1.5},
        },
        "mc": {
            "num_paths": 5000,
            "max_paths": 20000,
            "profit_target": 500,
        },
        "filters": {
            "max_capital": 15000,
            "max_loss_pct": 0.05,
            "min_epnl": 500,
            "min_pop_breakeven": 0.60,
        },
        "scoring": {
            "w_pop": 0.35,
            "w_roc": 0.30,
            "w_theta": 0.10,
            "w_tail": 0.15,
            "w_delta": 0.05,
            "w_gamma": 0.03,
            "w_vega": 0.02,
        },
    }


def _get_config_casters() -> dict:
    """Type casters for environment variable parsing."""
    return {
        "mc.num_paths": int,
        "mc.max_paths": int,
        "mc.profit_target": float,
        "filters.max_capital": float,
        "filters.max_loss_pct": float,
        "filters.min_epnl": float,
        "filters.min_pop_breakeven": float,
        "scoring.w_pop": float,
        "scoring.w_roc": float,
        "scoring.w_theta": float,
    }


def _display_results(result: dict) -> None:
    """Display optimization results in rich format (FR-048 to FR-055)."""
    console.print("\n[bold green]Optimization Results[/bold green]")

    top10 = result.get("top10", [])
    if not top10:
        # Empty result with diagnostics (FR-054, FR-055)
        console.print("[yellow]No candidates passed filters.[/yellow]")
        diagnostics = result.get("diagnostics", {})
        if diagnostics:
            console.print("\n[bold]Rejection Breakdown:[/bold]")
            for filter_name, count in diagnostics.get("rejections", {}).items():
                console.print(f"  {filter_name}: {count} candidates")
            if "hints" in diagnostics:
                console.print(f"\n[cyan]Hint: {diagnostics['hints']}[/cyan]")
        return

    # Display Top-10 summary
    console.print(f"\n[bold]Top-{len(top10)} Ranked Strategies:[/bold]")
    for i, candidate in enumerate(top10, 1):
        structure_type = candidate.get("structure_type", "Unknown")
        epnl = candidate.get("E[PnL]", 0)
        pop = candidate.get("POP_0", 0) * 100
        roc = candidate.get("ROC", 0) * 100
        score = candidate.get("composite_score", 0)

        console.print(
            f"  #{i}: {structure_type:20s} | E[PnL]=${epnl:6.0f} | POP={pop:5.1f}% | ROC={roc:4.1f}% | Score={score:.3f}"
        )

    # Display diagnostics summary
    diagnostics = result.get("diagnostics", {})
    if diagnostics:
        console.print("\n[bold]Stage Diagnostics:[/bold]")
        for stage_name, count in diagnostics.get("stage_counts", {}).items():
            console.print(f"  {stage_name}: {count} candidates")
        runtime = diagnostics.get("runtime_seconds", 0)
        console.print(f"\n[cyan]Total Runtime: {runtime:.1f} seconds[/cyan]")
