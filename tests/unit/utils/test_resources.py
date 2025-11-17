import pytest

from quant_scenario_engine.exceptions import ResourceLimitError
from quant_scenario_engine.utils.resources import estimate_footprint_gb, select_storage_policy


def test_estimate_and_policy_memory():
    est = estimate_footprint_gb(100, 10)
    assert est > 0
    policy, _ = select_storage_policy(10, 10, total_ram_gb=10)
    assert policy == "memory"


def test_policy_memmap_and_abort():
    policy, _ = select_storage_policy(1_500_000, 1_500, total_ram_gb=50)
    assert policy == "memmap"

    with pytest.raises(ResourceLimitError):
        select_storage_policy(10_000_000, 10_000_000, total_ram_gb=1)
