from __future__ import annotations

from kcs_adapters.desktop_draft_output import (
    compact_draft_result,
    quality_blocked_result,
    quality_blocker_gaps,
)
from kcs_core.models import ArticleType


def test_compact_draft_result_excludes_html_by_default() -> None:
    compact = compact_draft_result(
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "ok": True,
            "pipeline_ok": True,
            "ready_for_reviewer": True,
            "recommended_action": "create_candidate",
            "reuse_search_status": "checked",
            "schema_version": "kcs_mcp_tool_result_v1",
            "should_be_kcs_article": True,
        },
        {
            "bundle_ref": "reviewer-bundle-run-001",
            "html_path": (
                "local-data/reviewer-bundles/run-001/item-001/reviewer_only.html"
            ),
            "html_sha256": "a" * 64,
            "manifest_path": "local-data/reviewer-bundles/run-001/manifest.json",
        },
        include_reviewer_only_html=False,
        reviewer_only_html="<h1>Reviewer only</h1>",
    )

    assert compact["draft_generated"] is True
    assert compact["reviewer_bundle_written"] is True
    assert compact["auto_publish_allowed"] is False
    assert compact["public_output_approved"] is False
    assert "reviewer_only_html" not in compact


def test_quality_blocked_result_keeps_bundle_unwritten() -> None:
    result = {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "item_ref": "candidate-001",
        "quality_gaps": [
            {"kind": "missing_required_section", "severity": "blocker"},
            {"kind": "minor_copy_issue", "severity": "warning"},
        ],
        "reuse_search_status": "checked",
        "should_be_kcs_article": True,
    }

    blockers = quality_blocker_gaps(result)
    blocked = quality_blocked_result(
        result,
        blockers,
        schema_version="kcs_mcp_tool_result_v1",
    )

    assert blockers == [{"kind": "missing_required_section", "severity": "blocker"}]
    assert blocked["debug_code"] == "reviewer_html_quality_blocked"
    assert blocked["draft_generated"] is False
    assert blocked["reviewer_bundle_written"] is False
    assert blocked["writes_files"] is False
