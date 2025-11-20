"""Cache age helpers for distribution audit integration (US6a AS9)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from qse.distributions.cache.cache_manager import TTL_DAYS
from qse.utils.logging import get_logger

log = get_logger(__name__, component="distribution_cache")


def cache_age_days(path: Path) -> Optional[float]:
    """Return cache age in days or None if file missing."""
    if not path.exists():
        return None
    delta = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return delta.total_seconds() / 86400.0


def warn_if_stale(path: Path, ttl_days: int = TTL_DAYS) -> bool:
    """Log a warning when cache age exceeds TTL; return True if stale."""
    age = cache_age_days(path)
    if age is None:
        return False
    stale = age > ttl_days
    if stale:
        log.warning(
            "Cached distribution audit is stale; consider re-running audit",
            extra={"path": str(path), "age_days": round(age, 2), "ttl_days": ttl_days},
        )
    return stale


__all__ = ["cache_age_days", "warn_if_stale"]
