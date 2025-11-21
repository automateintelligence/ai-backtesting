from __future__ import annotations

import numpy as np
import pytest

from qse.exceptions import ResourceLimitError
from qse.interfaces.distribution import ReturnDistribution
from qse.models.options import OptionSpec
from qse.schema.strategy import StrategyParams
from qse.simulation.grid import (
    GridResult,
    StrategyGridDefinition,
    _clamp_workers,
    _preflight_resources,
    _score_results,
    expand_strategy_grid,
    run_grid,
)
from qse.simulation.metrics import MetricsReport


class FakeDistribution(ReturnDistribution):
    def fit(self, returns) -> None:  # pragma: no cover - no-op
        return None

    def sample(self, n_paths: int, n_steps: int, seed: int | None = None):
        rng = np.random.default_rng(seed)
        return rng.normal(0.001, 0.01, size=(n_paths, n_steps))


def test_expand_strategy_grid_cross_product() -> None:
    grid_def = StrategyGridDefinition(
        name="stock_basic",
        kind="stock",
        grid={"short_window": [3, 5], "long_window": [10, 15]},
        shared={"fees": 0.001},
    )

    params = expand_strategy_grid(grid_def)

    assert len(params) == 4
    windows = {(p.params["short_window"], p.params["long_window"]) for p in params}
    assert windows == {(3, 10), (3, 15), (5, 10), (5, 15)}
    assert all(isinstance(p, StrategyParams) for p in params)


def test_expand_strategy_grid_empty_returns_default() -> None:
    grid_def = StrategyGridDefinition(name="stock_basic", kind="stock", grid={}, shared={"fees": 0.001})

    params = expand_strategy_grid(grid_def)

    assert len(params) == 1
    assert params[0].params == {}
    assert params[0].fees == pytest.approx(0.001)


def test_score_results_ranks_objective() -> None:
    results = [
        GridResult(
            index=0,
            status="success",
            stock_params=None,
            option_params=None,
            metrics=MetricsReport(
                mean_pnl=10,
                median_pnl=9,
                max_drawdown=-0.1,
                sharpe=1.2,
                sortino=0.0,
                var=-0.05,
                cvar=-0.08,
                var_method="historical",
                lookback_window=None,
                covariance_estimator="sample",
                bankruptcy_rate=0.0,
                early_exercise_events=0,
            ),
        ),
        GridResult(
            index=1,
            status="success",
            stock_params=None,
            option_params=None,
            metrics=MetricsReport(
                mean_pnl=2,
                median_pnl=1,
                max_drawdown=-0.05,
                sharpe=0.4,
                sortino=0.0,
                var=-0.02,
                cvar=-0.03,
                var_method="historical",
                lookback_window=None,
                covariance_estimator="sample",
                bankruptcy_rate=0.0,
                early_exercise_events=0,
            ),
        ),
    ]

    ranked = _score_results(results, {"w1": 0.3, "w2": 0.3, "w3": 0.2, "w4": 0.2})

    assert ranked[0].objective_score is not None
    assert ranked[0].objective_score >= ranked[1].objective_score  # winner first
    assert ranked[0].normalized_metrics is not None


def test_clamp_workers_caps_to_contract_limit(monkeypatch) -> None:
    monkeypatch.setattr("os.cpu_count", lambda: 16)

    assert _clamp_workers(12) == 6


def test_preflight_resource_limit_exceeds_budget() -> None:
    with pytest.raises(ResourceLimitError):
        _preflight_resources(
            n_paths=1_000_000,
            n_steps=10_000,
            config_count=2,
            max_workers=4,
            total_ram_gb=1.0,
        )


def test_run_grid_executes_and_scores() -> None:
    option_spec = OptionSpec(
        option_type="call",
        strike="atm",
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.01,
        contracts=1,
    )
    strategy_grids = [
        StrategyGridDefinition(
            name="stock_basic",
            kind="stock",
            grid={"short_window": [3, 4]},
        ),
        StrategyGridDefinition(
            name="call_basic",
            kind="option",
            grid={"momentum_window": [2]},
            shared={"option_spec": {}},
            option_spec=option_spec,
        ),
    ]

    results = run_grid(
        strategy_grids=strategy_grids,
        distribution=FakeDistribution(),
        s0=100.0,
        n_paths=20,
        n_steps=20,
        seed=5,
        max_workers=1,
        time_budget_seconds=5.0,
    )

    assert len(results) == 2
    assert all(r.status == "success" for r in results)
    assert all(r.objective_score is not None for r in results)

