"""Universe screening utilities for candidate selection."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Iterable, Mapping

import pandas as pd

from quant_scenario_engine.interfaces.candidate_selector import CandidateSelector
from quant_scenario_engine.schema.episode import CandidateEpisode
from quant_scenario_engine.utils.logging import get_logger

log = get_logger(__name__, component="screen")


def _clamp_workers(max_workers: int) -> int:
    return max(1, min(int(max_workers), 6))


def _screen_symbol(symbol: str, df: pd.DataFrame, selector: CandidateSelector) -> list[CandidateEpisode]:
    if df.empty:
        log.warning("empty dataframe for symbol", extra={"symbol": symbol})
        return []
    df = df.copy()
    df["symbol"] = symbol
    episodes = selector.select(df)
    for ep in episodes:
        ep.symbol = symbol
    return episodes


def screen_universe(
    *,
    universe: Mapping[str, pd.DataFrame],
    selector: CandidateSelector,
    max_workers: int = 4,
    top_n: int | None = None,
) -> list[CandidateEpisode]:
    """Apply selector across a universe of symbols with optional parallelism."""

    worker_count = _clamp_workers(max_workers)
    results: list[CandidateEpisode] = []

    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(_screen_symbol, sym, df, selector): sym for sym, df in universe.items()}
        for fut in as_completed(futures):
            symbol = futures[fut]
            try:
                episodes = fut.result()
                results.extend(episodes)
            except Exception as exc:  # pragma: no cover - defensive logging
                log.error("screening failed for symbol", extra={"symbol": symbol, "error": str(exc)})

    if top_n is not None and results:
        results.sort(key=lambda ep: ep.score or 0.0, reverse=True)
        results = results[: int(top_n)]

    log.info("screening complete", extra={"candidates": len(results)})
    return results

