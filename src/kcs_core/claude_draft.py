"""Reviewer-only Claude/provider draft contracts for KCS-9c."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Protocol

from kcs_core.claude_handoff import KcsClaudeHandoffRequestPacket
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, dumps_payload, require_json_object
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
    normalize_optional_string,
)

CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION = "kcs_claude_draft_request_v1"
CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION = "kcs_claude_draft_response_v1"
REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION = "kcs_reviewer_only_draft_artifact_v1"
DRAFT_PURPOSE_REVIEWER_ONLY_ARTICLE = "reviewer_only_article_draft"

_ELIGIBLE_DRAFT_ACTIONS = frozenset(
    {
        RecommendedAction.CREATE_CANDIDATE.value,
        RecommendedAction.UPDATE_EXISTING.value,
        RecommendedAction.FLAG_EXISTING.value,
    }
)
_MAX_REQUEST_BYTES = 40 * 1024
_MAX_RESPONSE_BYTES = 64 * 1024
_MAX_ARTIFACT_BYTES = 96 * 1024
_MAX_TITLE_LENGTH = 180
_MAX_APPLICABLE_TO_LENGTH = 400
_MAX_SECTION_LENGTH = 3_000
_MAX_NOTE_LENGTH = 800
_MAX_REVIEWER_NOTES = 12
_MAX_CONTEXT_SUMMARY_LENGTH = 1_600
_SAFE_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,79}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_FORBIDDEN_TEXT_RE = re.compile(
    r"\b(?:customer_reply|reply_to_customer|agent_reply|email_reply|"
    r"ticket_response|zendesk_source_html|public_article_candidate|"
    r"reviewer_packet|evidence_basis|raw_ticket|raw_comments?|"
    r"internal_comments?|redaction_map)\b",
    re.I,
)
_CUSTOMER_REPLY_SECTION_RE = re.compile(
    r"\b(?:customer reply|reply to customer|agent reply|email reply|"
    r"ticket response)\s*:",
    re.I,
)
_ACTION_TOKEN_RE = re.compile(
    r"\b(?:reuse_existing|update_existing|create_candidate|flag_existing|"
    r"split_required|no_article)\b",
    re.I,
)
_ACTION_LABEL_RE = re.compile(
    r"\b(?:recommended action|proposed action|kcs action|decision)\s*:",
    re.I,
)
_PUBLIC_ENVIRONMENT_HEADING_RE = re.compile(
    r"<\s*h2(?:\s[^>]*)?>\s*environment\s*<\s*/\s*h2\s*>",
    re.I,
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
        "redaction_map",
        "reviewer_packet",
        "secret",
        "token",
        "zendesk_source_html",
    }
)
_REQUEST_FIELDS = frozenset(
    {
        "artifact_refs",
        "auto_publish_allowed",
        "case_ref",
        "draft_purpose",
        "draft_ref",
        "handoff_ref",
        "item_ref",
        "operator_override",
        "original_article_type",
        "original_decision_status",
        "original_readiness_state",
        "original_recommended_action",
        "provider_may_decide_action",
        "public_output_approved",
        "safe_drafting_context",
        "schema_version",
    }
)
_SAFE_DRAFTING_CONTEXT_FIELDS = frozenset(
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
        "applicable_to",
        "article_type",
        "auto_publish_allowed",
        "draft_status",
        "handoff_ref",
        "internal_only_content_present",
        "original_article_type",
        "original_decision_status",
        "original_readiness_state",
        "original_recommended_action",
        "provider_error_code",
        "public_output_approved",
        "reviewer_notes",
        "schema_version",
        "sections",
        "title",
        "unsupported_claims_present",
        "zendesk_source_html",
    }
)
_TECHNICAL_SECTION_FIELDS = frozenset(
    {
        "additional_information",
        "cause",
        "resolution",
        "symptoms",
    }
)
_HOWTO_SECTION_FIELDS = frozenset({"answer", "question"})
_ARTIFACT_FIELDS = frozenset(
    {
        "artifact_ref",
        "auto_publish_allowed",
        "case_ref",
        "draft_ref",
        "draft_response",
        "draft_response_sha256",
        "handoff_ref",
        "item_ref",
        "original_article_type",
        "original_decision_status",
        "original_readiness_state",
        "original_recommended_action",
        "public_output_approved",
        "reviewer_only",
        "schema_version",
    }
)
_ALLOWED_HTML_TAGS = frozenset(
    {"a", "br", "code", "em", "h1", "h2", "h3", "li", "ol", "p", "pre", "strong", "ul"}
)
_VOID_HTML_TAGS = frozenset({"br"})
_BLOCK_HTML_TAGS = frozenset({"br", "h1", "h2", "h3", "li", "ol", "p", "pre", "ul"})


class ClaudeDraftStatus(StrEnum):
    """Allowed KCS-9c draft response status values."""

    ACCEPTED = "accepted"
    FAILED = "failed"
    REJECTED = "rejected"


class ClaudeDraftProviderErrorCode(StrEnum):
    """Allowed KCS-9c provider error codes."""

    NONE = "none"
    PROVIDER_FAILED = "provider_failed"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    PROVIDER_REJECTED_CONTEXT = "provider_rejected_context"
    UNSAFE_OUTPUT_BLOCKED = "unsafe_output_blocked"


class ClaudeDraftProvider(Protocol):
    """Provider boundary for reviewer-only draft proposals."""

    def propose_draft(
        self, request: "KcsClaudeDraftRequestPacket"
    ) -> "KcsClaudeDraftResponsePacket | Mapping[str, Any]":
        """Return untrusted draft proposal output."""


@dataclass(frozen=True)
class KcsClaudeDraftRequestPacket:
    """Bounded request for KCS-9c reviewer-only draft generation."""

    draft_ref: str
    handoff_ref: str
    case_ref: str
    item_ref: str
    original_recommended_action: str
    original_article_type: str
    original_decision_status: str
    original_readiness_state: str
    draft_purpose: str = DRAFT_PURPOSE_REVIEWER_ONLY_ARTICLE
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    provider_may_decide_action: bool = False
    safe_drafting_context: JsonDict = field(default_factory=dict)
    operator_override: JsonDict = field(default_factory=dict)
    artifact_refs: JsonDict = field(default_factory=dict)
    schema_version: str = CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude draft schema_version")
        object.__setattr__(
            self, "draft_ref", ensure_safe_ref(self.draft_ref, label="draft_ref")
        )
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
            self.draft_purpose,
            DRAFT_PURPOSE_REVIEWER_ONLY_ARTICLE,
            "draft_purpose",
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
        _validate_draft_eligibility(
            self.original_recommended_action,
            self.original_article_type,
            self.original_decision_status,
            self.original_readiness_state,
        )
        for key in (
            "auto_publish_allowed",
            "public_output_approved",
            "provider_may_decide_action",
        ):
            _require_false(getattr(self, key), key)
        object.__setattr__(
            self,
            "safe_drafting_context",
            _validate_safe_drafting_context(self.safe_drafting_context),
        )
        if self.safe_drafting_context["article_type"] != self.original_article_type:
            raise ContractValidationError("claude draft article type mismatch")
        object.__setattr__(
            self,
            "operator_override",
            _validate_operator_override(self.operator_override),
        )
        object.__setattr__(
            self, "artifact_refs", _validate_artifact_refs(self.artifact_refs)
        )
        _ensure_no_provider_owned_action(self.to_json_dict())
        _ensure_serialized_size(self.to_json_dict(), _MAX_REQUEST_BYTES, "request")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsClaudeDraftRequestPacket":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _REQUEST_FIELDS, label="claude draft request")
        _ensure_no_provider_owned_action(data)
        if data.get("schema_version") != CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude draft schema_version")
        return cls(
            draft_ref=_required_string(data, "draft_ref"),
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
            draft_purpose=_required_string(data, "draft_purpose"),
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
            public_output_approved=_optional_bool(
                data, "public_output_approved", False
            ),
            provider_may_decide_action=_optional_bool(
                data, "provider_may_decide_action", False
            ),
            safe_drafting_context=_required_dict(data, "safe_drafting_context"),
            operator_override=_required_dict(data, "operator_override"),
            artifact_refs=_required_dict(data, "artifact_refs"),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "artifact_refs": dict(self.artifact_refs),
            "auto_publish_allowed": self.auto_publish_allowed,
            "case_ref": self.case_ref,
            "draft_purpose": self.draft_purpose,
            "draft_ref": self.draft_ref,
            "handoff_ref": self.handoff_ref,
            "item_ref": self.item_ref,
            "operator_override": dict(self.operator_override),
            "original_article_type": self.original_article_type,
            "original_decision_status": self.original_decision_status,
            "original_readiness_state": self.original_readiness_state,
            "original_recommended_action": self.original_recommended_action,
            "provider_may_decide_action": self.provider_may_decide_action,
            "public_output_approved": self.public_output_approved,
            "safe_drafting_context": dict(self.safe_drafting_context),
            "schema_version": self.schema_version,
        }


@dataclass(frozen=True)
class KcsClaudeDraftResponsePacket:
    """Validated untrusted provider draft proposal for reviewer use."""

    handoff_ref: str
    draft_status: str
    provider_error_code: str
    article_type: str
    title: str = ""
    applicable_to: str = ""
    sections: JsonDict = field(default_factory=dict)
    zendesk_source_html: str = ""
    reviewer_notes: tuple[str, ...] = ()
    unsupported_claims_present: bool = False
    internal_only_content_present: bool = False
    original_recommended_action: str | None = None
    original_article_type: str | None = None
    original_decision_status: str | None = None
    original_readiness_state: str | None = None
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    schema_version: str = CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported claude draft response schema_version"
            )
        object.__setattr__(
            self,
            "handoff_ref",
            ensure_safe_ref(self.handoff_ref, label="handoff_ref"),
        )
        object.__setattr__(
            self,
            "draft_status",
            _enum_value(self.draft_status, ClaudeDraftStatus, "draft_status"),
        )
        object.__setattr__(
            self,
            "provider_error_code",
            _enum_value(
                self.provider_error_code,
                ClaudeDraftProviderErrorCode,
                "provider_error_code",
            ),
        )
        object.__setattr__(
            self,
            "article_type",
            _enum_value(self.article_type, ArticleType, "article_type"),
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
        for key in ("auto_publish_allowed", "public_output_approved"):
            _require_false(getattr(self, key), key)
        if not isinstance(self.unsupported_claims_present, bool):
            raise ContractValidationError("claude draft unsupported claims invalid")
        if not isinstance(self.internal_only_content_present, bool):
            raise ContractValidationError("claude draft internal content invalid")
        _validate_status_pair(self.draft_status, self.provider_error_code)
        _validate_unsupported_claims(self.unsupported_claims_present)
        _validate_internal_only_content(self.internal_only_content_present)
        object.__setattr__(
            self,
            "title",
            _safe_text(self.title, "title", _MAX_TITLE_LENGTH, required=False),
        )
        object.__setattr__(
            self,
            "applicable_to",
            _safe_text(
                self.applicable_to,
                "applicable_to",
                _MAX_APPLICABLE_TO_LENGTH,
                required=False,
            ),
        )
        object.__setattr__(
            self,
            "sections",
            _validate_sections(self.sections, self.article_type, self.draft_status),
        )
        object.__setattr__(
            self,
            "zendesk_source_html",
            _validate_draft_html(self.zendesk_source_html, self.draft_status),
        )
        object.__setattr__(
            self,
            "reviewer_notes",
            _validate_reviewer_notes(self.reviewer_notes),
        )
        _validate_accepted_response_shape(self)
        _ensure_no_provider_owned_action(self.to_json_dict())
        _ensure_serialized_size(self.to_json_dict(), _MAX_RESPONSE_BYTES, "response")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsClaudeDraftResponsePacket":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _RESPONSE_FIELDS, label="claude draft response")
        _ensure_no_provider_owned_action(data)
        if data.get("schema_version") != CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported claude draft response schema_version"
            )
        return cls(
            handoff_ref=_required_string(data, "handoff_ref"),
            draft_status=_required_string(data, "draft_status"),
            provider_error_code=_required_string(data, "provider_error_code"),
            article_type=_required_string(data, "article_type"),
            title=_optional_string(data, "title") or "",
            applicable_to=_optional_string(data, "applicable_to") or "",
            sections=_required_dict(data, "sections"),
            zendesk_source_html=_optional_string(data, "zendesk_source_html") or "",
            reviewer_notes=tuple(_optional_string_list(data, "reviewer_notes")),
            unsupported_claims_present=_optional_bool(
                data, "unsupported_claims_present", False
            ),
            internal_only_content_present=_optional_bool(
                data, "internal_only_content_present", False
            ),
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
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
            public_output_approved=_optional_bool(
                data, "public_output_approved", False
            ),
        )

    def to_json_dict(self) -> JsonDict:
        payload: JsonDict = {
            "applicable_to": self.applicable_to,
            "article_type": self.article_type,
            "auto_publish_allowed": self.auto_publish_allowed,
            "draft_status": self.draft_status,
            "handoff_ref": self.handoff_ref,
            "internal_only_content_present": self.internal_only_content_present,
            "provider_error_code": self.provider_error_code,
            "public_output_approved": self.public_output_approved,
            "reviewer_notes": list(self.reviewer_notes),
            "schema_version": self.schema_version,
            "sections": dict(self.sections),
            "title": self.title,
            "unsupported_claims_present": self.unsupported_claims_present,
            "zendesk_source_html": self.zendesk_source_html,
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


@dataclass(frozen=True)
class KcsReviewerOnlyDraftArtifact:
    """Reviewer-only local artifact that stores validated untrusted draft output."""

    artifact_ref: str
    draft_ref: str
    handoff_ref: str
    case_ref: str
    item_ref: str
    original_recommended_action: str
    original_article_type: str
    original_decision_status: str
    original_readiness_state: str
    draft_response: JsonDict
    draft_response_sha256: str
    reviewer_only: bool = True
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    schema_version: str = REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported draft artifact schema_version")
        object.__setattr__(
            self,
            "artifact_ref",
            ensure_safe_ref(self.artifact_ref, label="artifact_ref"),
        )
        object.__setattr__(
            self, "draft_ref", ensure_safe_ref(self.draft_ref, label="draft_ref")
        )
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
        if self.reviewer_only is not True:
            raise ContractValidationError("draft artifact must be reviewer-only")
        for key in ("auto_publish_allowed", "public_output_approved"):
            _require_false(getattr(self, key), key)
        response = KcsClaudeDraftResponsePacket.from_json_dict(self.draft_response)
        if response.draft_status != ClaudeDraftStatus.ACCEPTED.value:
            raise ContractValidationError("draft artifact requires accepted response")
        expected_hash = _sha256_payload(response)
        if self.draft_response_sha256 != expected_hash:
            raise ContractValidationError("draft artifact response hash mismatch")
        _validate_artifact_response_matches_metadata(self, response)
        _ensure_serialized_size(self.to_json_dict(), _MAX_ARTIFACT_BYTES, "artifact")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "KcsReviewerOnlyDraftArtifact":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _ARTIFACT_FIELDS, label="reviewer draft artifact")
        if data.get("schema_version") != REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported draft artifact schema_version")
        return cls(
            artifact_ref=_required_string(data, "artifact_ref"),
            draft_ref=_required_string(data, "draft_ref"),
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
            draft_response=_required_dict(data, "draft_response"),
            draft_response_sha256=_required_string(data, "draft_response_sha256"),
            reviewer_only=_optional_bool(data, "reviewer_only", True),
            auto_publish_allowed=_optional_bool(data, "auto_publish_allowed", False),
            public_output_approved=_optional_bool(
                data, "public_output_approved", False
            ),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "artifact_ref": self.artifact_ref,
            "auto_publish_allowed": self.auto_publish_allowed,
            "case_ref": self.case_ref,
            "draft_ref": self.draft_ref,
            "draft_response": dict(self.draft_response),
            "draft_response_sha256": self.draft_response_sha256,
            "handoff_ref": self.handoff_ref,
            "item_ref": self.item_ref,
            "original_article_type": self.original_article_type,
            "original_decision_status": self.original_decision_status,
            "original_readiness_state": self.original_readiness_state,
            "original_recommended_action": self.original_recommended_action,
            "public_output_approved": self.public_output_approved,
            "reviewer_only": self.reviewer_only,
            "schema_version": self.schema_version,
        }


def build_claude_draft_request(
    handoff_request: KcsClaudeHandoffRequestPacket,
    *,
    draft_ref: str,
) -> KcsClaudeDraftRequestPacket:
    """Build a KCS-9c draft request from a validated KCS-9b request."""

    return KcsClaudeDraftRequestPacket(
        draft_ref=draft_ref,
        handoff_ref=handoff_request.handoff_ref,
        case_ref=handoff_request.case_ref,
        item_ref=handoff_request.item_ref,
        original_recommended_action=handoff_request.original_recommended_action,
        original_article_type=handoff_request.original_article_type,
        original_decision_status=handoff_request.original_decision_status,
        original_readiness_state=handoff_request.original_readiness_state,
        safe_drafting_context=dict(handoff_request.safe_context),
        operator_override=dict(handoff_request.operator_override),
        artifact_refs=dict(handoff_request.artifact_refs),
    )


def validate_claude_draft_response(
    payload: KcsClaudeDraftResponsePacket | Mapping[str, Any] | object,
    *,
    request: KcsClaudeDraftRequestPacket,
) -> KcsClaudeDraftResponsePacket:
    """Validate untrusted KCS-9c provider draft output against its request."""

    response = (
        payload
        if isinstance(payload, KcsClaudeDraftResponsePacket)
        else KcsClaudeDraftResponsePacket.from_json_dict(payload)
    )
    _validate_response_matches_request(response, request)
    return response


def submit_claude_draft_request(
    request: KcsClaudeDraftRequestPacket,
    *,
    provider: ClaudeDraftProvider,
) -> KcsClaudeDraftResponsePacket:
    """Submit a KCS-9c draft request and return value-safe provider output."""

    provider_failed = False
    raw_response: KcsClaudeDraftResponsePacket | Mapping[str, Any] | None = None
    try:
        raw_response = provider.propose_draft(request)
    except Exception:
        provider_failed = True
    if provider_failed or raw_response is None:
        return _safe_failed_response(
            request,
            ClaudeDraftProviderErrorCode.PROVIDER_FAILED.value,
        )
    try:
        return validate_claude_draft_response(raw_response, request=request)
    except ContractValidationError:
        return _safe_failed_response(
            request,
            ClaudeDraftProviderErrorCode.PROVIDER_RESPONSE_INVALID.value,
        )


def build_reviewer_only_draft_artifact(
    request: KcsClaudeDraftRequestPacket,
    response: KcsClaudeDraftResponsePacket,
    *,
    artifact_ref: str,
) -> KcsReviewerOnlyDraftArtifact:
    """Build a reviewer-only artifact from a validated accepted draft response."""

    validated = validate_claude_draft_response(response, request=request)
    if validated.draft_status != ClaudeDraftStatus.ACCEPTED.value:
        raise ContractValidationError("draft artifact requires accepted response")
    return KcsReviewerOnlyDraftArtifact(
        artifact_ref=artifact_ref,
        draft_ref=request.draft_ref,
        handoff_ref=request.handoff_ref,
        case_ref=request.case_ref,
        item_ref=request.item_ref,
        original_recommended_action=request.original_recommended_action,
        original_article_type=request.original_article_type,
        original_decision_status=request.original_decision_status,
        original_readiness_state=request.original_readiness_state,
        draft_response=validated.to_json_dict(),
        draft_response_sha256=_sha256_payload(validated),
    )


def write_reviewer_only_draft_artifact(
    artifact: KcsReviewerOnlyDraftArtifact,
    output_dir: Path,
) -> Path:
    """Write one reviewer-only draft artifact with guarded local file semantics."""

    output_dir = _prepare_output_dir(output_dir)
    output_path = output_dir / "kcs-reviewer-only-draft.json"
    _reject_symlink_path(output_path)
    if output_path.exists() or output_path.is_symlink():
        raise ContractValidationError("refusing to overwrite draft artifact")
    text = _json_text(artifact.to_json_dict())
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    try:
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        temp_path.replace(output_path)
    except OSError:
        _cleanup_path(temp_path)
        raise ContractValidationError("could not write draft artifact") from None
    return output_path


def _validate_draft_eligibility(
    action: str,
    article_type: str,
    decision_status: str,
    readiness_state: str,
) -> None:
    if action not in _ELIGIBLE_DRAFT_ACTIONS:
        raise ContractValidationError("claude draft request is not eligible")
    if article_type == ArticleType.NONE.value:
        raise ContractValidationError("claude draft request is not eligible")
    if decision_status != DecisionStatus.DECISION_READY.value:
        raise ContractValidationError("claude draft request is not eligible")
    if readiness_state != ReadinessState.READY_FOR_REVIEWER.value:
        raise ContractValidationError("claude draft request is not eligible")


def _validate_safe_drafting_context(value: object) -> JsonDict:
    data = _safe_object(
        value,
        _SAFE_DRAFTING_CONTEXT_FIELDS,
        "claude draft safe_drafting_context",
    )
    return {
        "article_type": _enum_value(
            data.get("article_type", ArticleType.NONE.value),
            ArticleType,
            "safe_drafting_context.article_type",
        ),
        "blocker_codes": _safe_code_list(data.get("blocker_codes", [])),
        "reason_codes": _safe_code_list(data.get("reason_codes", [])),
        "reviewer_only_reason_codes": _safe_code_list(
            data.get("reviewer_only_reason_codes", [])
        ),
        "short_public_safe_summary": _safe_text(
            data.get("short_public_safe_summary", ""),
            "safe_drafting_context.short_public_safe_summary",
            _MAX_CONTEXT_SUMMARY_LENGTH,
            required=False,
        ),
        "status_codes": _safe_code_list(data.get("status_codes", [])),
        "title_hint": _safe_text(
            data.get("title_hint", ""),
            "safe_drafting_context.title_hint",
            _MAX_TITLE_LENGTH,
            required=False,
        ),
        "warning_codes": _safe_code_list(data.get("warning_codes", [])),
    }


def _validate_operator_override(value: object) -> JsonDict:
    data = _safe_object(
        value,
        _OPERATOR_OVERRIDE_FIELDS,
        "claude draft operator_override",
    )
    operator_override_allowed = data.get("operator_override_allowed", False)
    if not isinstance(operator_override_allowed, bool):
        raise ContractValidationError("claude draft operator override invalid")
    allowed_modes = _safe_code_list(data.get("allowed_override_modes", []))
    override_status = _safe_code(data.get("override_status", "not_requested"))
    return {
        "allowed_override_modes": allowed_modes,
        "operator_override_allowed": operator_override_allowed,
        "override_status": override_status,
    }


def _validate_artifact_refs(value: object) -> JsonDict:
    data = _safe_object(value, _ARTIFACT_REF_FIELDS, "claude draft artifact_refs")
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


def _validate_sections(
    value: object,
    article_type: str,
    draft_status: str,
) -> JsonDict:
    if not isinstance(value, Mapping):
        raise ContractValidationError("claude draft sections invalid")
    ensure_safe_sanitized_payload(value)
    if draft_status != ClaudeDraftStatus.ACCEPTED.value:
        if value:
            raise ContractValidationError("claude draft sections invalid")
        return {}
    if article_type == ArticleType.TECHNICAL_SCR.value:
        ensure_allowed_keys(
            value,
            _TECHNICAL_SECTION_FIELDS,
            label="claude draft sections",
        )
        result = {
            "symptoms": _safe_text(
                value.get("symptoms"),
                "sections.symptoms",
                _MAX_SECTION_LENGTH,
                required=True,
            ),
            "cause": _safe_text(
                value.get("cause"),
                "sections.cause",
                _MAX_SECTION_LENGTH,
                required=True,
            ),
            "resolution": _safe_text(
                value.get("resolution"),
                "sections.resolution",
                _MAX_SECTION_LENGTH,
                required=True,
            ),
        }
        additional = _safe_text(
            value.get("additional_information", ""),
            "sections.additional_information",
            _MAX_SECTION_LENGTH,
            required=False,
        )
        if additional:
            result["additional_information"] = additional
        return result
    if article_type == ArticleType.HOWTO_QA.value:
        ensure_allowed_keys(value, _HOWTO_SECTION_FIELDS, label="claude draft sections")
        return {
            "question": _safe_text(
                value.get("question"),
                "sections.question",
                _MAX_SECTION_LENGTH,
                required=True,
            ),
            "answer": _safe_text(
                value.get("answer"),
                "sections.answer",
                _MAX_SECTION_LENGTH,
                required=True,
            ),
        }
    raise ContractValidationError("claude draft article type invalid")


def _validate_accepted_response_shape(response: KcsClaudeDraftResponsePacket) -> None:
    if response.draft_status != ClaudeDraftStatus.ACCEPTED.value:
        if (
            response.title
            or response.applicable_to
            or response.sections
            or response.zendesk_source_html
            or response.reviewer_notes
        ):
            raise ContractValidationError("claude draft status invalid")
        return
    if not response.title:
        raise ContractValidationError("claude draft title invalid")
    if (
        response.article_type == ArticleType.TECHNICAL_SCR.value
        and not response.applicable_to
    ):
        raise ContractValidationError("claude draft applicable_to invalid")
    if not response.sections:
        raise ContractValidationError("claude draft sections invalid")


def _validate_draft_html(value: object, draft_status: str) -> str:
    html = _safe_text(
        value,
        "zendesk_source_html",
        _MAX_RESPONSE_BYTES,
        required=False,
        allow_html=True,
    )
    if draft_status != ClaudeDraftStatus.ACCEPTED.value:
        if html:
            raise ContractValidationError("claude draft html invalid")
        return ""
    if not html:
        return ""
    _validate_html_subset(html)
    return html


def _validate_html_subset(value: str) -> None:
    if _PUBLIC_ENVIRONMENT_HEADING_RE.search(value):
        raise ContractValidationError("claude draft html invalid")
    parser = _DraftHtmlValidator()
    try:
        parser.feed(value)
        parser.close()
    except ContractValidationError:
        raise
    except Exception:
        raise ContractValidationError("claude draft html invalid") from None
    if parser.stack:
        raise ContractValidationError("claude draft html invalid")
    visible_text = "".join(parser.visible_text_parts)
    _ensure_safe_html_text(visible_text)
    _ensure_no_forbidden_text(visible_text)
    _ensure_no_provider_owned_action_text(visible_text)


class _DraftHtmlValidator(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.visible_text_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.casefold()
        if tag not in _ALLOWED_HTML_TAGS:
            raise ContractValidationError("claude draft html invalid")
        if tag == "a":
            self._validate_link_attrs(attrs)
        elif attrs:
            raise ContractValidationError("claude draft html invalid")
        if tag in _BLOCK_HTML_TAGS:
            self.visible_text_parts.append(" ")
        if tag not in _VOID_HTML_TAGS:
            self.stack.append(tag)

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.casefold()
        if tag not in _ALLOWED_HTML_TAGS:
            raise ContractValidationError("claude draft html invalid")
        if tag == "a":
            self._validate_link_attrs(attrs)
        elif tag != "br" or attrs:
            raise ContractValidationError("claude draft html invalid")
        if tag in _BLOCK_HTML_TAGS:
            self.visible_text_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag not in _ALLOWED_HTML_TAGS or tag in _VOID_HTML_TAGS:
            raise ContractValidationError("claude draft html invalid")
        if not self.stack or self.stack[-1] != tag:
            raise ContractValidationError("claude draft html invalid")
        self.stack.pop()
        if tag in _BLOCK_HTML_TAGS:
            self.visible_text_parts.append(" ")

    def handle_decl(self, decl: str) -> None:
        raise ContractValidationError("claude draft html invalid")

    def handle_data(self, data: str) -> None:
        _ensure_safe_html_text(data)
        _ensure_no_forbidden_text(data)
        _ensure_no_provider_owned_action_text(data)
        self.visible_text_parts.append(data)

    def handle_comment(self, data: str) -> None:
        raise ContractValidationError("claude draft html invalid")

    def handle_pi(self, data: str) -> None:
        raise ContractValidationError("claude draft html invalid")

    def handle_entityref(self, name: str) -> None:
        return

    def handle_charref(self, name: str) -> None:
        return

    def _validate_link_attrs(self, attrs: list[tuple[str, str | None]]) -> None:
        if len(attrs) != 1:
            raise ContractValidationError("claude draft html invalid")
        key, value = attrs[0]
        if key.casefold() != "href" or value is None:
            raise ContractValidationError("claude draft html invalid")
        # Default policy: no external URLs. Public-doc URLs require a future
        # explicit allowlist validator.
        ensure_safe_ref(value, label="draft_link_ref")


def _validate_reviewer_notes(value: object) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ContractValidationError("claude draft reviewer notes invalid")
    if len(value) > _MAX_REVIEWER_NOTES:
        raise ContractValidationError("claude draft reviewer notes invalid")
    return tuple(
        _safe_text(item, "reviewer_notes", _MAX_NOTE_LENGTH, required=True)
        for item in value
    )


def _validate_unsupported_claims(value: bool) -> None:
    if value:
        raise ContractValidationError("claude draft unsupported claims blocked")


def _validate_internal_only_content(value: bool) -> None:
    if value:
        raise ContractValidationError("claude draft internal content blocked")


def _validate_status_pair(status: str, error_code: str) -> None:
    if status == ClaudeDraftStatus.ACCEPTED.value:
        if error_code != ClaudeDraftProviderErrorCode.NONE.value:
            raise ContractValidationError("claude draft status invalid")
        return
    if error_code == ClaudeDraftProviderErrorCode.NONE.value:
        raise ContractValidationError("claude draft status invalid")


def _validate_response_matches_request(
    response: KcsClaudeDraftResponsePacket,
    request: KcsClaudeDraftRequestPacket,
) -> None:
    if response.handoff_ref != request.handoff_ref:
        raise ContractValidationError("claude draft response mismatch")
    if response.article_type != request.original_article_type:
        raise ContractValidationError("claude draft response mismatch")
    comparisons = (
        ("original_recommended_action", request.original_recommended_action),
        ("original_article_type", request.original_article_type),
        ("original_decision_status", request.original_decision_status),
        ("original_readiness_state", request.original_readiness_state),
    )
    for key, expected in comparisons:
        actual = getattr(response, key)
        if actual is not None and actual != expected:
            raise ContractValidationError("claude draft response mismatch")


def _validate_artifact_response_matches_metadata(
    artifact: KcsReviewerOnlyDraftArtifact,
    response: KcsClaudeDraftResponsePacket,
) -> None:
    if response.handoff_ref != artifact.handoff_ref:
        raise ContractValidationError("draft artifact response mismatch")
    if response.article_type != artifact.original_article_type:
        raise ContractValidationError("draft artifact response mismatch")
    comparisons = (
        ("original_recommended_action", artifact.original_recommended_action),
        ("original_article_type", artifact.original_article_type),
        ("original_decision_status", artifact.original_decision_status),
        ("original_readiness_state", artifact.original_readiness_state),
    )
    for key, expected in comparisons:
        actual = getattr(response, key)
        if actual is not None and actual != expected:
            raise ContractValidationError("draft artifact response mismatch")


def _safe_failed_response(
    request: KcsClaudeDraftRequestPacket,
    provider_error_code: str,
) -> KcsClaudeDraftResponsePacket:
    return KcsClaudeDraftResponsePacket(
        handoff_ref=request.handoff_ref,
        draft_status=ClaudeDraftStatus.FAILED.value,
        provider_error_code=provider_error_code,
        article_type=request.original_article_type,
        original_recommended_action=request.original_recommended_action,
        original_article_type=request.original_article_type,
        original_decision_status=request.original_decision_status,
        original_readiness_state=request.original_readiness_state,
    )


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
    allow_html: bool = False,
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
    if not allow_html:
        ensure_safe_sanitized_payload(normalized)
    else:
        _ensure_safe_html_text(normalized)
    _ensure_no_forbidden_text(normalized)
    _ensure_no_provider_owned_action_text(normalized)
    if normalized in _ACTION_VALUES:
        raise ContractValidationError("claude draft action output invalid")
    return normalized


def _ensure_safe_html_text(value: str) -> None:
    if any(pattern.search(value) for pattern in _PRIVATE_HTML_PATTERNS):
        raise ContractValidationError("claude draft html invalid")


_PRIVATE_HTML_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I),
    re.compile(r"https?://[^\s\"']+", re.I),
    re.compile(
        r"\b(?!example\.(?:com|net|org|invalid)\b)"
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63}\b",
        re.I,
    ),
    re.compile(r"(?:/Users/|/home/|C:\\Users\\)", re.I),
    re.compile(r"\b(?:PLSK|EXT)[-_.]?\d{4,}(?:[-_.]?\d+)*\b", re.I),
    re.compile(r"\b(?:ticket|zendesk|zd)[-_ #:]?\d{4,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+",
        re.I,
    ),
    re.compile(r"\bauthorization:\s*bearer\s+\S+", re.I),
)


def _ensure_no_forbidden_text(value: str) -> None:
    if _FORBIDDEN_TEXT_RE.search(value) or _CUSTOMER_REPLY_SECTION_RE.search(value):
        raise ContractValidationError("claude draft text invalid")


def _ensure_no_provider_owned_action_text(value: str) -> None:
    if _ACTION_TOKEN_RE.search(value) or _ACTION_LABEL_RE.search(value):
        raise ContractValidationError("claude draft action output invalid")


def _safe_code_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        raise ContractValidationError("claude draft codes invalid")
    return [_safe_code(item) for item in value]


def _safe_code(value: object) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("claude draft code invalid")
    normalized = normalize_optional_string(value)
    if (
        normalized is None
        or not _SAFE_CODE_RE.fullmatch(normalized)
        or any(fragment in normalized for fragment in _UNSAFE_CODE_FRAGMENTS)
        or normalized in _ACTION_VALUES
    ):
        raise ContractValidationError("claude draft code invalid")
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


def _ensure_no_provider_owned_action(value: object, *, original: bool = False) -> None:
    if isinstance(value, Mapping):
        _ensure_no_provider_owned_action_mapping(value)
        return
    if isinstance(value, list | tuple):
        for item in value:
            _ensure_no_provider_owned_action(item, original=original)
        return
    if isinstance(value, str) and not original and value in _ACTION_VALUES:
        raise ContractValidationError("claude draft action output invalid")


def _ensure_no_provider_owned_action_mapping(
    value: Mapping[object, object],
) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("claude draft payload invalid")
        if key in _ACTION_FIELD_NAMES:
            raise ContractValidationError("claude draft action output invalid")
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
        raise ContractValidationError(f"claude draft {label} invalid") from None
    if len(encoded) > max_bytes:
        raise ContractValidationError(f"claude draft {label} too large")


def _sha256_payload(payload: object) -> str:
    return sha256(dumps_payload(payload).encode("utf-8")).hexdigest()


def _json_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, allow_nan=False, indent=2) + "\n"


def _prepare_output_dir(output_dir: Path) -> Path:
    requested = Path(output_dir)
    if ".." in requested.parts:
        raise ContractValidationError("draft artifact path invalid")
    _reject_symlink_path(requested)
    try:
        requested.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise ContractValidationError(
            "could not prepare draft artifact directory"
        ) from None
    workspace = requested.resolve(strict=False)
    _reject_symlink_path(workspace)
    if not workspace.is_dir():
        raise ContractValidationError("draft artifact directory invalid")
    return workspace


def _reject_symlink_path(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    for part in path.parts:
        if part in ("", current.anchor):
            continue
        current = current / part
        if current.is_symlink():
            raise ContractValidationError("draft artifact path must not use symlinks")


def _cleanup_path(path: Path) -> None:
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        return
