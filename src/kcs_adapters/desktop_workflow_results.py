"""Controlled Desktop workflow result builders."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_adapters.desktop_operator_selection import (
    PendingDraftSelection,
    operator_choice_request,
    operator_choice_review_summary,
    split_candidate_cards,
)
from kcs_core.json_payload import JsonDict
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)


def semantic_provider_unavailable_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when no approved semantic provider is configured."""

    result = draft_author_failure_result(
        failure_stage="semantic_extraction",
        debug_code="semantic_extraction_provider_unavailable",
        schema_version=schema_version,
    )
    result["next_required_action"] = "configure_semantic_extraction_provider"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "configure_semantic_extraction_provider",
        "reason": "semantic_extraction_provider_unavailable",
    }
    return result


def semantic_review_required_result(
    *,
    schema_version: str,
    semantic_review_ref: str,
) -> JsonDict:
    """Return controlled result for the KCS-13 semantic-review breakpoint."""

    result = draft_author_failure_result(
        failure_stage="semantic_extraction",
        debug_code="semantic_identification_low_confidence",
        schema_version=schema_version,
    )
    result.update(
        {
            "draft_generated": False,
            "manual_draft_allowed": False,
            "next_arguments": {"semantic_review_ref": semantic_review_ref},
            "next_required_action": "prepare_semantic_review",
            "next_tool": "kcs_prepare_semantic_review",
            "reviewer_bundle_written": False,
            "semantic_review_ref": semantic_review_ref,
            "should_be_kcs_article": True,
            "workflow_state": "semantic_review_required",
        }
    )
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "prepare_semantic_review",
        "reason": "semantic_identification_low_confidence",
        "semantic_review_ref": semantic_review_ref,
        "workflow_state": "semantic_review_required",
    }
    return result


