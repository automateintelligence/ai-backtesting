from pathlib import Path

from qse.schema.run_meta import RunMeta


def test_run_meta_round_trip(tmp_path: Path):
    meta = RunMeta.capture_context(
        run_id="run-1",
        symbol="AAPL",
        config={"paths": 10},
        storage_policy="memory",
        seed=42,
        covariance_estimator="sample",
        var_method="historical",
        lookback_window=252,
    )
    path = tmp_path / "run_meta.json"
    meta.write_atomic(path)
    loaded = RunMeta.from_json(path.read_text())
    assert loaded.run_id == "run-1"
    assert loaded.storage_policy == "memory"
    assert loaded.reproducibility is not None
