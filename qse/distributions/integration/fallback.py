"""Fallback helpers when no validated audit is available (US6a AS10)."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from qse.distributions.laplace import LaplaceDistribution
from qse.interfaces.distribution import ReturnDistribution
from qse.utils.logging import get_logger

log = get_logger(__name__, component="distribution_fallback")


def laplace_fallback_distribution(reason: str) -> Tuple[ReturnDistribution, Dict[str, Any]]:
    """Return a minimally configured Laplace distribution plus metadata."""
    dist = LaplaceDistribution()
    # Provide safe defaults so sampling works even without fit
    dist.loc = 0.0
    dist.scale = 0.01
    metadata = {
        "model_name": "laplace",
        "model_validated": False,
        "fallback_reason": reason,
    }
    log.warning(
        "No validated distribution available; falling back to Laplace",
        extra={"reason": reason, "action": "run audit-distributions CLI"},
    )
    return dist, metadata


__all__ = ["laplace_fallback_distribution"]
