"""Metrics schema with serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from quant_scenario_engine.simulation.metrics import MetricsReport


def metrics_to_json(report: MetricsReport) -> str:
    return json.dumps(asdict(report), indent=2)


def write_metrics_json(report: MetricsReport, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(metrics_to_json(report))
    tmp.replace(path)


def write_metrics_csv(report: MetricsReport, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    headers = list(asdict(report).keys())
    values = [asdict(report)[h] for h in headers]
    tmp.write_text(",".join(headers) + "\n" + ",".join(str(v) for v in values))
    tmp.replace(path)

