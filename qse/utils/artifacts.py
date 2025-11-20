"""Artifact writer utilities."""

from __future__ import annotations

from pathlib import Path

from qse.schema.metrics import write_metrics_csv, write_metrics_json
from qse.schema.run_meta import RunMeta
from qse.simulation.metrics import MetricsReport


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_run_artifacts(base_dir: Path, metrics: MetricsReport, run_meta: RunMeta) -> None:
    ensure_dir(base_dir)
    write_metrics_json(metrics, base_dir / "metrics.json")
    write_metrics_csv(metrics, base_dir / "metrics.csv")
    run_meta.write_atomic(base_dir / "run_meta.json")

