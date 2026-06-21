from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import kcs_adapters.desktop_workflow as desktop_workflow
import kcs_adapters.desktop_workflow_status as desktop_workflow_status
from kcs_adapters.desktop_workflow import (
    ApprovedSummaryPipelineHooks,
    DesktopDraftWorkflow,
    OperatorSelectionExpiredError,
    SemanticExtractionProviderUnavailableError,
    UnavailableSemanticExtractionProvider,
    approved_summary_pipeline_status,
    approved_summary_quality_gaps,
    approved_summary_reuse_search_status,
    approved_summary_reviewer_only_draft,
    approved_summary_reviewer_only_preview,
    approved_summary_reviewer_only_preview_text,
    attach_pending_selection,
    compact_draft_result,
    execute_approved_summary_pipeline,
    finalize_author_result_with_bundle,
    operator_choice_request,
    operator_choice_review_summary,
    quality_blocked_result,
    quality_blocker_gaps,
    selection_error_result,
    semantic_provider_from_environment,
    split_required_result,
)
from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    ReadinessState,
    RecommendedAction,
)
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    KcsItemStatus,
    ProductRelation,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
)


class _Provider:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.contexts: list[dict[str, object]] = []

    def propose_candidates(self, context):
        self.contexts.append(dict(context))
        return self.payload


def _extraction_payload() -> dict[str, object]:
    return {
        "case_ref": "desktop-workflow-case-001",
        "extraction_source_ref": "desktop-workflow-run-001",
        "items": [
            {
                "article_type_hint": ArticleType.TECHNICAL_SCR.value,
                "candidate_id": "candidate-001",
                "confirmed_facts": ["A safe Plesk fact is confirmed."],
                "environment": {
                    "applicable_to": ["Plesk for Linux"],
                    "platform": "Plesk for Linux",
                },
                "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
                "product_relation": ProductRelation.PLESK_OWNED.value,
                "resolution_steps": ["Run systemctl restart product-service."],
                "source_refs": ["desktop-workflow-source-item-001"],
                "summary": "Plesk task has a safe synthetic issue",
                "supportability": Supportability.SUPPORTED.value,
                "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
                "supported_cause": "A required product service is stopped.",
                "supported_resolution_or_workaround": (
                    "Restart the required product service."
                ),
                "symptoms": ["A safe Plesk task fails."],
                "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
            }
        ],
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": ["desktop-workflow-source-001"],
    }


def _desktop_candidate(item_ref: str, title: str) -> dict[str, object]:
    return {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "item_ref": item_ref,
        "summary": title,
        "title": title,
    }


