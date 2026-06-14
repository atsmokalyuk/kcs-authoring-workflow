"""Bounded Claude/provider handoff contracts for KCS-9b."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any, Protocol

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, dumps_payload, require_json_object
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsValidationReportPacket,
    OperatorOverrideMode,
    OverrideStatus,
    ReadinessState,
    RecommendedAction,
)
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
    normalize_optional_string,
)

CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION = "kcs_claude_handoff_request_v1"
CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION = "kcs_claude_handoff_response_v1"
HANDOFF_PURPOSE_REVIEWER_ASSIST_NOTES = "reviewer_assist_notes"

_MAX_TITLE_HINT_LENGTH = 160
_MAX_PUBLIC_SUMMARY_LENGTH = 1200
_MAX_REVIEWER_ASSIST_NOTE_LENGTH = 600
_MAX_REVIEWER_ASSIST_NOTES = 10
_MAX_CODE_LIST_LENGTH = 50
_MAX_REQUEST_BYTES = 32 * 1024
_MAX_RESPONSE_BYTES = 16 * 1024
_MAX_CODE_LENGTH = 80
_SAFE_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,79}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_HTML_TAG_RE = re.compile(r"<\s*/?\s*[a-z][a-z0-9:-]*(?:\s[^>]*)?>", re.I)
_DRAFT_SECTION_RE = re.compile(
    r"\b(?:symptoms|cause|resolution|question|answer)\s*:",
    re.I,
)
_CUSTOMER_REPLY_RE = re.compile(r"\b(?:customer reply|reply to customer)\s*:", re.I)
_ACTION_TOKEN_RE = re.compile(
    r"\b(?:reuse_existing|update_existing|create_candidate|flag_existing|"
    r"split_required|no_article|blocked)\b",
    re.I,
)
_FORBIDDEN_TEXT_LABEL_RE = re.compile(
    r"\b(?:zendesk_source_html|public_article_candidate|reviewer_packet|"
    r"evidence_basis|raw_ticket|raw_comments?|internal_comments?|"
    r"draft_body|article_body|customer_reply)\b",
    re.I,
)
_UNSAFE_CODE_FRAGMENTS = frozenset(
    {
        "api_key",
        "article_body",
        "attachment_url",
        "credential",
        "customer_reply",
        "draft_body",
        "evidence_basis",
        "internal_comment",
        "password",
        "private",
        "public_article_candidate",
        "raw_comment",
        "raw_comments",
        "raw_internal",
        "raw_ticket",
        "reviewer_packet",
        "secret",
        "token",
        "zendesk_source_html",
    }
)
_ACTION_FIELD_NAMES = frozenset(
    {
        "action_decision",
        "decision",
        "kcs_action",
        "proposed_action",
        "recommended_action",
        "should_create",
        "should_flag",
        "should_update",
    }
)
_ACTION_VALUES = frozenset(action.value for action in RecommendedAction)
_ACTION_CONTEXT_CODE_ALIASES = {
    RecommendedAction.BLOCKED.value: "pipeline_blocked_context",
    RecommendedAction.CREATE_CANDIDATE.value: "new_article_candidate_context",
    RecommendedAction.FLAG_EXISTING.value: "existing_article_flag_context",
    RecommendedAction.NO_ARTICLE.value: "article_not_applicable_context",
    RecommendedAction.REUSE_EXISTING.value: "existing_article_reuse_context",
    RecommendedAction.SPLIT_REQUIRED.value: "split_review_required",
    RecommendedAction.UPDATE_EXISTING.value: "existing_article_update_context",
}
_REQUEST_FIELDS = frozenset(
    {
        "artifact_refs",
        "auto_publish_allowed",
        "case_ref",
        "decision_summary_sha256",
        "handoff_purpose",
        "handoff_ref",
        "include_full_reviewer_packet_body",
        "include_full_zendesk_html",
        "item_ref",
        "operator_override",
        "original_article_type",
        "original_decision_status",
        "original_readiness_state",
        "original_recommended_action",
        "provider_may_decide_action",
        "provider_may_generate_draft_body",
        "provider_profile",
        "public_output_approved",
        "readiness_summary_sha256",
        "safe_context",
        "schema_version",
    }
)
_SAFE_CONTEXT_FIELDS = frozenset(
    {
        "article_type",
        "blocker_codes",
        "reason_codes",
        "reviewer_only_reason_codes",
        "short_public_safe_summary",
        "status_codes",
        "title_hint",
        "warning_codes",
    }
)
_ARTIFACT_REF_FIELDS = frozenset(
    {
        "reviewer_packet_ref",
        "reviewer_packet_sha256",
        "zendesk_source_ref",
        "zendesk_source_sha256",
    }
)
_OPERATOR_OVERRIDE_FIELDS = frozenset(
    {
        "allowed_override_modes",
        "operator_override_allowed",
        "override_status",
    }
)
_RESPONSE_FIELDS = frozenset(
    {
        "auto_publish_allowed",
        "contains_article_draft",
        "handoff_ref",
        "original_article_type",
        "original_decision_status",
        "original_readiness_state",
        "original_recommended_action",
        "provider_error_code",
        "provider_status",
        "public_output_approved",
        "reviewer_assist_notes",
        "schema_version",
        "structured_comments",
    }
)
_STRUCTURED_COMMENTS_FIELDS = frozenset(
    {
        "comment_codes",
        "needs_reviewer_attention",
    }
)


class ClaudeHandoffProviderProfile(StrEnum):
    """Allowed KCS-9b provider profile markers."""

    FAKE_PROVIDER = "fake_provider"
    APPROVED_PROVIDER = "approved_provider"


class ClaudeHandoffProviderStatus(StrEnum):
    """Allowed KCS-9b provider response statuses."""

    ACCEPTED = "accepted"
    FAILED = "failed"
    REJECTED = "rejected"


class ClaudeHandoffProviderErrorCode(StrEnum):
    """Allowed KCS-9b provider error codes."""

    NONE = "none"
    PROVIDER_FAILED = "provider_failed"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_REJECTED_CONTEXT = "provider_rejected_context"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    UNSAFE_CONTEXT_BLOCKED = "unsafe_context_blocked"


class ClaudeHandoffProvider(Protocol):
    """Provider boundary for bounded reviewer-assist handoff."""

    def submit_handoff(
        self, request: "KcsClaudeHandoffRequestPacket"
    ) -> "KcsClaudeHandoffResponsePacket | Mapping[str, Any]":
        """Return untrusted reviewer-assist handoff output."""


@dataclass(frozen=True)
class KcsClaudeHandoffRequestPacket:
    """Compact bounded request for KCS-9b reviewer-assist handoff."""

    handoff_ref: str
    case_ref: str
    item_ref: str
    original_recommended_action: str
    original_article_type: str
    original_decision_status: str
    original_readiness_state: str
    provider_profile: str = ClaudeHandoffProviderProfile.FAKE_PROVIDER.value
    handoff_purpose: str = HANDOFF_PURPOSE_REVIEWER_ASSIST_NOTES
    decision_summary_sha256: str = ""
    readiness_summary_sha256: str = ""
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    provider_may_decide_action: bool = False
    provider_may_generate_draft_body: bool = False
    include_full_reviewer_packet_body: bool = False
    include_full_zendesk_html: bool = False
    safe_context: JsonDict = field(default_factory=lambda: _default_safe_context())
    operator_override: JsonDict = field(
        default_factory=lambda: _default_operator_override()
    )
    artifact_refs: JsonDict = field(default_factory=lambda: _default_artifact_refs())
    schema_version: str = CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude handoff schema_version")
        object.__setattr__(
            self,
            "handoff_ref",
            ensure_safe_ref(self.handoff_ref, label="handoff_ref"),
        )
        object.__setattr__(
            self, "case_ref", ensure_safe_ref(self.case_ref, label="case_ref")
        )
        object.__setattr__(
            self, "item_ref", ensure_safe_ref(self.item_ref, label="item_ref")
        )
        _require_exact_string(
            self.handoff_purpose,
            HANDOFF_PURPOSE_REVIEWER_ASSIST_NOTES,
            "handoff_purpose",
        )
        object.__setattr__(
            self,
            "provider_profile",
            _enum_value(
                self.provider_profile,
                ClaudeHandoffProviderProfile,
                "provider_profile",
            ),
        )
        object.__setattr__(
            self,
            "original_recommended_action",
            _enum_value(
                self.original_recommended_action,
                RecommendedAction,
                "original_recommended_action",
            ),
        )
        object.__setattr__(
            self,
            "original_article_type",
            _enum_value(
                self.original_article_type,
                ArticleType,
                "original_article_type",
            ),
        )
        object.__setattr__(
            self,
            "original_decision_status",
            _enum_value(
                self.original_decision_status,
                DecisionStatus,
                "original_decision_status",
            ),
        )
        object.__setattr__(
            self,
            "original_readiness_state",
            _enum_value(
                self.original_readiness_state,
                ReadinessState,
                "original_readiness_state",
            ),
        )
        for key in (
            "auto_publish_allowed",
            "public_output_approved",
            "provider_may_decide_action",
            "provider_may_generate_draft_body",
            "include_full_reviewer_packet_body",
            "include_full_zendesk_html",
        ):
            _require_false(getattr(self, key), key)
        object.__setattr__(
            self,
            "decision_summary_sha256",
            _validate_hash_or_empty(
                self.decision_summary_sha256,
                "decision_summary_sha256",
            ),
        )
        object.__setattr__(
            self,
            "readiness_summary_sha256",
            _validate_hash_or_empty(
                self.readiness_summary_sha256,
                "readiness_summary_sha256",
            ),
        )
        object.__setattr__(
            self, "safe_context", _validate_safe_context(self.safe_context)
        )
        if self.safe_context["article_type"] != self.original_article_type:
            raise ContractValidationError("claude handoff article type mismatch")
        object.__setattr__(
            self,
            "operator_override",
            _validate_operator_override(self.operator_override),
        )
        object.__setattr__(
            self, "artifact_refs", _validate_artifact_refs(self.artifact_refs)
        )
        _ensure_serialized_size(self.to_json_dict(), _MAX_REQUEST_BYTES, "request")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsClaudeHandoffRequestPacket":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _REQUEST_FIELDS, label="claude handoff request")
        _ensure_no_provider_owned_action(data)
        if data.get("schema_version") != CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude handoff schema_version")
        return cls(
            handoff_ref=_required_string(data, "handoff_ref"),
            case_ref=_required_string(data, "case_ref"),
            item_ref=_required_string(data, "item_ref"),
            original_recommended_action=_required_string(
                data, "original_recommended_action"
            ),
            original_article_type=_required_string(data, "original_article_type"),
            original_decision_status=_required_string(
                data, "original_decision_status"
            ),
            original_readiness_state=_required_string(
                data, "original_readiness_state"
            ),
            provider_profile=_required_string(data, "provider_profile"),
            handoff_purpose=_required_string(data, "handoff_purpose"),
            decision_summary_sha256=_optional_string(
                data, "decision_summary_sha256"
            )
            or "",
            readiness_summary_sha256=_optional_string(
                data, "readiness_summary_sha256"
            )
            or "",
            auto_publish_allowed=_optional_bool(
                data, "auto_publish_allowed", False
            ),
            public_output_approved=_optional_bool(
                data, "public_output_approved", False
            ),
            provider_may_decide_action=_optional_bool(
                data, "provider_may_decide_action", False
            ),
            provider_may_generate_draft_body=_optional_bool(
                data, "provider_may_generate_draft_body", False
            ),
            include_full_reviewer_packet_body=_optional_bool(
                data, "include_full_reviewer_packet_body", False
            ),
            include_full_zendesk_html=_optional_bool(
                data, "include_full_zendesk_html", False
            ),
            safe_context=_required_dict(data, "safe_context"),
            operator_override=_required_dict(data, "operator_override"),
            artifact_refs=_required_dict(data, "artifact_refs"),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "artifact_refs": dict(self.artifact_refs),
            "auto_publish_allowed": self.auto_publish_allowed,
            "case_ref": self.case_ref,
            "decision_summary_sha256": self.decision_summary_sha256,
            "handoff_purpose": self.handoff_purpose,
            "handoff_ref": self.handoff_ref,
            "include_full_reviewer_packet_body": (
                self.include_full_reviewer_packet_body
            ),
            "include_full_zendesk_html": self.include_full_zendesk_html,
            "item_ref": self.item_ref,
            "operator_override": dict(self.operator_override),
            "original_article_type": self.original_article_type,
            "original_decision_status": self.original_decision_status,
            "original_readiness_state": self.original_readiness_state,
            "original_recommended_action": self.original_recommended_action,
            "provider_may_decide_action": self.provider_may_decide_action,
            "provider_may_generate_draft_body": (
                self.provider_may_generate_draft_body
            ),
            "provider_profile": self.provider_profile,
            "public_output_approved": self.public_output_approved,
            "readiness_summary_sha256": self.readiness_summary_sha256,
            "safe_context": dict(self.safe_context),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class KcsClaudeHandoffResponsePacket:
    """Validated KCS-9b provider response with reviewer-assist notes only."""

    handoff_ref: str
    provider_status: str
    provider_error_code: str
    reviewer_assist_notes: tuple[str, ...] = ()
    structured_comments: JsonDict = field(
        default_factory=lambda: _default_structured_comments()
    )
    original_recommended_action: str | None = None
    original_article_type: str | None = None
    original_decision_status: str | None = None
    original_readiness_state: str | None = None
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    contains_article_draft: bool = False
    schema_version: str = CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported claude handoff response schema_version"
            )
        object.__setattr__(
            self,
            "handoff_ref",
            ensure_safe_ref(self.handoff_ref, label="handoff_ref"),
        )
        object.__setattr__(
            self,
            "provider_status",
            _enum_value(
                self.provider_status,
                ClaudeHandoffProviderStatus,
                "provider_status",
            ),
        )
        object.__setattr__(
            self,
            "provider_error_code",
            _enum_value(
                self.provider_error_code,
                ClaudeHandoffProviderErrorCode,
                "provider_error_code",
            ),
        )
        _validate_provider_status_pair(
            self.provider_status,
            self.provider_error_code,
        )
        object.__setattr__(
            self,
            "reviewer_assist_notes",
            _validate_reviewer_assist_notes(self.reviewer_assist_notes),
        )
        object.__setattr__(
            self,
            "structured_comments",
            _validate_structured_comments(self.structured_comments),
        )
        object.__setattr__(
            self,
            "original_recommended_action",
            _optional_enum_value(
                self.original_recommended_action,
                RecommendedAction,
                "original_recommended_action",
            ),
        )
        object.__setattr__(
            self,
            "original_article_type",
            _optional_enum_value(
                self.original_article_type,
                ArticleType,
                "original_article_type",
            ),
        )
        object.__setattr__(
            self,
            "original_decision_status",
            _optional_enum_value(
                self.original_decision_status,
                DecisionStatus,
                "original_decision_status",
            ),
        )
        object.__setattr__(
            self,
            "original_readiness_state",
            _optional_enum_value(
                self.original_readiness_state,
                ReadinessState,
                "original_readiness_state",
            ),
        )
        for key in (
            "auto_publish_allowed",
            "public_output_approved",
            "contains_article_draft",
        ):
            _require_false(getattr(self, key), key)
        _validate_response_status_payload(
            self.provider_status,
            self.reviewer_assist_notes,
            self.structured_comments,
        )
        _ensure_no_provider_owned_action(self.to_json_dict())
        _ensure_serialized_size(self.to_json_dict(), _MAX_RESPONSE_BYTES, "response")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsClaudeHandoffResponsePacket":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _RESPONSE_FIELDS, label="claude handoff response")
        _ensure_no_provider_owned_action(data)
        if data.get("schema_version") != CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported claude handoff response schema_version"
            )
        return cls(
            handoff_ref=_required_string(data, "handoff_ref"),
            provider_status=_required_string(data, "provider_status"),
            provider_error_code=_required_string(data, "provider_error_code"),
            reviewer_assist_notes=tuple(
                _optional_string_list(data, "reviewer_assist_notes")
            ),
            structured_comments=_required_dict(data, "structured_comments"),
            original_recommended_action=_optional_string(
                data, "original_recommended_action"
            ),
            original_article_type=_optional_string(data, "original_article_type"),
            original_decision_status=_optional_string(
                data, "original_decision_status"
            ),
            original_readiness_state=_optional_string(
                data, "original_readiness_state"
            ),
            auto_publish_allowed=_optional_bool(
                data, "auto_publish_allowed", False
            ),
            public_output_approved=_optional_bool(
                data, "public_output_approved", False
            ),
            contains_article_draft=_optional_bool(
                data, "contains_article_draft", False
            ),
        )

    def to_json_dict(self) -> JsonDict:
        payload: JsonDict = {
            "auto_publish_allowed": self.auto_publish_allowed,
            "contains_article_draft": self.contains_article_draft,
            "handoff_ref": self.handoff_ref,
            "provider_error_code": self.provider_error_code,
            "provider_status": self.provider_status,
            "public_output_approved": self.public_output_approved,
            "reviewer_assist_notes": list(self.reviewer_assist_notes),
            "schema_version": self.schema_version,
            "structured_comments": dict(self.structured_comments),
        }
        for key in (
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
        ):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value
        return payload


def build_claude_handoff_request(
    decision: KcsActionDecisionPacket,
    validation_report: KcsValidationReportPacket,
    *,
    handoff_ref: str,
    item_ref: str | None = None,
    provider_profile: str = ClaudeHandoffProviderProfile.FAKE_PROVIDER.value,
    safe_context: Mapping[str, Any] | None = None,
    artifact_refs: Mapping[str, Any] | None = None,
) -> KcsClaudeHandoffRequestPacket:
    """Build a bounded KCS-9b handoff request from deterministic KCS outputs."""

    base_context = _safe_context_from_packets(decision, validation_report)
    if safe_context is not None:
        base_context.update(dict(safe_context))
    return KcsClaudeHandoffRequestPacket(
        handoff_ref=handoff_ref,
        case_ref=validation_report.case_ref,
        item_ref=item_ref or decision.candidate_id,
        original_recommended_action=decision.recommended_action,
        original_article_type=decision.article_type,
        original_decision_status=decision.status,
        original_readiness_state=validation_report.state,
        provider_profile=provider_profile,
        decision_summary_sha256=_sha256_payload(decision),
        readiness_summary_sha256=_sha256_payload(validation_report),
        safe_context=base_context,
        operator_override={
            "allowed_override_modes": list(decision.allowed_override_modes),
            "operator_override_allowed": decision.operator_override_allowed,
            "override_status": decision.override_status,
        },
        artifact_refs=(
            dict(artifact_refs)
            if artifact_refs is not None
            else _default_artifact_refs()
        ),
    )


def validate_claude_handoff_response(
    payload: KcsClaudeHandoffResponsePacket | Mapping[str, Any] | object,
    *,
    request: KcsClaudeHandoffRequestPacket,
) -> KcsClaudeHandoffResponsePacket:
    """Validate an untrusted KCS-9b provider response against its request."""

    response = (
        payload
        if isinstance(payload, KcsClaudeHandoffResponsePacket)
        else KcsClaudeHandoffResponsePacket.from_json_dict(payload)
    )
    _validate_response_matches_request(response, request)
    return response


def submit_claude_handoff(
    request: KcsClaudeHandoffRequestPacket,
    *,
    provider: ClaudeHandoffProvider,
) -> KcsClaudeHandoffResponsePacket:
    """Submit a bounded handoff to a provider and return a value-safe response."""

    provider_failed = False
    raw_response: KcsClaudeHandoffResponsePacket | Mapping[str, Any] | None = None
    try:
        raw_response = provider.submit_handoff(request)
    except Exception:
        provider_failed = True
    if provider_failed or raw_response is None:
        return _safe_failed_response(
            request,
            ClaudeHandoffProviderErrorCode.PROVIDER_FAILED.value,
        )
    try:
        return validate_claude_handoff_response(raw_response, request=request)
    except ContractValidationError:
        return _safe_failed_response(
            request,
            ClaudeHandoffProviderErrorCode.PROVIDER_RESPONSE_INVALID.value,
        )


def _safe_context_from_packets(
    decision: KcsActionDecisionPacket,
    validation_report: KcsValidationReportPacket,
) -> JsonDict:
    return {
        "article_type": decision.article_type,
        "blocker_codes": _handoff_context_codes(
            [*decision.blockers, *validation_report.blockers]
        ),
        "reason_codes": [],
        "reviewer_only_reason_codes": [],
        "short_public_safe_summary": "",
        "status_codes": _dedupe_codes(
            [
                f"decision_status_{decision.status}",
                f"readiness_state_{validation_report.state}",
            ]
        ),
        "title_hint": "",
        "warning_codes": _handoff_context_codes(validation_report.warnings),
    }


def _safe_failed_response(
    request: KcsClaudeHandoffRequestPacket,
    provider_error_code: str,
) -> KcsClaudeHandoffResponsePacket:
    return KcsClaudeHandoffResponsePacket(
        handoff_ref=request.handoff_ref,
        provider_status=ClaudeHandoffProviderStatus.FAILED.value,
        provider_error_code=provider_error_code,
        structured_comments=_default_structured_comments(),
        original_recommended_action=request.original_recommended_action,
        original_article_type=request.original_article_type,
        original_decision_status=request.original_decision_status,
        original_readiness_state=request.original_readiness_state,
    )


def _validate_response_matches_request(
    response: KcsClaudeHandoffResponsePacket,
    request: KcsClaudeHandoffRequestPacket,
) -> None:
    if response.handoff_ref != request.handoff_ref:
        raise ContractValidationError("claude handoff response mismatch")
    comparisons = (
        ("original_recommended_action", request.original_recommended_action),
        ("original_article_type", request.original_article_type),
        ("original_decision_status", request.original_decision_status),
        ("original_readiness_state", request.original_readiness_state),
    )
    for key, expected in comparisons:
        actual = getattr(response, key)
        if actual is not None and actual != expected:
            raise ContractValidationError("claude handoff response mismatch")


def _validate_safe_context(value: object) -> JsonDict:
    data = _safe_object(value, _SAFE_CONTEXT_FIELDS, "claude handoff safe_context")
    context = {
        "article_type": _enum_value(
            data.get("article_type", ArticleType.NONE.value),
            ArticleType,
            "safe_context.article_type",
        ),
        "blocker_codes": _safe_code_list(data.get("blocker_codes", [])),
        "reason_codes": _safe_code_list(data.get("reason_codes", [])),
        "reviewer_only_reason_codes": _safe_code_list(
            data.get("reviewer_only_reason_codes", [])
        ),
        "short_public_safe_summary": _safe_text(
            data.get("short_public_safe_summary", ""),
            "safe_context.short_public_safe_summary",
            _MAX_PUBLIC_SUMMARY_LENGTH,
            required=False,
        ),
        "status_codes": _safe_code_list(data.get("status_codes", [])),
        "title_hint": _safe_text(
            data.get("title_hint", ""),
            "safe_context.title_hint",
            _MAX_TITLE_HINT_LENGTH,
            required=False,
        ),
        "warning_codes": _safe_code_list(data.get("warning_codes", [])),
    }
    _ensure_no_provider_owned_action(context)
    return context


def _validate_operator_override(value: object) -> JsonDict:
    data = _safe_object(
        value,
        _OPERATOR_OVERRIDE_FIELDS,
        "claude handoff operator_override",
    )
    operator_override_allowed = data.get("operator_override_allowed", False)
    if not isinstance(operator_override_allowed, bool):
        raise ContractValidationError("claude handoff operator override invalid")
    override_status = _enum_value(
        data.get("override_status", OverrideStatus.NOT_REQUESTED.value),
        OverrideStatus,
        "operator_override.override_status",
    )
    allowed_modes = _enum_list(
        data.get("allowed_override_modes", []),
        OperatorOverrideMode,
        "operator_override.allowed_override_modes",
    )
    return {
        "allowed_override_modes": allowed_modes,
        "operator_override_allowed": operator_override_allowed,
        "override_status": override_status,
    }


def _validate_artifact_refs(value: object) -> JsonDict:
    data = _safe_object(value, _ARTIFACT_REF_FIELDS, "claude handoff artifact_refs")
    return {
        "reviewer_packet_ref": _safe_ref_or_empty(
            data.get("reviewer_packet_ref", ""),
            "artifact_refs.reviewer_packet_ref",
        ),
        "reviewer_packet_sha256": _validate_hash_or_empty(
            data.get("reviewer_packet_sha256", ""),
            "artifact_refs.reviewer_packet_sha256",
        ),
        "zendesk_source_ref": _safe_ref_or_empty(
            data.get("zendesk_source_ref", ""),
            "artifact_refs.zendesk_source_ref",
        ),
        "zendesk_source_sha256": _validate_hash_or_empty(
            data.get("zendesk_source_sha256", ""),
            "artifact_refs.zendesk_source_sha256",
        ),
    }


def _validate_structured_comments(value: object) -> JsonDict:
    data = _safe_object(
        value,
        _STRUCTURED_COMMENTS_FIELDS,
        "claude handoff structured_comments",
    )
    needs_reviewer_attention = data.get("needs_reviewer_attention", False)
    if not isinstance(needs_reviewer_attention, bool):
        raise ContractValidationError("claude handoff structured comments invalid")
    comment_codes = _safe_code_list(data.get("comment_codes", []))
    return {
        "comment_codes": comment_codes,
        "needs_reviewer_attention": needs_reviewer_attention,
    }


def _validate_reviewer_assist_notes(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple | list):
        raise ContractValidationError("claude handoff reviewer notes invalid")
    if len(value) > _MAX_REVIEWER_ASSIST_NOTES:
        raise ContractValidationError("claude handoff reviewer notes invalid")
    notes: list[str] = []
    for item in value:
        notes.append(
            _safe_text(
                item,
                "reviewer_assist_notes",
                _MAX_REVIEWER_ASSIST_NOTE_LENGTH,
                required=True,
            )
        )
    _ensure_no_provider_owned_action(notes)
    return tuple(notes)


def _safe_object(
    value: object,
    allowed_keys: frozenset[str],
    label: str,
) -> JsonDict:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{label} invalid")
    ensure_safe_sanitized_payload(value)
    ensure_allowed_keys(value, allowed_keys, label=label)
    _ensure_no_provider_owned_action(value)
    return dict(value)


def _safe_text(
    value: object,
    label: str,
    max_length: int,
    *,
    required: bool,
) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"{label} invalid")
    normalized = normalize_optional_string(value)
    if normalized is None:
        if required:
            raise ContractValidationError(f"{label} invalid")
        return ""
    if len(normalized) > max_length:
        raise ContractValidationError(f"{label} invalid")
    _ensure_no_forbidden_handoff_text(normalized)
    if normalized in _ACTION_VALUES:
        raise ContractValidationError("claude handoff action output invalid")
    return normalized


def _safe_code_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        raise ContractValidationError("claude handoff codes invalid")
    if len(value) > _MAX_CODE_LIST_LENGTH:
        raise ContractValidationError("claude handoff codes invalid")
    return [_safe_code(item) for item in value]


def _safe_code(value: object) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("claude handoff code invalid")
    normalized = normalize_optional_string(value)
    if (
        normalized is None
        or len(normalized) > _MAX_CODE_LENGTH
        or not _SAFE_CODE_RE.fullmatch(normalized)
        or any(fragment in normalized for fragment in _UNSAFE_CODE_FRAGMENTS)
        or normalized in _ACTION_VALUES
    ):
        raise ContractValidationError("claude handoff code invalid")
    return normalized


def _enum_value(value: object, enum_type: type[StrEnum], label: str) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"unsupported {label}")
    ensure_safe_sanitized_payload(value)
    try:
        return enum_type(value).value
    except ValueError:
        raise ContractValidationError(f"unsupported {label}") from None


def _optional_enum_value(
    value: object,
    enum_type: type[StrEnum],
    label: str,
) -> str | None:
    if value is None:
        return None
    return _enum_value(value, enum_type, label)


def _enum_list(
    value: object,
    enum_type: type[StrEnum],
    label: str,
) -> list[str]:
    if not isinstance(value, list | tuple):
        raise ContractValidationError(f"unsupported {label}")
    return [_enum_value(item, enum_type, label) for item in value]


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{key} must be a non-empty string")
    return value


def _optional_string(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be a string")
    return value


def _optional_string_list(data: Mapping[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ContractValidationError(f"{key} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ContractValidationError(f"{key} must contain only strings")
    return list(value)


def _optional_bool(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ContractValidationError(f"{key} must be a boolean")
    return value


def _required_dict(data: Mapping[str, Any], key: str) -> JsonDict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ContractValidationError(f"{key} must be an object")
    return dict(value)


def _require_exact_string(value: object, expected: str, label: str) -> None:
    if value != expected:
        raise ContractValidationError(f"{label} invalid")


def _require_false(value: object, label: str) -> None:
    if value is not False:
        raise ContractValidationError(f"{label} must be false")


def _validate_hash_or_empty(value: object, label: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ContractValidationError(f"{label} invalid")
    if value == "":
        return ""
    if not _SHA256_RE.fullmatch(value):
        raise ContractValidationError(f"{label} invalid")
    return value


def _safe_ref_or_empty(value: object, label: str) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str):
        raise ContractValidationError(f"{label} invalid")
    return ensure_safe_ref(value, label=label)


def _validate_provider_status_pair(status: str, error_code: str) -> None:
    if status == ClaudeHandoffProviderStatus.ACCEPTED.value:
        if error_code != ClaudeHandoffProviderErrorCode.NONE.value:
            raise ContractValidationError("claude handoff provider status invalid")
        return
    if error_code == ClaudeHandoffProviderErrorCode.NONE.value:
        raise ContractValidationError("claude handoff provider status invalid")


def _validate_response_status_payload(
    status: str,
    reviewer_assist_notes: tuple[str, ...],
    structured_comments: Mapping[str, object],
) -> None:
    if status == ClaudeHandoffProviderStatus.ACCEPTED.value:
        return
    if reviewer_assist_notes:
        raise ContractValidationError("claude handoff provider status invalid")
    if structured_comments != _default_structured_comments():
        raise ContractValidationError("claude handoff provider status invalid")


def _ensure_no_forbidden_handoff_text(value: str) -> None:
    if (
        _HTML_TAG_RE.search(value)
        or _CUSTOMER_REPLY_RE.search(value)
        or _FORBIDDEN_TEXT_LABEL_RE.search(value)
        or _ACTION_TOKEN_RE.search(value)
        or _looks_like_article_draft_text(value)
    ):
        raise ContractValidationError("claude handoff text invalid")


def _looks_like_article_draft_text(value: str) -> bool:
    sections = {
        match.group(0).casefold().rstrip(":")
        for match in _DRAFT_SECTION_RE.finditer(value)
    }
    return (
        {"symptoms", "cause", "resolution"}.issubset(sections)
        or {"question", "answer"}.issubset(sections)
    )


def _ensure_no_provider_owned_action(value: object, *, original: bool = False) -> None:
    if isinstance(value, Mapping):
        _ensure_no_provider_owned_action_mapping(value)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _ensure_no_provider_owned_action(item, original=original)
        return
    if isinstance(value, str) and not original:
        if value in _ACTION_VALUES or _ACTION_TOKEN_RE.search(value):
            raise ContractValidationError("claude handoff action output invalid")


def _ensure_no_provider_owned_action_mapping(
    value: Mapping[object, object],
) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("claude handoff payload invalid")
        if key in _ACTION_FIELD_NAMES:
            raise ContractValidationError("claude handoff action output invalid")
        _ensure_no_provider_owned_action(item, original=key.startswith("original_"))


def _ensure_serialized_size(
    payload: Mapping[str, Any],
    max_bytes: int,
    label: str,
) -> None:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContractValidationError(f"claude handoff {label} invalid") from None
    if len(encoded) > max_bytes:
        raise ContractValidationError(f"claude handoff {label} too large")


def _sha256_payload(payload: object) -> str:
    return sha256(dumps_payload(payload).encode("utf-8")).hexdigest()


def _dedupe_codes(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _handoff_context_codes(values: Sequence[str]) -> list[str]:
    return _dedupe_codes(
        [_ACTION_CONTEXT_CODE_ALIASES.get(value, value) for value in values]
    )


def _default_safe_context() -> JsonDict:
    return {
        "article_type": ArticleType.NONE.value,
        "blocker_codes": [],
        "reason_codes": [],
        "reviewer_only_reason_codes": [],
        "short_public_safe_summary": "",
        "status_codes": [],
        "title_hint": "",
        "warning_codes": [],
    }


def _default_operator_override() -> JsonDict:
    return {
        "allowed_override_modes": [],
        "operator_override_allowed": False,
        "override_status": OverrideStatus.NOT_REQUESTED.value,
    }


def _default_artifact_refs() -> JsonDict:
    return {
        "reviewer_packet_ref": "",
        "reviewer_packet_sha256": "",
        "zendesk_source_ref": "",
        "zendesk_source_sha256": "",
    }


def _default_structured_comments() -> JsonDict:
    return {
        "comment_codes": [],
        "needs_reviewer_attention": False,
    }
