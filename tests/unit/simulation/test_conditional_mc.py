import pandas as pd

from quant_scenario_engine.schema.episode import CandidateEpisode
from quant_scenario_engine.simulation.conditional_mc import run_conditional_mc


def _make_df(days: int = 120):
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    closes = [100 + i * 0.5 for i in range(days)]
    return pd.DataFrame(
        {
            "date": dates,
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1_000_000] * days,
        }
    )


def _episodes(count: int, dates: pd.DatetimeIndex):
    return [
        CandidateEpisode(symbol="TEST", t0=dates[i], horizon=10, state_features={"gap_pct": -5.0, "volume_z": 2.8})
        for i in range(count)
    ]


def test_conditional_mc_prefers_bootstrap_when_enough_episodes():
    df = _make_df()
    eps = _episodes(30, df["date"])

    result = run_conditional_mc(
        df=df,
        episodes=eps,
        paths=10,
        steps=5,
        seed=123,
        distribution="laplace",
        stock_strategy="stock_basic",
        state_features={"gap_pct": -5.0, "volume_z": 2.8},
    )

    assert result.selection.method == "bootstrap"
    assert result.selection.episode_count == 30
    assert result.metrics.mean_pnl is not None


def test_conditional_mc_falls_back_when_no_matching_episodes():
    df = _make_df()
    eps = _episodes(5, df["date"])

    result = run_conditional_mc(
        df=df,
        episodes=eps,
        paths=5,
        steps=5,
        seed=7,
        distribution="laplace",
        stock_strategy="stock_basic",
        state_features={"gap_pct": 1.0, "volume_z": -3.0},
        distance_threshold=0.1,
    )

    assert result.selection.method == "unconditional"
    assert result.selection.episode_count == 0
