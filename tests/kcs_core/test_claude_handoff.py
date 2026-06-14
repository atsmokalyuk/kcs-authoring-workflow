from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

import kcs_core
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    ClaudeHandoffProviderErrorCode,
    ClaudeHandoffProviderStatus,
    KcsClaudeHandoffRequestPacket,
    KcsClaudeHandoffResponsePacket,
    build_claude_handoff_request,
    submit_claude_handoff,
    validate_claude_handoff_response,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dump_json_dict
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsValidationReportPacket,
    ReadinessState,
    RecommendedAction,
    RequiredNextStep,
)


def _decision(**overrides: object) -> KcsActionDecisionPacket:
    values: dict[str, object] = {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": "item-001",
        "confidence": 0.84,
        "evidence_basis": {"source_refs": ["fixture-source-001"]},
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "status": DecisionStatus.DECISION_READY.value,
    }
    values.update(overrides)
    return KcsActionDecisionPacket(**values)  # type: ignore[arg-type]


def _validation_report(**overrides: object) -> KcsValidationReportPacket:
    values: dict[str, object] = {
        "auto_publish_allowed": False,
        "blockers": [],
        "case_ref": "case-001",
        "checks": ["readiness_checked"],
        "decision_summary": {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "auto_publish_allowed": False,
            "candidate_id": "item-001",
            "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
            "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
            "status": DecisionStatus.DECISION_READY.value,
        },
        "evidence_validation": {"blockers": [], "ok": True, "warnings": []},
        "ok": True,
        "ready_for_reviewer": True,
        "renderer_validation": {
            "blockers": [],
            "checks": ["auto_publish_allowed_false"],
            "has_public_article_candidate": True,
            "has_zendesk_source_html": True,
            "renderer_status": "zendesk_html_generated",
            "schema_version": "kcs_renderer_validation_report_v1",
            "warnings": [],
        },
        "required_next_step": RequiredNextStep.NONE.value,
        "reviewer_packet_sha256": "a" * 64,
        "state": ReadinessState.READY_FOR_REVIEWER.value,
        "warnings": ["reviewer_should_confirm_title"],
        "zendesk_source_sha256": "b" * 64,
    }
    values.update(overrides)
    return KcsValidationReportPacket(**values)  # type: ignore[arg-type]


def _request(**overrides: object) -> KcsClaudeHandoffRequestPacket:
    request = build_claude_handoff_request(
        _decision(),
        _validation_report(),
        handoff_ref="handoff-001",
        safe_context={
            "short_public_safe_summary": "Synthetic public-safe reviewer context.",
            "title_hint": "Safe synthetic title",
        },
    )
    if not overrides:
        return request
    payload = request.to_json_dict()
    payload.update(overrides)
    return KcsClaudeHandoffRequestPacket.from_json_dict(payload)


def _response_payload(
    request: KcsClaudeHandoffRequestPacket | None = None,
    **overrides: object,
) -> dict[str, object]:
    request = request or _request()
    payload: dict[str, object] = {
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
        "reviewer_assist_notes": ["Reviewer should confirm the synthetic title."],
        "schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        "structured_comments": {
            "comment_codes": ["title_review_suggested"],
            "needs_reviewer_attention": True,
        },
    }
    payload.update(overrides)
    return payload


def test_build_request_from_decision_and_readiness_without_artifact_paths() -> None:
    request = _request()
    payload = dump_json_dict(request)

    assert payload["schema_version"] == CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION
    assert payload["original_recommended_action"] == "create_candidate"
    assert payload["original_article_type"] == "technical_scr"
    assert payload["original_decision_status"] == "decision_ready"
    assert payload["original_readiness_state"] == "ready_for_reviewer"
    assert payload["provider_profile"] == "fake_provider"
    assert payload["auto_publish_allowed"] is False
    assert payload["public_output_approved"] is False
    assert payload["provider_may_decide_action"] is False
    assert payload["provider_may_generate_draft_body"] is False
    assert payload["include_full_reviewer_packet_body"] is False
    assert payload["include_full_zendesk_html"] is False
    assert payload["artifact_refs"] == {
        "reviewer_packet_ref": "",
        "reviewer_packet_sha256": "",
        "zendesk_source_ref": "",
        "zendesk_source_sha256": "",
    }
    assert "zendesk_source_html" not in repr(payload)
    assert "evidence_basis" not in repr(payload)


def test_request_accepts_safe_artifact_refs_and_hashes() -> None:
    request = build_claude_handoff_request(
        _decision(),
        _validation_report(),
        handoff_ref="handoff-001",
        artifact_refs={
            "reviewer_packet_ref": "artifact-reviewer-packet-001",
            "reviewer_packet_sha256": "c" * 64,
            "zendesk_source_ref": "artifact-zendesk-html-001",
            "zendesk_source_sha256": "d" * 64,
        },
    )

    assert request.artifact_refs["reviewer_packet_ref"] == (
        "artifact-reviewer-packet-001"
    )
    assert request.artifact_refs["zendesk_source_sha256"] == "d" * 64


