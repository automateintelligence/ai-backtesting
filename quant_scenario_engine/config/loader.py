"""Config loader with CLI > ENV > YAML precedence (FR-024/FR-026)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from quant_scenario_engine.exceptions import ConfigValidationError


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ConfigValidationError(f"Config file not found: {path}")
    if path.suffix.lower() not in {".yml", ".yaml", ".json"}:
        raise ConfigValidationError("Config file must be YAML or JSON")
    text = path.read_text()
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ConfigValidationError("pyyaml is required to load YAML configs") from exc
    return yaml.safe_load(text) or {}


def _coerce(value: str, caster: Callable[[str], Any]) -> Any:
    try:
        return caster(value)
    except Exception as exc:  # pragma: no cover - defensive
        raise ConfigValidationError(f"Failed to parse config value '{value}': {exc}")


def load_config_with_precedence(
    *,
    config_path: Optional[Path],
    env_prefix: str,
    cli_values: Dict[str, Any],
    defaults: Dict[str, Any],
    casters: Dict[str, Callable[[Any], Any]],
) -> Dict[str, Any]:
    """Merge config values with precedence CLI > ENV > YAML > defaults."""

    file_values: Dict[str, Any] = {}
    if config_path:
        file_values = _load_yaml(config_path)

    env_values: Dict[str, Any] = {}
    for key, caster in casters.items():
        env_key = f"{env_prefix}{key.upper()}"
        if env_key in os.environ:
            env_values[key] = _coerce(os.environ[env_key], caster)

    merged: Dict[str, Any] = {}
    for key, default in defaults.items():
        cli_val = cli_values.get(key)
        if cli_val is not None:
            merged[key] = cli_val
            continue
        if key in env_values:
            merged[key] = env_values[key]
            continue
        if key in file_values:
            merged[key] = file_values[key]
            continue
        merged[key] = default

    return merged
