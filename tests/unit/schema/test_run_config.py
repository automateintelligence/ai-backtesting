import pytest

from qse.exceptions import ConfigValidationError
from qse.schema.run_config import RunConfig


def test_run_config_valid_and_to_dict():
    cfg = RunConfig(
        n_paths=10,
        n_steps=5,
        seed=42,
        distribution_model="laplace",
        data_source="yfinance",
        covariance_estimator="sample",
        var_method="historical",
    )
    out = cfg.to_dict()
    assert out["n_paths"] == 10
    assert out["var_method"] == "historical"


def test_run_config_validation_errors():
    with pytest.raises(ConfigValidationError):
        RunConfig(
            n_paths=0,
            n_steps=5,
            seed=42,
            distribution_model="laplace",
            data_source="yfinance",
        )
    with pytest.raises(ConfigValidationError):
        RunConfig(
            n_paths=10,
            n_steps=5,
            seed=42,
            distribution_model="laplace",
            data_source="yfinance",
            var_method="bad",  # type: ignore
        )