def test_build_request_from_blocked_state_preserves_original_action_only() -> None:
    decision = _decision(
        article_type=ArticleType.NONE.value,
        blockers=["possible_duplicate_not_checked"],
        recommended_action=RecommendedAction.BLOCKED.value,
        status=DecisionStatus.BLOCKED.value,
    )
    report = _validation_report(
        blockers=["decision_blocked"],
        decision_summary={
            "article_type": ArticleType.NONE.value,
            "auto_publish_allowed": False,
            "candidate_id": "item-001",
            "recommended_action": RecommendedAction.BLOCKED.value,
            "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
            "status": DecisionStatus.BLOCKED.value,
        },
        ok=False,
        ready_for_reviewer=False,
        required_next_step=RequiredNextStep.FIX_EVIDENCE.value,
        renderer_validation={
            "blockers": [],
            "checks": ["auto_publish_allowed_false"],
            "has_public_article_candidate": False,
            "has_zendesk_source_html": False,
            "renderer_status": "not_run",
            "schema_version": "kcs_renderer_validation_report_v1",
            "warnings": [],
        },
        state=ReadinessState.BLOCKED.value,
        warnings=[],
    )

    request = build_claude_handoff_request(
        decision,
        report,
        handoff_ref="handoff-001",
    )

    assert request.original_recommended_action == "blocked"
    assert request.original_readiness_state == "blocked"
    assert request.safe_context["status_codes"] == [
        "decision_status_blocked",
        "readiness_state_blocked",
    ]


def test_build_request_from_split_required_state_aliases_action_like_code() -> None:
    decision = _decision(
        article_type=ArticleType.NONE.value,
        blockers=["multi_issue"],
        recommended_action=RecommendedAction.SPLIT_REQUIRED.value,
        status=DecisionStatus.SPLIT_REQUIRED.value,
    )
    report = _validation_report(
        blockers=["split_required"],
        decision_summary={
            "article_type": ArticleType.NONE.value,
            "auto_publish_allowed": False,
            "candidate_id": "item-001",
            "recommended_action": RecommendedAction.SPLIT_REQUIRED.value,
            "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
            "status": DecisionStatus.SPLIT_REQUIRED.value,
        },
        ok=False,
        ready_for_reviewer=False,
        required_next_step=RequiredNextStep.REVIEW_SPLIT_ITEMS.value,
        renderer_validation={
            "blockers": [],
            "checks": ["auto_publish_allowed_false"],
            "has_public_article_candidate": False,
            "has_zendesk_source_html": False,
            "renderer_status": "not_run",
            "schema_version": "kcs_renderer_validation_report_v1",
            "warnings": [],
        },
        state=ReadinessState.REVIEW_BLOCKED.value,
        warnings=[],
    )

    request = build_claude_handoff_request(
        decision,
        report,
        handoff_ref="handoff-001",
    )

    assert request.original_recommended_action == "split_required"
    assert request.safe_context["blocker_codes"] == [
        "multi_issue",
        "split_review_required",
    ]


@pytest.mark.parametrize("provider_profile", ["fake_provider", "approved_provider"])
def test_request_accepts_allowed_provider_profiles(provider_profile: str) -> None:
    assert (
        _request(provider_profile=provider_profile).provider_profile
        == provider_profile
    )


@pytest.mark.parametrize(
    "provider_profile",
    [
        "https://provider.example.invalid",
        "/Users/operator/provider",
        "token=SECRET",
        "claude --dangerous",
    ],
)
def test_request_rejects_unsafe_provider_profile_without_echo(
    provider_profile: str,
) -> None:
    with pytest.raises(ContractValidationError) as captured:
        _request(provider_profile=provider_profile)

    assert provider_profile not in str(captured.value)


@pytest.mark.parametrize(
    "field",
    [
        "auto_publish_allowed",
        "public_output_approved",
        "provider_may_decide_action",
        "provider_may_generate_draft_body",
        "include_full_reviewer_packet_body",
        "include_full_zendesk_html",
    ],
)
def test_request_rejects_true_safety_flags(field: str) -> None:
    with pytest.raises(ContractValidationError):
        _request(**{field: True})


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"reviewer_packet": {"safe": "shape"}},
        {"zendesk_source_html": "<h1>Should not be included</h1>"},
        {"evidence_basis": {"source_refs": ["fixture-source-001"]}},
    ],
)
def test_request_rejects_full_or_forbidden_root_fields(
    payload_patch: dict[str, object],
) -> None:
    payload = _request().to_json_dict()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)


