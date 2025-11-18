"""
Demo script showing how to use the --plot-fit functionality to visualize
distribution fits with quality metrics.

Usage:
    # Synthetic data (default):
    python scripts/distribution_fit_plotting_demo.py

    # Real market data:
    python scripts/distribution_fit_plotting_demo.py --symbol AAPL
    python scripts/distribution_fit_plotting_demo.py --symbol AAPL --lookback 500

This demonstrates the model selection criteria currently used in the code:
- AIC component (20%): Lower AIC is better
- Tail component (40%): Lower tail error is better (average of 95% and 99% quantile errors)
- VaR component (30%): VaR backtest pass rate
- Cluster component (10%): Volatility clustering (autocorrelation of squared returns)

Selection logic:
1. Filter to fit_success=True models
2. If require_heavy_tails=True, filter to heavy_tailed=True models
3. Select model with HIGHEST total score
4. Fallback to best available fit if no heavy-tailed models
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path

from quant_scenario_engine.distributions.distribution_audit import audit_distributions_for_symbol


def fetch_real_data(symbol: str, lookback_days: int = 1000) -> tuple[pd.Series, dict]:
    """
    Fetch real market data from yfinance.

    Returns
    -------
    tuple[pd.Series, dict]
        Price series and metadata dict with summary statistics
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "yfinance is required for fetching real market data. "
            "Install with: pip install yfinance"
        )

    print(f"Fetching {lookback_days} days of price data for {symbol}...")
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{lookback_days}d")

    if hist.empty:
        raise ValueError(f"No data returned for symbol {symbol}")

    price_series = hist["Close"]
    log_returns = np.log(price_series / price_series.shift(1)).dropna()

    metadata = {
        "symbol": symbol,
        "n_samples": len(price_series),
        "initial_price": price_series.iloc[0],
        "final_price": price_series.iloc[-1],
        "total_return": (price_series.iloc[-1] / price_series.iloc[0] - 1) * 100,
        "annualized_vol": np.std(log_returns) * np.sqrt(252),
        "start_date": price_series.index[0].strftime("%Y-%m-%d"),
        "end_date": price_series.index[-1].strftime("%Y-%m-%d"),
    }

    return price_series, metadata


def generate_synthetic_data() -> tuple[pd.Series, dict]:
    """
    Generate synthetic return data with fat tails.

    Returns
    -------
    tuple[pd.Series, dict]
        Price series and metadata dict with generation parameters
    """
    np.random.seed(42)
    n_samples = 1000

    # Create Student-t distributed returns with heavy tails (df=5)
    from scipy.stats import t
    df = 5  # degrees of freedom (lower = heavier tails)
    loc = 0.0005  # slight positive drift
    scale = 0.015  # daily volatility ~1.5%

    log_returns = t.rvs(df=df, loc=loc, scale=scale, size=n_samples)

    # Convert to price series
    initial_price = 100.0
    prices = initial_price * np.exp(np.cumsum(log_returns))
    price_series = pd.Series(prices, index=pd.date_range("2023-01-01", periods=n_samples, freq="D"))

    metadata = {
        "symbol": "DEMO",
        "n_samples": n_samples,
        "true_distribution": f"Student-t(df={df}, μ={loc:.6f}, σ={scale:.4f})",
        "initial_price": initial_price,
        "final_price": prices[-1],
        "total_return": (prices[-1] / initial_price - 1) * 100,
        "annualized_vol": np.std(log_returns) * np.sqrt(252),
    }

    return price_series, metadata


