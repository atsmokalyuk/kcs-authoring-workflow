from __future__ import annotations

import json

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dump_json_dict, dumps_payload, require_json_object
from kcs_core.models import KcsReviewerPacket, RecommendedAction


class _TestPayload:
    def __init__(self, data: object) -> None:
        self._data = data

    def to_json_dict(self) -> object:
        return self._data


def test_dump_json_dict_returns_serializable_payload() -> None:
    packet = KcsReviewerPacket(
        case_ref="CASE-SYNTH",
        recommended_action=RecommendedAction.NO_ARTICLE.value,
        review_required=True,
    )

    payload = dump_json_dict(packet)

    assert payload["schema_version"] == KcsReviewerPacket.SCHEMA_VERSION
    assert json.loads(dumps_payload(packet)) == payload


def test_require_json_object_rejects_non_object_payload() -> None:
    with pytest.raises(ContractValidationError):
        require_json_object(["not", "an", "object"])


def test_dump_json_dict_rejects_non_object_to_json_dict_result() -> None:
    with pytest.raises(ContractValidationError):
        dump_json_dict(_TestPayload(["not", "an", "object"]))  # type: ignore[arg-type]


def test_dump_json_dict_rejects_non_string_object_keys() -> None:
    with pytest.raises(ContractValidationError):
        dump_json_dict(_TestPayload({True: "value"}))  # type: ignore[arg-type]


def test_dump_json_dict_rejects_nan_values() -> None:
    with pytest.raises(ContractValidationError):
        dump_json_dict(_TestPayload({"confidence": float("nan")}))  # type: ignore[arg-type]


def test_dumps_payload_rejects_non_serializable_values() -> None:
    with pytest.raises(ContractValidationError):
        dumps_payload(_TestPayload({"bad": object()}))  # type: ignore[arg-type]
