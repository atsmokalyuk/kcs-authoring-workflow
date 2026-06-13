"""Runtime-independent schema-versioned packet models for KCS core contracts."""

from __future__ import annotations

import re
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


class DecisionStatus(StrEnum):
    """Allowed KCS decision status values."""

    DECISION_READY = "decision_ready"
    SPLIT_REQUIRED = "split_required"
    BLOCKED = "blocked"


class OperatorOverrideMode(StrEnum):
    """Allowed future operator override mode values."""

    REVIEWER_ONLY_DRAFT = "reviewer_only_draft"


class OverrideStatus(StrEnum):
    """Allowed future operator override status values."""

    NOT_REQUESTED = "not_requested"


class ReadinessState(StrEnum):
    """Allowed KCS reviewer-readiness loop state values."""

    READY_FOR_REVIEWER = "ready_for_reviewer"
    BLOCKED = "blocked"
    DRAFT_REQUIRED = "draft_required"
    REVIEW_BLOCKED = "review_blocked"


class RequiredNextStep(StrEnum):
    """Allowed next-step values for KCS-5 readiness reports."""

    NONE = "none"
    FIX_EVIDENCE = "fix_evidence"
    RUN_REUSE_SEARCH = "run_reuse_search"
    RENDER_REVIEWER_PACKET = "render_reviewer_packet"
    FIX_REVIEWER_PACKET = "fix_reviewer_packet"
    REVIEW_SPLIT_ITEMS = "review_split_items"


_VALIDATION_REPORT_CODE_RE = re.compile(r"[a-z][a-z0-9_]*")
_VALIDATION_REPORT_HASH_RE = re.compile(r"[0-9a-f]{64}")
_VALIDATION_REPORT_METADATA_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_VALIDATION_REPORT_LICENSE_RE = re.compile(
    r"\b(?:plsk|ext)[-_]?\d{4,}(?:[-_]?\d+)*\b",
    re.I,
)
_VALIDATION_REPORT_TICKET_RE = re.compile(
    r"\b(?:ticket|zendesk|zd)[-_]?\d{4,}\b",
    re.I,
)
_MAX_VALIDATION_REPORT_CODE_LENGTH = 100
_VALIDATION_REPORT_UNSAFE_FRAGMENTS = frozenset(
    {
        "api_key",
        "internal_comment",
        "password",
        "private",
        "raw_internal",
        "raw_ticket",
        "secret",
        "token",
    }
)
_EVIDENCE_VALIDATION_KEYS = frozenset({"ok", "blockers", "warnings"})
_DECISION_SUMMARY_KEYS = frozenset(
    {
        "allowed_override_modes",
        "article_type",
        "auto_publish_allowed",
        "blockers",
        "candidate_id",
        "has_selected_reuse_match",
        "operator_override_allowed",
        "override_status",
        "recommended_action",
        "schema_version",
        "split_item_count",
        "status",
    }
)
_RENDERER_VALIDATION_KEYS = frozenset(
    {
        "blockers",
        "checks",
        "has_public_article_candidate",
        "has_zendesk_source_html",
        "renderer_status",
        "schema_version",
        "warnings",
    }
)
_RENDERER_VALIDATION_SCHEMA_VERSION = "kcs_renderer_validation_report_v1"
_RENDERER_STATUS_VALUES = frozenset(
    {
        "flag_existing_review_required",
        "no_public_article_output",
        "not_run",
        "split_required",
        "zendesk_html_generated",
        "zendesk_html_not_generated",
    }
)


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
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "NormalizedTicketEvidencePacket":
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
            "supported_resolution_or_workaround": (
                self.supported_resolution_or_workaround
            ),
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
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "ReuseSearchResultsPacket":
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
    split_items: list[JsonDict] = field(default_factory=list)
    auto_publish_allowed: bool = False
    status: str = DecisionStatus.DECISION_READY.value
    operator_override_allowed: bool = False
    allowed_override_modes: list[str] = field(default_factory=list)
    override_status: str = OverrideStatus.NOT_REQUESTED.value

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "recommended_action",
            _enum_value(
                RecommendedAction,
                self.recommended_action,
                "recommended_action",
            ),
        )
        object.__setattr__(
            self,
            "article_type",
            _enum_value(ArticleType, self.article_type, "article_type"),
        )
        object.__setattr__(
            self,
            "status",
            _enum_value(DecisionStatus, self.status, "status"),
        )
        object.__setattr__(
            self,
            "allowed_override_modes",
            [
                _enum_value(
                    OperatorOverrideMode,
                    mode,
                    "allowed_override_modes",
                )
                for mode in self.allowed_override_modes
            ],
        )
        object.__setattr__(
            self,
            "override_status",
            _enum_value(OverrideStatus, self.override_status, "override_status"),
        )
        if self.auto_publish_allowed:
            raise ContractValidationError(
                "auto_publish_allowed must be false for MVP packets"
            )

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsActionDecisionPacket":
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
            status=(
                _optional_string(data, "status")
                or DecisionStatus.DECISION_READY.value
            ),
            split_items=_optional_dict_list(data, "split_items"),
            operator_override_allowed=_optional_bool(
                data, "operator_override_allowed", False
            ),
            allowed_override_modes=_optional_string_list(
                data, "allowed_override_modes"
            ),
            override_status=(
                _optional_string(data, "override_status")
                or OverrideStatus.NOT_REQUESTED.value
            ),
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
            "status": self.status,
            "split_items": [dict(item) for item in self.split_items],
            "operator_override_allowed": self.operator_override_allowed,
            "allowed_override_modes": list(self.allowed_override_modes),
            "override_status": self.override_status,
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
            _enum_value(
                RecommendedAction,
                self.recommended_action,
                "recommended_action",
            ),
        )
        if self.auto_publish_allowed:
            raise ContractValidationError(
                "auto_publish_allowed must be false for MVP packets"
            )

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


