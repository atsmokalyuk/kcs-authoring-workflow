from __future__ import annotations

from kcs_adapters import desktop_draft_tool
from kcs_adapters.desktop_tool_results import tool_result_text


def _completed_outcomes() -> list[dict[str, object]]:
    return [
        {
            "bundle_ref": "run-first",
            "comparison_outcome": "none_fit",
            "draft_generated": True,
            "html_path": (
                "local-data/reviewer-bundles/run-first/issue-001/"
                "reviewer_only.html"
            ),
            "item_ref": "issue-001",
            "manifest_path": (
                "local-data/reviewer-bundles/run-first/manifest.json"
            ),
            "recommended_action": "create_candidate",
            "reviewer_bundle_written": True,
        },
        {
            "bundle_ref": "run-second",
            "comparison_outcome": "none_fit",
            "draft_generated": True,
            "html_path": (
                "local-data/reviewer-bundles/run-second/issue-002/"
                "reviewer_only.html"
            ),
            "item_ref": "issue-002",
            "manifest_path": (
                "local-data/reviewer-bundles/run-second/manifest.json"
            ),
            "recommended_action": "create_candidate",
            "reviewer_bundle_written": True,
        },
    ]


def test_next_comparison_text_preserves_completed_bundle_handoff() -> None:
    text = tool_result_text(
        {
            "accepted_ticket_facts": ["Second accepted issue."],
            "comparison_candidates": [],
            "comparison_outcomes": [
                "reuse",
                "update",
                "none_fit",
                "need_more_evidence",
            ],
            "comparison_ref": "comparison-second",
            "comparison_sequence_outcomes": _completed_outcomes()[:1],
            "result_kind": "reuse_comparison_required",
            "submit_tool": "kcs_confirm_reuse_comparison",
        }
    )

    assert "Completed item results" in text
    assert text.index("issue-001") < text.index("comparison-second")
    assert "run-first" in text
    assert "local-data/reviewer-bundles/run-first/manifest.json" in text
    assert "local-data/reviewer-bundles/run-first/issue-001/reviewer_only.html" in text


def test_final_draft_text_lists_every_sequence_bundle_in_order() -> None:
    text = tool_result_text(
        {
            "auto_publish_allowed": False,
            "bundle_ref": "run-second",
            "comparison_sequence_outcomes": _completed_outcomes(),
            "draft_generated": True,
            "html_path": (
                "local-data/reviewer-bundles/run-second/issue-002/"
                "reviewer_only.html"
            ),
            "item_ref": "issue-002",
            "kcs_ready": True,
            "manifest_path": (
                "local-data/reviewer-bundles/run-second/manifest.json"
            ),
            "public_output_approved": False,
            "ready_for_reviewer": True,
            "recommended_action": "create_candidate",
            "result_kind": "draft_article_authoring",
            "reviewer_bundle_written": True,
            "reuse_search_status": "checked",
        }
    )

    assert "Ordered sequence results" in text
    sequence = text.split("Ordered sequence results:", maxsplit=1)[1]
    assert sequence.index("issue-001") < sequence.index("issue-002")
    assert "run-first" in text
    assert "run-second" in text
    assert "local-data/reviewer-bundles/run-first/manifest.json" in text
    assert "local-data/reviewer-bundles/run-second/manifest.json" in text


def test_inline_html_result_keeps_complete_sequence_handoff() -> None:
    text = tool_result_text(
        {
            "auto_publish_allowed": False,
            "comparison_sequence_outcomes": _completed_outcomes(),
            "draft_generated": True,
            "html_path": (
                "local-data/reviewer-bundles/run-second/issue-002/"
                "reviewer_only.html"
            ),
            "item_ref": "issue-002",
            "public_output_approved": False,
            "result_kind": "draft_article_authoring",
            "reviewer_only_html": "<h1>Second issue</h1>",
        }
    )

    assert "Ordered sequence results" in text
    sequence = text.split("Ordered sequence results:", maxsplit=1)[1]
    assert sequence.index("issue-001") < sequence.index("issue-002")
    assert "run-first" in text
    assert "run-second" in text


def test_sequence_ledger_carries_reviewer_artifact_paths() -> None:
    ledger = desktop_draft_tool._comparison_outcome_ledger(
        item_ref="issue-001",
        comparison_outcome="none_fit",
        result={
            "bundle_ref": "run-first",
            "draft_generated": True,
            "html_path": (
                "local-data/reviewer-bundles/run-first/issue-001/"
                "reviewer_only.html"
            ),
            "manifest_path": (
                "local-data/reviewer-bundles/run-first/manifest.json"
            ),
            "recommended_action": "create_candidate",
            "reviewer_bundle_written": True,
        },
    )

    assert ledger["bundle_ref"] == "run-first"
    assert ledger["manifest_path"] == (
        "local-data/reviewer-bundles/run-first/manifest.json"
    )
    assert ledger["html_path"] == (
        "local-data/reviewer-bundles/run-first/issue-001/reviewer_only.html"
    )
