"""Environment variable overrides (US7)."""

from __future__ import annotations

import os
from typing import Any, Callable

from qse.exceptions import ConfigValidationError


def load_env(prefix: str, casters: dict[str, Callable[[Any], Any]]) -> dict[str, Any]:
    env_values: dict[str, Any] = {}
    for key, caster in casters.items():
        env_key = f"{prefix}{key.upper()}"
        if env_key in os.environ:
            try:
                env_values[key] = caster(os.environ[env_key])
            except Exception as exc:
                raise ConfigValidationError(f"Failed to parse env var {env_key}: {exc}") from exc
    return env_values