def semantic_review_metadata_blocked_result(
    *,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return controlled result when semantic-review metadata is unusable."""

    result = draft_author_failure_result(
        failure_stage="semantic_extraction",
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result.update(
        {
            "draft_generated": False,
            "manual_draft_allowed": False,
            "next_required_action": "repair_clean_ticket_metadata",
            "reviewer_bundle_written": False,
            "should_be_kcs_article": True,
            "workflow_state": "semantic_review_metadata_blocked",
        }
    )
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "repair_clean_ticket_metadata",
        "reason": debug_code,
        "workflow_state": "semantic_review_metadata_blocked",
    }
    return result


def semantic_review_prepare_failure_result(
    *,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return controlled result for invalid semantic-review prepare calls."""

    result = draft_author_failure_result(
        failure_stage="semantic_extraction",
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result.update(
        {
            "draft_generated": False,
            "manual_draft_allowed": False,
            "next_required_action": "restart_with_ticket_ref",
            "reviewer_bundle_written": False,
            "should_be_kcs_article": True,
            "workflow_state": "semantic_review_prepare_blocked",
        }
    )
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "restart_with_ticket_ref",
        "reason": debug_code,
        "workflow_state": "semantic_review_prepare_blocked",
    }
    return result


def operator_selection_unavailable_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when a second call has no pending state."""

    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code="operator_selection_invalid",
        schema_version=schema_version,
    )
    result["next_required_action"] = "restart_with_approved_summary_text"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "restart_with_approved_summary_text",
        "reason": "operator_selection_invalid",
    }
    return result


def operator_selection_expired_result(*, schema_version: str) -> JsonDict:
    """Return controlled result when pending operator selection expired."""

    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code="operator_selection_expired",
        schema_version=schema_version,
    )
    result["next_required_action"] = "restart_with_approved_summary_text"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "restart_with_approved_summary_text",
        "reason": "operator_selection_expired",
    }
    return result


def selection_error_result(
    arguments: Mapping[str, Any],
    pending_selection: PendingDraftSelection,
    *,
    schema_version: str,
    submit_tool: str,
) -> JsonDict | None:
    """Return split selection error result, or None when selection is confirmed."""

    selection_ref = arguments.get("operator_selection_ref")
    selected_item_ref = arguments.get("operator_selected_item_ref")
    choice_confirmed = arguments.get("operator_choice_confirmed")
    if (
        selection_ref == pending_selection.selection_ref
        and selected_item_ref in pending_selection.candidate_refs
        and choice_confirmed is True
    ):
        return None

    debug_code = "operator_selection_required"
    if selection_ref or selected_item_ref or choice_confirmed is not None:
        debug_code = "operator_selection_invalid"
    result = draft_author_failure_result(
        failure_stage="operator_selection",
        debug_code=debug_code,
        schema_version=schema_version,
    )
    result["automatic_item_retry_allowed"] = False
    result["item_candidates"] = list(pending_selection.item_candidate_cards)
    result["manual_draft_allowed"] = False
    result["next_required_action"] = "operator_select_single_item"
    result["operator_choice_options"] = list(pending_selection.item_candidate_cards)
    result["operator_choice_request"] = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    result["operator_choice_confirmed"] = False
    result["operator_prompt"] = (
        "The approved sanitized ticket contains multiple separately searchable "
        "KCS items. Choose one item in the native choice popup before drafting."
    )
    result["operator_prompt_style"] = "native_choice_popup"
    result["operator_selection_ref"] = pending_selection.selection_ref
    result["recommended_action"] = "split_required"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "operator_select_single_item",
        "operator_prompt_style": "native_choice_popup",
        "operator_choice_request": operator_choice_review_summary(pending_selection),
        "operator_selection_ref": pending_selection.selection_ref,
        "reason": debug_code,
    }
    return result


def split_required_result(
    candidates: list[JsonDict],
    *,
    schema_version: str,
) -> JsonDict | None:
    """Return a split-required result for multiple KCS item candidates."""

    if len(candidates) <= 1:
        return None
    result = draft_author_failure_result(
        failure_stage="item_identification",
        debug_code="multiple_kcs_items_detected",
        schema_version=schema_version,
    )
    result["item_candidates"] = split_candidate_cards(candidates)
    result["automatic_item_retry_allowed"] = False
    result["manual_draft_allowed"] = False
    result["next_required_action"] = "operator_select_single_item"
    result["operator_choice_options"] = result["item_candidates"]
    result["operator_prompt"] = (
        "The approved sanitized ticket contains multiple separately searchable "
        "KCS items. Choose which article to draft first."
    )
    result["operator_prompt_style"] = "native_choice_popup"
    result["recommended_action"] = "split_required"
    result["review_summary"] = {
        "draft_available": False,
        "next_required_action": "operator_select_single_item",
        "operator_prompt_style": "native_choice_popup",
        "reason": "multiple_kcs_items_detected",
    }
    return result


def draft_author_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
    """Return a Desktop draft authoring failure result."""

    return {
        **_workflow_failure_result(
            failure_stage=failure_stage,
            debug_code=debug_code,
            schema_version=schema_version,
        ),
        "article_type": ArticleType.NONE.value,
        "atomic_item": {},
        "blockers": [debug_code],
        "open_questions": [],
        "quality_gaps": [],
        "recommended_action": "blocked",
        "result_kind": "approved_summary_authoring",
        "review_summary": {
            "draft_available": False,
            "reason": debug_code,
        },
        "should_be_kcs_article": False,
    }


def _workflow_failure_result(
    *,
    failure_stage: str,
    debug_code: str,
    schema_version: str,
) -> JsonDict:
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


__all__ = [
    "draft_author_failure_result",
    "operator_selection_expired_result",
    "operator_selection_unavailable_result",
    "selection_error_result",
    "semantic_review_metadata_blocked_result",
    "semantic_review_prepare_failure_result",
    "semantic_review_required_result",
    "semantic_provider_unavailable_result",
    "split_required_result",
]