@dataclass(frozen=True)
class KcsValidationReportPacket:
    """Validation report and ready-for-reviewer loop state packet."""

    SCHEMA_VERSION: ClassVar[str] = "kcs_validation_report_packet_v1"

    case_ref: str
    ok: bool
    ready_for_reviewer: bool
    state: str
    required_next_step: str
    checks: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence_validation: JsonDict = field(default_factory=dict)
    decision_summary: JsonDict = field(default_factory=dict)
    renderer_validation: JsonDict = field(default_factory=dict)
    reviewer_packet_sha256: str = ""
    zendesk_source_sha256: str = ""
    auto_publish_allowed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "state",
            _enum_value(ReadinessState, self.state, "state"),
        )
        object.__setattr__(
            self,
            "required_next_step",
            _enum_value(
                RequiredNextStep,
                self.required_next_step,
                "required_next_step",
            ),
        )
        if self.auto_publish_allowed:
            raise ContractValidationError(
                "auto_publish_allowed must be false for MVP packets"
            )
        ready_state = self.state == ReadinessState.READY_FOR_REVIEWER.value
        if self.ok != ready_state or self.ready_for_reviewer != ready_state:
            raise ContractValidationError(
                "readiness booleans must match readiness state"
            )
        _validate_validation_report_state(
            self.state,
            self.required_next_step,
            self.blockers,
        )
        for key in ("checks", "blockers", "warnings"):
            object.__setattr__(
                self,
                key,
                _validate_validation_report_codes(getattr(self, key), key),
            )
        object.__setattr__(
            self,
            "evidence_validation",
            _validate_evidence_validation_summary(self.evidence_validation),
        )
        object.__setattr__(
            self,
            "decision_summary",
            _validate_decision_summary(self.decision_summary),
        )
        object.__setattr__(
            self,
            "renderer_validation",
            _validate_renderer_validation_summary(self.renderer_validation),
        )
        object.__setattr__(
            self,
            "reviewer_packet_sha256",
            _validate_validation_report_hash(
                self.reviewer_packet_sha256,
                "reviewer_packet_sha256",
            ),
        )
        object.__setattr__(
            self,
            "zendesk_source_sha256",
            _validate_validation_report_hash(
                self.zendesk_source_sha256,
                "zendesk_source_sha256",
            ),
        )

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsValidationReportPacket":
        data = require_json_object(payload)
        _require_schema_version(data, cls.SCHEMA_VERSION)
        return cls(
            case_ref=_require_string(data, "case_ref"),
            ok=_require_bool(data, "ok"),
            ready_for_reviewer=_require_bool(data, "ready_for_reviewer"),
            state=_require_string(data, "state"),
            required_next_step=_require_string(data, "required_next_step"),
            checks=_string_list(data, "checks"),
            blockers=_string_list(data, "blockers"),
            warnings=_string_list(data, "warnings"),
            evidence_validation=_require_dict(data, "evidence_validation"),
            decision_summary=_require_dict(data, "decision_summary"),
            renderer_validation=_require_dict(data, "renderer_validation"),
            reviewer_packet_sha256=_optional_string(
                data, "reviewer_packet_sha256"
            )
            or "",
            zendesk_source_sha256=_optional_string(data, "zendesk_source_sha256")
            or "",
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "case_ref": self.case_ref,
            "ok": self.ok,
            "ready_for_reviewer": self.ready_for_reviewer,
            "state": self.state,
            "required_next_step": self.required_next_step,
            "checks": list(self.checks),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "evidence_validation": dict(self.evidence_validation),
            "decision_summary": dict(self.decision_summary),
            "renderer_validation": dict(self.renderer_validation),
            "reviewer_packet_sha256": self.reviewer_packet_sha256,
            "zendesk_source_sha256": self.zendesk_source_sha256,
            "auto_publish_allowed": self.auto_publish_allowed,
        }


