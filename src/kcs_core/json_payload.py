"""Small JSON payload helpers for KCS packet contracts."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from kcs_core.errors import ContractValidationError

JsonDict = dict[str, Any]


class JsonPayload(Protocol):
    """Protocol for packet objects that can be serialized to JSON dicts."""

    def to_json_dict(self) -> JsonDict:
        """Return a JSON-serializable dictionary."""


PacketT = TypeVar("PacketT", bound=JsonPayload)


def require_json_object(payload: Mapping[str, Any] | object) -> Mapping[str, Any]:
    """Return payload when it is a JSON object, otherwise raise a contract error."""

    if not isinstance(payload, Mapping):
        raise ContractValidationError("payload must be a JSON object")
    return payload


def dump_json_dict(payload: JsonPayload) -> JsonDict:
    """Return a JSON-compatible dict and verify it can be encoded."""

    data = payload.to_json_dict()
    require_json_object(data)
    _ensure_strict_json_value(data)
    _dumps_strict_json(data)
    return dict(data)


def dumps_payload(payload: JsonPayload) -> str:
    """Serialize a packet payload using deterministic key ordering."""

    return _dumps_strict_json(dump_json_dict(payload), compact=True)


def _dumps_strict_json(data: Mapping[str, Any], *, compact: bool = False) -> str:
    try:
        if compact:
            return json.dumps(
                data,
                sort_keys=True,
                allow_nan=False,
                separators=(",", ":"),
            )
        return json.dumps(data, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ContractValidationError(
            "payload must be strict JSON-serializable"
        ) from exc


def _ensure_strict_json_value(value: object) -> None:
    if isinstance(value, Mapping):
        _ensure_strict_json_object(value)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_strict_json_value(item)
        return
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ContractValidationError("payload must be strict JSON-serializable")
    raise ContractValidationError("payload must be strict JSON-serializable")


def _ensure_strict_json_object(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("payload object keys must be strings")
        _ensure_strict_json_value(item)
