"""Serializer for distribution audit results (US6a AS7, T170)."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return {k: to_dict(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


def serialize_payload(obj: Any) -> str:
    return json.dumps(to_dict(obj), indent=2, default=str)


def deserialize_payload(payload: str) -> dict[str, Any]:
    return json.loads(payload)


__all__ = ["serialize_payload", "deserialize_payload", "to_dict"]