def test_execute_approved_summary_pipeline_owns_stage_order(monkeypatch) -> None:
    calls: list[str] = []
    evidence = SimpleNamespace(case_ref="case-001")
    safety = SimpleNamespace(ok=True)
    evidence_validation = SimpleNamespace(ok=True)
    decision = SimpleNamespace(
        article_type=ArticleType.TECHNICAL_SCR.value,
        candidate_id="candidate-001",
        recommended_action=RecommendedAction.CREATE_CANDIDATE.value,
        status=DecisionStatus.DECISION_READY.value,
    )
    reviewer_packet = SimpleNamespace(review_required=True)
    readiness = SimpleNamespace(
        ready_for_reviewer=True,
        state=ReadinessState.READY_FOR_REVIEWER.value,
    )

    def fake_handoff_request(decision_arg, readiness_arg, **kwargs):
        calls.append("handoff")
        assert decision_arg is decision
        assert readiness_arg is readiness
        assert kwargs["handoff_ref"] == "handoff-candidate-001"
        assert kwargs["safe_context"] == {
            "short_public_safe_summary": "short summary",
            "title_hint": "Title hint",
        }
        return SimpleNamespace(handoff_ref="handoff-candidate-001")

    def fake_draft_request(handoff_request, **kwargs):
        calls.append("draft_ready")
        assert handoff_request.handoff_ref == "handoff-candidate-001"
        assert kwargs == {"draft_ref": "draft-candidate-001"}
        return SimpleNamespace(draft_ref="draft-candidate-001")

    monkeypatch.setattr(
        desktop_workflow,
        "build_claude_handoff_request",
        fake_handoff_request,
    )
    monkeypatch.setattr(
        desktop_workflow_status,
        "build_claude_draft_request",
        fake_draft_request,
    )

    execution = execute_approved_summary_pipeline(
        {"approved_summary_text": "Approved sanitized summary."},
        hooks=ApprovedSummaryPipelineHooks(
            build_payload=lambda arguments: (
                calls.append("payload") or {"payload": True}
            ),
            build_evidence=lambda arguments, payload: (
                calls.append("evidence") or evidence
            ),
            validate_safety=lambda evidence_arg: (
                calls.append("safety") or safety
            ),
            validate_evidence=lambda evidence_arg: (
                calls.append("evidence_validation") or evidence_validation
            ),
            decide=lambda arguments, evidence_arg: (
                calls.append("decision") or decision
            ),
            render=lambda evidence_arg, decision_arg: (
                calls.append("renderer") or reviewer_packet
            ),
            build_readiness=lambda evidence_arg, decision_arg, reviewer_arg: (
                calls.append("readiness") or readiness
            ),
            item_ref=lambda arguments, decision_arg: (
                calls.append("item_ref") or "candidate-001"
            ),
            short_summary=lambda arguments: (
                calls.append("short_summary") or "short summary"
            ),
            title=lambda arguments: calls.append("title") or "Title hint",
        ),
    )

    assert calls == [
        "payload",
        "evidence",
        "safety",
        "evidence_validation",
        "decision",
        "renderer",
        "readiness",
        "item_ref",
        "short_summary",
        "title",
        "handoff",
        "draft_ready",
    ]
    assert execution.item_ref == "candidate-001"
    assert execution.draft_request_ready is True
    assert execution.handoff_request.handoff_ref == "handoff-candidate-001"
    assert approved_summary_pipeline_status(
        execution,
        schema_version="kcs_mcp_tool_result_v1",
        reuse_search_status="checked",
    ) == {
        "auto_publish_allowed": False,
        "case_ref": "case-001",
        "checks": [
            {"kind": "input_validation", "ok": True},
            {"kind": "evidence_builder", "ok": True},
            {"kind": "input_safety", "ok": True},
            {"kind": "evidence_validation", "ok": True},
            {"kind": "decision", "ok": True},
            {"kind": "renderer", "ok": True},
            {"kind": "readiness", "ok": True},
            {"kind": "draft_request_ready", "ok": True},
        ],
        "debug_code": "none",
        "draft_request_ready": True,
        "evidence_valid": True,
        "failure_stage": "none",
        "handoff_ref": "handoff-candidate-001",
        "input_safety_ok": True,
        "item_ref": "candidate-001",
        "network_calls": False,
        "ok": True,
        "original_article_type": ArticleType.TECHNICAL_SCR.value,
        "original_decision_status": DecisionStatus.DECISION_READY.value,
        "original_readiness_state": ReadinessState.READY_FOR_REVIEWER.value,
        "original_recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "pipeline_ok": True,
        "provider_calls": False,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": True,
        "result_kind": "approved_summary_pipeline",
        "reuse_search_status": "checked",
        "schema_version": "kcs_mcp_tool_result_v1",
        "validation_ok": True,
        "writes_files": False,
    }


def test_desktop_workflow_builds_reviewer_draft_preview_and_quality_gaps() -> None:
    execution = SimpleNamespace(
        arguments={"item": {"reuse_search_checked": True}},
        decision=SimpleNamespace(article_type=ArticleType.TECHNICAL_SCR.value),
        payload={
            "issue_candidates": [
                {
                    "supported_resolution_or_workaround": (
                        "Restart the required product service."
                    )
                }
            ]
        },
        reviewer_packet=SimpleNamespace(
            public_article_candidate={
                "applicable_to": ["Plesk for Linux", "approved-summary-source-001"],
                "cause": "A required product service is stopped.",
                "resolution_steps": ["Run systemctl restart product-service."],
                "symptoms": ["A safe Plesk task fails."],
                "title": "Plesk task fails: required product service is stopped",
            },
            zendesk_source_html=(
                "<h1>Plesk task fails: required product service is stopped</h1>"
                "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
                "<h2>Symptoms</h2><ol><li>A safe Plesk task fails.</li></ol>"
                "<h2>Cause</h2><p>A required product service is stopped.</p>"
                "<h2>Resolution</h2><div class=\"resolution\"><ol>"
                "<li><a href=\"https://support.plesk.com/hc/en-us/articles/"
                "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH\">"
                "Connect to the Plesk server via SSH.</a></li>"
                "<li>Run systemctl restart product-service.</li></ol></div>"
            ),
        ),
    )

    draft = approved_summary_reviewer_only_draft(execution)
    preview = approved_summary_reviewer_only_preview(draft)
    preview_text = approved_summary_reviewer_only_preview_text(draft)

    assert draft == {
        "applicable_to": ["Plesk for Linux"],
        "cause": "A required product service is stopped.",
        "resolution": "Restart the required product service.",
        "resolution_steps": ["Run systemctl restart product-service."],
        "status": "reviewer_only",
        "symptoms": ["A safe Plesk task fails."],
        "title": "Plesk task fails: required product service is stopped",
    }
    assert preview == draft
    assert (
        "Title: Plesk task fails: required product service is stopped" in preview_text
    )
    assert approved_summary_reuse_search_status(execution.arguments) == "checked"
    assert approved_summary_quality_gaps(execution, draft) == [
        {"kind": "reference_not_provided", "severity": "info"}
    ]


