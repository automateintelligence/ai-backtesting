import numpy as np

from quant_scenario_engine.distributions.laplace import LaplaceDistribution
from quant_scenario_engine.models.options import OptionSpec
from quant_scenario_engine.simulation.run import run_compare


def test_run_compare_executes():
    returns = np.random.laplace(0, 0.01, size=400)
    dist = LaplaceDistribution()
    dist.fit(returns)
    spec = OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.01,
        contracts=1,
    )
    result = run_compare(s0=100.0, distribution=dist, n_paths=5, n_steps=5, seed=123, option_spec=spec)
    assert result.metrics.mean_pnl is not None
    assert result.signals.option_spec == spec
