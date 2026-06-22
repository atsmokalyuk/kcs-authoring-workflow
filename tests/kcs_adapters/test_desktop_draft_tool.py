from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from kcs_adapters import desktop_clean_ticket_metadata
from kcs_adapters.desktop_draft_tool import DesktopDraftArticleTool
from kcs_adapters.desktop_semantic_providers import (
    SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET,
    ApprovedSummarySemanticExtractionProvider,
)
from kcs_adapters.desktop_ticket_ref import APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
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


def _write_cleanup_clean_ticket(root, *, ticket_ref: str, text: str) -> None:
    clean_dir = root / "local-data" / "approved-summaries" / ticket_ref
    clean_dir.mkdir(parents=True)
    clean_path = clean_dir / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    clean_path.write_text(text, encoding="utf-8")
    metadata_path = (
        clean_dir / desktop_clean_ticket_metadata.CLEAN_TICKET_METADATA_FILE_NAME
    )
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": (
                    desktop_clean_ticket_metadata
                    .CLEAN_TICKET_CLEANUP_FORM_METADATA_SCHEMA_VERSION
                ),
                "clean_ticket_ref": ticket_ref,
                "clean_ticket_path": str(clean_path),
                "clean_ticket_sha256": (
                    desktop_clean_ticket_metadata.clean_ticket_sha256(text)
                ),
                "confirmed_no_pii": True,
                "scan_clean": True,
                "updated_at": "2026-06-21T00:00:00Z",
                "version": 1,
                "write_target": "mvp_approved_summary",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
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


def test_draft_tool_selection_keeps_pending_candidate_after_blocker(tmp_path) -> None:
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
    assert workflow.pending_selection is pending
    assert calls
    assert calls[0]["approved_summary_text"] == "Approved sanitized summary."
    assert calls[0]["item"]["candidate_id"] == "candidate-001"


def test_draft_tool_ticket_ref_uses_approved_clean_file_source_kind(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KCS_AUTHORING_MVP_REPO_ROOT", str(tmp_path))
    text = (
        "Customer Ticket Content\n"
        "The customer reports an update failure and several follow-up errors.\n"
        "The investigation checked /etc/resolv.conf and "
        "/etc/httpd/conf/plesk.conf.d/server.conf.\n"
        "A support article was referenced at "
        "https://support.plesk.com/hc/en-us/articles/12377512781975.\n"
        "The final cause and resolution are likely present, but the transcript "
        "contains multiple issue threads and needs semantic review.\n"
    )
    _write_cleanup_clean_ticket(tmp_path, ticket_ref="ticket-clean-form", text=text)
    workflow = DesktopDraftWorkflow(
        provider=ApprovedSummarySemanticExtractionProvider(),
        selection_ttl_seconds=900,
    )
    tool = _draft_tool_with_author(tmp_path, workflow, calls=[])

    result = tool.draft_article({"ticket_ref": "ticket-clean-form"})

    assert result["failure_stage"] == "semantic_extraction"
    assert result["debug_code"] == "semantic_identification_low_confidence"
    assert result["workflow_state"] == "semantic_review_required"
    assert result["next_tool"] == "kcs_prepare_semantic_review"
    assert result["ticket_ref"] == "ticket-clean-form"


def test_draft_tool_semantic_submit_preserves_clean_file_source_kind(tmp_path) -> None:
    workflow = DesktopDraftWorkflow(provider=None, selection_ttl_seconds=900)
    approved_summary_text = (
        "Customer Ticket Content\n"
        "The ticket contains a command shown with a root shell prompt.\n"
        "# plesk repair web\n"
        "The cleaned transcript was approved by the local cleanup form."
    )
    pending = workflow.start_pending_semantic_review(
        approved_summary_text=approved_summary_text,
        ticket_ref="ticket-clean-form",
        source_kind=SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET,
    )
    calls: list[Mapping[str, Any]] = []
    tool = _draft_tool_with_author(tmp_path, workflow, calls)

    packet = tool.prepare_semantic_review(
        {"semantic_review_ref": pending.semantic_review_ref}
    )
    source_refs = packet["allowed_source_refs"]
    result = tool.submit_semantic_review(
        {
            "candidate_semantic_extraction": {
                "case_ref": packet["case_ref"],
                "extraction_source_ref": "semantic-review-submit-001",
                "items": [
                    {
                        "article_type_hint": "technical_scr",
                        "candidate_id": "candidate-001",
                        "confirmed_facts": [
                            "The ticket contains the root prompt command."
                        ],
                        "environment": {
                            "applicable_to": ["Plesk for Linux"],
                            "platform": "Plesk for Linux",
                            "product": "Plesk",
                        },
                        "kcs_item_status": "candidate_allowed",
                        "product_relation": "plesk_owned",
                        "resolution_steps": [
                            "Connect to the Plesk server via SSH.",
                            "Run the command from the ticket: # plesk repair web.",
                        ],
                        "source_refs": source_refs[:1],
                        "summary": "Plesk web server configuration repair is required",
                        "supportability": "supported",
                        "supportability_basis": "explicit_input_mention",
                        "supported_cause": (
                            "The Plesk web server configuration is broken."
                        ),
                        "supported_resolution_or_workaround": (
                            "Run the repair command shown in the ticket."
                        ),
                        "symptoms": ["Web server configuration is broken."],
                        "visibility_hint": "public_customer_safe",
                    }
                ],
                "schema_version": "candidate_semantic_extraction_v1",
                "source_refs": source_refs[:1],
            },
            "semantic_review_ref": pending.semantic_review_ref,
        }
    )

    assert result["result_kind"] == "draft_article_authoring"
    assert calls
    assert (
        calls[0]["_approved_summary_text_source"]
        == SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
    )
    assert calls[0]["approved_summary_text"] == approved_summary_text
