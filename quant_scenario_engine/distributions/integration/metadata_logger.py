"""Helpers to attach distribution audit metadata to run provenance (US6a AS9)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from quant_scenario_engine.schema.run_meta import RunMeta
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="distribution_metadata")


def _extract_best_score(best_model: str, scores: Iterable[dict]) -> Optional[float]:
    for entry in scores:
        if entry.get("model") == best_model:
            score_val = entry.get("score")
            if score_val is None:
                score_val = entry.get("total_score")
            if score_val is not None:
                return float(score_val)
    return None


def build_audit_metadata(
    *,
    best_model: Optional[str],
    best_fit: Dict[str, Any] | None,
    scores: Iterable[dict] | None,
    cache_path: Path | None,
    stale: bool,
) -> Dict[str, Any]:
    """Create a metadata payload suitable for run_meta recording."""
    fit_timestamp = None
    if cache_path and cache_path.exists():
        fit_timestamp = datetime.fromtimestamp(cache_path.stat().st_mtime).isoformat()

    best_score = _extract_best_score(best_model or "", scores or []) if best_model else None

    metadata: Dict[str, Any] = {
        "model_name": best_model,
        "model_validated": bool(best_model) and not stale,
        "fit_date": fit_timestamp,
        "aic": best_fit.get("aic") if best_fit else None,
        "bic": best_fit.get("bic") if best_fit else None,
        "score": best_score,
        "cache_path": str(cache_path) if cache_path else None,
        "cache_stale": stale,
    }
    return metadata


def attach_metadata(target: RunMeta | dict | None, metadata: Dict[str, Any]) -> None:
    """Attach audit metadata to a RunMeta instance or dict in-place."""
    if target is None:
        return
    if isinstance(target, RunMeta):
        target.distribution_audit = metadata
    elif isinstance(target, dict):
        target["distribution_audit"] = metadata
    else:  # pragma: no cover - defensive branch
        log.warning("Unsupported run_meta container for audit metadata", extra={"type": type(target)})


__all__ = ["build_audit_metadata", "attach_metadata"]