def demo_fit_plotting(symbol: str | None = None, lookback_days: int = 1000):
    """
    Generate fit diagnostic plots for synthetic or real market data.

    Parameters
    ----------
    symbol : str | None
        If provided, fetch real data for this ticker symbol.
        If None, use synthetic Student-t data.
    lookback_days : int
        Number of days of historical data to fetch (for real data only).
    """
    # Fetch or generate data
    if symbol:
        price_series, metadata = fetch_real_data(symbol, lookback_days)
        symbol_name = symbol.upper()
    else:
        price_series, metadata = generate_synthetic_data()
        symbol_name = "DEMO"

    # Print data summary
    print("=" * 80)
    print("Distribution Fit Analysis Demo")
    print("=" * 80)

    if symbol:
        print(f"\nReal market data: {metadata['symbol']}")
        print(f"Period: {metadata['start_date']} to {metadata['end_date']}")
        print(f"Samples: {metadata['n_samples']} daily prices")
    else:
        print(f"\nSynthetic data: {metadata['n_samples']} samples")
        print(f"True distribution: {metadata['true_distribution']}")

    print(f"Initial price: ${metadata['initial_price']:.2f}")
    print(f"Final price: ${metadata['final_price']:.2f}")
    print(f"Total return: {metadata['total_return']:.2f}%")
    print(f"Annualized volatility (realized): {metadata['annualized_vol']:.2%}")

    # Run audit with plotting enabled
    print("\n" + "=" * 80)
    print("Running distribution audit with fit plotting...")
    print("=" * 80)

    output_filename = f"{symbol_name.lower()}_fit_diagnostics.png"
    output_path = f"output/distribution_fits/{output_filename}"

    result = audit_distributions_for_symbol(
        symbol=symbol_name,
        price_series=price_series,
        train_fraction=0.8,
        require_heavy_tails=True,
        plot_fit=True,  # <-- Enable diagnostic plots
        plot_output_path=output_path,
    )

    # Display results
    print("\n" + "=" * 80)
    print("MODEL SELECTION RESULTS")
    print("=" * 80)

    print("\nFit Results:")
    for fr in result.fit_results:
        status = "✓ SUCCESS" if fr.fit_success else "✗ FAILED"
        ht_status = "✓" if fr.heavy_tailed else "✗"
        print(f"\n  {fr.model_name.upper()}: {status}")
        print(f"    Heavy-tailed: {ht_status}")
        print(f"    AIC: {fr.aic:.2f}")
        print(f"    BIC: {fr.bic:.2f}")
        print(f"    Parameters: {fr.params}")
        if fr.warnings:
            print(f"    Warnings: {fr.warnings}")

    print("\n" + "-" * 80)
    print("Model Scores (Higher is Better):")
    print("-" * 80)

    for score in sorted(result.scores, key=lambda s: s.total_score, reverse=True):
        print(f"\n  {score.model_name.upper()}: {score.total_score:.4f}")
        print(f"    AIC component (20%):     {score.components['aic']:.4f}")
        print(f"    Tail component (40%):    {score.components['tail']:.4f}")
        print(f"    VaR component (30%):     {score.components['var']:.4f}")
        print(f"    Cluster component (10%): {score.components['cluster']:.4f}")

    print("\n" + "=" * 80)
    print("BEST MODEL SELECTION")
    print("=" * 80)

    if result.best_model:
        print(f"\n✓ Selected: {result.best_model.name.upper()}")
        if result.best_fit:
            print(f"  AIC: {result.best_fit.aic:.2f}")
            print(f"  BIC: {result.best_fit.bic:.2f}")
            print(f"  Heavy-tailed: {'Yes' if result.best_fit.heavy_tailed else 'No'}")
            print(f"  Parameters: {result.best_fit.params}")
    else:
        print("\n✗ No model selected (all fits failed or no heavy-tailed models available)")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC PLOTS GENERATED")
    print("=" * 80)
    print(f"\nPlot saved to: {output_path}")
    print("\nThe plot contains 4 panels:")
    print("  1. PDF Overlay: Empirical histogram + fitted PDFs with legends")
    print("  2. CDF Comparison: Cumulative distributions")
    print("  3. Q-Q Plots: Quantile-quantile diagnostic for all models")
    print("  4. Left Tail Focus: Extreme loss region (bottom 10%)")
    print("\nEach legend shows:")
    print("  - Model name and fitted parameters")
    print("  - AIC and BIC values")
    print("  - Heavy-tail indicator (✓/✗)")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Demo script for distribution fit diagnostic plotting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Synthetic data (default):
  python scripts/distribution_fit_plotting_demo.py

  # Real market data:
  python scripts/distribution_fit_plotting_demo.py --symbol AAPL
  python scripts/distribution_fit_plotting_demo.py --symbol TSLA --lookback 500
        """,
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Stock ticker symbol (e.g., AAPL, TSLA). If not provided, uses synthetic data.",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=1000,
        help="Number of days of historical data to fetch (default: 1000). Only used with --symbol.",
    )

    args = parser.parse_args()
    demo_fit_plotting(symbol=args.symbol, lookback_days=args.lookback)
