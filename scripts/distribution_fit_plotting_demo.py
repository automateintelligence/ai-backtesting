"""
Demo script showing how to use the --plot-fit functionality to visualize
distribution fits with quality metrics.

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

import numpy as np
import pandas as pd
from pathlib import Path

from quant_scenario_engine.distributions.distribution_audit import audit_distributions_for_symbol


def demo_fit_plotting():
    """Generate synthetic return data and create fit diagnostic plots."""

    # Generate synthetic log returns with fat tails (Student-t distribution)
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

    print("=" * 80)
    print("Distribution Fit Analysis Demo")
    print("=" * 80)
    print(f"\nGenerated {n_samples} synthetic daily returns")
    print(f"True distribution: Student-t(df={df}, μ={loc:.6f}, σ={scale:.4f})")
    print(f"Initial price: ${initial_price:.2f}")
    print(f"Final price: ${prices[-1]:.2f}")
    print(f"Total return: {(prices[-1]/initial_price - 1)*100:.2f}%")
    print(f"Annualized volatility (realized): {np.std(log_returns) * np.sqrt(252):.2%}")

    # Run audit with plotting enabled
    print("\n" + "=" * 80)
    print("Running distribution audit with fit plotting...")
    print("=" * 80)

    result = audit_distributions_for_symbol(
        symbol="DEMO",
        price_series=price_series,
        train_fraction=0.8,
        require_heavy_tails=True,
        plot_fit=True,  # <-- Enable diagnostic plots
        plot_output_path="output/distribution_fits/demo_fit_diagnostics.png",
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
    print("\nPlot saved to: output/distribution_fits/demo_fit_diagnostics.png")
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
    demo_fit_plotting()
