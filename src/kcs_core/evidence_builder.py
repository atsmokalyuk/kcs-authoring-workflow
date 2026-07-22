"""Evidence package builder for approved sanitized KCS inputs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, require_json_object
from kcs_core.models import ArticleType, CandidateOrigin, NormalizedTicketEvidencePacket
from kcs_core.safety import (
    EvidenceVisibility,
    InputClass,
    validate_evidence_safety,
)
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
    normalize_json_object,
    normalize_json_object_list,
    normalize_optional_string,
    normalize_string_list,
)

APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION = "approved_zendesk_evidence_export_v1"


class EvidenceBuildSafetyError(ContractValidationError):
    """Raised when a normalized evidence export fails the safety gate."""


_ALLOWED_EXPORT_FIELDS = frozenset(
    {
        "confirmed_facts",
        "environment",
        "input_class",
        "issue_candidates",
        "open_questions",
        "sanitizer_report",
        "schema_version",
        "source_refs",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "visibility_summary",
    }
)
_ALLOWED_CANDIDATE_FIELDS = frozenset(
    {
        "answer_steps",
        "applicable_to",
        "article_type",
        "atomic",
        "candidate_id",
        "candidate_origin",
        "confirmed_facts",
        "customer_reported",
        "customer_specific",
        "environment",
        "internal_reviewer_notes",
        "kcs_applicable",
        "open_questions",
        "public_solution_safe",
        "question",
        "resolution_state",
        "resolution_steps",
        "reuse_checked",
        "reuse_search_run_ref",
        "reuse_search_status",
        "source_refs",
        "split_required",
        "summary",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "third_party_generic",
        "third_party_only",
        "title",
        "unsupported_public_article",
    }
)
_CANDIDATE_STRING_FIELDS = frozenset(
    {
        "article_type",
        "candidate_origin",
        "question",
        "resolution_state",
        "reuse_search_run_ref",
        "reuse_search_status",
        "summary",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "title",
    }
)
_CANDIDATE_LIST_FIELDS = frozenset(
    {
        "answer_steps",
        "applicable_to",
        "confirmed_facts",
        "internal_reviewer_notes",
        "open_questions",
        "resolution_steps",
        "source_refs",
        "symptoms",
    }
)
_CANDIDATE_BOOL_FIELDS = frozenset(
    {
        "atomic",
        "customer_reported",
        "customer_specific",
        "kcs_applicable",
        "public_solution_safe",
        "reuse_checked",
        "split_required",
        "third_party_generic",
        "third_party_only",
        "unsupported_public_article",
    }
)


@dataclass(frozen=True)
class EvidenceBuildPolicy:
    """Policy controls for KCS-7 evidence package building."""

    input_class: str = InputClass.NORMALIZED_ZENDESK_EVIDENCE.value
    assume_sanitized: bool = False
    allow_internal_reviewer_only: bool = False


def build_evidence_packet_from_zendesk_export(
    payload: Mapping[str, Any],
    *,
    case_ref: str,
    policy: EvidenceBuildPolicy,
) -> NormalizedTicketEvidencePacket:
    """Build a normalized evidence packet from approved sanitized export JSON."""

    data = require_json_object(payload)
    ensure_safe_sanitized_payload(data)
    _require_export_schema(data)
    ensure_allowed_keys(data, _ALLOWED_EXPORT_FIELDS, label="evidence export")

    packet = NormalizedTicketEvidencePacket(
        case_ref=ensure_safe_ref(case_ref, label="case_ref"),
        input_class=_input_class(data, policy),
        source_refs=_source_refs(data.get("source_refs")),
        issue_candidates=_issue_candidates(data.get("issue_candidates")),
        environment=normalize_json_object(data.get("environment"), required=True),
        symptoms=_top_level_or_single_candidate_list(data, "symptoms"),
        confirmed_facts=_top_level_or_single_candidate_list(data, "confirmed_facts"),
        supported_cause=_top_level_or_single_candidate_string(
            data, "supported_cause"
        ),
        supported_resolution_or_workaround=_top_level_or_single_candidate_string(
            data, "supported_resolution_or_workaround"
        ),
        open_questions=normalize_string_list(data.get("open_questions")),
        visibility_summary=_visibility_summary(data, policy),
        sanitizer_report=_sanitizer_report(data, policy),
    )
    _ensure_packet_safe(packet)
    return packet


def _require_export_schema(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION:
        raise ContractValidationError("unsupported evidence export schema_version")


def _input_class(data: Mapping[str, Any], policy: EvidenceBuildPolicy) -> str:
    value = normalize_optional_string(data.get("input_class")) or policy.input_class
    try:
        return InputClass(value).value
    except ValueError as exc:
        raise ContractValidationError("unsupported evidence input_class") from exc


def _source_refs(value: object) -> list[str]:
    refs = normalize_string_list(value, required=True)
    return [ensure_safe_ref(ref, label="source_ref") for ref in refs]


def _issue_candidates(value: object) -> list[JsonDict]:
    candidates = normalize_json_object_list(value)
    if not candidates:
        raise ContractValidationError("evidence export requires issue_candidates")
    return [_issue_candidate(candidate) for candidate in candidates]


def _issue_candidate(candidate: Mapping[str, Any]) -> JsonDict:
    ensure_allowed_keys(candidate, _ALLOWED_CANDIDATE_FIELDS, label="issue candidate")
    result: JsonDict = {}
    for key, value in candidate.items():
        normalized = _candidate_field(key, value)
        if normalized is not None:
            result[key] = normalized
    return result


def _candidate_field(key: str, value: object) -> object:
    if key == "candidate_id":
        if not isinstance(value, str):
            raise ContractValidationError(
                "candidate_id must be an opaque safe reference"
            )
        return ensure_safe_ref(value, label="candidate_id")
    if key in _CANDIDATE_STRING_FIELDS:
        return _candidate_string(key, value)
    if key in _CANDIDATE_LIST_FIELDS:
        return _candidate_list(key, value)
    if key in _CANDIDATE_BOOL_FIELDS:
        return _candidate_bool(value)
    if key == "environment":
        return normalize_json_object(value)
    return None


def _candidate_string(key: str, value: object) -> str | None:
    normalized = normalize_optional_string(value)
    if normalized is not None:
        _validate_candidate_string(key, normalized)
    return normalized


def _candidate_bool(value: object) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError("issue candidate boolean field invalid")
    return value


def _validate_candidate_string(key: str, value: str) -> None:
    if key == "article_type":
        try:
            ArticleType(value)
        except ValueError as exc:
            raise ContractValidationError(
                "unsupported issue candidate article_type"
            ) from exc
    if key == "candidate_origin":
        try:
            CandidateOrigin(value)
        except ValueError as exc:
            raise ContractValidationError(
                "unsupported issue candidate origin"
            ) from exc


def _candidate_list(key: str, value: object) -> list[str]:
    values = normalize_string_list(value)
    if key == "source_refs":
        return [ensure_safe_ref(ref, label="candidate_source_ref") for ref in values]
    return values


def _top_level_or_single_candidate_list(
    data: Mapping[str, Any], key: str
) -> list[str]:
    values = normalize_string_list(data.get(key))
    if values or len(_raw_candidates(data)) != 1:
        return values
    return normalize_string_list(_raw_candidates(data)[0].get(key))


def _top_level_or_single_candidate_string(
    data: Mapping[str, Any], key: str
) -> str | None:
    value = normalize_optional_string(data.get(key))
    if value is not None or len(_raw_candidates(data)) != 1:
        return value
    candidate = _raw_candidates(data)[0]
    candidate_value = normalize_optional_string(candidate.get(key))
    if candidate_value is not None:
        return candidate_value
    if key == "supported_resolution_or_workaround":
        return normalize_optional_string(candidate.get("supported_answer"))
    return None


def _raw_candidates(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = data.get("issue_candidates")
    if not isinstance(candidates, list):
        return []
    return [candidate for candidate in candidates if isinstance(candidate, Mapping)]


def _visibility_summary(
    data: Mapping[str, Any], policy: EvidenceBuildPolicy
) -> JsonDict:
    summary = normalize_json_object(data.get("visibility_summary"), required=True)
    classes = _visibility_classes(summary)
    if EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value in classes:
        if not policy.allow_internal_reviewer_only:
            raise ContractValidationError("internal evidence requires explicit policy")
        summary["internal_only_evidence_approved"] = True
    return summary


def _visibility_classes(summary: Mapping[str, Any]) -> tuple[str, ...]:
    value = summary.get("classes", summary.get("visibility_classes"))
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple) and all(isinstance(item, str) for item in value):
        return tuple(value)
    visibility = summary.get("visibility")
    if isinstance(visibility, str):
        return (visibility,)
    return ()


def _sanitizer_report(
    data: Mapping[str, Any], policy: EvidenceBuildPolicy
) -> JsonDict:
    report = normalize_json_object(data.get("sanitizer_report"))
    if report:
        return report
    if policy.assume_sanitized:
        return {"status": "passed", "source": "kcs7_policy"}
    raise ContractValidationError("sanitizer report is required")


def _ensure_packet_safe(packet: NormalizedTicketEvidencePacket) -> None:
    result = validate_evidence_safety(packet)
    if not result.ok:
        raise EvidenceBuildSafetyError(
            f"evidence export failed safety gate: {', '.join(result.blockers)}"
        )
