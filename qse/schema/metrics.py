"""Metrics schema with serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path

from qse.simulation.metrics import MetricsReport


def metrics_to_json(report: MetricsReport) -> str:
    return json.dumps(report.to_formatted_dict(include_units=True), indent=2)


def write_metrics_json(report: MetricsReport, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(metrics_to_json(report))
    tmp.replace(path)


def write_metrics_csv(report: MetricsReport, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    formatted = report.to_formatted_dict(include_units=True)
    headers = list(formatted.keys())
    values = [formatted[h] for h in headers]
    tmp.write_text(",".join(headers) + "\n" + ",".join(str(v) for v in values))
    tmp.replace(path)
