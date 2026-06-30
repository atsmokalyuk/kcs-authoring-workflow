from __future__ import annotations

from types import SimpleNamespace

import kcs_adapters.desktop_workflow_status as desktop_workflow_status
from kcs_adapters import desktop_workflow
from kcs_adapters.desktop_workflow_status import (
    approved_summary_draft_request_ready,
    approved_summary_pipeline_status,
    approved_summary_reuse_search_status,
    approved_summary_reuse_was_checked,
)
from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)


def test_approved_summary_pipeline_status_is_compact() -> None:
    execution = SimpleNamespace(
        decision=SimpleNamespace(
            article_type=ArticleType.TECHNICAL_SCR.value,
            recommended_action=RecommendedAction.CREATE_CANDIDATE.value,
            status=DecisionStatus.DECISION_READY.value,
        ),
        draft_request_ready=True,
        evidence=SimpleNamespace(case_ref="case-001"),
        evidence_validation=SimpleNamespace(ok=True),
        handoff_request=SimpleNamespace(handoff_ref="handoff-candidate-001"),
        item_ref="candidate-001",
        readiness=SimpleNamespace(
            ready_for_reviewer=True,
            state=ReadinessState.READY_FOR_REVIEWER.value,
        ),
        safety=SimpleNamespace(ok=True),
    )

    status = approved_summary_pipeline_status(
        execution,
        schema_version="kcs_mcp_tool_result_v1",
        reuse_search_status="checked",
    )

    assert status["debug_code"] == "none"
    assert status["item_ref"] == "candidate-001"
    assert status["reuse_search_status"] == "checked"
    assert status["provider_calls"] is False
    assert status["writes_files"] is False


def test_approved_summary_reuse_status_accepts_top_level_and_item_flags() -> None:
    assert approved_summary_reuse_was_checked({"reuse_search_checked": True}) is True
    assert (
        approved_summary_reuse_was_checked(
            {"item": {"reuse_search_checked": True}}
        )
        is True
    )
    assert approved_summary_reuse_search_status({}) == "skipped"


def test_approved_summary_draft_request_ready_blocks_not_ready() -> None:
    assert (
        approved_summary_draft_request_ready(
            SimpleNamespace(handoff_ref="handoff-candidate-001"),
            "candidate-001",
            SimpleNamespace(ready_for_reviewer=False),
        )
        is False
    )


def test_approved_summary_draft_request_ready_blocks_invalid_request(
    monkeypatch,
) -> None:
    def fail_build_draft_request(handoff_request, **kwargs):
        raise ContractValidationError("invalid draft request")

    monkeypatch.setattr(
        desktop_workflow_status,
        "build_claude_draft_request",
        fail_build_draft_request,
    )

    assert (
        approved_summary_draft_request_ready(
            SimpleNamespace(handoff_ref="handoff-candidate-001"),
            "candidate-001",
            SimpleNamespace(ready_for_reviewer=True),
        )
        is False
    )


def test_desktop_workflow_reexports_status_helpers() -> None:
    assert (
        desktop_workflow.approved_summary_draft_request_ready
        is approved_summary_draft_request_ready
    )
    assert (
        desktop_workflow.approved_summary_pipeline_status
        is approved_summary_pipeline_status
    )
    assert (
        desktop_workflow.approved_summary_reuse_search_status
        is approved_summary_reuse_search_status
    )
    assert (
        desktop_workflow.approved_summary_reuse_was_checked
        is approved_summary_reuse_was_checked
    )
