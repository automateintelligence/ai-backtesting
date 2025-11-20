import numpy as np

from qse.models.options import OptionSpec
from qse.schema.signals import StrategySignals
from qse.simulation.metrics import compute_metrics
from qse.simulation.simulator import MarketSimulator


def test_compute_metrics_basic():
    pnl = np.array([1.0, 2.0, -1.0])
    equity = np.array([100.0, 101.0, 102.0])
    report = compute_metrics(pnl, equity)
    assert report.mean_pnl == pnl.mean()
    assert report.var_method == "historical"


def test_market_simulator_runs():
    paths = np.array([[1, 2, 3], [2, 3, 4]], dtype=float)
    signals = StrategySignals(
        signals_stock=np.ones_like(paths, dtype=np.int8),
        signals_option=np.zeros_like(paths, dtype=np.int8),
        option_spec=None,
        features_used=[],
    )
    sim = MarketSimulator()
    report = sim.run(paths, signals)
    assert report.mean_pnl is not None


def test_market_simulator_with_option():
    paths = np.array([[100, 101, 102]], dtype=float)
    spec = OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.01,
        contracts=1,
    )
    signals = StrategySignals(
        signals_stock=np.zeros_like(paths, dtype=np.int8),
        signals_option=np.ones_like(paths, dtype=np.int8),
        option_spec=spec,
        features_used=[],
    )
    sim = MarketSimulator()
    report = sim.run(paths, signals)
    assert report.mean_pnl is not None
