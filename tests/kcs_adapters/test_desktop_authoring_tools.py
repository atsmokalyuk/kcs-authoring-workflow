from __future__ import annotations

from kcs_adapters.desktop_authoring_tools import DesktopAuthoringTools
from kcs_adapters.desktop_workflow import DesktopDraftWorkflow


def _authoring_tools(tmp_path):
    return DesktopAuthoringTools(
        draft_workflow=DesktopDraftWorkflow(
            provider=None,
            selection_ttl_seconds=900,
        ),
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
    )


def test_draft_article_rejects_hidden_broad_shape(tmp_path) -> None:
    result = _authoring_tools(tmp_path).draft_article(
        {"item": {"title": "Do not accept Desktop-owned item payloads."}}
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert result["pipeline_ok"] is False
    assert result["failure_stage"] == "input_validation"
    assert result["debug_code"] == "draft_article_call_shape_invalid"
    assert "reviewer_only_html" not in result


def test_draft_article_missing_provider_is_controlled(tmp_path) -> None:
    result = _authoring_tools(tmp_path).draft_article(
        {"approved_summary_text": "Approved sanitized summary for article."}
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert result["pipeline_ok"] is False
    assert result["failure_stage"] == "semantic_extraction"
    assert result["debug_code"] == "semantic_extraction_provider_unavailable"
    assert result["next_required_action"] == "configure_semantic_extraction_provider"


def test_support_behavior_instructions_shape(tmp_path) -> None:
    result = _authoring_tools(tmp_path).support_get_behavior_instructions({})

    assert result["ok"] is True
    assert result["result_kind"] == "behavior_instructions"
    assert result["should_be_kcs_article"] is True
    assert result["writes_files"] is False
