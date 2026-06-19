"""Contract validation and smoke helpers for Desktop MCP tools."""

from __future__ import annotations

from hashlib import sha256

from kcs_core.claude_draft import (
    CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    KcsClaudeDraftRequestPacket,
    build_claude_draft_request,
    validate_claude_draft_response,
)
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    ClaudeHandoffProviderErrorCode,
    ClaudeHandoffProviderStatus,
    KcsClaudeHandoffRequestPacket,
    validate_claude_handoff_response,
)
from kcs_core.json_payload import JsonDict, JsonPayload, dumps_payload
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)


def validate_handoff_request_payload(
    request_payload: object,
    *,
    schema_version: str,
) -> JsonDict:
    request = KcsClaudeHandoffRequestPacket.from_json_dict(request_payload)
    return handoff_request_summary(request, schema_version=schema_version)


def validate_handoff_response_payload(
    request_payload: object,
    response_payload: object,
    *,
    schema_version: str,
) -> JsonDict:
    request = KcsClaudeHandoffRequestPacket.from_json_dict(request_payload)
    response = validate_claude_handoff_response(
        response_payload,
        request=request,
    )
    return handoff_response_summary(request, response, schema_version=schema_version)


def validate_draft_request_payload(
    request_payload: object,
    *,
    schema_version: str,
) -> JsonDict:
    request = KcsClaudeDraftRequestPacket.from_json_dict(request_payload)
    return draft_request_summary(request, schema_version=schema_version)


def validate_draft_response_payload(
    request_payload: object,
    response_payload: object,
    *,
    schema_version: str,
) -> JsonDict:
    request = KcsClaudeDraftRequestPacket.from_json_dict(request_payload)
    response = validate_claude_draft_response(
        response_payload,
        request=request,
    )
    return draft_response_summary(request, response, schema_version=schema_version)


def run_contract_smoke(*, schema_version: str) -> list[JsonDict]:
    handoff_request = _synthetic_handoff_request()
    handoff_response = validate_claude_handoff_response(
        _synthetic_handoff_response(handoff_request),
        request=handoff_request,
    )
    draft_request = build_claude_draft_request(
        handoff_request,
        draft_ref="draft-001",
    )
    draft_response = validate_claude_draft_response(
        _synthetic_draft_response(draft_request),
        request=draft_request,
    )
    return [
        handoff_request_summary(handoff_request, schema_version=schema_version),
        handoff_response_summary(
            handoff_request,
            handoff_response,
            schema_version=schema_version,
        ),
        draft_request_summary(draft_request, schema_version=schema_version),
        draft_response_summary(
            draft_request,
            draft_response,
            schema_version=schema_version,
        ),
    ]


def handoff_request_summary(
    request: KcsClaudeHandoffRequestPacket,
    *,
    schema_version: str,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "case_ref": request.case_ref,
        "handoff_ref": request.handoff_ref,
        "item_ref": request.item_ref,
        "ok": True,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "public_output_approved": False,
        "request_schema_version": CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        "request_sha256": _payload_sha256(request),
        "result_kind": "handoff_request_validation",
        "schema_version": schema_version,
        "validation_ok": True,
    }


def handoff_response_summary(
    request: KcsClaudeHandoffRequestPacket,
    response: JsonPayload,
    *,
    schema_version: str,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "handoff_ref": request.handoff_ref,
        "ok": True,
        "provider_error_code": response.to_json_dict()["provider_error_code"],
        "provider_status": response.to_json_dict()["provider_status"],
        "public_output_approved": False,
        "response_schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "response_sha256": _payload_sha256(response),
        "result_kind": "handoff_response_validation",
        "schema_version": schema_version,
        "validation_ok": True,
    }


def draft_request_summary(
    request: KcsClaudeDraftRequestPacket,
    *,
    schema_version: str,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "case_ref": request.case_ref,
        "draft_ref": request.draft_ref,
        "handoff_ref": request.handoff_ref,
        "item_ref": request.item_ref,
        "ok": True,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "public_output_approved": False,
        "request_schema_version": CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
        "request_sha256": _payload_sha256(request),
        "result_kind": "draft_request_validation",
        "schema_version": schema_version,
        "validation_ok": True,
    }


