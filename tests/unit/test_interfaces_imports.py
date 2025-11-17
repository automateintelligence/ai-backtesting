from quant_scenario_engine.interfaces.candidate_selector import CandidateSelector
from quant_scenario_engine.interfaces.distribution import ReturnDistribution
from quant_scenario_engine.interfaces.pricing import OptionPricer
from quant_scenario_engine.interfaces.strategy import Strategy


def test_interface_subclassing():
    class DemoSelector(CandidateSelector):
        def select_candidates(self):
            return []

    class DemoDist(ReturnDistribution):
        def fit(self, returns):
            self.metadata.fit_status = "success"

        def sample(self, n_paths: int, n_steps: int, seed: int | None = None):
            return None

    class DemoPricer(OptionPricer):
        def price(self, path_slice, option_spec):
            return path_slice

    class DemoStrategy(Strategy):
        def generate_signals(self, price_paths, features, params):
            return None

    assert DemoSelector().select_candidates() == []
    dist = DemoDist()
    dist.fit([])
    assert dist.metadata.fit_status == "success"
    assert DemoPricer().price([1], None) == [1]
    assert DemoStrategy().generate_signals(None, None, None) is None
