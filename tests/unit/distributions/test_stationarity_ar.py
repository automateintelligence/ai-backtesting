import numpy as np

from qse.distributions.ar_detection import detect_ar_process
from qse.distributions.stationarity import check_stationarity


def test_ar_detection_returns_order_suggestion():
    series = np.array([0, 1, 0, 1, 0], dtype=float)
    result = detect_ar_process(series, max_lag=3)
    assert result.order_suggestion >= 0
    assert isinstance(result.acf_values, list)


def test_stationarity_recommendation():
    series = np.random.normal(0, 1, size=100)
    result = check_stationarity(series)
    assert result.recommendation in {"difference_if_needed", "difference", "stationary", "unknown"}
