import pandas as pd
import pytest

from qse.optimizers.costs import (
    CostAssumptions,
    compute_commission,
    compute_entry_cash,
    compute_expected_exit_cost,
)
from qse.optimizers.models import CandidateStructure, Leg


def make_vertical():
    legs = [
        Leg(option_type="call", strike=100, expiry=pd.Timestamp("2025-01-01"), side="sell", premium=5.0, bid=4.9, ask=5.1),
        Leg(option_type="call", strike=105, expiry=pd.Timestamp("2025-01-01"), side="buy", premium=3.0, bid=2.9, ask=3.1),
    ]
    return CandidateStructure(structure_type="vertical", legs=legs, expiry=pd.Timestamp("2025-01-01"), width=5.0)


def test_entry_cash_uses_bid_ask_when_available():
    candidate = make_vertical()
    entry = compute_entry_cash(candidate.legs, CostAssumptions())
    # entry = short at bid 4.9*100 - long at ask 3.1*100 = 490 - 310 = 180
    assert entry == pytest.approx(180.0)


def test_exit_cost_reverses_fills():
    candidate = make_vertical()
    exit_cost = compute_expected_exit_cost(candidate.legs, CostAssumptions())
    # exit: buy back short at ask 5.1*100, sell long at bid 2.9*100 => 510 - 290 = 220 cost
    assert exit_cost == pytest.approx(220.0)


def test_commission_applies_per_contract():
    candidate = make_vertical()
    commission = compute_commission(candidate.legs, CostAssumptions(commission_per_contract=0.65))
    assert commission == 0.65 * 2
