from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import kcs_core
from kcs_core.claude_draft import (
    CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION,
    ClaudeDraftProviderErrorCode,
    ClaudeDraftStatus,
    KcsClaudeDraftRequestPacket,
    KcsClaudeDraftResponsePacket,
    KcsReviewerOnlyDraftArtifact,
    build_claude_draft_request,
    build_reviewer_only_draft_artifact,
    submit_claude_draft_request,
    validate_claude_draft_response,
    write_reviewer_only_draft_artifact,
)
from kcs_core.claude_handoff import build_claude_handoff_request
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dump_json_dict, dumps_payload
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    OperatorOverrideMode,
    OverrideStatus,
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


def _handoff_request(
    *,
    action: RecommendedAction = RecommendedAction.CREATE_CANDIDATE,
    article_type: ArticleType = ArticleType.TECHNICAL_SCR,
    readiness_state: ReadinessState = ReadinessState.READY_FOR_REVIEWER,
    decision_status: DecisionStatus = DecisionStatus.DECISION_READY,
) -> Any:
    decision = _decision(
        article_type=article_type.value,
        recommended_action=action.value,
        status=decision_status.value,
    )
    report_overrides: dict[str, object] = {
        "decision_summary": {
            "article_type": article_type.value,
            "auto_publish_allowed": False,
            "candidate_id": "item-001",
            "recommended_action": action.value,
            "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
            "status": decision_status.value,
        },
        "state": readiness_state.value,
    }
    if readiness_state != ReadinessState.READY_FOR_REVIEWER:
        report_overrides.update(
            {
                "blockers": ["decision_blocked"],
                "ok": False,
                "ready_for_reviewer": False,
                "required_next_step": RequiredNextStep.FIX_EVIDENCE.value,
            }
        )
    return build_claude_handoff_request(
        decision,
        _validation_report(**report_overrides),
        handoff_ref="handoff-001",
        safe_context={
            "short_public_safe_summary": "Synthetic public-safe reviewer context.",
            "title_hint": "Safe synthetic title",
        },
    )


def _request(**overrides: object) -> KcsClaudeDraftRequestPacket:
    request = build_claude_draft_request(
        _handoff_request(),
        draft_ref="draft-001",
    )
    if not overrides:
        return request
    payload = request.to_json_dict()
    payload.update(overrides)
    return KcsClaudeDraftRequestPacket.from_json_dict(payload)


