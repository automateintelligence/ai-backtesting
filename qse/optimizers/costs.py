"""Transaction cost modeling (FR-042–FR-047)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from qse.optimizers.models import CandidateStructure, Leg


@dataclass(frozen=True)
class CostAssumptions:
    commission_per_contract: float = 0.65
    spread_pct: float = 0.15  # fallback when bid/ask missing, pct of mid


def _leg_prices(leg: Leg, spread_pct: float) -> tuple[float, float]:
    """Return (bid, ask) using provided fields or synthetic spread around premium."""
    if leg.bid is not None and leg.ask is not None:
        return leg.bid, leg.ask
    mid = leg.premium
    half_spread = mid * spread_pct / 2.0
    return mid - half_spread, mid + half_spread


def compute_entry_cash(legs: Iterable[Leg], assumptions: CostAssumptions) -> float:
    """Compute entry cash flow (positive = credit received, negative = debit paid)."""
    total = 0.0
    for leg in legs:
        bid, ask = _leg_prices(leg, assumptions.spread_pct)
        qty = abs(leg.quantity)
        price = bid if leg.side == "sell" else ask
        sign = 1 if leg.side == "sell" else -1
        total += sign * price * qty * 100.0
    return total


def compute_expected_exit_cost(legs: Iterable[Leg], assumptions: CostAssumptions) -> float:
    """Estimate exit cost by paying the spread again (reverse the trade)."""
    cost = 0.0
    for leg in legs:
        bid, ask = _leg_prices(leg, assumptions.spread_pct)
        qty = abs(leg.quantity)
        # Reverse fills: buy back shorts at ask, sell longs at bid
        price = ask if leg.side == "sell" else bid
        # Exit cost is cash outflow; shorts lose credit, longs receive proceeds (reduce cost)
        sign = 1 if leg.side == "sell" else -1
        cost += sign * price * qty * 100.0
    return cost


def compute_commission(legs: Iterable[Leg], assumptions: CostAssumptions) -> float:
    return sum(abs(leg.quantity) * assumptions.commission_per_contract for leg in legs)


def apply_costs(candidate: CandidateStructure, assumptions: CostAssumptions | None = None) -> CandidateStructure:
    """Attach cost estimates to candidate.metrics if present."""
    assumptions = assumptions or CostAssumptions()
    if candidate.metrics is None:
        return candidate
    entry_cash = compute_entry_cash(candidate.legs, assumptions)
    exit_cost = compute_expected_exit_cost(candidate.legs, assumptions)
    commission = compute_commission(candidate.legs, assumptions)
    candidate.metrics.entry_cash = entry_cash
    candidate.metrics.expected_exit_cost = exit_cost
    candidate.metrics.commission = commission
    return candidate


__all__ = [
    "CostAssumptions",
    "compute_entry_cash",
    "compute_expected_exit_cost",
    "compute_commission",
    "apply_costs",
]
