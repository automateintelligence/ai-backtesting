"""Config loader with CLI > ENV > YAML precedence (FR-024/FR-026)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from qse.exceptions import ConfigValidationError


def _load_yaml(path: Path) -> dict[str, Any]:
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
    config_path: Path | None,
    env_prefix: str,
    cli_values: dict[str, Any],
    defaults: dict[str, Any],
    casters: dict[str, Callable[[Any], Any]],
) -> dict[str, Any]:
    """
    Merge config values with precedence CLI > ENV > YAML > defaults.

    Supports nested overrides via dot-notation (e.g., "mc.num_paths" -> {"mc": {"num_paths": value}}).
    CLI values from optimize command are pre-parsed into nested dicts.

    Spec: FR-003, FR-056, FR-058 (--override flag support)
    Tasks: T012
    """

    file_values: dict[str, Any] = {}
    if config_path:
        file_values = _load_yaml(config_path)

    env_values: dict[str, Any] = {}
    for key, caster in casters.items():
        env_key = f"{env_prefix}{key.upper()}"
        if env_key in os.environ:
            env_values[key] = _coerce(os.environ[env_key], caster)

    # Deep merge with precedence: CLI > ENV > YAML > defaults
    # Use deep_merge to handle nested dicts from CLI overrides
    merged = _deep_merge(defaults, file_values)
    merged = _deep_merge(merged, env_values)
    merged = _deep_merge(merged, cli_values)

    # Log overrides
    for key, val in cli_values.items():
        if val is not None and key in defaults and defaults.get(key) != val:
            _log_override(key, "CLI", defaults.get(key), val)
    for key, val in env_values.items():
        if key in defaults and defaults.get(key) != val and key not in cli_values:
            _log_override(key, "ENV", defaults.get(key), val)
    for key, val in file_values.items():
        if key in defaults and defaults.get(key) != val and key not in cli_values and key not in env_values:
            _log_override(key, "YAML", defaults.get(key), val)

    return merged


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """
    Deep merge two dictionaries, with override taking precedence.

    Recursively merges nested dicts. Non-dict values in override replace base values.

    Example:
        base = {"mc": {"num_paths": 5000, "max_paths": 20000}}
        override = {"mc": {"num_paths": 10000}}
        result = {"mc": {"num_paths": 10000, "max_paths": 20000}}
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dicts
            result[key] = _deep_merge(result[key], value)
        else:
            # Override non-dict values or add new keys
            result[key] = value
    return result


def _log_override(field: str, source: str, old: Any, new: Any) -> None:
    try:
        import logging

        log = logging.getLogger(__name__)
        log.info("Config override", extra={"field": field, "source": source, "old": old, "new": new})
    except Exception:
        return
