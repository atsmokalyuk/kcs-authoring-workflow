"""Desktop approved-summary authoring pipeline helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters import desktop_ticket_ref as _desktop_ticket_ref
from kcs_adapters.desktop_workflow import (
    ApprovedSummaryExecution,
    ApprovedSummaryPipelineHooks,
    ApprovedSummaryPipelineStageError,
    approved_summary_open_questions,
    approved_summary_pipeline_status,
    approved_summary_public_candidate,
    approved_summary_quality_gaps,
    approved_summary_reuse_search_status,
    approved_summary_reuse_was_checked,
    approved_summary_reviewer_only_draft,
    approved_summary_reviewer_only_html,
    approved_summary_reviewer_only_preview,
    approved_summary_reviewer_only_preview_text,
    execute_approved_summary_pipeline,
    safe_candidate_list,
    safe_candidate_string,
)
from kcs_adapters.desktop_workflow_results import draft_author_failure_result
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import (
    EvidenceBuildPolicy,
    build_evidence_packet_from_zendesk_export,
)
from kcs_core.json_payload import JsonDict
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
    ReadinessState,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import InputClass, SafetyGateResult, validate_evidence_safety
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.validation import EvidenceValidationResult, validate_evidence_packet

ApprovedSummaryInputError = _desktop_payload.ApprovedSummaryInputError
ApprovedSummaryPayloadArgumentError = (
    _desktop_payload.ApprovedSummaryPayloadArgumentError
)


class DesktopAuthoringArgumentError(ValueError):
    """Approved-summary argument shape error."""


def execute_pipeline(arguments: Mapping[str, Any]) -> ApprovedSummaryExecution:
    """Run the approved-summary KCS pipeline through Desktop hooks."""

    return execute_approved_summary_pipeline(
        arguments,
        hooks=ApprovedSummaryPipelineHooks(
            build_payload=_checked_approved_summary_pipeline_payload,
            build_evidence=_build_approved_summary_evidence,
            validate_safety=_validate_approved_summary_safety,
            validate_evidence=_validate_approved_summary_evidence,
            decide=_decide_approved_summary_action,
            render=_render_approved_summary_reviewer_packet,
            build_readiness=_build_approved_summary_readiness,
            item_ref=_approved_summary_pipeline_item_ref,
            short_summary=_desktop_payload.approved_summary_short_summary,
            title=_desktop_payload.approved_summary_title,
        ),
    )


def pipeline_status_result(
    execution: ApprovedSummaryExecution,
    *,
    schema_version: str,
) -> JsonDict:
    """Return compact status for a completed approved-summary pipeline run."""

    return approved_summary_pipeline_status(
        execution,
        schema_version=schema_version,
        reuse_search_status=approved_summary_reuse_search_status(
            execution.arguments
        ),
    )


def author_result(
    execution: ApprovedSummaryExecution,
    *,
    schema_version: str,
) -> JsonDict:
    """Return reviewer-only authoring result for a completed pipeline run."""

    status = pipeline_status_result(execution, schema_version=schema_version)
    draft = approved_summary_reviewer_only_draft(execution)
    return {
        **status,
        "article_type": execution.decision.article_type,
        "atomic_item": _approved_summary_atomic_item(execution),
        "blockers": [],
        "draft_sections": draft,
        "open_questions": approved_summary_open_questions(execution),
        "quality_gaps": approved_summary_quality_gaps(execution, draft),
        "recommended_action": execution.decision.recommended_action,
        "result_kind": "approved_summary_authoring",
        "review_summary": _approved_summary_review_status(execution),
        "reviewer_only_html": approved_summary_reviewer_only_html(execution),
        "reviewer_only_draft": draft,
        "reviewer_only_preview": approved_summary_reviewer_only_preview(draft),
        "reviewer_only_preview_text": approved_summary_reviewer_only_preview_text(
            draft
        ),
        "should_be_kcs_article": _approved_summary_should_be_article(execution),
    }


def author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return controlled approved-summary authoring failure."""

    return draft_author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=schema_version,
    )