def test_desktop_workflow_blocks_diagnostic_transcript_in_resolution_html() -> None:
    execution = SimpleNamespace(
        arguments={"item": {"reuse_search_checked": True}},
        decision=SimpleNamespace(article_type=ArticleType.TECHNICAL_SCR.value),
        payload={"issue_candidates": [{"supported_resolution_or_workaround": ""}]},
        reviewer_packet=SimpleNamespace(
            public_article_candidate={
                "applicable_to": ["Plesk for Linux"],
                "cause": "A custom collectd configuration points metrics elsewhere.",
                "resolution_steps": [
                    "drwxrwxr-x 3 root root 18 Jun 17 2021 plugin data.",
                ],
                "symptoms": ["Plesk Monitoring graphs show no data."],
                "title": "Monitoring graphs show no data in Plesk",
            },
            zendesk_source_html=(
                "<h1>Monitoring graphs show no data in Plesk</h1>"
                "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
                "<h2>Symptoms</h2>"
                "<ol><li>Plesk Monitoring graphs show no data.</li></ol>"
                "<h2>Cause</h2>"
                "<p>A custom collectd configuration points metrics elsewhere.</p>"
                "<h2>Resolution</h2>"
                "<ol><li>drwxrwxr-x 3 root root 18 Jun 17 2021 "
                "plugin data.</li></ol>"
            ),
        ),
    )

    assert {
        "kind": "diagnostic_transcript_in_resolution",
        "severity": "blocker",
    } in approved_summary_quality_gaps(execution, {})


def test_desktop_workflow_calls_provider_and_converts_candidates() -> None:
    provider = _Provider(_extraction_payload())
    workflow = DesktopDraftWorkflow(provider=provider, selection_ttl_seconds=60)

    candidates = workflow.item_candidates_from_summary("Approved sanitized summary.")

    assert provider.contexts == [
        {
            "approved_summary_text": "Approved sanitized summary.",
            "request_kind": "desktop_draft_article",
        }
    ]
    assert candidates == [
        {
            "applicable_to": ["Plesk for Linux"],
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "confirmed_facts": ["A safe Plesk fact is confirmed."],
            "environment": {
                "applicable_to": ["Plesk for Linux"],
                "platform": "Plesk for Linux",
            },
            "item_ref": "candidate-001",
            "resolution_steps": ["Run systemctl restart product-service."],
            "summary": "Plesk task has a safe synthetic issue",
            "supported_cause": "A required product service is stopped.",
            "supported_resolution_or_workaround": (
                "Restart the required product service."
            ),
            "symptoms": ["A safe Plesk task fails."],
            "title": "Plesk task has a safe synthetic issue",
        }
    ]


def test_desktop_workflow_owns_pending_selection_state() -> None:
    workflow = DesktopDraftWorkflow(
        provider=_Provider(_extraction_payload()),
        selection_ttl_seconds=60,
    )
    candidates = workflow.item_candidates_from_summary("Approved sanitized summary.")
    pending = workflow.start_pending_selection(
        candidates,
        approved_summary_text="Approved sanitized summary.",
    )

    selected = workflow.selected_candidate(
        selection_ref=pending.selection_ref,
        selected_item_ref="candidate-001",
    )

    assert selected["item_ref"] == "candidate-001"
    assert workflow.pending_selection is None


