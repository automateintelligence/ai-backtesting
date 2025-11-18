"""Cache manager for distribution audits (US6a AS7, T169)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

TTL_DAYS = 30


def _key(symbol: str, lookback_days: int | None, end_date: str | None, data_source: str | None) -> str:
    return "_".join(
        [
            symbol,
            str(lookback_days or "na"),
            str(end_date or "na"),
            str(data_source or "na"),
        ]
    )


def get_cache_path(cache_dir: Path, symbol: str, lookback_days: int | None, end_date: str | None, data_source: str | None) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{_key(symbol, lookback_days, end_date, data_source)}.json"


def is_fresh(path: Path, ttl_days: int = TTL_DAYS) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return datetime.now() - mtime <= timedelta(days=ttl_days)


def load_cache(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


__all__ = ["get_cache_path", "is_fresh", "load_cache", "save_cache", "TTL_DAYS"]