def test_request_rejects_unknown_nested_safe_context_key_without_echo() -> None:
    payload = _request().to_json_dict()
    safe_context = dict(payload["safe_context"])  # type: ignore[arg-type]
    safe_context["raw_note"] = "safe-looking but unsupported"
    payload["safe_context"] = safe_context

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)

    assert "raw_note" not in str(captured.value)


def test_request_rejects_unknown_artifact_ref_key_without_echo() -> None:
    payload = _request().to_json_dict()
    artifact_refs = dict(payload["artifact_refs"])  # type: ignore[arg-type]
    artifact_refs["absolute_path"] = "/Users/operator/raw"
    payload["artifact_refs"] = artifact_refs

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)

    assert "absolute_path" not in str(captured.value)
    assert "/Users/operator/raw" not in str(captured.value)


@pytest.mark.parametrize(
    "safe_context_patch",
    [
        {"title_hint": "A" * 161},
        {"short_public_safe_summary": "A" * 1201},
        {"status_codes": ["safe_code"] * 51},
        {"warning_codes": ["create_candidate"]},
        {"short_public_safe_summary": "Contact person@example.com"},
    ],
)
def test_request_rejects_unsafe_or_oversized_safe_context(
    safe_context_patch: dict[str, object],
) -> None:
    payload = _request().to_json_dict()
    safe_context = dict(payload["safe_context"])  # type: ignore[arg-type]
    safe_context.update(safe_context_patch)
    payload["safe_context"] = safe_context

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)

    assert "person@example.com" not in str(captured.value)


@pytest.mark.parametrize(
    "text",
    [
        "<h1>Draft title</h1><p>Draft body</p>",
        "Symptoms: issue. Cause: supported cause. Resolution: do this.",
        "Question: How to do this? Answer: Do that.",
        "Provider recommends flag_existing.",
        "Customer reply: please run this command.",
        "zendesk_source_html: <p>draft</p>",
        "evidence_basis: {'source_refs': ['safe-ref']}",
    ],
)
def test_request_rejects_draft_action_or_full_packet_markers_in_free_text(
    text: str,
) -> None:
    payload = _request().to_json_dict()
    safe_context = dict(payload["safe_context"])  # type: ignore[arg-type]
    safe_context["short_public_safe_summary"] = text
    payload["safe_context"] = safe_context

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)

    assert text not in str(captured.value)


def test_request_rejects_safe_context_article_type_mismatch() -> None:
    payload = _request().to_json_dict()
    safe_context = dict(payload["safe_context"])  # type: ignore[arg-type]
    safe_context["article_type"] = ArticleType.HOWTO_QA.value
    payload["safe_context"] = safe_context

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "artifact_refs",
    [
        {"reviewer_packet_ref": "/Users/operator/reviewer.json"},
        {"zendesk_source_ref": "customer.example.net"},
        {"reviewer_packet_sha256": "not-a-hash"},
    ],
)
def test_request_rejects_unsafe_artifact_refs(
    artifact_refs: dict[str, object],
) -> None:
    payload = _request().to_json_dict()
    payload["artifact_refs"] = {
        **dict(payload["artifact_refs"]),  # type: ignore[arg-type]
        **artifact_refs,
    }

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)


def test_response_accepts_exact_original_metadata_echo() -> None:
    request = _request()
    response = validate_claude_handoff_response(
        _response_payload(request),
        request=request,
    )

    assert response.provider_status == "accepted"
    assert response.provider_error_code == "none"
    assert response.original_recommended_action == "create_candidate"
    assert response.auto_publish_allowed is False
    assert response.public_output_approved is False
    assert response.contains_article_draft is False


def test_response_rejects_mismatched_original_metadata() -> None:
    request = _request()
    payload = _response_payload(
        request,
        original_recommended_action=RecommendedAction.FLAG_EXISTING.value,
    )

    with pytest.raises(ContractValidationError):
        validate_claude_handoff_response(payload, request=request)


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"recommended_action": RecommendedAction.CREATE_CANDIDATE.value},
        {"proposed_action": RecommendedAction.REUSE_EXISTING.value},
        {"draft_body": "Provider attempted to draft an article."},
    ],
)
def test_response_rejects_provider_owned_action_or_draft_fields(
    payload_patch: dict[str, object],
) -> None:
    payload = _response_payload()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


