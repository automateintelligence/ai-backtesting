"""Model ranking helpers for distribution audit (US6a AS2)."""

from __future__ import annotations

from typing import Iterable, List, Tuple

from qse.distributions.models import FitResult


def rank_by_information_criteria(fit_results: Iterable[FitResult]) -> List[Tuple[str, float, float]]:
    """
    Rank models by AIC/BIC (lower is better).

    Returns list of tuples (model_name, aic, bic) sorted by AIC then BIC.
    Models with fit_success=False are placed at the end.
    """
    scored: List[Tuple[str, float, float, bool]] = []
    for fr in fit_results:
        scored.append((fr.model_name, fr.aic, fr.bic, fr.fit_success))

    ranked = sorted(scored, key=lambda x: (not x[3], x[1], x[2]))
    return [(name, aic, bic) for name, aic, bic, _ in ranked]


__all__ = ["rank_by_information_criteria"]
