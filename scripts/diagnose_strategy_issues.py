"""Example: Diagnose why a strategy has poor performance.

This script demonstrates a complete workflow:
1. Run a strategy (like the TSLA example with poor metrics)
2. Interpret the metrics to identify problems
3. Inspect positions to understand what went wrong
4. Provide actionable recommendations

Based on the TSLA example:
- mean_pnl: -4.27
- median_pnl: -3.45
- max_drawdown: -72.87%
- sharpe: -0.0142
- sortino: -0.0189
- var: -62.24%
- cvar: -79.24%
"""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.analysis.signals import (
    analyze_signals,
    generate_signal_summary,
    print_position_history,
)
from quant_scenario_engine.distributions.factory import get_distribution
from quant_scenario_engine.mc.generator import generate_price_paths
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.simulation.compare import run_compare


def interpret_metrics(metrics) -> dict:
    """Interpret metrics and provide risk assessment."""
    # Returns analysis
    mean_pnl = metrics.mean_pnl
    max_dd = metrics.max_drawdown
    sharpe = metrics.sharpe
    var_95 = metrics.var
    cvar_95 = metrics.cvar

    # Risk assessment
    risk_level = "EXTREME" if max_dd < -0.5 else "HIGH" if max_dd < -0.3 else "MODERATE" if max_dd < -0.2 else "LOW"

    # Return quality
    return_quality = "POOR" if mean_pnl < 0 else "WEAK" if mean_pnl < 100 else "MODERATE" if mean_pnl < 500 else "GOOD"

    # Risk-adjusted return
    sharpe_quality = "POOR" if sharpe < 0 else "WEAK" if sharpe < 0.5 else "MODERATE" if sharpe < 1.0 else "GOOD"

    # Overall grade
    if risk_level == "EXTREME" or return_quality == "POOR":
        grade = "D-"
    elif risk_level == "HIGH" and return_quality == "WEAK":
        grade = "D+"
    elif risk_level == "MODERATE" and sharpe_quality in ["WEAK", "POOR"]:
        grade = "C"
    elif risk_level == "LOW" and sharpe_quality == "MODERATE":
        grade = "B"
    else:
        grade = "A"

    return {
        "mean_pnl": mean_pnl,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "risk_level": risk_level,
        "return_quality": return_quality,
        "sharpe_quality": sharpe_quality,
        "grade": grade,
    }


def diagnose_positions(signals_stock, signals_option, price_paths) -> dict:
    """Analyze positions to identify problems."""
    stock_analysis = analyze_signals(signals_stock, price_paths, "stock")
    option_analysis = analyze_signals(signals_option, price_paths, "option")

    # Check for over-trading
    stock_overtrading = stock_analysis['mean_changes_per_path'] > 20
    option_overtrading = option_analysis['mean_changes_per_path'] > 20

    # Check for excessive time in market with poor returns
    stock_time_in_market = stock_analysis['pct_time_in_position']
    option_time_in_market = option_analysis['pct_time_in_position']

    # Check position sizes
    stock_position_size = stock_analysis['mean_position_size']
    option_position_size = option_analysis['mean_position_size']

    return {
        "stock": {
            "trades_per_path": stock_analysis['mean_changes_per_path'],
            "time_in_market_pct": stock_time_in_market,
            "avg_position_size": stock_position_size,
            "overtrading": stock_overtrading,
        },
        "option": {
            "trades_per_path": option_analysis['mean_changes_per_path'],
            "time_in_market_pct": option_time_in_market,
            "avg_position_size": option_position_size,
            "overtrading": option_overtrading,
        }
    }