def draft_response_summary(
    request: KcsClaudeDraftRequestPacket,
    response: JsonPayload,
    *,
    schema_version: str,
) -> JsonDict:
    payload = response.to_json_dict()
    return {
        "auto_publish_allowed": False,
        "draft_ref": request.draft_ref,
        "draft_status": payload["draft_status"],
        "handoff_ref": request.handoff_ref,
        "ok": True,
        "provider_error_code": payload["provider_error_code"],
        "public_output_approved": False,
        "response_schema_version": CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
        "response_sha256": _payload_sha256(response),
        "result_kind": "draft_response_validation",
        "schema_version": schema_version,
        "validation_ok": True,
    }


def _synthetic_handoff_request() -> KcsClaudeHandoffRequestPacket:
    return KcsClaudeHandoffRequestPacket.from_json_dict(
        {
            "artifact_refs": {
                "reviewer_packet_ref": "",
                "reviewer_packet_sha256": "",
                "zendesk_source_ref": "",
                "zendesk_source_sha256": "",
            },
            "case_ref": "case-001",
            "handoff_purpose": "reviewer_assist_notes",
            "handoff_ref": "handoff-001",
            "item_ref": "item-001",
            "operator_override": {
                "allowed_override_modes": [],
                "operator_override_allowed": False,
                "override_status": "not_requested",
            },
            "original_article_type": ArticleType.TECHNICAL_SCR.value,
            "original_decision_status": DecisionStatus.DECISION_READY.value,
            "original_readiness_state": ReadinessState.READY_FOR_REVIEWER.value,
            "original_recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
            "provider_profile": "fake_provider",
            "safe_context": {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "blocker_codes": [],
                "reason_codes": [],
                "reviewer_only_reason_codes": [],
                "short_public_safe_summary": "Synthetic safe context.",
                "status_codes": ["decision_status_decision_ready"],
                "title_hint": "Safe synthetic title",
                "warning_codes": [],
            },
            "schema_version": CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        }
    )


def _synthetic_handoff_response(
    request: KcsClaudeHandoffRequestPacket,
) -> JsonDict:
    return {
        "auto_publish_allowed": False,
        "contains_article_draft": False,
        "handoff_ref": request.handoff_ref,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "provider_error_code": ClaudeHandoffProviderErrorCode.NONE.value,
        "provider_status": ClaudeHandoffProviderStatus.ACCEPTED.value,
        "public_output_approved": False,
        "reviewer_assist_notes": ["Reviewer should verify the safe summary."],
        "schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "structured_comments": {
            "comment_codes": ["reviewer_attention_requested"],
            "needs_reviewer_attention": True,
        },
    }


def _synthetic_draft_response(request: KcsClaudeDraftRequestPacket) -> JsonDict:
    return {
        "applicable_to": "Plesk for Linux",
        "article_type": request.original_article_type,
        "auto_publish_allowed": False,
        "draft_status": ClaudeDraftStatus.ACCEPTED.value,
        "handoff_ref": request.handoff_ref,
        "internal_only_content_present": False,
        "original_article_type": request.original_article_type,
        "original_decision_status": request.original_decision_status,
        "original_readiness_state": request.original_readiness_state,
        "original_recommended_action": request.original_recommended_action,
        "provider_error_code": ClaudeDraftProviderErrorCode.NONE.value,
        "public_output_approved": False,
        "reviewer_notes": ["Reviewer should verify the synthetic draft."],
        "schema_version": CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
        "sections": {
            "cause": "A supported product setting is disabled.",
            "resolution": "Enable the supported product setting in Plesk.",
            "symptoms": "A safe product task fails with a reusable error.",
        },
        "title": "Plesk task fails with a reusable error",
        "unsupported_claims_present": False,
        "zendesk_source_html": (
            "<h1>Plesk task fails with a reusable error</h1>"
            "<h2>Applicable to</h2><p>Plesk for Linux</p>"
            "<h2>Symptoms</h2><p>A safe product task fails.</p>"
            "<h2>Cause</h2><p>A supported product setting is disabled.</p>"
            "<h2>Resolution</h2><ol><li>Enable the setting.</li></ol>"
        ),
    }


def _payload_sha256(payload: JsonPayload) -> str:
    return sha256(dumps_payload(payload).encode("utf-8")).hexdigest()


__all__ = [
    "draft_request_summary",
    "draft_response_summary",
    "handoff_request_summary",
    "handoff_response_summary",
    "run_contract_smoke",
    "validate_draft_request_payload",
    "validate_draft_response_payload",
    "validate_handoff_request_payload",
    "validate_handoff_response_payload",
]
