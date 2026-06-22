"""Desktop candidate conversion from validated semantic extraction output."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CandidateSemanticExtraction,
    validate_candidate_semantic_extraction,
)


def desktop_item_candidates_from_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> list[JsonDict]:
    """Convert validated core semantic candidates to Desktop draft candidates."""

    normalized = _validated_semantic_extraction(extraction)
    return [
        _desktop_candidate_from_semantic_item(
            item,
            fallback_environment=fallback_environment,
        )
        for item in normalized.items
    ]


def _validated_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
) -> CandidateSemanticExtraction:
    validation = validate_candidate_semantic_extraction(extraction)
    if not validation.ok:
        raise ContractValidationError("semantic extraction output invalid")
    return (
        extraction
        if isinstance(extraction, CandidateSemanticExtraction)
        else CandidateSemanticExtraction.from_json_dict(extraction)
    )


def _desktop_candidate_from_semantic_item(
    item: Any,
    *,
    fallback_environment: Mapping[str, Any] | None,
) -> JsonDict:
    if item.article_type_hint not in {
        ArticleType.TECHNICAL_SCR.value,
        ArticleType.HOWTO_QA.value,
    }:
        raise ContractValidationError("semantic article type invalid")
    environment = _merged_environment(
        item.environment,
        fallback_environment=fallback_environment,
    )
    candidate: JsonDict = {
        "article_type": item.article_type_hint,
        "confirmed_facts": list(item.confirmed_facts),
        "environment": environment,
        "item_ref": item.candidate_id,
        "summary": item.summary,
        "title": item.summary,
    }
    _attach_semantic_lists(candidate, item, environment=environment)
    _attach_semantic_optional_fields(candidate, item)
    ensure_safe_sanitized_payload(candidate)
    return candidate


def _merged_environment(
    environment: Mapping[str, Any],
    *,
    fallback_environment: Mapping[str, Any] | None,
) -> JsonDict:
    merged: JsonDict = {
        key: value
        for key, value in dict(fallback_environment or {}).items()
        if _environment_value_present(value)
    }
    merged.update(
        {
            key: value
            for key, value in dict(environment).items()
            if _environment_value_present(value)
        }
    )
    return merged


def _environment_value_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(isinstance(item, str) and item.strip() for item in value)
    return True


def _attach_semantic_lists(
    candidate: JsonDict,
    item: Any,
    *,
    environment: Mapping[str, Any],
) -> None:
    applicable_to = _applicable_to_from_environment(environment)
    if applicable_to:
        candidate["applicable_to"] = applicable_to
    symptoms = list(item.symptoms)
    if not symptoms and item.article_type_hint == ArticleType.HOWTO_QA.value:
        symptoms = [item.question or item.summary]
    if symptoms:
        candidate["symptoms"] = symptoms
    if item.resolution_steps:
        candidate["resolution_steps"] = list(item.resolution_steps)


def _attach_semantic_optional_fields(candidate: JsonDict, item: Any) -> None:
    optional_fields = (
        "supported_cause",
        "supported_resolution_or_workaround",
        "question",
        "supported_answer",
    )
    for field_name in optional_fields:
        value = getattr(item, field_name)
        if value is not None:
            candidate[field_name] = value


def _applicable_to_from_environment(environment: Mapping[str, Any]) -> list[str]:
    value = environment.get("applicable_to")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [
            item.strip()
            for item in value
            if isinstance(item, str) and item.strip()
        ]
    platform = environment.get("platform")
    if isinstance(platform, str) and platform.strip():
        return [platform.strip()]
    return []


__all__ = [
    "desktop_item_candidates_from_semantic_extraction",
]