def test_desktop_workflow_builds_operator_choice_request() -> None:
    workflow = DesktopDraftWorkflow(
        provider=_Provider(_extraction_payload()),
        selection_ttl_seconds=60,
    )
    candidates = workflow.item_candidates_from_summary("Approved sanitized summary.")
    pending = workflow.start_pending_selection(
        candidates,
        approved_summary_text="Approved sanitized summary.",
    )

    request = operator_choice_request(pending, submit_tool="kcs_draft_article")
    review_summary = operator_choice_review_summary(pending)

    assert request["mode"] == "single_select"
    assert request["submit_tool"] == "kcs_draft_article"
    assert request["options"] == [
        {
            "label": "Plesk task has a safe synthetic issue",
            "submit_arguments": {
                "operator_selected_item_ref": "candidate-001",
                "operator_selection_ref": pending.selection_ref,
            },
            "value": "candidate-001",
        }
    ]
    assert review_summary == {
        "mode": "single_select",
        "option_count": 1,
        "presentation": "native_choice_popup_preferred",
        "prose_only_choice_allowed": False,
        "selection_ref": pending.selection_ref,
    }


def test_desktop_workflow_builds_split_required_result() -> None:
    result = split_required_result(
        [
            _desktop_candidate("candidate-001", "First safe issue"),
            _desktop_candidate("candidate-002", "Second safe issue"),
        ],
        schema_version="kcs_mcp_tool_result_v1",
    )

    assert result is not None
    assert result["debug_code"] == "multiple_kcs_items_detected"
    assert result["recommended_action"] == "split_required"
    assert result["manual_draft_allowed"] is False
    assert result["automatic_item_retry_allowed"] is False
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


def test_desktop_workflow_attaches_pending_selection_choice_request() -> None:
    pending = DesktopDraftWorkflow(
        provider=_Provider(_extraction_payload()),
        selection_ttl_seconds=60,
    ).start_pending_selection(
        [_desktop_candidate("candidate-001", "First safe issue")],
        approved_summary_text="Approved sanitized summary.",
    )
    result = {
        "review_summary": {
            "draft_available": False,
            "reason": "multiple_kcs_items_detected",
        }
    }

    attach_pending_selection(result, pending, submit_tool="kcs_draft_article")

    assert result["operator_selection_ref"] == pending.selection_ref
    assert result["operator_choice_confirmed"] is False
    assert result["operator_choice_request"]["options"][0]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": pending.selection_ref,
    }
    assert (
        result["review_summary"]["operator_choice_request"]["selection_ref"]
        == pending.selection_ref
    )


def test_desktop_workflow_selection_error_requires_exact_choice_args() -> None:
    pending = DesktopDraftWorkflow(
        provider=_Provider(_extraction_payload()),
        selection_ttl_seconds=60,
    ).start_pending_selection(
        [_desktop_candidate("candidate-001", "First safe issue")],
        approved_summary_text="Approved sanitized summary.",
    )

    missing_choice = selection_error_result(
        {},
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_draft_article",
    )
    accepted_choice = selection_error_result(
        {
            "operator_choice_confirmed": True,
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending.selection_ref,
        },
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_draft_article",
    )

    assert missing_choice is not None
    assert missing_choice["debug_code"] == "operator_selection_required"
    assert missing_choice["manual_draft_allowed"] is False
    assert missing_choice["recommended_action"] == "split_required"
    assert accepted_choice is None


def test_desktop_workflow_expires_pending_selection() -> None:
    workflow = DesktopDraftWorkflow(
        provider=_Provider(_extraction_payload()),
        selection_ttl_seconds=0,
    )
    candidates = workflow.item_candidates_from_summary("Approved sanitized summary.")
    pending = workflow.start_pending_selection(
        candidates,
        approved_summary_text="Approved sanitized summary.",
    )

    with pytest.raises(OperatorSelectionExpiredError):
        workflow.selected_candidate(
            selection_ref=pending.selection_ref,
            selected_item_ref="candidate-001",
        )


def test_desktop_workflow_unavailable_provider_is_controlled() -> None:
    workflow = DesktopDraftWorkflow(
        provider=UnavailableSemanticExtractionProvider(),
        selection_ttl_seconds=60,
    )

    with pytest.raises(SemanticExtractionProviderUnavailableError):
        workflow.item_candidates_from_summary("Approved sanitized summary.")


def test_desktop_workflow_validates_context_before_provider_call() -> None:
    provider = _Provider(_extraction_payload())
    workflow = DesktopDraftWorkflow(provider=provider, selection_ttl_seconds=60)

    with pytest.raises(ContractValidationError):
        workflow.item_candidates_from_summary("api_key=secret-value")

    assert provider.contexts == []


