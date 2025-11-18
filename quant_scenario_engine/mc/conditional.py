"""Conditional Monte Carlo distribution selection (bootstrap → refit → unconditional)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

from quant_scenario_engine.distributions.conditional import ConditionalRefitDistribution
from quant_scenario_engine.distributions.episode_bootstrap import EpisodeBootstrapDistribution
from quant_scenario_engine.exceptions import DistributionFitError
from quant_scenario_engine.interfaces.distribution import ReturnDistribution
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="mc.conditional")


@dataclass
class ConditionalSelection:
    distribution: ReturnDistribution
    method: str
    fallback_reason: Optional[str]
    episode_count: int


def select_conditional_distribution(
    *,
    episode_returns: Iterable[np.ndarray],
    base_distribution: ReturnDistribution,
    n_steps: int,
    min_episodes: int = 30,
    min_samples: int = 60,
) -> ConditionalSelection:
    """Choose conditional sampling method with fallbacks."""

    episodes_list = [np.asarray(r, dtype=float).flatten() for r in episode_returns if len(r) > 0]
    fallback_reason: str | None = None

    # 1) Episode bootstrap (non-parametric)
    try:
        bootstrap = EpisodeBootstrapDistribution(min_episodes=min_episodes, min_samples=min_samples)
        bootstrap.fit(episodes_list, min_samples=max(n_steps, min_samples))
        log.info("conditional MC using episode bootstrap", extra={"episodes": len(episodes_list)})
        return ConditionalSelection(distribution=bootstrap, method="bootstrap", fallback_reason=None, episode_count=len(episodes_list))
    except DistributionFitError as exc:  # pragma: no cover - exercised via fallback tests
        fallback_reason = str(exc)
        log.warning("bootstrap conditional MC fallback", extra={"reason": fallback_reason})

    # 2) Parametric refit on conditioned samples
    try:
        if episodes_list:
            conditioned = np.concatenate(episodes_list)
            refit = ConditionalRefitDistribution(base_distribution)
            refit.fit(conditioned, min_samples=max(min_samples, n_steps))
            log.info("conditional MC using parametric refit", extra={"samples": conditioned.size})
            return ConditionalSelection(
                distribution=refit, method="parametric_refit", fallback_reason=fallback_reason, episode_count=len(episodes_list)
            )
    except DistributionFitError as exc:  # pragma: no cover - exercised via fallback tests
        fallback_reason = str(exc)
        log.warning("parametric conditional MC fallback", extra={"reason": fallback_reason})

    # 3) Unconditional fallback
    log.info("conditional MC using unconditional distribution", extra={"reason": fallback_reason})
    return ConditionalSelection(
        distribution=base_distribution,
        method="unconditional",
        fallback_reason=fallback_reason or "insufficient episodes",
        episode_count=len(episodes_list),
    )


__all__ = ["select_conditional_distribution", "ConditionalSelection"]
