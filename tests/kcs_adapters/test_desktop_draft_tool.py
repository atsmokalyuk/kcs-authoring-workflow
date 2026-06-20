from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_adapters.desktop_draft_tool import DesktopDraftArticleTool
from kcs_adapters.desktop_workflow import DesktopDraftWorkflow
from kcs_core.json_payload import JsonDict


def _unused_authoring_callback(arguments: Mapping[str, Any]) -> JsonDict:
    raise AssertionError(f"unexpected authoring callback: {arguments!r}")


def _draft_tool(tmp_path) -> DesktopDraftArticleTool:
    return DesktopDraftArticleTool(
        draft_workflow=DesktopDraftWorkflow(
            provider=None,
            selection_ttl_seconds=900,
        ),
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
        author_approved_summary=_unused_authoring_callback,
        author_ticket=_unused_authoring_callback,
    )


def _draft_tool_with_author(
    tmp_path,
    workflow: DesktopDraftWorkflow,
    calls: list[Mapping[str, Any]],
) -> DesktopDraftArticleTool:
    def author_approved_summary(arguments: Mapping[str, Any]) -> JsonDict:
        calls.append(arguments)
        return {
            "debug_code": "stub_not_ready",
            "pipeline_ok": False,
            "ready_for_reviewer": False,
            "result_kind": "approved_summary_authoring",
            "reviewer_only_html": "<p>must not leak</p>",
        }

    return DesktopDraftArticleTool(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
        author_approved_summary=author_approved_summary,
        author_ticket=_unused_authoring_callback,
    )


def test_draft_tool_rejects_hidden_broad_shape(tmp_path) -> None:
    result = _draft_tool(tmp_path).draft_article(
        {"item_candidates": [{"title": "Desktop must not own candidates."}]}
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert result["pipeline_ok"] is False
    assert result["failure_stage"] == "input_validation"
    assert result["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in result


def test_draft_tool_missing_provider_is_controlled(tmp_path) -> None:
    result = _draft_tool(tmp_path).draft_article(
        {"approved_summary_text": "Approved sanitized summary for article."}
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert result["pipeline_ok"] is False
    assert result["failure_stage"] == "semantic_extraction"
    assert result["debug_code"] == "semantic_extraction_provider_unavailable"
    assert result["next_required_action"] == "configure_semantic_extraction_provider"


def test_draft_tool_selection_uses_pending_candidate_and_strips_html(tmp_path) -> None:
    workflow = DesktopDraftWorkflow(provider=None, selection_ttl_seconds=900)
    pending = workflow.start_pending_selection(
        [
            {
                "article_type": "technical_scr",
                "item_ref": "candidate-001",
                "title": "Selected safe item",
            }
        ],
        approved_summary_text="Approved sanitized summary.",
    )
    calls: list[Mapping[str, Any]] = []
    tool = _draft_tool_with_author(tmp_path, workflow, calls)

    result = tool.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending.selection_ref,
        }
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert result["reviewer_bundle_written"] is False
    assert "reviewer_only_html" not in result
    assert workflow.pending_selection is None
    assert calls
    assert calls[0]["approved_summary_text"] == "Approved sanitized summary."
    assert calls[0]["item"]["candidate_id"] == "candidate-001"