def test_response_rejects_action_values_inside_structured_comments() -> None:
    payload = _response_payload(
        structured_comments={
            "comment_codes": [RecommendedAction.CREATE_CANDIDATE.value],
            "needs_reviewer_attention": True,
        }
    )

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "code",
    [
        "draft_body",
        "article_body",
        "customer_reply",
        "reviewer_packet",
        "public_article_candidate",
        "raw_comments",
    ],
)
def test_response_rejects_forbidden_label_like_comment_codes(code: str) -> None:
    payload = _response_payload(
        structured_comments={
            "comment_codes": [code],
            "needs_reviewer_attention": True,
        }
    )

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"auto_publish_allowed": True},
        {"public_output_approved": True},
        {"contains_article_draft": True},
        {"reviewer_assist_notes": ["A" * 601]},
        {"reviewer_assist_notes": ["safe note"] * 11},
        {"reviewer_assist_notes": ["Contact person@example.com"]},
        {"structured_comments": {"raw_note": "unsupported"}},
    ],
)
def test_response_rejects_unsafe_or_oversized_payload(
    payload_patch: dict[str, object],
) -> None:
    payload = _response_payload()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)

    assert "person@example.com" not in str(captured.value)
    assert "raw_note" not in str(captured.value)


@pytest.mark.parametrize(
    "note",
    [
        "<h1>Draft title</h1><p>Draft body</p>",
        "Symptoms: issue. Cause: supported cause. Resolution: do this.",
        "Question: How to do this? Answer: Do that.",
        "Provider recommends flag_existing.",
        "Customer reply: please run this command.",
        "zendesk_source_html: <p>draft</p>",
        "evidence_basis: {'source_refs': ['safe-ref']}",
    ],
)
def test_response_rejects_draft_action_or_full_packet_markers_in_notes(
    note: str,
) -> None:
    payload = _response_payload(reviewer_assist_notes=[note])

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)

    assert note not in str(captured.value)


@pytest.mark.parametrize(
    ("provider_status", "provider_error_code"),
    [
        ("accepted", "provider_failed"),
        ("failed", "none"),
        ("rejected", "none"),
        ("unknown", "none"),
        ("failed", "unknown"),
    ],
)
def test_response_enforces_status_error_invariants(
    provider_status: str,
    provider_error_code: str,
) -> None:
    payload = _response_payload(
        provider_status=provider_status,
        provider_error_code=provider_error_code,
        reviewer_assist_notes=[],
    )

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


def test_failed_response_rejects_reviewer_assist_notes() -> None:
    payload = _response_payload(
        provider_status="failed",
        provider_error_code="provider_failed",
        reviewer_assist_notes=["Even a safe note should not pass on failure."],
    )

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


def test_rejected_response_rejects_structured_comments() -> None:
    payload = _response_payload(
        provider_status="rejected",
        provider_error_code="provider_rejected_context",
        reviewer_assist_notes=[],
        structured_comments={
            "comment_codes": ["reviewer_attention_requested"],
            "needs_reviewer_attention": True,
        },
    )

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


def test_provider_exception_returns_value_safe_failed_response() -> None:
    private_value = "token=SECRET person@example.com"

    class FailingProvider:
        def submit_handoff(
            self, request: KcsClaudeHandoffRequestPacket
        ) -> Mapping[str, Any]:
            raise RuntimeError(private_value)

    response = submit_claude_handoff(_request(), provider=FailingProvider())
    payload = response.to_json_dict()

    assert response.provider_status == "failed"
    assert response.provider_error_code == "provider_failed"
    assert private_value not in repr(payload)


def test_provider_invalid_response_returns_value_safe_failed_response() -> None:
    class BadProvider:
        def submit_handoff(
            self, request: KcsClaudeHandoffRequestPacket
        ) -> Mapping[str, Any]:
            return {
                **_response_payload(request),
                "recommended_action": "create_candidate",
            }

    response = submit_claude_handoff(_request(), provider=BadProvider())

    assert response.provider_status == "failed"
    assert response.provider_error_code == "provider_response_invalid"


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"safe_context": {"title_hint": float("nan")}},
        {"artifact_refs": {1: "artifact-reviewer-packet-001"}},
    ],
)
def test_request_rejects_non_strict_json(payload_patch: dict[str, object]) -> None:
    payload = _request().to_json_dict()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffRequestPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "payload_patch",
    [
        {"reviewer_assist_notes": [float("inf")]},
        {"structured_comments": {1: "safe_code"}},
    ],
)
def test_response_rejects_non_strict_json(payload_patch: dict[str, object]) -> None:
    payload = _response_payload()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError):
        KcsClaudeHandoffResponsePacket.from_json_dict(payload)


def test_root_api_exports_kcs9b_names() -> None:
    assert kcs_core.KcsClaudeHandoffRequestPacket is KcsClaudeHandoffRequestPacket
    assert kcs_core.KcsClaudeHandoffResponsePacket is KcsClaudeHandoffResponsePacket
    assert kcs_core.build_claude_handoff_request is build_claude_handoff_request
    assert kcs_core.submit_claude_handoff is submit_claude_handoff
    assert kcs_core.validate_claude_handoff_response is (
        validate_claude_handoff_response
    )
