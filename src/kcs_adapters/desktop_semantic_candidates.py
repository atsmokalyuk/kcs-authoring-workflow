"""Desktop candidate conversion from validated semantic extraction output."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CandidateSemanticExtraction,
    KcsItemStatus,
    validate_candidate_semantic_extraction,
)

_QUESTION_MARK_RE = re.compile(r"\?+\s*$")
_HOW_FIRST_PERSON_RE = re.compile(
    r"^how\s+(?:can|do|does|should)\s+"
    r"(?:i|we|a\s+customer|the\s+customer|users?)\s+(?P<body>.+)$",
    re.I,
)
_CAUSE_ACTION_LANGUAGE_RE = re.compile(
    r"\b(?:apply|change|check|connect|disable|enable|execute|fix|follow|"
    r"log\s+in|open|repair|replace|restart|run|set|switch|try|use|verify)\b",
    re.I,
)
_CAUSE_EXPLANATORY_LANGUAGE_RE = re.compile(
    r"\b(?:because|caus(?:e|ed|es)|corrupt(?:ed|ion)|disabled|does\s+not|"
    r"empty|fail(?:ed|s|ure)?|incorrect|incompatible|invalid|missing|"
    r"mismatch|not\s+configured|wrong)\b",
    re.I,
)
_QUESTION_CONTEXT_CONNECTOR_RE = re.compile(
    r"\s*,?\s+(?:such as|for example|including|with error(?:s)?(?: like)?|"
    r"when)\s+.+$",
    re.I,
)

def desktop_item_candidates_from_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> list[JsonDict]:
    """Convert validated core semantic candidates to Desktop draft candidates."""

    candidates, _outcomes = desktop_candidate_set_from_semantic_extraction(
        extraction,
        fallback_environment=fallback_environment,
    )
    return candidates


def desktop_candidate_set_from_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> tuple[list[JsonDict], list[JsonDict]]:
    """Return draftable candidates and a ledger for every semantic item."""

    normalized = _validated_semantic_extraction(extraction)
    outcomes = [_semantic_item_outcome_card(item) for item in normalized.items]
    candidates = [
        _desktop_candidate_from_semantic_item(
            item,
            fallback_environment=fallback_environment,
        )
        for item in normalized.items
        if _is_draftable_semantic_item(item)
    ]
    return candidates, outcomes


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
    article_type = _effective_article_type(item)
    if article_type not in {
        ArticleType.TECHNICAL_SCR.value,
        ArticleType.HOWTO_QA.value,
    }:
        raise ContractValidationError("semantic article type invalid")
    environment = _merged_environment(
        item.environment,
        fallback_environment=fallback_environment,
    )
    title = _candidate_title(item, article_type=article_type)
    candidate: JsonDict = {
        "article_type": article_type,
        "confirmed_facts": _confirmed_facts(item, article_type=article_type),
        "environment": environment,
        "item_ref": item.candidate_id,
        "summary": title,
        "title": title,
    }
    _attach_semantic_lists(
        candidate,
        item,
        article_type=article_type,
        environment=environment,
    )
    _attach_semantic_optional_fields(candidate, item)
    ensure_safe_sanitized_payload(candidate)
    return candidate


def _is_draftable_semantic_item(item: Any) -> bool:
    return item.kcs_item_status in {
        KcsItemStatus.CANDIDATE_ALLOWED.value,
        KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,
    }


def _semantic_item_outcome_card(item: Any) -> JsonDict:
    card: JsonDict = {
        "article_type": _safe_article_type_for_outcome(item),
        "item_ref": item.candidate_id,
        "kcs_item_status": item.kcs_item_status,
        "outcome": _semantic_item_outcome(item),
        "title": _candidate_title(
            item,
            article_type=_safe_article_type_for_outcome(item),
        ),
    }
    if item.open_questions:
        card["open_questions"] = list(item.open_questions)
    ensure_safe_sanitized_payload(card)
    return card


def _safe_article_type_for_outcome(item: Any) -> str:
    try:
        return _effective_article_type(item)
    except Exception:
        return str(item.article_type_hint)


def _semantic_item_outcome(item: Any) -> str:
    if item.kcs_item_status == KcsItemStatus.CANDIDATE_ALLOWED.value:
        return "draft_candidate"
    if item.kcs_item_status == KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value:
        return "internal_candidate"
    if item.kcs_item_status == KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value:
        return "blocked_need_more_evidence"
    return "not_draftable"


def _effective_article_type(item: Any) -> str:
    """Treat explicit Q&A evidence as Q&A even when Claude labels it SCR."""

    article_type = item.article_type_hint
    if article_type != ArticleType.TECHNICAL_SCR.value:
        return str(article_type)
    if _has_supported_cause_for_scr(item):
        return str(article_type)
    if _has_text(item.question) or _has_text(item.supported_answer):
        return ArticleType.HOWTO_QA.value
    return str(article_type)


def _has_supported_cause_for_scr(item: Any) -> bool:
    if not _has_text(item.supported_cause):
        return False
    cause = str(item.supported_cause).strip()
    if _CAUSE_ACTION_LANGUAGE_RE.search(cause) and not (
        _CAUSE_EXPLANATORY_LANGUAGE_RE.search(cause)
    ):
        return False
    return True


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
    article_type: str,
    environment: Mapping[str, Any],
) -> None:
    applicable_to = _applicable_to_from_environment(environment)
    if applicable_to:
        candidate["applicable_to"] = applicable_to
    symptoms = list(item.symptoms)
    if not symptoms and article_type == ArticleType.HOWTO_QA.value:
        symptoms = [item.question or item.summary]
    if symptoms:
        candidate["symptoms"] = symptoms
    if item.resolution_steps:
        candidate["resolution_steps"] = list(item.resolution_steps)
        if article_type == ArticleType.HOWTO_QA.value:
            candidate["answer_steps"] = list(item.resolution_steps)


def _attach_semantic_optional_fields(candidate: JsonDict, item: Any) -> None:
    optional_fields = ("supported_resolution_or_workaround", "supported_answer")
    for field_name in optional_fields:
        value = getattr(item, field_name)
        if value is not None:
            candidate[field_name] = value
    if candidate.get("article_type") != ArticleType.HOWTO_QA.value:
        value = getattr(item, "supported_cause")
        if value is not None:
            candidate["supported_cause"] = value
    question = _candidate_question(
        item,
        article_type=str(candidate.get("article_type", "")),
    )
    if question is not None:
        candidate["question"] = question


def _confirmed_facts(item: Any, *, article_type: str) -> list[str]:
    facts = list(item.confirmed_facts)
    if facts:
        return facts
    if article_type != ArticleType.HOWTO_QA.value:
        return facts
    for value in (item.question, item.supported_answer, item.summary):
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return facts


def _candidate_title(item: Any, *, article_type: str) -> str:
    if article_type == ArticleType.HOWTO_QA.value and _has_text(item.question):
        return _compact_howto_title(item.question)
    if article_type == ArticleType.HOWTO_QA.value and _has_text(item.summary):
        return _compact_howto_title(item.summary)
    return str(item.summary)


def _candidate_question(item: Any, *, article_type: str) -> str | None:
    if not _has_text(item.question):
        return item.question
    if article_type != ArticleType.HOWTO_QA.value:
        return item.question
    return _normalize_howto_question_text(item.question)


def _normalize_howto_question_text(value: str) -> str:
    text = _normalize_howto_base(value)
    if text.endswith("?"):
        return text
    return f"{text}?"


def _compact_howto_title(value: str) -> str:
    text = _normalize_howto_base(value)
    text = _QUESTION_CONTEXT_CONNECTOR_RE.sub("", text).strip()
    if not text:
        text = _normalize_howto_base(value)
    if text.endswith("?"):
        return text
    return f"{text}?"


def _normalize_howto_base(value: str) -> str:
    text = _QUESTION_MARK_RE.sub("", value.strip()).strip()
    match = _HOW_FIRST_PERSON_RE.match(text)
    if match is not None:
        return _how_to_phrase(match.group("body"))
    return text


def _how_to_phrase(body: str) -> str:
    body = body.strip()
    if not body:
        return "How to perform the requested task"
    return f"How to {body[0].lower()}{body[1:]}"


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
    "desktop_candidate_set_from_semantic_extraction",
    "desktop_item_candidates_from_semantic_extraction",
]
