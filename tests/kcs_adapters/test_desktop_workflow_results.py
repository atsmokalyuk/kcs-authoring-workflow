from __future__ import annotations

from kcs_adapters import desktop_workflow
from kcs_adapters.desktop_operator_selection import new_pending_draft_selection
from kcs_adapters.desktop_workflow_results import (
    draft_author_failure_result,
    operator_selection_expired_result,
    operator_selection_unavailable_result,
    selection_error_result,
    semantic_provider_unavailable_result,
    split_required_result,
)
from kcs_core.models import ArticleType


def _candidate(item_ref: str, title: str) -> dict[str, object]:
    return {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "item_ref": item_ref,
        "title": title,
    }


def test_semantic_provider_unavailable_result_is_controlled() -> None:
    result = semantic_provider_unavailable_result(
        schema_version="kcs_mcp_tool_result_v1"
    )

    assert result["debug_code"] == "semantic_extraction_provider_unavailable"
    assert result["next_required_action"] == "configure_semantic_extraction_provider"
    assert result["draft_request_ready"] is False
    assert "manual_draft_allowed" not in result
    assert "reviewer_only_html" not in result


def test_operator_selection_results_restart_with_summary() -> None:
    unavailable = operator_selection_unavailable_result(
        schema_version="kcs_mcp_tool_result_v1"
    )
    expired = operator_selection_expired_result(
        schema_version="kcs_mcp_tool_result_v1"
    )

    assert unavailable["debug_code"] == "operator_selection_invalid"
    assert expired["debug_code"] == "operator_selection_expired"
    assert unavailable["next_required_action"] == "restart_with_approved_summary_text"
    assert expired["next_required_action"] == "restart_with_approved_summary_text"


def test_selection_error_requires_exact_confirmed_choice() -> None:
    pending = new_pending_draft_selection(
        [_candidate("candidate-001", "Safe issue")],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    required = selection_error_result(
        {},
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_draft_article",
    )
    accepted = selection_error_result(
        {
            "operator_choice_confirmed": True,
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending.selection_ref,
        },
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_draft_article",
    )

    assert required is not None
    assert required["debug_code"] == "operator_selection_required"
    assert required["recommended_action"] == "split_required"
    assert required["manual_draft_allowed"] is False
    assert accepted is None


def test_split_required_result_is_compact_and_has_no_html() -> None:
    result = split_required_result(
        [
            _candidate("candidate-001", "First safe issue"),
            _candidate("candidate-002", "Second safe issue"),
        ],
        schema_version="kcs_mcp_tool_result_v1",
    )

    assert result is not None
    assert result["debug_code"] == "multiple_kcs_items_detected"
    assert result["recommended_action"] == "split_required"
    assert result["item_candidates"] == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-001",
            "title": "First safe issue",
        },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-002",
            "title": "Second safe issue",
        },
    ]
    assert "reviewer_only_html" not in result


def test_draft_author_failure_result_uses_blocked_contract() -> None:
    result = draft_author_failure_result(
        failure_stage="input_validation",
        debug_code="draft_article_args_invalid",
        schema_version="kcs_mcp_tool_result_v1",
    )

    assert result["article_type"] == ArticleType.NONE.value
    assert result["recommended_action"] == "blocked"
    assert result["blockers"] == ["draft_article_args_invalid"]
    assert result["ready_for_reviewer"] is False
    assert result["writes_files"] is False


def test_desktop_workflow_reexports_workflow_result_builders() -> None:
    assert (
        desktop_workflow.semantic_provider_unavailable_result
        is semantic_provider_unavailable_result
    )
    assert (
        desktop_workflow.operator_selection_unavailable_result
        is operator_selection_unavailable_result
    )
    assert (
        desktop_workflow.operator_selection_expired_result
        is operator_selection_expired_result
    )
    assert desktop_workflow.selection_error_result is selection_error_result
    assert desktop_workflow.split_required_result is split_required_result
    assert desktop_workflow.draft_author_failure_result is draft_author_failure_result
