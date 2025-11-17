"""Position sizing utilities for targeting expected P&L."""

from __future__ import annotations

import numpy as np


def _compute_share_sizes_for_target(
    closes: np.ndarray,
    target_profit_usd: float,
    expected_daily_move_pct: float,
    max_position_usd: float | None = None,
) -> np.ndarray:
    """
    Returns an integer number of shares per path (shape: [n_paths]) that
    targets approximately `target_profit_usd` for an average one-day move
    of `expected_daily_move_pct` in the underlying.

    shares_i ≈ target_profit / (price_i * expected_daily_move_pct)

    Args:
        closes: Price paths array [n_paths, n_steps]
        target_profit_usd: Target profit in USD (e.g., 500-1000)
        expected_daily_move_pct: Expected daily move as decimal (e.g., 0.02 = 2%)
        max_position_usd: Optional maximum position size cap in USD

    Returns:
        Array of share counts per path [n_paths]
    """
    first_prices = closes[:, 0].astype(float)
    first_prices[first_prices <= 0] = np.nan

    expected_move = first_prices * float(expected_daily_move_pct)
    expected_move[expected_move <= 0] = np.nan

    raw_shares = target_profit_usd / expected_move  # shape: [n_paths]
    raw_shares = np.floor(raw_shares)
    raw_shares[~np.isfinite(raw_shares)] = 0

    shares = raw_shares

    if max_position_usd is not None and max_position_usd > 0:
        max_shares = np.floor(max_position_usd / first_prices)
        max_shares[~np.isfinite(max_shares)] = 0
        shares = np.minimum(shares, max_shares)

    shares = np.maximum(shares, 0)
    return shares.astype(int)


def _compute_contract_sizes_for_target(
    closes: np.ndarray,
    target_profit_usd: float,
    expected_daily_move_pct: float,
    assumed_delta: float = 0.5,
    max_position_usd: float | None = None,
) -> np.ndarray:
    """
    Roughly: pnl ≈ contracts * 100 * delta * (price * move_pct)
    => contracts ≈ target_profit / (100 * delta * price * move_pct)

    Args:
        closes: Price paths array [n_paths, n_steps]
        target_profit_usd: Target profit in USD (e.g., 500-1000)
        expected_daily_move_pct: Expected daily move as decimal (e.g., 0.02 = 2%)
        assumed_delta: Assumed option delta (e.g., 0.5 for ATM)
        max_position_usd: Optional maximum position size cap in USD

    Returns:
        Array of contract counts per path [n_paths]
    """
    first_prices = closes[:, 0].astype(float)
    first_prices[first_prices <= 0] = np.nan

    expected_move = first_prices * float(expected_daily_move_pct)
    expected_move[expected_move <= 0] = np.nan

    denom = 100.0 * float(assumed_delta) * expected_move
    raw_contracts = target_profit_usd / denom
    raw_contracts = np.floor(raw_contracts)
    raw_contracts[~np.isfinite(raw_contracts)] = 0

    contracts = raw_contracts

    if max_position_usd is not None and max_position_usd > 0:
        # Approximate premium per contract as price * 0.5 for ATM with 30–45 DTE.
        approx_premium = first_prices * 0.5
        max_contracts = np.floor(max_position_usd / (approx_premium * 100.0))
        max_contracts[~np.isfinite(max_contracts)] = 0
        contracts = np.minimum(contracts, max_contracts)

    contracts = np.maximum(contracts, 0)
    return contracts.astype(int)


__all__ = ["_compute_share_sizes_for_target", "_compute_contract_sizes_for_target"]
