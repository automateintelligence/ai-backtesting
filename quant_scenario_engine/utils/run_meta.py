"""Helpers to build run_meta from components."""

from __future__ import annotations

from typing import Any

from quant_scenario_engine.schema.run_meta import RunMeta


def build_run_meta(
    run_id: str,
    symbol: str,
    config: dict[str, Any],
    storage_policy: str,
    seed: int,
    covariance_estimator: str | None = None,
    var_method: str | None = None,
    lookback_window: int | None = None,
    drift_status: str | None = None,
    iv_source: str | None = None,
    parameter_stability: str | None = None,
    distribution_audit: dict[str, Any] | None = None,
) -> RunMeta:
    return RunMeta.capture_context(
        run_id=run_id,
        symbol=symbol,
        config=config,
        storage_policy=storage_policy,
        seed=seed,
        covariance_estimator=covariance_estimator,
        var_method=var_method,
        lookback_window=lookback_window,
        drift_status=drift_status,
        iv_source=iv_source,
        parameter_stability=parameter_stability,
        distribution_audit=distribution_audit,
    )