def main():
    """Run complete diagnostic workflow."""

    print("=" * 80)
    print("STRATEGY DIAGNOSTIC WORKFLOW")
    print("=" * 80)
    print()
    print("This example shows how to diagnose poor strategy performance.")
    print("We'll simulate a scenario similar to the TSLA example with concerning metrics.")
    print()

    # Configuration
    config = {
        "s0": 100.0,
        "n_paths": 500,
        "n_steps": 60,
        "seed": 42,
    }

    print(f"Configuration: {config['n_paths']} paths, {config['n_steps']} steps")
    print()

    # Fit distribution - use more volatile distribution to simulate poor performance
    dist = get_distribution("laplace")
    synthetic_returns = np.concatenate([
        np.random.laplace(0, 0.02, size=400),
        np.random.laplace(0, 0.05, size=100),  # More extreme moves
    ])
    dist.fit(synthetic_returns)

    # Option spec
    call_spec = OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.25,
        risk_free_rate=0.01,
        contracts=1,
    )

    print("STEP 1: Running strategy...")
    print("-" * 80)

    # Run compare
    result = run_compare(
        **config,
        distribution=dist,
        stock_strategy="stock_sma_trend",
        option_strategy="option_atm_call_momentum",
        option_spec=call_spec,
        compute_features=True,
    )

    print("✓ Strategy execution complete")
    print()

    # STEP 2: Interpret metrics
    print("STEP 2: Interpreting metrics...")
    print("-" * 80)

    metrics = result.metrics
    interpretation = interpret_metrics(metrics)

    print(f"Mean P&L: ${interpretation['mean_pnl']:,.2f}")
    print(f"Max Drawdown: {interpretation['max_drawdown']:.2%}")
    print(f"Sharpe Ratio: {interpretation['sharpe']:.4f}")
    print(f"VaR (95%): {interpretation['var_95']:.2%}")
    print(f"CVaR (95%): {interpretation['cvar_95']:.2%}")
    print()
    print(f"Risk Level: {interpretation['risk_level']}")
    print(f"Return Quality: {interpretation['return_quality']}")
    print(f"Sharpe Quality: {interpretation['sharpe_quality']}")
    print(f"Overall Grade: {interpretation['grade']}")
    print()

    # STEP 3: Analyze positions
    print("STEP 3: Analyzing positions...")
    print("-" * 80)

    signals = result.signals
    stock_signals = signals.signals_stock
    option_signals = signals.signals_option

    # Regenerate price paths for analysis
    price_paths = generate_price_paths(
        s0=config["s0"],
        distribution=dist,
        n_paths=config["n_paths"],
        n_steps=config["n_steps"],
        seed=config["seed"],
    )

    diagnosis = diagnose_positions(stock_signals, option_signals, price_paths)

    print("Stock Strategy:")
    print(f"  Trades per path: {diagnosis['stock']['trades_per_path']:.1f}")
    print(f"  Time in market: {diagnosis['stock']['time_in_market_pct']:.1f}%")
    print(f"  Avg position size: {diagnosis['stock']['avg_position_size']:.0f} shares")
    print(f"  Overtrading? {'YES ⚠️' if diagnosis['stock']['overtrading'] else 'No'}")
    print()

    print("Option Strategy:")
    print(f"  Trades per path: {diagnosis['option']['trades_per_path']:.1f}")
    print(f"  Time in market: {diagnosis['option']['time_in_market_pct']:.1f}%")
    print(f"  Avg position size: {diagnosis['option']['avg_position_size']:.0f} contracts")
    print(f"  Overtrading? {'YES ⚠️' if diagnosis['option']['overtrading'] else 'No'}")
    print()

    # STEP 4: Print signal summary
    print("STEP 4: Signal summary...")
    print("-" * 80)
    summary = generate_signal_summary(stock_signals, option_signals, price_paths)
    print(summary)

    # STEP 5: Show specific position history
    print("STEP 5: Inspecting position history for path 0...")
    print("-" * 80)
    print()
    print("Stock positions:")
    print_position_history(
        stock_signals, price_paths, path_idx=0, signal_type="stock", max_rows=10
    )
    print()

    print("Option positions:")
    print_position_history(
        option_signals, price_paths, path_idx=0, signal_type="option", max_rows=10
    )
    print()

    # STEP 6: Provide recommendations
    print("STEP 6: Recommendations")
    print("=" * 80)
    print()

    if interpretation['grade'] in ['D-', 'D+']:
        print("⚠️  CRITICAL ISSUES DETECTED")
        print()
        print("This strategy has unacceptable risk levels. Consider:")
        print()
        print("1. REDUCE POSITION SIZING")
        print("   - Current position sizing may be too aggressive")
        print("   - Reduce target_profit_usd from $750 to $250-$400")
        print("   - This will reduce position sizes and overall risk")
        print()
        print("2. ADD STOP LOSSES")
        print("   - Implement max loss per position (e.g., -20%)")
        print("   - Add portfolio-level drawdown limits (e.g., -30%)")
        print()
        print("3. REVIEW STRATEGY LOGIC")
        print("   - Check if SMA periods are appropriate (currently 12/38)")
        print("   - Consider longer periods (20/50) for more stable signals")
        print("   - Review entry/exit conditions")
        print()

        if diagnosis['stock']['overtrading']:
            print("4. ADDRESS OVERTRADING")
            print(f"   - Stock strategy makes {diagnosis['stock']['trades_per_path']:.1f} trades/path")
            print("   - This is excessive and likely causing whipsaw losses")
            print("   - Increase SMA periods or add confirmation filters")
            print()

        if diagnosis['stock']['time_in_market_pct'] > 70:
            print("5. TIME IN MARKET IS TOO HIGH")
            print(f"   - Strategy is in market {diagnosis['stock']['time_in_market_pct']:.1f}% of time")
            print("   - With negative returns, this means constant exposure to losses")
            print("   - Add filters to be more selective about entries")
            print()

    elif interpretation['grade'] in ['C', 'C+']:
        print("⚠️  MODERATE ISSUES DETECTED")
        print()
        print("Strategy has room for improvement:")
        print("1. Risk management could be tighter")
        print("2. Consider adding stop losses")
        print("3. Review position sizing")

    else:
        print("✓ Strategy performance is acceptable")
        print("Continue monitoring and consider minor optimizations")

    print()
    print("=" * 80)
    print()
    print("For more details on metrics, see: planning/METRICS_INTERPRETATION_GUIDE.md")
    print("For position analysis methods, see: planning/HOW_TO_INSPECT_POSITIONS.md")
    print()


if __name__ == "__main__":
    main()
