from __future__ import annotations

from types import SimpleNamespace

from kcs_adapters import desktop_reviewer_preview, desktop_workflow
from kcs_adapters.desktop_reviewer_preview import (
    approved_summary_quality_gaps,
    approved_summary_reviewer_only_draft,
    approved_summary_reviewer_only_preview_text,
    safe_candidate_list,
    safe_candidate_string,
)
from kcs_core.models import ArticleType


def _execution() -> SimpleNamespace:
    return SimpleNamespace(
        arguments={"item": {"reuse_search_checked": True}},
        decision=SimpleNamespace(
            article_type=ArticleType.TECHNICAL_SCR.value,
            recommended_action="create_candidate",
        ),
        payload={
            "issue_candidates": [
                {
                    "supported_resolution_or_workaround": (
                        "Restart the affected product service."
                    )
                }
            ]
        },
        reviewer_packet=SimpleNamespace(
            public_article_candidate={
                "applicable_to": ["Plesk for Linux", "approved-summary-source-001"],
                "cause": "A product service is stopped.",
                "resolution_steps": ["Run systemctl restart product-service."],
                "symptoms": ["A Plesk feature fails."],
                "title": "Plesk feature fails",
            },
            zendesk_source_html="<h1>Plesk feature fails</h1>",
        ),
    )


def test_reviewer_only_draft_filters_internal_applicable_to_refs() -> None:
    draft = approved_summary_reviewer_only_draft(_execution())

    assert draft["applicable_to"] == ["Plesk for Linux"]
    assert draft["resolution"] == "Restart the affected product service."
    assert draft["resolution_steps"] == ["Run systemctl restart product-service."]


def test_reviewer_only_preview_text_keeps_sections() -> None:
    text = approved_summary_reviewer_only_preview_text(
        {
            "applicable_to": ["Plesk for Linux"],
            "cause": "A product service is stopped.",
            "resolution": "Restart the affected product service.",
            "resolution_steps": ["Run systemctl restart product-service."],
            "status": "reviewer_only",
            "symptoms": ["A Plesk feature fails."],
            "title": "Plesk feature fails",
        }
    )

    assert "Title: Plesk feature fails" in text
    assert "Applicable to:" in text
    assert "Resolution steps:" in text


def test_quality_gaps_use_html_quality_and_reuse_status(monkeypatch) -> None:
    monkeypatch.setattr(
        desktop_reviewer_preview,
        "review_reviewer_only_html",
        lambda html, *, require_resolution_container: [
            {"kind": "html_quality_checked", "severity": "info"}
        ],
    )

    gaps = approved_summary_quality_gaps(
        _execution(),
        {
            "applicable_to": ["Plesk for Linux"],
            "cause": "A product service is stopped.",
            "resolution": "Restart the affected product service.",
            "resolution_steps": ["Run systemctl restart product-service."],
            "symptoms": ["A Plesk feature fails."],
        },
    )

    assert {"kind": "html_quality_checked", "severity": "info"} in gaps
    assert {"kind": "reuse_search_skipped", "severity": "warning"} not in gaps


def test_quality_gaps_block_resolution_delegated_to_existing_kb() -> None:
    gaps = approved_summary_quality_gaps(
        _execution(),
        {
            "applicable_to": ["Plesk for Linux"],
            "cause": "A known product issue affects generated web configuration.",
            "resolution": (
                "Open the existing Plesk knowledge base article for bug "
                "PPPM-5892 at "
                "https://support.plesk.com/hc/en-us/articles/115001678209 "
                "and apply the documented fix."
            ),
            "resolution_steps": [
                (
                    "Open the existing Plesk knowledge base article for bug "
                    "PPPM-5892 at "
                    "https://support.plesk.com/hc/en-us/articles/115001678209 "
                    "and apply the documented fix."
                )
            ],
            "symptoms": ["Apache fails to start."],
        },
    )

    assert {
        "kind": "resolution_delegates_to_existing_kb_article",
        "severity": "blocker",
    } in gaps


def test_safe_candidate_fields_normalize_scalar_and_list_values() -> None:
    candidate = {"scalar": "value", "list": ["one", 2, "two"]}

    assert safe_candidate_string(candidate, "scalar") == "value"
    assert safe_candidate_string(candidate, "missing") == ""
    assert safe_candidate_list(candidate, "scalar") == ["value"]
    assert safe_candidate_list(candidate, "list") == ["one", "two"]


def test_desktop_workflow_reexports_reviewer_preview_helpers() -> None:
    assert (
        desktop_workflow.approved_summary_reviewer_only_draft
        is approved_summary_reviewer_only_draft
    )
    assert (
        desktop_workflow.approved_summary_quality_gaps
        is approved_summary_quality_gaps
    )
    assert desktop_workflow.safe_candidate_list is safe_candidate_list
    assert desktop_workflow.safe_candidate_string is safe_candidate_string