def test_approved_provider_from_environment_uses_local_summary_provider(
    monkeypatch,
) -> None:
    monkeypatch.setenv(desktop_workflow.SEMANTIC_PROVIDER_ENV, "approved")
    provider = semantic_provider_from_environment()

    with pytest.raises(desktop_workflow.NoSemanticCandidatesError):
        provider.propose_candidates(
            {
                "approved_summary_text": "Approved sanitized summary.",
                "request_kind": "desktop_draft_article",
            }
        )


def test_compact_draft_result_keeps_html_out_by_default() -> None:
    result = {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "auto_publish_allowed": False,
        "draft_request_ready": True,
        "ok": True,
        "pipeline_ok": True,
        "public_output_approved": False,
        "ready_for_reviewer": True,
        "recommended_action": "create_candidate",
        "reuse_search_status": "checked",
        "schema_version": "kcs_mcp_tool_result_v1",
        "should_be_kcs_article": True,
    }
    bundle = {
        "bundle_ref": "reviewer-bundle-run-001",
        "html_path": "local-data/reviewer-bundles/run-001/item-001/reviewer_only.html",
        "html_sha256": "a" * 64,
        "manifest_path": "local-data/reviewer-bundles/run-001/manifest.json",
    }

    compact = compact_draft_result(
        result,
        bundle,
        include_reviewer_only_html=False,
        reviewer_only_html="<h1>Reviewer only</h1>",
    )

    assert compact["bundle_ref"] == "reviewer-bundle-run-001"
    assert compact["draft_generated"] is True
    assert compact["kcs_ready"] is True
    assert compact["reviewer_bundle_written"] is True
    assert compact["writes_files"] is True
    assert compact["auto_publish_allowed"] is False
    assert compact["public_output_approved"] is False
    assert "reviewer_only_html" not in compact


def test_compact_draft_result_carries_configured_bundle_storage_hint() -> None:
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
            "bundle_storage_hint": "~/Documents/KCS Authoring",
            "bundle_storage_ref": "user_documents_kcs_authoring",
            "html_path": (
                "local-data/reviewer-bundles/run-001/item-001/reviewer_only.html"
            ),
            "html_sha256": "a" * 64,
            "manifest_path": "local-data/reviewer-bundles/run-001/manifest.json",
        },
        include_reviewer_only_html=False,
        reviewer_only_html="<h1>Reviewer only</h1>",
    )

    assert compact["bundle_storage_hint"] == "~/Documents/KCS Authoring"
    assert compact["bundle_storage_ref"] == "user_documents_kcs_authoring"
    assert "reviewer_only_html" not in compact


def test_finalize_author_result_writes_bundle_and_keeps_html_out_by_default(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_HINT",
        "~/Documents/KCS Authoring",
    )
    monkeypatch.setenv(
        "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_REF",
        "user_documents_kcs_authoring",
    )
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"
    compact = finalize_author_result_with_bundle(
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-001",
            "ok": True,
            "pipeline_ok": True,
            "ready_for_reviewer": True,
            "recommended_action": "create_candidate",
            "reuse_search_status": "checked",
            "reviewer_only_html": "<h1>Reviewer only</h1>",
            "schema_version": "kcs_mcp_tool_result_v1",
            "should_be_kcs_article": True,
        },
        bundle_root=bundle_root,
        include_reviewer_only_html=False,
        schema_version="kcs_mcp_tool_result_v1",
    )

    html_files = list(bundle_root.glob("run-*/candidate-001/reviewer_only.html"))
    assert len(html_files) == 1
    assert html_files[0].read_text(encoding="utf-8") == "<h1>Reviewer only</h1>"
    assert compact["reviewer_bundle_written"] is True
    assert compact["bundle_storage_hint"] == "~/Documents/KCS Authoring"
    assert compact["bundle_storage_ref"] == "user_documents_kcs_authoring"
    assert compact["html_path"].startswith("local-data/reviewer-bundles/run-")
    assert compact["html_sha256"]
    assert "reviewer_only_html" not in compact
    manifest_files = list(bundle_root.glob("run-*/manifest.json"))
    assert len(manifest_files) == 1
    manifest = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert manifest["bundle_storage_hint"] == "~/Documents/KCS Authoring"
    assert manifest["bundle_storage_ref"] == "user_documents_kcs_authoring"


