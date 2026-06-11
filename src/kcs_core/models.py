"""Schema-versioned packet models for KCS-1 contract tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, require_json_object


class RecommendedAction(StrEnum):
    """Allowed KCS candidate actions."""

    REUSE_EXISTING = "reuse_existing"
    UPDATE_EXISTING = "update_existing"
    CREATE_CANDIDATE = "create_candidate"
    FLAG_EXISTING = "flag_existing"
    SPLIT_REQUIRED = "split_required"
    NO_ARTICLE = "no_article"
    BLOCKED = "blocked"


class ArticleType(StrEnum):
    """Allowed KCS article type values."""

    TECHNICAL_SCR = "technical_scr"
    HOWTO_QA = "howto_qa"
    NONE = "none"


def _require_schema_version(payload: Mapping[str, Any], expected: str) -> None:
    actual = payload.get("schema_version")
    if actual != expected:
        raise ContractValidationError(
            f"unsupported schema_version {actual!r}; expected {expected!r}"
        )


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{key} must be a non-empty string")
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be a string when present")
    return value


def _require_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ContractValidationError(f"{key} must be a boolean")
    return value


def _optional_bool(payload: Mapping[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise ContractValidationError(f"{key} must be a boolean")
    return value


def _require_number(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ContractValidationError(f"{key} must be a number")
    return float(value)


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ContractValidationError(f"{key} must be a list")
    return value


def _require_dict(payload: Mapping[str, Any], key: str) -> JsonDict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ContractValidationError(f"{key} must be an object")
    return dict(value)


def _optional_dict(payload: Mapping[str, Any], key: str) -> JsonDict | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ContractValidationError(f"{key} must be an object when present")
    return dict(value)


def _enum_value(enum_type: type[StrEnum], value: str, key: str) -> str:
    try:
        return enum_type(value).value
    except ValueError as exc:
        raise ContractValidationError(f"unknown {key}: {value!r}") from exc


@dataclass(frozen=True)
class NormalizedTicketEvidencePacket:
    """Normalized, sanitized source evidence packet."""

    SCHEMA_VERSION: ClassVar[str] = "normalized_ticket_evidence_packet_v1"

    case_ref: str
    input_class: str
    source_refs: list[str] = field(default_factory=list)
    issue_candidates: list[JsonDict] = field(default_factory=list)
    environment: JsonDict = field(default_factory=dict)
    symptoms: list[str] = field(default_factory=list)
    confirmed_facts: list[str] = field(default_factory=list)
    supported_cause: str | None = None
    supported_resolution_or_workaround: str | None = None
    open_questions: list[str] = field(default_factory=list)
    visibility_summary: JsonDict = field(default_factory=dict)
    sanitizer_report: JsonDict = field(default_factory=dict)

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any] | object) -> "NormalizedTicketEvidencePacket":
        data = require_json_object(payload)
        _require_schema_version(data, cls.SCHEMA_VERSION)
        return cls(
            case_ref=_require_string(data, "case_ref"),
            input_class=_require_string(data, "input_class"),
            source_refs=_string_list(data, "source_refs"),
            issue_candidates=_dict_list(data, "issue_candidates"),
            environment=_require_dict(data, "environment"),
            symptoms=_string_list(data, "symptoms"),
            confirmed_facts=_string_list(data, "confirmed_facts"),
            supported_cause=_optional_string(data, "supported_cause"),
            supported_resolution_or_workaround=_optional_string(
                data, "supported_resolution_or_workaround"
            ),
            open_questions=_string_list(data, "open_questions"),
            visibility_summary=_require_dict(data, "visibility_summary"),
            sanitizer_report=_require_dict(data, "sanitizer_report"),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "case_ref": self.case_ref,
            "input_class": self.input_class,
            "source_refs": list(self.source_refs),
            "issue_candidates": [dict(item) for item in self.issue_candidates],
            "environment": dict(self.environment),
            "symptoms": list(self.symptoms),
            "confirmed_facts": list(self.confirmed_facts),
            "supported_cause": self.supported_cause,
            "supported_resolution_or_workaround": self.supported_resolution_or_workaround,
            "open_questions": list(self.open_questions),
            "visibility_summary": dict(self.visibility_summary),
            "sanitizer_report": dict(self.sanitizer_report),
        }


@dataclass(frozen=True)
class ReuseSearchResultsPacket:
    """Structured search/reuse results packet."""

    SCHEMA_VERSION: ClassVar[str] = "reuse_search_results_packet_v1"

    search_run_ref: str
    searched: bool
    search_source: str
    matches: list[JsonDict] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any] | object) -> "ReuseSearchResultsPacket":
        data = require_json_object(payload)
        _require_schema_version(data, cls.SCHEMA_VERSION)
        return cls(
            search_run_ref=_require_string(data, "search_run_ref"),
            searched=_require_bool(data, "searched"),
            search_source=_require_string(data, "search_source"),
            matches=_dict_list(data, "matches"),
            blockers=_string_list(data, "blockers"),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "search_run_ref": self.search_run_ref,
            "searched": self.searched,
            "search_source": self.search_source,
            "matches": [dict(item) for item in self.matches],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class KcsActionDecisionPacket:
    """Deterministic KCS action decision packet shape."""

    SCHEMA_VERSION: ClassVar[str] = "kcs_action_decision_packet_v1"

    candidate_id: str
    recommended_action: str
    article_type: str
    confidence: float
    blockers: list[str] = field(default_factory=list)
    evidence_basis: JsonDict = field(default_factory=dict)
    selected_reuse_match: JsonDict | None = None
    auto_publish_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommended_action",
            _enum_value(RecommendedAction, self.recommended_action, "recommended_action"),
        )
        object.__setattr__(
            self,
            "article_type",
            _enum_value(ArticleType, self.article_type, "article_type"),
        )
        if self.auto_publish_allowed:
            raise ContractValidationError("auto_publish_allowed must be false for MVP packets")

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any] | object) -> "KcsActionDecisionPacket":
        data = require_json_object(payload)
        _require_schema_version(data, cls.SCHEMA_VERSION)
        return cls(
            candidate_id=_require_string(data, "candidate_id"),
            recommended_action=_require_string(data, "recommended_action"),
            article_type=_require_string(data, "article_type"),
            confidence=_require_number(data, "confidence"),
            blockers=_string_list(data, "blockers"),
            evidence_basis=_require_dict(data, "evidence_basis"),
            selected_reuse_match=_optional_dict(data, "selected_reuse_match"),
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "candidate_id": self.candidate_id,
            "recommended_action": self.recommended_action,
            "article_type": self.article_type,
            "confidence": self.confidence,
            "blockers": list(self.blockers),
            "evidence_basis": dict(self.evidence_basis),
            "selected_reuse_match": (
                dict(self.selected_reuse_match)
                if self.selected_reuse_match is not None
                else None
            ),
            "auto_publish_allowed": self.auto_publish_allowed,
        }


@dataclass(frozen=True)
class KcsReviewerPacket:
    """Reviewer-ready KCS packet shape."""

    SCHEMA_VERSION: ClassVar[str] = "kcs_reviewer_packet_v1"

    case_ref: str
    recommended_action: str
    review_required: bool
    public_article_candidate: JsonDict | None = None
    internal_reviewer_notes: list[str] = field(default_factory=list)
    evidence_basis: JsonDict = field(default_factory=dict)
    validation_report: JsonDict = field(default_factory=dict)
    zendesk_source_html: str | None = None
    auto_publish_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommended_action",
            _enum_value(RecommendedAction, self.recommended_action, "recommended_action"),
        )
        if self.auto_publish_allowed:
            raise ContractValidationError("auto_publish_allowed must be false for MVP packets")

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any] | object) -> "KcsReviewerPacket":
        data = require_json_object(payload)
        _require_schema_version(data, cls.SCHEMA_VERSION)
        return cls(
            case_ref=_require_string(data, "case_ref"),
            recommended_action=_require_string(data, "recommended_action"),
            review_required=_require_bool(data, "review_required"),
            public_article_candidate=_optional_dict(data, "public_article_candidate"),
            internal_reviewer_notes=_string_list(data, "internal_reviewer_notes"),
            evidence_basis=_require_dict(data, "evidence_basis"),
            validation_report=_require_dict(data, "validation_report"),
            zendesk_source_html=_optional_string(data, "zendesk_source_html"),
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "case_ref": self.case_ref,
            "recommended_action": self.recommended_action,
            "review_required": self.review_required,
            "public_article_candidate": (
                dict(self.public_article_candidate)
                if self.public_article_candidate is not None
                else None
            ),
            "internal_reviewer_notes": list(self.internal_reviewer_notes),
            "evidence_basis": dict(self.evidence_basis),
            "validation_report": dict(self.validation_report),
            "zendesk_source_html": self.zendesk_source_html,
            "auto_publish_allowed": self.auto_publish_allowed,
        }


def _string_list(payload: Mapping[str, Any], key: str) -> list[str]:
    values = _require_list(payload, key)
    if not all(isinstance(value, str) for value in values):
        raise ContractValidationError(f"{key} must contain only strings")
    return list(values)


def _dict_list(payload: Mapping[str, Any], key: str) -> list[JsonDict]:
    values = _require_list(payload, key)
    if not all(isinstance(value, dict) for value in values):
        raise ContractValidationError(f"{key} must contain only objects")
    return [dict(value) for value in values]


def ensure_json_payloads(packets: Sequence[Any]) -> list[JsonDict]:
    """Return JSON dicts for packet-like objects used by tests and fixtures."""

    return [packet.to_json_dict() for packet in packets]
