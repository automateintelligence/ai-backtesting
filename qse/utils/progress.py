"""Lightweight progress reporter for long-running operations."""

from __future__ import annotations

import logging
import time


class ProgressReporter:
    """Emit progress logs based on count or time intervals.

    Designed to satisfy FR-039: progress every N items (default 10) or every
    minute, whichever comes first.
    """

    def __init__(
        self,
        *,
        total: int | None = None,
        log: logging.Logger | None = None,
        every: int = 10,
        every_seconds: int = 60,
        component: str | None = None,
    ) -> None:
        self.total = total
        self.log = log or logging.getLogger(__name__)
        self.every = max(1, every)
        self.every_seconds = max(1, every_seconds)
        self.component = component
        self._count = 0
        self._last_log = time.time()

    def tick(self, message: str | None = None, *, increment: int = 1) -> None:
        self._count += increment
        now = time.time()
        should_log = (
            self._count % self.every == 0
            or (now - self._last_log) >= self.every_seconds
            or (self.total is not None and self._count >= self.total)
        )
        if not should_log:
            return
        pct = None
        if self.total:
            pct = round((self._count / self.total) * 100, 2)
        msg = message or "progress"
        extra = {"component": self.component, "progress_count": self._count}
        if pct is not None:
            extra["progress_pct"] = pct
            msg = f"{msg} ({self._count}/{self.total}, {pct}% complete)"
        self.log.info(msg, extra=extra)
        self._last_log = now