def ticket_author_failure_result(
    *,
    ticket_ref: str,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return controlled approved-ticket authoring failure."""

    result = author_failure_result(
        failure_stage=failure_stage,
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result["result_kind"] = "approved_ticket_authoring"
    result["ticket_ref"] = ticket_ref
    result["approved_summary_source"] = "local_approved_summary"
    if debug_code in {
        "approved_ticket_ref_invalid",
        "approved_ticket_summary_invalid",
        "approved_ticket_summary_not_found",
    }:
        result["automatic_item_retry_allowed"] = True
        result["manual_draft_allowed"] = False
        result["next_required_action"] = (
            "retry_with_approved_summary_text_from_attachment"
        )
        result["review_summary"] = {
            "draft_available": False,
            "next_required_action": (
                "retry_with_approved_summary_text_from_attachment"
            ),
            "reason": debug_code,
        }
    return result


def pipeline_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return compact approved-summary pipeline failure status."""

    stage_order = {
        "input_validation": 0,
        "item_identification": 0,
        "operator_selection": 0,
        "semantic_extraction": 0,
        "evidence_builder": 1,
        "input_safety": 2,
        "evidence_validation": 3,
        "decision": 4,
        "renderer": 5,
        "readiness": 6,
        "draft_request_ready": 7,
    }
    failed_index = stage_order.get(failure_stage, len(stage_order))

    def stage_passed(stage: str) -> bool:
        return stage_order[stage] < failed_index

    return {
        "auto_publish_allowed": False,
        "case_ref": "approved-summary-case-001",
        "checks": [
            {"kind": "input_validation", "ok": stage_passed("input_validation")},
            {"kind": "evidence_builder", "ok": stage_passed("evidence_builder")},
            {"kind": "input_safety", "ok": stage_passed("input_safety")},
            {
                "kind": "evidence_validation",
                "ok": stage_passed("evidence_validation"),
            },
            {"kind": "decision", "ok": stage_passed("decision")},
            {"kind": "renderer", "ok": stage_passed("renderer")},
            {"kind": "readiness", "ok": stage_passed("readiness")},
            {
                "kind": "draft_request_ready",
                "ok": stage_passed("draft_request_ready"),
            },
        ],
        "debug_code": debug_code,
        "draft_request_ready": False,
        "evidence_valid": stage_passed("evidence_validation"),
        "failure_stage": failure_stage,
        "input_safety_ok": stage_passed("input_safety"),
        "network_calls": False,
        "ok": False,
        "original_article_type": ArticleType.NONE.value,
        "original_decision_status": DecisionStatus.BLOCKED.value,
        "original_readiness_state": ReadinessState.BLOCKED.value,
        "original_recommended_action": RecommendedAction.BLOCKED.value,
        "pipeline_ok": False,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": False,
        "result_kind": "approved_summary_pipeline",
        "schema_version": schema_version,
        "validation_ok": False,
        "writes_files": False,
    }


def ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    """Return approved-summary authoring arguments loaded from a ticket ref."""

    try:
        return _desktop_ticket_ref.approved_ticket_author_arguments(arguments)
    except ApprovedSummaryInputError as exc:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code=exc.debug_code,
        ) from None
    except (ContractValidationError, DesktopAuthoringArgumentError):
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code="approved_ticket_summary_invalid",
        ) from None


def ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    """Return the safe approved ticket ref from authoring arguments."""

    return _desktop_ticket_ref.approved_ticket_ref_from_arguments(arguments)


def _checked_approved_summary_pipeline_payload(
    arguments: Mapping[str, Any],
) -> JsonDict:
    try:
        return _desktop_payload.approved_summary_pipeline_payload(arguments)
    except ApprovedSummaryInputError as exc:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code=exc.debug_code,
        ) from None
    except ApprovedSummaryPayloadArgumentError:
        raise DesktopAuthoringArgumentError(
            "Invalid approved summary arguments."
        ) from None
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_validation",
            debug_code="approved_summary_input_invalid",
        ) from None


def _approved_summary_pipeline_item_ref(
    arguments: Mapping[str, Any],
    decision: KcsActionDecisionPacket,
) -> str:
    return decision.candidate_id or _desktop_payload.approved_summary_item_ref(
        arguments
    )


def _approved_summary_should_be_article(
    execution: ApprovedSummaryExecution,
) -> bool:
    return (
        execution.decision.status == DecisionStatus.DECISION_READY.value
        and execution.decision.recommended_action
        in {
            RecommendedAction.CREATE_CANDIDATE.value,
            RecommendedAction.UPDATE_EXISTING.value,
            RecommendedAction.FLAG_EXISTING.value,
        }
    )


