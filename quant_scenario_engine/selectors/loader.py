"""Selector YAML loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from quant_scenario_engine.selectors.gap_volume import GapVolumeSelector


def load_selector(path: Path):
    data = yaml.safe_load(path.read_text())
    name = data.get("name", "gap_volume")
    params: dict[str, Any] = data.get("parameters", {})
    if name == "gap_volume":
        return GapVolumeSelector(
            gap_min=float(params.get("gap_min", 0.03)),
            volume_z_min=float(params.get("volume_z_min", 1.5)),
            horizon=int(params.get("horizon", 10)),
        )
    raise ValueError(f"Unknown selector type: {name}")


__all__ = ["load_selector"]

