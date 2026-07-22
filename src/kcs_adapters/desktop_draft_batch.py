"""Python-owned sequential draft-batch result contract."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from kcs_core.json_payload import JsonDict

BATCH_SELECTED_ITEM_MAX_ITEMS = 5
MAX_CLOSED_BLOCKER_CODES = 16
_CLOSED_BLOCKER_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,79}")
RETRYABLE_CANDIDATE_BLOCKERS = {
    "approved_summary_resolution_steps_incomplete": (
        "add_operator_confirmed_resolution_detail"
    ),
}
TERMINAL_CANDIDATE_BLOCKERS = frozenset(
    {
        "approved_summary_decision_blocked",
        "approved_summary_environment_required",
        "approved_summary_evidence_validation_blocked",
        "approved_summary_readiness_blocked",
        "approved_summary_renderer_bounds_failed",
        "approved_summary_renderer_visibility_blocked",
        "approved_summary_resolution_step_destructive",
        "approved_summary_resolution_steps_required",
        "approved_summary_safety_blocked",
        "approved_summary_supported_cause_uncertain",
        "reviewer_html_quality_blocked",
    }
)


def valid_batch_item_refs(value: object) -> bool:
    """Return whether a plural selection is non-empty, unique, and opaque."""

    return (
        isinstance(value, list)
        and bool(value)
        and len(value) <= BATCH_SELECTED_ITEM_MAX_ITEMS
        and all(isinstance(item, str) and bool(item) for item in value)
        and len(value) == len(set(value))
    )


def candidate_result_outcome(result: Mapping[str, Any]) -> str:
    """Classify one authoring result through the reviewed closed taxonomy."""

    if result.get("draft_generated") is True:
        return "completed_draft"
    debug_code = result.get("debug_code")
    retry_action = (
        RETRYABLE_CANDIDATE_BLOCKERS.get(debug_code)
        if isinstance(debug_code, str)
        else None
    )
    if (
        retry_action is not None
        and retry_action == result.get("next_required_action")
    ):
        return "blocked_retryable"
    if debug_code in TERMINAL_CANDIDATE_BLOCKERS:
        return "completed_blocked"
    return "workflow_stopped"


def candidate_outcome_ledger(
    *,
    item_ref: str,
    outcome: str,
    result: Mapping[str, Any],
) -> JsonDict:
    """Return one value-safe per-candidate outcome record."""

    ledger: JsonDict = {
        "attempted": True,
        "item_ref": item_ref,
        "outcome": outcome,
    }
    for key in (
        "article_type",
        "candidate_origin",
        "debug_code",
        "failure_stage",
        "next_required_action",
        "bundle_ref",
        "bundle_storage_hint",
        "bundle_storage_ref",
        "html_path",
        "html_sha256",
        "manifest_path",
        "recommended_action",
        "reuse_search_status",
    ):
        value = result.get(key)
        if isinstance(value, str) and value:
            ledger[key] = value
    blockers = result.get("blockers")
    closed_blockers = closed_blocker_codes(blockers)
    if closed_blockers:
        ledger["blockers"] = closed_blockers
    ledger["reviewer_bundle_written"] = (
        result.get("reviewer_bundle_written") is True
    )
    ledger["kcs_ready"] = result.get("kcs_ready") is True
    ledger["ready_for_reviewer"] = result.get("ready_for_reviewer") is True
    ledger["new_draft_created"] = (
        outcome == "completed_draft"
        and result.get("recommended_action") != "flag_existing"
    )
    ledger["presentation_status"] = _candidate_presentation_status(
        outcome=outcome,
        result=result,
    )
    ledger["writes_files"] = result.get("writes_files") is True
    return ledger


def not_attempted_candidate_outcome(item_ref: str) -> JsonDict:
    """Return a value-safe ledger entry after a workflow stop."""

    return {
        "attempted": False,
        "item_ref": item_ref,
        "outcome": "not_attempted",
    }


def batch_result(
    *,
    batch_status: str,
    candidate_outcomes: list[JsonDict],
    failure_result: Mapping[str, Any] | None,
    remaining_status: Mapping[str, Any] | None,
    schema_version: str,
    candidate_labels: Mapping[str, str] | None = None,
    semantic_item_outcomes: list[JsonDict] | None = None,
) -> JsonDict:
    """Return the bounded batch envelope and per-candidate ledger."""

    draft_generated_count = sum(
        item.get("outcome") == "completed_draft" for item in candidate_outcomes
    )
    attempted_count = sum(item.get("attempted") is True for item in candidate_outcomes)
    completed_count = sum(
        item.get("outcome") in {"completed_blocked", "completed_draft"}
        for item in candidate_outcomes
    )
    retryable_blocked_count = sum(
        item.get("outcome") == "blocked_retryable" for item in candidate_outcomes
    )
    terminal_blocked_count = sum(
        item.get("outcome") in {"completed_blocked", "workflow_stopped"}
        for item in candidate_outcomes
    )
    workflow_stopped_count = sum(
        item.get("outcome") == "workflow_stopped" for item in candidate_outcomes
    )
    new_draft_created_count = sum(
        item.get("new_draft_created") is True for item in candidate_outcomes
    )
    blocker_codes = _blocker_codes(candidate_outcomes)
    result: JsonDict = {
        "auto_publish_allowed": False,
        "automatic_item_retry_allowed": False,
        "batch_status": batch_status,
        "blockers": blocker_codes,
        "candidate_outcomes": candidate_outcomes,
        "attempted_count": attempted_count,
        "completed_count": completed_count,
        "debug_code": _batch_debug_code(failure_result, blocker_codes),
        "draft_generated": draft_generated_count > 0,
        "draft_generated_count": draft_generated_count,
        "new_draft_created_count": new_draft_created_count,
        "retryable_blocked_count": retryable_blocked_count,
        "selected_count": len(candidate_outcomes),
        "terminal_blocked_count": terminal_blocked_count,
        "failure_stage": _batch_failure_stage(failure_result),
        "manual_draft_allowed": False,
        "network_calls": False,
        "ok": batch_status == "batch_completed",
        "operator_followup": operator_followup(
            batch_status=batch_status,
            candidate_outcomes=candidate_outcomes,
            candidate_labels=candidate_labels or {},
        ),
        "pipeline_ok": batch_status == "batch_completed",
        "provider_calls": False,
        "public_output_approved": False,
        "result_kind": "draft_article_batch",
        "reviewer_bundle_written": any(
            item.get("reviewer_bundle_written") is True
            for item in candidate_outcomes
        ),
        "schema_version": schema_version,
        "validation_ok": batch_status == "batch_completed",
        "workflow_stopped_count": workflow_stopped_count,
        "writes_files": any(
            item.get("writes_files") is True for item in candidate_outcomes
        ),
    }
    _attach_failure_action(result, failure_result)
    if semantic_item_outcomes is not None:
        result["semantic_item_outcomes"] = semantic_item_outcomes
    if remaining_status is not None:
        result.update(remaining_status)
    return result


def operator_followup(
    *,
    batch_status: str,
    candidate_outcomes: list[JsonDict],
    candidate_labels: Mapping[str, str],
) -> JsonDict:
    """Return one bounded operator-facing decision for a completed batch."""

    if batch_status == "batch_stopped":
        return _stopped_operator_followup(candidate_outcomes, candidate_labels)
    reviewer_ready = [
        _followup_card(item, candidate_labels)
        for item in candidate_outcomes
        if item.get("ready_for_reviewer") is True
    ]
    completed_not_ready = [
        _followup_card(item, candidate_labels)
        for item in candidate_outcomes
        if item.get("outcome") == "completed_draft"
        and item.get("ready_for_reviewer") is not True
    ]
    retryable = [
        _followup_card(item, candidate_labels)
        for item in candidate_outcomes
        if item.get("outcome") == "blocked_retryable"
    ]
    tool_review = [
        _followup_card(item, candidate_labels)
        for item in candidate_outcomes
        if item.get("outcome") in {"completed_blocked", "workflow_stopped"}
    ]
    not_attempted = [
        _followup_card(item, candidate_labels)
        for item in candidate_outcomes
        if item.get("outcome") == "not_attempted"
    ]
    followup: JsonDict = {
        "allow_leave_blocked": False,
        "completed_not_ready_candidates": completed_not_ready,
        "not_attempted_candidates": not_attempted,
        "reviewer_ready_candidates": reviewer_ready,
        "retryable_candidates": retryable,
        "summary_candidates": [
            _followup_card(item, candidate_labels) for item in candidate_outcomes
        ],
        "tool_review_candidates": tool_review,
    }
    if tool_review:
        followup.update(
            {
                "kind": "tool_review_required",
                "prompt": (
                    "No operator action is available. Tool-side review is required "
                    "for the blocked candidates."
                ),
            }
        )
        return followup
    followup.update(
        {
            "kind": "none",
            "prompt": (
                "Retryable candidates remain blocked; no operator follow-up is "
                "required. They may be resumed later only with exact confirmed "
                "resolution or workaround steps."
                if retryable
                else "No operator follow-up is required."
            ),
        }
    )
    return followup


def _stopped_operator_followup(
    candidate_outcomes: list[JsonDict],
    candidate_labels: Mapping[str, str],
) -> JsonDict:
    blocked_outcomes = {
        "blocked_retryable",
        "completed_blocked",
        "workflow_stopped",
    }
    return {
        "allow_leave_blocked": False,
        "completed_not_ready_candidates": [],
        "kind": "tool_review_required",
        "not_attempted_candidates": [
            _followup_card(item, candidate_labels)
            for item in candidate_outcomes
            if item.get("outcome") == "not_attempted"
        ],
        "prompt": (
            "The batch stopped fail-closed. Tool-side review is required; "
            "do not retry blocked or not-attempted candidates."
        ),
        "retryable_candidates": [],
        "reviewer_ready_candidates": [
            _followup_card(item, candidate_labels)
            for item in candidate_outcomes
            if item.get("ready_for_reviewer") is True
        ],
        "summary_candidates": [
            _followup_card(item, candidate_labels) for item in candidate_outcomes
        ],
        "tool_review_candidates": [
            _followup_card(item, candidate_labels)
            for item in candidate_outcomes
            if item.get("outcome") in blocked_outcomes
        ],
    }


def _followup_card(
    item: Mapping[str, Any],
    candidate_labels: Mapping[str, str],
) -> JsonDict:
    card: JsonDict = {
        "item_ref": item["item_ref"],
        **_followup_metadata(item),
    }
    label = candidate_labels.get(item["item_ref"])
    if label:
        card["label"] = label
    if item.get("reviewer_bundle_written") is True:
        for key in ("bundle_ref", "html_path"):
            value = item.get(key)
            if isinstance(value, str) and value:
                card[key] = value
    return card


def _followup_metadata(item: Mapping[str, Any]) -> JsonDict:
    string_fields = (
        "candidate_origin",
        "debug_code",
        "next_required_action",
        "outcome",
        "presentation_status",
        "recommended_action",
        "reuse_search_status",
    )
    metadata: JsonDict = {
        key: value
        for key in string_fields
        if isinstance((value := item.get(key)), str) and value
    }
    metadata.update(
        {
            key: value
            for key in ("kcs_ready", "ready_for_reviewer")
            if isinstance((value := item.get(key)), bool)
        }
    )
    blockers = closed_blocker_codes(item.get("blockers"))
    if blockers:
        metadata["blockers"] = blockers
    return metadata


def _candidate_presentation_status(
    *,
    outcome: str,
    result: Mapping[str, Any],
) -> str:
    if outcome != "completed_draft":
        return outcome
    if result.get("recommended_action") == "flag_existing":
        return "existing_article_review"
    if result.get("kcs_ready") is True:
        return "draft_generated_kcs_ready"
    return "draft_generated_not_kcs_ready"


def _blocker_codes(candidate_outcomes: list[JsonDict]) -> list[str]:
    return closed_blocker_codes(
        [
        item["debug_code"]
        for item in candidate_outcomes
        if item.get("outcome") in {
            "blocked_retryable",
            "completed_blocked",
            "workflow_stopped",
        }
        and isinstance(item.get("debug_code"), str)
        ]
    )


def closed_blocker_codes(value: object) -> list[str]:
    """Return bounded closed blocker identifiers only."""

    if not isinstance(value, list):
        return []
    return list(
        dict.fromkeys(
            item
            for item in value
            if isinstance(item, str) and _CLOSED_BLOCKER_CODE_RE.fullmatch(item)
        )
    )[:MAX_CLOSED_BLOCKER_CODES]


def _batch_debug_code(
    failure_result: Mapping[str, Any] | None,
    blocker_codes: list[str],
) -> object:
    if failure_result is not None:
        return failure_result.get("debug_code", "batch_workflow_stopped")
    return "batch_candidate_blocked" if blocker_codes else "none"


def _batch_failure_stage(failure_result: Mapping[str, Any] | None) -> object:
    if failure_result is None:
        return "none"
    return failure_result.get("failure_stage", "unknown")


def _attach_failure_action(
    result: JsonDict,
    failure_result: Mapping[str, Any] | None,
) -> None:
    if failure_result is None:
        return
    next_required_action = failure_result.get("next_required_action")
    if isinstance(next_required_action, str) and next_required_action:
        result["next_required_action"] = next_required_action


__all__ = [
    "BATCH_SELECTED_ITEM_MAX_ITEMS",
    "RETRYABLE_CANDIDATE_BLOCKERS",
    "TERMINAL_CANDIDATE_BLOCKERS",
    "batch_result",
    "candidate_outcome_ledger",
    "candidate_result_outcome",
    "not_attempted_candidate_outcome",
    "operator_followup",
    "valid_batch_item_refs",
]
