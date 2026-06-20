"""Desktop approved-summary status and reuse helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_core.claude_draft import build_claude_draft_request
from kcs_core.claude_handoff import KcsClaudeHandoffRequestPacket
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import (
    DecisionStatus,
    KcsValidationReportPacket,
)


def approved_summary_draft_request_ready(
    handoff_request: KcsClaudeHandoffRequestPacket,
    item_ref: str,
    readiness: KcsValidationReportPacket,
) -> bool:
    """Return whether a Claude draft request can be built for this run."""

    if not readiness.ready_for_reviewer:
        return False
    try:
        build_claude_draft_request(handoff_request, draft_ref=f"draft-{item_ref}")
    except ContractValidationError:
        return False
    return True


def approved_summary_pipeline_status(
    execution: Any,
    *,
    schema_version: str,
    reuse_search_status: str,
) -> JsonDict:
    """Return compact status for an approved-summary pipeline execution."""

    decision = execution.decision
    readiness = execution.readiness
    safety = execution.safety
    evidence_validation = execution.evidence_validation
    return {
        "auto_publish_allowed": False,
        "case_ref": execution.evidence.case_ref,
        "checks": [
            {"kind": "input_validation", "ok": True},
            {"kind": "evidence_builder", "ok": True},
            {"kind": "input_safety", "ok": safety.ok},
            {"kind": "evidence_validation", "ok": evidence_validation.ok},
            {
                "kind": "decision",
                "ok": decision.status == DecisionStatus.DECISION_READY.value,
            },
            {"kind": "renderer", "ok": True},
            {"kind": "readiness", "ok": readiness.ready_for_reviewer},
            {"kind": "draft_request_ready", "ok": execution.draft_request_ready},
        ],
        "debug_code": "none",
        "draft_request_ready": execution.draft_request_ready,
        "evidence_valid": evidence_validation.ok,
        "failure_stage": "none",
        "handoff_ref": execution.handoff_request.handoff_ref,
        "input_safety_ok": safety.ok,
        "item_ref": execution.item_ref,
        "network_calls": False,
        "ok": safety.ok and readiness.ready_for_reviewer,
        "original_article_type": decision.article_type,
        "original_decision_status": decision.status,
        "original_readiness_state": readiness.state,
        "original_recommended_action": decision.recommended_action,
        "pipeline_ok": safety.ok and readiness.ready_for_reviewer,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": readiness.ready_for_reviewer,
        "result_kind": "approved_summary_pipeline",
        "reuse_search_status": reuse_search_status,
        "schema_version": schema_version,
        "validation_ok": evidence_validation.ok,
        "writes_files": False,
    }


def approved_summary_reuse_was_checked(arguments: Mapping[str, Any]) -> bool:
    """Return whether the authoring request claims reuse search was checked."""

    reuse_checked = arguments.get("reuse_search_checked")
    item = arguments.get("item")
    if reuse_checked is None and isinstance(item, Mapping):
        reuse_checked = item.get("reuse_search_checked")
    return reuse_checked is True


def approved_summary_reuse_search_status(arguments: Mapping[str, Any]) -> str:
    """Return compact reuse search status for Desktop results."""

    return "checked" if approved_summary_reuse_was_checked(arguments) else "skipped"


__all__ = [
    "approved_summary_draft_request_ready",
    "approved_summary_pipeline_status",
    "approved_summary_reuse_search_status",
    "approved_summary_reuse_was_checked",
]