def _string_list(payload: Mapping[str, Any], key: str) -> list[str]:
    values = _require_list(payload, key)
    if not all(isinstance(value, str) for value in values):
        raise ContractValidationError(f"{key} must contain only strings")
    return list(values)


def _validate_validation_report_state(
    state: str, required_next_step: str, blockers: list[str]
) -> None:
    if state == ReadinessState.READY_FOR_REVIEWER.value:
        if required_next_step != RequiredNextStep.NONE.value or blockers:
            raise ContractValidationError(
                "ready reports must have no next step and no blockers"
            )
        return
    if required_next_step == RequiredNextStep.NONE.value:
        raise ContractValidationError("not-ready reports must include a next step")
    if state in {
        ReadinessState.BLOCKED.value,
        ReadinessState.DRAFT_REQUIRED.value,
        ReadinessState.REVIEW_BLOCKED.value,
    } and not blockers:
        raise ContractValidationError("not-ready reports must include blockers")


def _validate_validation_report_codes(values: object, key: str) -> list[str]:
    if not isinstance(values, list) or not all(
        isinstance(value, str) for value in values
    ):
        raise ContractValidationError(f"{key} must contain only report code strings")
    for value in values:
        if (
            not value
            or len(value) > _MAX_VALIDATION_REPORT_CODE_LENGTH
            or not _VALIDATION_REPORT_CODE_RE.fullmatch(value)
            or _contains_unsafe_validation_report_metadata(value)
        ):
            raise ContractValidationError(f"{key} contains unsafe report code")
    return list(values)


def _validate_evidence_validation_summary(value: object) -> JsonDict:
    data = _validate_validation_report_object(
        value,
        "evidence_validation",
        _EVIDENCE_VALIDATION_KEYS,
    )
    if "ok" in data:
        _require_report_bool(data["ok"], "evidence_validation.ok")
    for key in ("blockers", "warnings"):
        if key in data:
            data[key] = _validate_validation_report_codes(
                data[key],
                f"evidence_validation.{key}",
            )
    return data


def _validate_decision_summary(value: object) -> JsonDict:
    data = _validate_validation_report_object(
        value,
        "decision_summary",
        _DECISION_SUMMARY_KEYS,
    )
    _validate_decision_summary_schema(data)
    _validate_decision_summary_enums(data)
    _validate_decision_summary_lists(data)
    _validate_decision_summary_scalars(data)
    return data


def _validate_decision_summary_schema(data: JsonDict) -> None:
    if "schema_version" in data:
        _require_report_exact_string(
            data["schema_version"],
            KcsActionDecisionPacket.SCHEMA_VERSION,
            "decision_summary.schema_version",
        )
    if "candidate_id" in data:
        _validate_report_metadata_or_empty(
            data["candidate_id"],
            "decision_summary.candidate_id",
        )


def _validate_decision_summary_enums(data: JsonDict) -> None:
    enum_fields: tuple[tuple[str, type[StrEnum]], ...] = (
        ("recommended_action", RecommendedAction),
        ("article_type", ArticleType),
        ("status", DecisionStatus),
        ("override_status", OverrideStatus),
    )
    for key, enum_type in enum_fields:
        if key in data:
            _require_report_enum(data[key], enum_type, f"decision_summary.{key}")


def _validate_decision_summary_lists(data: JsonDict) -> None:
    if "blockers" in data:
        data["blockers"] = _validate_validation_report_codes(
            data["blockers"],
            "decision_summary.blockers",
        )
    if "allowed_override_modes" in data:
        data["allowed_override_modes"] = _validate_report_enum_list(
            data["allowed_override_modes"],
            OperatorOverrideMode,
            "decision_summary.allowed_override_modes",
        )


def _validate_decision_summary_scalars(data: JsonDict) -> None:
    if "split_item_count" in data:
        _require_report_non_negative_int(
            data["split_item_count"],
            "decision_summary.split_item_count",
        )
    for key in (
        "has_selected_reuse_match",
        "operator_override_allowed",
    ):
        if key in data:
            _require_report_bool(data[key], f"decision_summary.{key}")
    if "auto_publish_allowed" in data and data["auto_publish_allowed"] is not False:
        raise ContractValidationError(
            "decision_summary.auto_publish_allowed must be false"
        )


