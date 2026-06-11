"""Small JSON payload helpers for KCS packet contracts."""

from __future__ import annotations

import json
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
    json.dumps(data, sort_keys=True)
    return data


def dumps_payload(payload: JsonPayload) -> str:
    """Serialize a packet payload using deterministic key ordering."""

    return json.dumps(dump_json_dict(payload), sort_keys=True, separators=(",", ":"))
