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
) -> list[JsonDict]:
    """Convert validated core semantic candidates to Desktop draft candidates."""

    normalized = _validated_semantic_extraction(extraction)
    return [_desktop_candidate_from_semantic_item(item) for item in normalized.items]


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


def _desktop_candidate_from_semantic_item(item: Any) -> JsonDict:
    if item.article_type_hint not in {
        ArticleType.TECHNICAL_SCR.value,
        ArticleType.HOWTO_QA.value,
    }:
        raise ContractValidationError("semantic article type invalid")
    candidate: JsonDict = {
        "article_type": item.article_type_hint,
        "confirmed_facts": list(item.confirmed_facts),
        "environment": dict(item.environment),
        "item_ref": item.candidate_id,
        "summary": item.summary,
        "title": item.summary,
    }
    _attach_semantic_lists(candidate, item)
    _attach_semantic_optional_fields(candidate, item)
    ensure_safe_sanitized_payload(candidate)
    return candidate


def _attach_semantic_lists(candidate: JsonDict, item: Any) -> None:
    applicable_to = _applicable_to_from_environment(item.environment)
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