def _response_payload(
    request: KcsClaudeDraftRequestPacket | None = None,
    **overrides: object,
) -> dict[str, object]:
    request = request or _request()
    payload: dict[str, object] = {
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
        "reviewer_notes": ["Reviewer should confirm the synthetic title."],
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
    payload.update(overrides)
    return payload


def test_build_draft_request_from_valid_handoff() -> None:
    request = build_claude_draft_request(_handoff_request(), draft_ref="draft-001")
    payload = dump_json_dict(request)

    assert payload["schema_version"] == CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION
    assert payload["original_recommended_action"] == "create_candidate"
    assert payload["original_article_type"] == "technical_scr"
    assert payload["original_readiness_state"] == "ready_for_reviewer"
    assert payload["auto_publish_allowed"] is False
    assert payload["public_output_approved"] is False
    assert payload["provider_may_decide_action"] is False
    assert "evidence_basis" not in repr(payload)
    assert "zendesk_source_html" not in repr(payload)


@pytest.mark.parametrize(
    "action",
    [
        RecommendedAction.CREATE_CANDIDATE,
        RecommendedAction.UPDATE_EXISTING,
        RecommendedAction.FLAG_EXISTING,
    ],
)
def test_article_output_actions_are_draft_eligible(action: RecommendedAction) -> None:
    request = build_claude_draft_request(
        _handoff_request(action=action),
        draft_ref="draft-001",
    )

    assert request.original_recommended_action == action.value


@pytest.mark.parametrize(
    "action",
    [
        RecommendedAction.REUSE_EXISTING,
        RecommendedAction.NO_ARTICLE,
        RecommendedAction.BLOCKED,
        RecommendedAction.SPLIT_REQUIRED,
    ],
)
def test_non_article_output_actions_reject_draft_request(
    action: RecommendedAction,
) -> None:
    with pytest.raises(ContractValidationError):
        build_claude_draft_request(
            _handoff_request(action=action, article_type=ArticleType.NONE),
            draft_ref="draft-001",
        )


def test_non_ready_state_rejects_draft_request() -> None:
    with pytest.raises(ContractValidationError):
        build_claude_draft_request(
            _handoff_request(readiness_state=ReadinessState.BLOCKED),
            draft_ref="draft-001",
        )


def test_draft_request_rejects_unsafe_nested_context_without_echo() -> None:
    private_value = "person@example.com"
    payload = _request().to_json_dict()
    context = dict(payload["safe_drafting_context"])  # type: ignore[arg-type]
    context["raw_note"] = private_value
    payload["safe_drafting_context"] = context

    with pytest.raises(ContractValidationError) as captured:
        KcsClaudeDraftRequestPacket.from_json_dict(payload)

    assert private_value not in str(captured.value)


def test_draft_request_rejects_absolute_artifact_path() -> None:
    payload = _request().to_json_dict()
    artifact_refs = dict(payload["artifact_refs"])  # type: ignore[arg-type]
    artifact_refs["reviewer_packet_ref"] = "/Users/operator/raw"
    payload["artifact_refs"] = artifact_refs

    with pytest.raises(ContractValidationError):
        KcsClaudeDraftRequestPacket.from_json_dict(payload)


def test_draft_request_accepts_explicit_reviewer_only_override_metadata() -> None:
    decision = _decision(
        allowed_override_modes=[OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value],
        operator_override_allowed=True,
        override_status=OverrideStatus.NOT_REQUESTED.value,
    )
    handoff_request = build_claude_handoff_request(
        decision,
        _validation_report(),
        handoff_ref="handoff-001",
        safe_context={
            "short_public_safe_summary": "Synthetic public-safe reviewer context.",
            "title_hint": "Safe synthetic title",
        },
    )

    request = build_claude_draft_request(handoff_request, draft_ref="draft-001")

    assert request.operator_override["operator_override_allowed"] is True
    assert request.operator_override["allowed_override_modes"] == [
        "reviewer_only_draft"
    ]
    assert request.public_output_approved is False


@pytest.mark.parametrize(
    "payload_patch",
    [
        {
            "safe_drafting_context": {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "score": float("nan"),
            }
        },
        {"safe_drafting_context": {1: "safe"}},
        {
            "safe_drafting_context": {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title_hint": "x" * 50_000,
            }
        },
    ],
)
def test_draft_request_rejects_malformed_json_or_size(
    payload_patch: dict[str, object],
) -> None:
    payload = _request().to_json_dict()
    payload.update(payload_patch)

    with pytest.raises(ContractValidationError):
        KcsClaudeDraftRequestPacket.from_json_dict(payload)


def test_valid_response_accepts_reviewer_only_draft() -> None:
    request = _request()
    response = validate_claude_draft_response(
        _response_payload(request),
        request=request,
    )

    assert response.draft_status == ClaudeDraftStatus.ACCEPTED.value
    assert response.auto_publish_allowed is False
    assert response.public_output_approved is False
    assert response.zendesk_source_html


@pytest.mark.parametrize(
    "override",
    [
        {"recommended_action": RecommendedAction.FLAG_EXISTING.value},
        {"auto_publish_allowed": True},
        {"public_output_approved": True},
        {"unsupported_claims_present": True},
        {"internal_only_content_present": True},
        {"article_type": ArticleType.HOWTO_QA.value},
        {"reviewer_notes": ["Customer reply: please run this command."]},
    ],
)
def test_response_rejects_forbidden_or_mismatched_output(
    override: dict[str, object],
) -> None:
    request = _request()
    payload = _response_payload(request, **override)

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(payload, request=request)


def test_response_rejects_mismatched_original_action() -> None:
    request = _request()
    payload = _response_payload(
        request,
        original_recommended_action=RecommendedAction.UPDATE_EXISTING.value,
    )

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(payload, request=request)


@pytest.mark.parametrize(
    "sections",
    [
        {"cause": "Cause.", "resolution": "Resolution."},
        {"symptoms": "Symptoms.", "resolution": "Resolution."},
        {"symptoms": "Symptoms.", "cause": "Cause."},
        {
            "symptoms": "Symptoms.",
            "cause": "Cause.",
            "resolution": "Resolution.",
            "raw_note": "safe",
        },
    ],
)
def test_technical_response_requires_scr_sections(sections: dict[str, object]) -> None:
    request = _request()

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, sections=sections),
            request=request,
        )