def test_finalize_author_result_strips_html_from_not_ready_result(tmp_path) -> None:
    compact = finalize_author_result_with_bundle(
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-001",
            "ok": False,
            "pipeline_ok": False,
            "ready_for_reviewer": False,
            "recommended_action": "blocked",
            "reuse_search_status": "checked",
            "reviewer_only_html": "<h1>Do not expose</h1>",
            "schema_version": "kcs_mcp_tool_result_v1",
            "should_be_kcs_article": True,
            "writes_files": True,
            "zendesk_source_html": "<h1>Do not expose source</h1>",
        },
        bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        include_reviewer_only_html=True,
        schema_version="kcs_mcp_tool_result_v1",
    )

    assert compact["reviewer_bundle_written"] is False
    assert compact["writes_files"] is False
    assert "reviewer_only_html" not in compact
    assert "zendesk_source_html" not in compact


def test_finalize_author_result_manifest_marks_missing_reuse_as_draft_only(
    tmp_path,
) -> None:
    bundle_root = tmp_path / "local-data" / "reviewer-bundles"

    compact = finalize_author_result_with_bundle(
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "item_ref": "candidate-001",
            "ok": True,
            "pipeline_ok": True,
            "ready_for_reviewer": True,
            "recommended_action": "create_candidate",
            "reuse_search_status": "skipped",
            "reviewer_only_html": "<h1>Reviewer only</h1>",
            "schema_version": "kcs_mcp_tool_result_v1",
            "should_be_kcs_article": True,
        },
        bundle_root=bundle_root,
        include_reviewer_only_html=False,
        schema_version="kcs_mcp_tool_result_v1",
    )

    manifest_files = list(bundle_root.glob("run-*/manifest.json"))
    assert len(manifest_files) == 1
    manifest = json.loads(manifest_files[0].read_text(encoding="utf-8"))
    assert compact["debug_code"] == "draft_only_reuse_search_missing"
    assert compact["ready_for_reviewer"] is False
    assert compact["kcs_ready"] is False
    assert manifest["debug_code"] == "draft_only_reuse_search_missing"
    assert manifest["ready_for_reviewer"] is False
    assert manifest["kcs_ready"] is False
    assert manifest["recommended_action"] == "draft_only"


def test_finalize_author_result_rejects_bundle_root_outside_boundary(
    tmp_path,
) -> None:
    with pytest.raises(ContractValidationError):
        finalize_author_result_with_bundle(
            {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "item_ref": "candidate-001",
                "ok": True,
                "pipeline_ok": True,
                "ready_for_reviewer": True,
                "recommended_action": "create_candidate",
                "reuse_search_status": "checked",
                "reviewer_only_html": "<h1>Reviewer only</h1>",
                "schema_version": "kcs_mcp_tool_result_v1",
                "should_be_kcs_article": True,
            },
            bundle_root=tmp_path / "unexpected-bundles",
            include_reviewer_only_html=False,
            schema_version="kcs_mcp_tool_result_v1",
        )


def test_compact_draft_result_marks_missing_reuse_as_draft_only() -> None:
    compact = compact_draft_result(
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "ok": True,
            "pipeline_ok": True,
            "ready_for_reviewer": True,
            "recommended_action": "create_candidate",
            "reuse_search_status": "skipped",
            "schema_version": "kcs_mcp_tool_result_v1",
            "should_be_kcs_article": True,
        },
        {
            "bundle_ref": "reviewer-bundle-run-001",
            "html_path": (
                "local-data/reviewer-bundles/run-001/item-001/reviewer_only.html"
            ),
            "html_sha256": "b" * 64,
            "manifest_path": "local-data/reviewer-bundles/run-001/manifest.json",
        },
        include_reviewer_only_html=True,
        reviewer_only_html="<h1>Reviewer only</h1>",
    )

    assert compact["draft_generated"] is True
    assert compact["debug_code"] == "draft_only_reuse_search_missing"
    assert compact["kcs_ready"] is False
    assert compact["pipeline_ok"] is False
    assert compact["ready_for_reviewer"] is False
    assert compact["recommended_action"] == "draft_only"
    assert compact["blockers"] == ["reuse_search_not_checked"]
    assert compact["reviewer_only_html"] == "<h1>Reviewer only</h1>"


def test_quality_blocked_result_uses_blocker_gaps_without_bundle() -> None:
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
    assert blocked["blockers"] == ["missing_required_section"]
    assert blocked["draft_generated"] is False
    assert blocked["reviewer_bundle_written"] is False
    assert blocked["writes_files"] is False
    assert blocked["ready_for_reviewer"] is False
