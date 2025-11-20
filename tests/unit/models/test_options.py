import pytest

from qse.exceptions import ConfigValidationError
from qse.models.options import OptionSpec


def test_option_spec_valid():
    spec = OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.2,
        risk_free_rate=0.05,
        contracts=1,
        iv_source="config_default",
    )
    assert spec.option_type == "call"
    assert spec.early_exercise is False


def test_option_spec_validation_errors():
    with pytest.raises(ConfigValidationError):
        OptionSpec(
            option_type="call",
            strike=-1.0,
            maturity_days=30,
            implied_vol=0.2,
            risk_free_rate=0.05,
            contracts=1,
            iv_source="config_default",
        )
    with pytest.raises(ConfigValidationError):
        OptionSpec(
            option_type="invalid",  # type: ignore
            strike=100.0,
            maturity_days=30,
            implied_vol=0.2,
            risk_free_rate=0.05,
            contracts=1,
            iv_source="config_default",
        )