def test_howto_response_requires_question_answer() -> None:
    request = build_claude_draft_request(
        _handoff_request(article_type=ArticleType.HOWTO_QA),
        draft_ref="draft-001",
    )
    payload = _response_payload(
        request,
        applicable_to="",
        article_type=ArticleType.HOWTO_QA.value,
        sections={"question": "How to enable the safe setting?"},
        zendesk_source_html=(
            "<h1>How to enable the safe setting?</h1>"
            "<h2>Question</h2><p>How to enable it?</p>"
        ),
    )

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(payload, request=request)


@pytest.mark.parametrize(
    "html",
    [
        "<script>alert(1)</script>",
        '<p onerror="alert(1)">Unsafe</p>',
        '<iframe src="safe"></iframe>',
        '<img src="safe">',
        '<a href="https://customer.example.net/private">private</a>',
        '<a href="public-doc"><strong>broken</a></strong>',
        "<h2>Environment</h2><p>Plesk</p>",
    ],
)
def test_response_rejects_unsafe_html(html: str) -> None:
    request = _request()

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, zendesk_source_html=html),
            request=request,
        )


@pytest.mark.parametrize(
    "html",
    [
        "<p>person&#64;customer&#46;example&#46;net</p>",
        "<p>10&#46;0&#46;0&#46;1</p>",
        "<p>PLSK&#45;12345678&#45;1234</p>",
    ],
)
def test_response_rejects_entity_encoded_private_values_in_html(
    html: str,
) -> None:
    request = _request()

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, zendesk_source_html=html),
            request=request,
        )


def test_response_rejects_html_comments() -> None:
    request = _request()
    html = "<h1>Safe title</h1><!-- hidden provider content --><p>Safe text</p>"

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, zendesk_source_html=html),
            request=request,
        )


@pytest.mark.parametrize(
    "html",
    [
        "<p>PLSK-<strong>12345678-1234</strong></p>",
        "<p>10.<strong>0.0</strong>.1</p>",
        "<p>ticket-<strong>123456</strong></p>",
        "<p>flag_<strong>existing</strong></p>",
    ],
)
def test_response_rejects_split_private_or_action_values_in_html(
    html: str,
) -> None:
    request = _request()

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, zendesk_source_html=html),
            request=request,
        )


@pytest.mark.parametrize(
    "override",
    [
        {"reviewer_notes": ["Provider recommends flag_existing."]},
        {
            "sections": {
                "cause": "Provider recommends flag_existing.",
                "resolution": "Enable the supported product setting.",
                "symptoms": "A safe product task fails with a reusable error.",
            }
        },
        {
            "zendesk_source_html": (
                "<h1>Safe title</h1>"
                "<p>Recommended action: flag_existing</p>"
            )
        },
    ],
)
def test_response_rejects_provider_owned_action_in_text(
    override: dict[str, object],
) -> None:
    request = _request()

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(
            _response_payload(request, **override),
            request=request,
        )


def test_provider_failure_is_value_safe_without_echo() -> None:
    private_value = "token=SECRET person@example.com"

    class FailingProvider:
        def propose_draft(self, request: KcsClaudeDraftRequestPacket) -> object:
            raise RuntimeError(private_value)

    response = submit_claude_draft_request(_request(), provider=FailingProvider())
    payload = response.to_json_dict()

    assert payload["draft_status"] == "failed"
    assert payload["provider_error_code"] == "provider_failed"
    assert private_value not in repr(payload)


def test_invalid_provider_response_returns_safe_failure() -> None:
    private_value = "person@example.com"

    class InvalidProvider:
        def propose_draft(
            self, request: KcsClaudeDraftRequestPacket
        ) -> Mapping[str, Any]:
            return _response_payload(request, title=private_value)

    response = submit_claude_draft_request(_request(), provider=InvalidProvider())

    assert response.draft_status == "failed"
    assert response.provider_error_code == "provider_response_invalid"
    assert private_value not in repr(response.to_json_dict())


