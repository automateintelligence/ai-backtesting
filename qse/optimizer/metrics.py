"""Adaptive Monte Carlo CI control helpers (FR-032/FR-033).

This module centralizes defaults for adaptive path control so both the optimizer
and diagnostics can consume a single policy. It is intentionally lightweight
and side-effect free so it can be unit tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple


@dataclass(frozen=True)
class AdaptiveCISettings:
    """Configuration for adaptive path control.

    Attributes:
        baseline_paths: Initial path count to run before any adaptation.
        max_paths: Maximum allowed paths (hard cap).
        epnl_ci_target: Target half-width in dollars for E[PnL] CI.
        pop_ci_target: Target half-width (0-1) for POP CI.
    """

    baseline_paths: int = 5_000
    max_paths: int = 20_000
    epnl_ci_target: float = 100.0
    pop_ci_target: float = 0.03


def should_increase_paths(
    epnl_ci_halfwidth: float,
    pop_ci_halfwidth: float,
    settings: AdaptiveCISettings = AdaptiveCISettings(),
) -> bool:
    """Return True if either CI half-width exceeds configured thresholds."""

    return (epnl_ci_halfwidth is not None and epnl_ci_halfwidth > settings.epnl_ci_target) or (
        pop_ci_halfwidth is not None and pop_ci_halfwidth > settings.pop_ci_target
    )


def next_path_count(
    current_paths: int,
    epnl_ci_halfwidth: float,
    pop_ci_halfwidth: float,
    settings: AdaptiveCISettings = AdaptiveCISettings(),
) -> Tuple[int, Literal["continue", "cap_reached", "threshold_met"]]:
    """Compute the next path count based on CI widths and caps.

    Doubling policy (FR-032): if CI thresholds are exceeded, double paths
    until either thresholds are met or max_paths reached. Returns the next
    path count and a status flag for diagnostics.
    """

    if should_increase_paths(epnl_ci_halfwidth, pop_ci_halfwidth, settings):
        proposed = min(current_paths * 2, settings.max_paths)
        if proposed == current_paths:
            return current_paths, "cap_reached"
        return proposed, "continue"
    return current_paths, "threshold_met"
