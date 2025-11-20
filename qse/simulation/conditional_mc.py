"""State-conditioned Monte Carlo orchestration (US6)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from qse.distributions.factory import get_distribution
from qse.distributions.integration.metadata_logger import attach_metadata
from qse.distributions.integration.model_loader import load_validated_model
from qse.interfaces.distribution import ReturnDistribution
from qse.mc.conditional import ConditionalSelection, select_conditional_distribution
from qse.mc.generator import generate_price_paths
from qse.models.options import OptionSpec
from qse.schema.episode import CandidateEpisode
from qse.simulation.conditional import _run_simulation_on_paths, extract_episode_windows
from qse.simulation.metrics import MetricsReport
from qse.utils.logging import get_logger

log = get_logger(__name__, component="conditional_mc")


@dataclass
class ConditionalMCRun:
    metrics: MetricsReport
    selection: ConditionalSelection
    run_meta: dict

    def to_json(self) -> str:
        payload = {
            "method": self.selection.method,
            "fallback_reason": self.selection.fallback_reason,
            "episode_count": self.selection.episode_count,
            "metrics": self.metrics.to_formatted_dict(),
        }
        payload.update(self.run_meta)
        return json.dumps(payload, indent=2)


def _filter_episodes_by_state(
    episodes: Iterable[CandidateEpisode],
    state_features: Dict[str, float] | None,
    distance_threshold: float,
) -> list[CandidateEpisode]:
    if not state_features:
        return list(episodes)

    def distance(ep: CandidateEpisode) -> float:
        keys = state_features.keys()
        if not keys:
            return 0.0
        diffs = [(float(ep.state_features.get(k, 0.0)) - float(state_features.get(k, 0.0))) ** 2 for k in keys]
        return math.sqrt(sum(diffs))

    filtered = [ep for ep in episodes if distance(ep) <= distance_threshold]
    return filtered


def _episode_returns(df: pd.DataFrame, episodes: Iterable[CandidateEpisode], max_steps: int | None = None) -> list[np.ndarray]:
    windows = extract_episode_windows(df, episodes)
    returns: list[np.ndarray] = []
    for window in windows:
        prices = window["close"].to_numpy()
        if prices.size < 2:
            continue
        rets = np.diff(np.log(prices))
        if max_steps:
            rets = rets[:max_steps]
        returns.append(rets)
    return returns


def run_conditional_mc(
    *,
    df: pd.DataFrame,
    episodes: list[CandidateEpisode],
    paths: int,
    steps: int,
    seed: int | None,
    distribution: str = "laplace",
    stock_strategy: str = "stock_basic",
    option_strategy: Optional[str] = None,
    option_spec: Optional[OptionSpec] = None,
    state_features: Dict[str, float] | None = None,
    distance_threshold: float = 2.0,
    use_audit: bool = True,
    symbol: str | None = None,
    lookback_days: int | None = None,
    end_date: str | None = None,
    data_source: str | None = None,
    audit_cache_dir: str | None = None,
) -> ConditionalMCRun:
    """Run conditional Monte Carlo simulation from current state."""

    if df.empty:
        raise ValueError("DataFrame is empty")
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column")

    df_sorted = df.sort_values("date") if "date" in df.columns else df.sort_index()
    prices = df_sorted["close"].to_numpy()
    log_returns = np.diff(np.log(prices))

    if distribution == "audit":
        use_audit = True

    def _force_laplace_fallback() -> ReturnDistribution:
        dist = get_distribution("laplace")
        # Manually set safe defaults to avoid heavy-tail fit constraints
        dist.loc = 0.0  # type: ignore[attr-defined]
        dist.scale = 0.01  # type: ignore[attr-defined]
        return dist

    audit_metadata: dict | None = None
    if use_audit:
        lookback_value = lookback_days or len(df_sorted)
        loaded = load_validated_model(
            symbol=symbol or "UNKNOWN",
            lookback_days=lookback_value,
            end_date=end_date,
            data_source=data_source,
            cache_dir=audit_cache_dir,
        )
        base_dist = loaded.distribution
        audit_metadata = loaded.metadata
        log.info(
            "using validated distribution from audit",
            extra={"symbol": symbol, "model": audit_metadata.get("model_name"), "validated": audit_metadata.get("model_validated")},
        )
    else:
        base_dist = get_distribution(distribution)
        try:
            base_dist.fit(log_returns)
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.warning("unconditional distribution fit failed, using Laplace fallback defaults", extra={"error": str(exc)})
            base_dist = _force_laplace_fallback()

    filtered_eps = _filter_episodes_by_state(episodes, state_features, distance_threshold)
    episode_rets = _episode_returns(df_sorted, filtered_eps, max_steps=steps)
    selection = select_conditional_distribution(
        episode_returns=episode_rets, base_distribution=base_dist, n_steps=steps, min_episodes=30, min_samples=max(steps, 60)
    )

    s0 = float(prices[-1])
    price_paths = generate_price_paths(s0=s0, distribution=selection.distribution, n_paths=paths, n_steps=steps, seed=seed)

    metrics = _run_simulation_on_paths(
        price_paths,
        stock_strategy=stock_strategy,
        option_strategy=option_strategy,
        option_spec=option_spec,
        features=None,
    )

    run_meta = {
        "method": selection.method,
        "fallback_reason": selection.fallback_reason,
        "episode_count": selection.episode_count,
        "state_features": state_features or {},
        "distance_threshold": distance_threshold,
    }
    if audit_metadata:
        attach_metadata(run_meta, audit_metadata)
    log.info(
        "conditional MC completed",
        extra={
            "method": selection.method,
            "fallback_reason": selection.fallback_reason,
            "episode_count": selection.episode_count,
        },
    )
    return ConditionalMCRun(metrics=metrics, selection=selection, run_meta=run_meta)


__all__ = ["run_conditional_mc", "ConditionalMCRun"]