def test_non_object_provider_response_returns_safe_failure() -> None:
    class InvalidProvider:
        def propose_draft(self, request: KcsClaudeDraftRequestPacket) -> object:
            return ["not", "an", "object"]

    response = submit_claude_draft_request(_request(), provider=InvalidProvider())

    assert response.draft_status == "failed"
    assert response.provider_error_code == "provider_response_invalid"


def test_provider_response_cannot_choose_output_path() -> None:
    request = _request()
    payload = _response_payload(request)
    payload["output_path"] = "artifact-001"

    with pytest.raises(ContractValidationError):
        validate_claude_draft_response(payload, request=request)


def test_build_and_write_reviewer_only_draft_artifact(tmp_path: Path) -> None:
    request = _request()
    response = validate_claude_draft_response(
        _response_payload(request),
        request=request,
    )
    artifact = build_reviewer_only_draft_artifact(
        request,
        response,
        artifact_ref="artifact-001",
    )
    path = write_reviewer_only_draft_artifact(artifact, tmp_path / "draft-output")

    payload = KcsReviewerOnlyDraftArtifact.from_json_dict(
        _load_json(path)
    ).to_json_dict()
    assert payload["schema_version"] == REVIEWER_ONLY_DRAFT_ARTIFACT_SCHEMA_VERSION
    assert payload["reviewer_only"] is True
    assert payload["auto_publish_allowed"] is False
    assert payload["public_output_approved"] is False
    assert payload["original_recommended_action"] == "create_candidate"
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ContractValidationError):
        KcsReviewerPacket.from_json_dict(payload)
    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_artifact_rejects_embedded_response_metadata_mismatch() -> None:
    request = _request()
    response = validate_claude_draft_response(
        _response_payload(request),
        request=request,
    )
    artifact = build_reviewer_only_draft_artifact(
        request,
        response,
        artifact_ref="artifact-001",
    )
    payload = artifact.to_json_dict()
    draft_response = dict(payload["draft_response"])  # type: ignore[arg-type]
    draft_response["original_recommended_action"] = (
        RecommendedAction.UPDATE_EXISTING.value
    )
    mutated_response = KcsClaudeDraftResponsePacket.from_json_dict(draft_response)
    payload["draft_response"] = mutated_response.to_json_dict()
    payload["draft_response_sha256"] = sha256(
        dumps_payload(mutated_response).encode("utf-8")
    ).hexdigest()

    with pytest.raises(ContractValidationError):
        KcsReviewerOnlyDraftArtifact.from_json_dict(payload)


def test_artifact_writer_rejects_overwrite_and_symlink(tmp_path: Path) -> None:
    request = _request()
    response = validate_claude_draft_response(
        _response_payload(request),
        request=request,
    )
    artifact = build_reviewer_only_draft_artifact(
        request,
        response,
        artifact_ref="artifact-001",
    )
    output_dir = tmp_path / "draft-output"
    write_reviewer_only_draft_artifact(artifact, output_dir)

    with pytest.raises(ContractValidationError):
        write_reviewer_only_draft_artifact(artifact, output_dir)

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ContractValidationError):
        write_reviewer_only_draft_artifact(artifact, link)

    with pytest.raises(ContractValidationError):
        write_reviewer_only_draft_artifact(artifact, tmp_path / ".." / "outside")


def test_root_exports_include_kcs_9c_api() -> None:
    assert kcs_core.KcsClaudeDraftRequestPacket is KcsClaudeDraftRequestPacket
    assert kcs_core.KcsClaudeDraftResponsePacket is KcsClaudeDraftResponsePacket
    assert kcs_core.KcsReviewerOnlyDraftArtifact is KcsReviewerOnlyDraftArtifact
    assert kcs_core.build_claude_draft_request is build_claude_draft_request
    assert kcs_core.write_reviewer_only_draft_artifact is (
        write_reviewer_only_draft_artifact
    )


def _load_json(path: Path) -> dict[str, Any]:
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data