def _approved_summary_atomic_item(
    execution: ApprovedSummaryExecution,
) -> JsonDict:
    candidate = approved_summary_public_candidate(execution.reviewer_packet)
    symptoms = safe_candidate_list(candidate, "symptoms")
    return {
        "item_ref": execution.item_ref,
        "summary": safe_candidate_string(candidate, "summary")
        or (symptoms[0] if symptoms else ""),
        "title": safe_candidate_string(candidate, "title"),
    }


def _approved_summary_review_status(
    execution: ApprovedSummaryExecution,
) -> JsonDict:
    return {
        "draft_request_ready": execution.draft_request_ready,
        "readiness_state": execution.readiness.state,
        "recommended_action": execution.decision.recommended_action,
        "review_required": execution.reviewer_packet.review_required,
    }


def _build_approved_summary_evidence(
    arguments: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> NormalizedTicketEvidencePacket:
    try:
        return build_evidence_packet_from_zendesk_export(
            payload,
            case_ref=_desktop_payload.approved_summary_case_ref(arguments),
            policy=EvidenceBuildPolicy(
                input_class=InputClass.OPERATOR_SANITIZED_SUMMARY.value,
                assume_sanitized=True,
            ),
        )
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_builder",
            debug_code="approved_summary_evidence_build_failed",
        ) from None


def _validate_approved_summary_safety(
    evidence: NormalizedTicketEvidencePacket,
) -> SafetyGateResult:
    try:
        safety = validate_evidence_safety(evidence)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_safety",
            debug_code="approved_summary_safety_failed",
        ) from None
    if not safety.ok:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="input_safety",
            debug_code="approved_summary_safety_blocked",
        )
    return safety


def _validate_approved_summary_evidence(
    evidence: NormalizedTicketEvidencePacket,
) -> EvidenceValidationResult:
    try:
        evidence_validation = validate_evidence_packet(evidence)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_validation",
            debug_code="approved_summary_evidence_validation_failed",
        ) from None
    if not evidence_validation.ok:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="evidence_validation",
            debug_code="approved_summary_evidence_validation_blocked",
        )
    return evidence_validation


def _decide_approved_summary_action(
    arguments: Mapping[str, Any],
    evidence: NormalizedTicketEvidencePacket,
) -> KcsActionDecisionPacket:
    try:
        decision = decide_kcs_action(
            evidence, _approved_summary_reuse_results(arguments)
        )
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="decision",
            debug_code="approved_summary_decision_failed",
        ) from None
    if decision.status != DecisionStatus.DECISION_READY.value:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="decision",
            debug_code="approved_summary_decision_blocked",
        )
    return decision


def _render_approved_summary_reviewer_packet(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
) -> KcsReviewerPacket:
    try:
        return render_reviewer_packet(evidence, decision)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="renderer",
            debug_code="approved_summary_renderer_failed",
        ) from None


def _build_approved_summary_readiness(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    reviewer_packet: KcsReviewerPacket,
) -> KcsValidationReportPacket:
    try:
        readiness = build_validation_report(evidence, decision, reviewer_packet)
    except ContractValidationError:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="readiness",
            debug_code="approved_summary_readiness_failed",
        ) from None
    if not readiness.ready_for_reviewer:
        raise ApprovedSummaryPipelineStageError(
            failure_stage="readiness",
            debug_code="approved_summary_readiness_blocked",
        )
    return readiness


def _approved_summary_reuse_results(
    arguments: Mapping[str, Any],
) -> ReuseSearchResultsPacket:
    reuse_checked = approved_summary_reuse_was_checked(arguments)
    return ReuseSearchResultsPacket(
        search_run_ref=_approved_summary_reuse_search_run_ref(arguments),
        searched=True,
        search_source=(
            "operator_approved_summary"
            if reuse_checked
            else "operator_approved_summary_reuse_skipped"
        ),
        matches=[],
        blockers=[],
    )


def _approved_summary_reuse_search_run_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("reuse_search_run_ref")
    item = _desktop_payload.approved_summary_optional_item_object(arguments)
    if value is None and item is not None:
        value = item.get("reuse_search_run_ref")
    if isinstance(value, str) and value.strip():
        ensure_safe_sanitized_payload(value)
        return value.strip()
    return "operator-approved-summary-reuse-skipped"


__all__ = [
    "DesktopAuthoringArgumentError",
    "author_failure_result",
    "author_result",
    "execute_pipeline",
    "pipeline_failure_result",
    "pipeline_status_result",
    "ticket_author_arguments",
    "ticket_author_failure_result",
    "ticket_ref_from_arguments",
]