def _validate_renderer_validation_summary(value: object) -> JsonDict:
    data = _validate_validation_report_object(
        value,
        "renderer_validation",
        _RENDERER_VALIDATION_KEYS,
    )
    if "schema_version" in data:
        _require_report_exact_string(
            data["schema_version"],
            _RENDERER_VALIDATION_SCHEMA_VERSION,
            "renderer_validation.schema_version",
        )
    if "renderer_status" in data:
        _require_report_renderer_status(
            data["renderer_status"],
            "renderer_validation.renderer_status",
        )
    for key in ("checks", "blockers", "warnings"):
        if key in data:
            data[key] = _validate_validation_report_codes(
                data[key],
                f"renderer_validation.{key}",
            )
    for key in ("has_public_article_candidate", "has_zendesk_source_html"):
        if key in data:
            _require_report_bool(data[key], f"renderer_validation.{key}")
    return data


def _validate_validation_report_object(
    value: object, key: str, allowed_keys: frozenset[str]
) -> JsonDict:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{key} must be an object")
    if not set(value) <= allowed_keys:
        raise ContractValidationError(f"{key} contains unsupported field")
    return dict(value)


def _require_report_bool(value: object, key: str) -> None:
    if type(value) is not bool:
        raise ContractValidationError(f"{key} must be a boolean")


def _require_report_non_negative_int(value: object, key: str) -> None:
    if type(value) is not int or value < 0:
        raise ContractValidationError(f"{key} must be a non-negative integer")


def _require_report_exact_string(value: object, expected: str, key: str) -> None:
    if value != expected:
        raise ContractValidationError(f"{key} has unsupported value")


def _require_report_enum(value: object, enum_type: type[StrEnum], key: str) -> None:
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be a string")
    _enum_value(enum_type, value, key)


def _validate_report_enum_list(
    value: object,
    enum_type: type[StrEnum],
    key: str,
) -> list[str]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{key} must be a list")
    return [_enum_value(enum_type, item, key) for item in value]


def _require_report_renderer_status(value: object, key: str) -> None:
    if not isinstance(value, str) or (
        value != "" and value not in _RENDERER_STATUS_VALUES
    ):
        raise ContractValidationError(f"{key} has unsupported value")


def _validate_report_metadata_or_empty(value: object, key: str) -> None:
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be a string")
    if (
        value
        and (
            len(value) > _MAX_VALIDATION_REPORT_CODE_LENGTH
            or not _VALIDATION_REPORT_METADATA_RE.fullmatch(value)
            or _contains_unsafe_validation_report_metadata(value)
        )
    ):
        raise ContractValidationError(f"{key} contains unsafe report value")


def _validate_validation_report_metadata_string(value: str, key: str) -> None:
    if (
        value
        and (
            len(value) > _MAX_VALIDATION_REPORT_CODE_LENGTH
            or not _VALIDATION_REPORT_METADATA_RE.fullmatch(value)
            or _contains_unsafe_validation_report_metadata(value)
        )
    ):
        raise ContractValidationError(f"{key} contains unsafe report value")


def _contains_unsafe_validation_report_metadata(value: str) -> bool:
    normalized = value.casefold().replace("-", "_")
    if any(fragment in normalized for fragment in _VALIDATION_REPORT_UNSAFE_FRAGMENTS):
        return True
    return bool(
        _VALIDATION_REPORT_LICENSE_RE.search(value)
        or _VALIDATION_REPORT_TICKET_RE.search(value)
    )


def _validate_validation_report_hash(value: object, key: str) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be a string")
    if value and not _VALIDATION_REPORT_HASH_RE.fullmatch(value):
        raise ContractValidationError(f"{key} must be empty or a sha256 hex digest")
    return value


def _dict_list(payload: Mapping[str, Any], key: str) -> list[JsonDict]:
    values = _require_list(payload, key)
    if not all(isinstance(value, dict) for value in values):
        raise ContractValidationError(f"{key} must contain only objects")
    return [dict(value) for value in values]


def _optional_dict_list(payload: Mapping[str, Any], key: str) -> list[JsonDict]:
    if key not in payload:
        return []
    return _dict_list(payload, key)


def _optional_string_list(payload: Mapping[str, Any], key: str) -> list[str]:
    if key not in payload:
        return []
    return _string_list(payload, key)


def ensure_json_payloads(packets: Sequence[Any]) -> list[JsonDict]:
    """Return JSON dicts for packet-like objects used by tests and fixtures."""

    return [packet.to_json_dict() for packet in packets]
