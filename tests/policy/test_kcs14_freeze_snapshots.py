from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path
from typing import Any

from kcs_adapters.desktop_draft_output import (
    compact_draft_result,
    quality_blocked_result,
)
from kcs_adapters.desktop_mcp_results import McpToolResult, mcp_tool_response
from kcs_adapters.desktop_protocol import (
    MCP_INITIALIZE_INSTRUCTIONS,
    SEMANTIC_CONTROL_GUIDANCE,
)
from kcs_adapters.desktop_tool_descriptors import tool_descriptors
from kcs_adapters.desktop_tool_names import (
    CLAUDE_DESKTOP_TOOL_ALIASES,
    TOOL_SUBMIT_SEMANTIC_REVIEW,
)
from kcs_adapters.desktop_tool_results import tool_result_text
from kcs_adapters.desktop_tool_schemas import tool_output_schema
from kcs_adapters.desktop_workflow_results import (
    draft_author_failure_result,
    semantic_review_required_result,
    split_required_result,
)
from kcs_core import claude_draft, claude_handoff, models

ROOT = Path(__file__).resolve().parents[2]

APPROVED_SUMMARY_INPUT_PROPERTIES = (
    "applicable_to",
    "approved_summary_text",
    "article_title",
    "article_type",
    "auto_publish_allowed",
    "candidate_id",
    "case_ref",
    "cause",
    "commands",
    "confirmed_facts",
    "customer_replies",
    "debug",
    "diagnosis",
    "environment",
    "evidence",
    "facts",
    "fix",
    "item",
    "log_evidence",
    "logs",
    "network_calls",
    "notes",
    "open_questions",
    "problem",
    "problem_statement",
    "provider_calls",
    "public_output_approved",
    "publishes",
    "question",
    "ready_for_real_ticket_use",
    "reference_article",
    "reference_article_html",
    "reference_article_text",
    "resolution",
    "resolution_procedure",
    "resolution_steps",
    "resolution_summary",
    "reuse_search_checked",
    "reuse_search_run_ref",
    "root_cause",
    "root_cause_analysis",
    "secondary_finding",
    "secondary_findings",
    "secondary_issue",
    "secondary_issues",
    "solution",
    "steps",
    "supported_answer",
    "supported_cause",
    "supported_resolution_or_workaround",
    "symptom",
    "symptoms",
    "title",
    "writes_files",
)

DESKTOP_TOOL_SNAPSHOT = (
    (
        "kcs.draft_ticket",
        "kcs_draft_ticket",
        ("debug", "ticket_ref"),
        ("ticket_ref",),
        False,
        False,
    ),
    (
        "kcs.register_clean_ticket",
        "kcs_register_clean_ticket",
        ("clean_ticket_text", "debug", "ticket_ref"),
        ("clean_ticket_text",),
        False,
        False,
    ),
    (
        "kcs.draft_article",
        "kcs_draft_article",
        (
            "approved_summary_text",
            "debug",
            "operator_confirmed_resolution_steps",
            "operator_selected_item_ref",
            "operator_selected_item_refs",
            "operator_selection_ref",
        ),
        (),
        False,
        False,
    ),
    (
        "kcs.confirm_reuse_comparison",
        "kcs_confirm_reuse_comparison",
        ("candidate_ref", "comparison_ref", "outcome"),
        ("comparison_ref", "outcome"),
        False,
        False,
    ),
    (
        "kcs.prepare_semantic_review",
        "kcs_prepare_semantic_review",
        ("semantic_review_ref",),
        ("semantic_review_ref",),
        True,
        True,
    ),
    (
        "kcs.submit_semantic_review",
        "kcs_submit_semantic_review",
        (
            "operator_selection_ref",
            "semantic_issue_proposal",
            "semantic_review_ref",
        ),
        ("semantic_issue_proposal", "semantic_review_ref"),
        False,
        False,
    ),
    (
        "support.get_behavior_instructions",
        "support_get_behavior_instructions",
        (),
        (),
        True,
        True,
    ),
    ("kcs.get_policy_summary", "kcs_get_policy_summary", (), (), True, True),
    ("kcs.get_mcp_readiness", "kcs_get_mcp_readiness", (), (), True, True),
    (
        "kcs.validate_handoff_request",
        "kcs_validate_handoff_request",
        ("request",),
        ("request",),
        True,
        True,
    ),
    (
        "kcs.validate_handoff_response",
        "kcs_validate_handoff_response",
        ("request", "response"),
        ("request", "response"),
        True,
        True,
    ),
    (
        "kcs.validate_draft_request",
        "kcs_validate_draft_request",
        ("request",),
        ("request",),
        True,
        True,
    ),
    (
        "kcs.validate_draft_response",
        "kcs_validate_draft_response",
        ("request", "response"),
        ("request", "response"),
        True,
        True,
    ),
    ("kcs.run_contract_smoke", "kcs_run_contract_smoke", (), (), True, True),
    (
        "kcs.run_approved_summary_pipeline",
        "kcs_run_approved_summary_pipeline",
        APPROVED_SUMMARY_INPUT_PROPERTIES,
        ("approved_summary_text",),
        True,
        True,
    ),
    (
        "kcs.author_approved_summary",
        "kcs_author_approved_summary",
        APPROVED_SUMMARY_INPUT_PROPERTIES,
        ("approved_summary_text",),
        True,
        True,
    ),
    (
        "kcs.author_ticket",
        "kcs_author_ticket",
        (
            "auto_publish_allowed",
            "customer_replies",
            "debug",
            "network_calls",
            "provider_calls",
            "public_output_approved",
            "publishes",
            "ready_for_real_ticket_use",
            "reference_article",
            "reference_article_html",
            "reference_article_text",
            "ticket_ref",
            "writes_files",
        ),
        ("ticket_ref",),
        True,
        True,
    ),
)

REJECTED_ACTIVE_SEMANTIC_SUBMIT_FIELDS = frozenset(
    {
        "operator_excluded_source_refs",
        "semantic_boundary_action",
        "semantic_claim_ownership",
        "semantic_observation_relations",
    }
)

REJECTED_ACTIVE_SEMANTIC_SCHEMA_TERMS = (
    "semantic_claim_ownership_v1",
    "semantic_observation_relations_v1",
)

TOOL_OUTPUT_SUCCESS_KEYS = (
    "accepted_ticket_facts",
    "allowed_source_refs",
    "approved_summary_source",
    "article_type",
    "atomic_item",
    "attempted_count",
    "auto_publish_allowed",
    "automatic_item_retry_allowed",
    "batch_status",
    "blockers",
    "boundary_blocker_codes",
    "boundary_blocker_count",
    "bundle_ref",
    "bundle_storage_hint",
    "bundle_storage_ref",
    "byte_length",
    "candidate_origin",
    "candidate_outcomes",
    "case_ref",
    "checks",
    "clean_ticket_sha256",
    "clean_ticket_storage_hint",
    "clean_ticket_storage_ref",
    "clean_ticket_store_ref",
    "comparison_candidates",
    "comparison_outcome",
    "comparison_outcomes",
    "comparison_ref",
    "comparison_sequence_outcomes",
    "completed_count",
    "coverage_record_field_names",
    "customer_replies",
    "debug_code",
    "draft_generated",
    "draft_generated_count",
    "draft_ref",
    "draft_request_ready",
    "draft_sections",
    "draft_status",
    "evidence_valid",
    "excerpt_count",
    "excerpt_total_bytes",
    "existing_article_review",
    "failure_stage",
    "handoff_ref",
    "html_path",
    "html_sha256",
    "input_safety_ok",
    "issue_boundary_contract",
    "issue_field_names",
    "issue_shape_contract",
    "item_candidates",
    "item_ref",
    "kcs_ready",
    "manifest_path",
    "manual_draft_allowed",
    "max_candidates",
    "network_calls",
    "new_draft_created_count",
    "next_arguments",
    "next_required_action",
    "next_tool",
    "next_tool_name",
    "ok",
    "open_questions",
    "operator_boundary_correction",
    "operator_choice_confirmed",
    "operator_choice_options",
    "operator_choice_request",
    "operator_choice_submit_options",
    "operator_evidence_provenance",
    "operator_followup",
    "operator_prompt",
    "operator_prompt_style",
    "operator_resolution_detail_policy",
    "operator_selected_item_ref",
    "operator_selected_item_refs",
    "operator_selection_ref",
    "original_article_type",
    "original_decision_status",
    "original_readiness_state",
    "original_recommended_action",
    "pipeline_ok",
    "prompts_exposed",
    "proposal_field_contracts",
    "proposal_shape_contracts",
    "protocol_version",
    "provider_calls",
    "provider_error_code",
    "provider_status",
    "public_output_approved",
    "publishes",
    "quality_gaps",
    "ready_for_real_ticket_use",
    "ready_for_reviewer",
    "recommended_action",
    "remaining_item_candidates",
    "remaining_operator_choice_request",
    "remaining_operator_choice_submit_options",
    "remaining_selection_ref",
    "request_schema_version",
    "request_sha256",
    "required_submit_shape",
    "resources_exposed",
    "response_schema_version",
    "response_sha256",
    "result_kind",
    "retryable_blocked_count",
    "retryable_item_candidates",
    "reuse_search_run_ref",
    "reuse_search_status",
    "review_summary",
    "reviewer_bundle_written",
    "reviewer_only_draft",
    "reviewer_only_html",
    "reviewer_only_preview",
    "reviewer_only_preview_text",
    "schema_correction_used",
    "schema_version",
    "selected_count",
    "selected_excerpts",
    "selected_reuse_match",
    "semantic_item_outcomes",
    "semantic_review_packet_sha256",
    "semantic_review_ref",
    "semantic_submission_correction",
    "server_name",
    "server_version",
    "should_be_kcs_article",
    "smoke_ok",
    "submit_arguments",
    "submit_tool",
    "task",
    "terminal_blocked_count",
    "terminal_cause_debug_code",
    "ticket_ref",
    "tool_count",
    "tools",
    "validation_ok",
    "workflow_state",
    "workflow_stopped_count",
    "writes_files",
)

PACKET_SCHEMA_SNAPSHOT = {
    "KcsActionDecisionPacket": (
        "kcs_action_decision_packet_v1",
        (
            "candidate_id",
            "recommended_action",
            "article_type",
            "confidence",
            "blockers",
            "evidence_basis",
            "selected_reuse_match",
            "split_items",
            "auto_publish_allowed",
            "status",
            "operator_override_allowed",
            "allowed_override_modes",
            "override_status",
        ),
    ),
    "KcsClaudeDraftRequestPacket": (
        "kcs_claude_draft_request_v1",
        (
            "draft_ref",
            "handoff_ref",
            "case_ref",
            "item_ref",
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "draft_purpose",
            "auto_publish_allowed",
            "public_output_approved",
            "provider_may_decide_action",
            "safe_drafting_context",
            "operator_override",
            "artifact_refs",
            "schema_version",
        ),
    ),
    "KcsClaudeDraftResponsePacket": (
        "kcs_claude_draft_response_v1",
        (
            "handoff_ref",
            "draft_status",
            "provider_error_code",
            "article_type",
            "title",
            "applicable_to",
            "sections",
            "zendesk_source_html",
            "reviewer_notes",
            "unsupported_claims_present",
            "internal_only_content_present",
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "auto_publish_allowed",
            "public_output_approved",
            "schema_version",
        ),
    ),
    "KcsClaudeHandoffRequestPacket": (
        "kcs_claude_handoff_request_v1",
        (
            "handoff_ref",
            "case_ref",
            "item_ref",
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "provider_profile",
            "handoff_purpose",
            "decision_summary_sha256",
            "readiness_summary_sha256",
            "auto_publish_allowed",
            "public_output_approved",
            "provider_may_decide_action",
            "provider_may_generate_draft_body",
            "include_full_reviewer_packet_body",
            "include_full_zendesk_html",
            "safe_context",
            "operator_override",
            "artifact_refs",
            "schema_version",
        ),
    ),
    "KcsClaudeHandoffResponsePacket": (
        "kcs_claude_handoff_response_v1",
        (
            "handoff_ref",
            "provider_status",
            "provider_error_code",
            "reviewer_assist_notes",
            "structured_comments",
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "auto_publish_allowed",
            "public_output_approved",
            "contains_article_draft",
            "schema_version",
        ),
    ),
    "KcsReviewerOnlyDraftArtifact": (
        "kcs_reviewer_only_draft_artifact_v1",
        (
            "artifact_ref",
            "draft_ref",
            "handoff_ref",
            "case_ref",
            "item_ref",
            "original_recommended_action",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "draft_response",
            "draft_response_sha256",
            "reviewer_only",
            "auto_publish_allowed",
            "public_output_approved",
            "schema_version",
        ),
    ),
    "KcsReviewerPacket": (
        "kcs_reviewer_packet_v1",
        (
            "case_ref",
            "recommended_action",
            "review_required",
            "public_article_candidate",
            "internal_reviewer_notes",
            "evidence_basis",
            "validation_report",
            "zendesk_source_html",
            "auto_publish_allowed",
        ),
    ),
    "KcsValidationReportPacket": (
        "kcs_validation_report_packet_v1",
        (
            "case_ref",
            "ok",
            "ready_for_reviewer",
            "state",
            "required_next_step",
            "checks",
            "blockers",
            "warnings",
            "evidence_validation",
            "decision_summary",
            "renderer_validation",
            "reviewer_packet_sha256",
            "zendesk_source_sha256",
            "auto_publish_allowed",
        ),
    ),
    "NormalizedTicketEvidencePacket": (
        "normalized_ticket_evidence_packet_v1",
        (
            "case_ref",
            "input_class",
            "source_refs",
            "issue_candidates",
            "environment",
            "symptoms",
            "confirmed_facts",
            "supported_cause",
            "supported_resolution_or_workaround",
            "open_questions",
            "visibility_summary",
            "sanitizer_report",
        ),
    ),
    "ReuseSearchResultsPacket": (
        "reuse_search_results_packet_v1",
        (
            "search_run_ref",
            "searched",
            "search_source",
            "matches",
            "blockers",
        ),
    ),
}

FROZEN_CONTRACT_PATHS = (
    "src/kcs_adapters/desktop_draft_output.py",
    "src/kcs_adapters/desktop_mcp_results.py",
    "src/kcs_adapters/desktop_reviewer_bundle.py",
    "src/kcs_adapters/desktop_semantic_review.py",
    "src/kcs_adapters/desktop_ticket_ref.py",
    "src/kcs_adapters/desktop_tool_descriptors.py",
    "src/kcs_adapters/desktop_tool_names.py",
    "src/kcs_adapters/desktop_tool_results.py",
    "src/kcs_adapters/desktop_tool_schemas.py",
    "src/kcs_adapters/desktop_workflow_results.py",
    "src/kcs_core/claude_draft.py",
    "src/kcs_core/claude_handoff.py",
    "src/kcs_core/decision.py",
    "src/kcs_core/models.py",
    "src/kcs_core/renderer.py",
    "src/kcs_core/reviewer_bundle.py",
    "src/kcs_core/safety.py",
    "src/kcs_core/semantic_extraction.py",
    "src/kcs_core/validation.py",
)


def _packet_schema_snapshot() -> dict[str, tuple[str, tuple[str, ...]]]:
    packet_classes = (
        models.NormalizedTicketEvidencePacket,
        models.ReuseSearchResultsPacket,
        models.KcsActionDecisionPacket,
        models.KcsReviewerPacket,
        models.KcsValidationReportPacket,
        claude_handoff.KcsClaudeHandoffRequestPacket,
        claude_handoff.KcsClaudeHandoffResponsePacket,
        claude_draft.KcsClaudeDraftRequestPacket,
        claude_draft.KcsClaudeDraftResponsePacket,
        claude_draft.KcsReviewerOnlyDraftArtifact,
    )
    return {
        cls.__name__: (
            _schema_version(cls),
            tuple(field.name for field in dataclasses.fields(cls)),
        )
        for cls in packet_classes
    }


def _schema_version(cls: type[Any]) -> str:
    version = getattr(cls, "SCHEMA_VERSION", None)
    if isinstance(version, str):
        return version
    default_version = cls.__dataclass_fields__["schema_version"].default
    assert isinstance(default_version, str)
    return default_version


def test_semantic_control_guidance_consistency() -> None:
    submit_descriptor = next(
        descriptor
        for descriptor in tool_descriptors()
        if descriptor.name == TOOL_SUBMIT_SEMANTIC_REVIEW
    )
    surfaces = {
        "initialize": MCP_INITIALIZE_INSTRUCTIONS,
        "submit tool": submit_descriptor.description,
        "result prose": tool_result_text(
            {"required_submit_shape": {}, "result_kind": "semantic_review_packet"}
        ),
        "Cowork skill": (
            ROOT / "packaging/cowork/kcs-authoring/skills/"
            "kcs-authoring-control/SKILL.md"
        ).read_text(encoding="utf-8"),
        "Desktop manifest": (
            ROOT / "packaging/claude-desktop/"
            "kcs-authoring-mvp-validator-control/manifest.json"
        ).read_text(encoding="utf-8"),
    }
    expected = " ".join(SEMANTIC_CONTROL_GUIDANCE.split())

    for surface_name, surface_text in surfaces.items():
        assert expected in " ".join(surface_text.split()), surface_name


def test_desktop_tools_list_shape_matches_pre_refactor_snapshot() -> None:
    actual = tuple(
        (
            descriptor.name,
            CLAUDE_DESKTOP_TOOL_ALIASES[descriptor.name],
            tuple(sorted(descriptor.input_schema.get("properties", {}))),
            tuple(descriptor.input_schema.get("required", ())),
            descriptor.annotations["idempotentHint"],
            descriptor.annotations["readOnlyHint"],
        )
        for descriptor in tool_descriptors()
    )

    assert actual == DESKTOP_TOOL_SNAPSHOT


def test_rejected_semantic_experiments_stay_off_active_submit_surface() -> None:
    descriptor = next(
        item
        for item in tool_descriptors()
        if item.name == TOOL_SUBMIT_SEMANTIC_REVIEW
    )
    properties = frozenset(descriptor.input_schema.get("properties", {}))

    assert properties == {
        "operator_selection_ref",
        "semantic_issue_proposal",
        "semantic_review_ref",
    }
    assert properties.isdisjoint(REJECTED_ACTIVE_SEMANTIC_SUBMIT_FIELDS)
    for schema_term in REJECTED_ACTIVE_SEMANTIC_SCHEMA_TERMS:
        assert schema_term not in descriptor.description


def test_tool_output_success_keys_match_pre_refactor_snapshot() -> None:
    output_schema = tool_output_schema()
    success_properties = output_schema["anyOf"][0]["properties"]

    assert tuple(sorted(success_properties)) == TOOL_OUTPUT_SUCCESS_KEYS


def test_packet_schema_versions_and_field_sets_match_pre_refactor_snapshot() -> None:
    assert _packet_schema_snapshot() == PACKET_SCHEMA_SNAPSHOT


def test_mcp_result_envelope_keys_match_pre_refactor_snapshot() -> None:
    descriptor = tool_descriptors()[0]
    response = mcp_tool_response(
        descriptor=descriptor,
        result=McpToolResult(
            ok=True,
            result={
                "ok": True,
                "result_kind": "policy_summary",
                "schema_version": "kcs_mcp_tool_result_v1",
            },
        ),
    )

    assert tuple(sorted(response)) == ("content", "isError", "structuredContent")
    assert tuple(sorted(response["structuredContent"])) == (
        "ok",
        "result_kind",
        "schema_version",
    )


def test_compact_result_key_sets_match_pre_refactor_snapshots() -> None:
    result = {
        "schema_version": "kcs_mcp_tool_result_v1",
        "article_type": "howto_qa",
        "auto_publish_allowed": False,
        "blockers": [],
        "debug_code": "none",
        "draft_request_ready": True,
        "existing_article_review": {},
        "failure_stage": "",
        "item_ref": "item-1",
        "network_calls": False,
        "ok": True,
        "pipeline_ok": True,
        "provider_calls": False,
        "public_output_approved": False,
        "quality_gaps": [],
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": True,
        "recommended_action": "create_candidate",
        "result_kind": "draft_article_authoring",
        "reuse_search_status": "checked",
        "selected_reuse_match": None,
        "should_be_kcs_article": True,
        "validation_ok": True,
        "writes_files": False,
    }
    bundle = {
        "bundle_ref": "bundle-1",
        "bundle_storage_hint": "local",
        "bundle_storage_ref": "bundle-ref",
        "html_path": "reviewer.html",
        "html_sha256": "0" * 64,
        "manifest_path": "manifest.json",
    }
    snapshots = {
        "compact_draft_result": tuple(
            sorted(
                compact_draft_result(
                    result,
                    bundle,
                    include_reviewer_only_html=True,
                    reviewer_only_html="<p>Reviewer only</p>",
                )
            )
        ),
        "quality_blocked_result": tuple(
            sorted(
                quality_blocked_result(
                    result,
                    [{"kind": "reviewer_html_quality_blocked"}],
                    schema_version="kcs_mcp_tool_result_v1",
                )
            )
        ),
        "draft_author_failure_result": tuple(
            sorted(
                draft_author_failure_result(
                    failure_stage="decision",
                    debug_code="blocked",
                    schema_version="kcs_mcp_tool_result_v1",
                )
            )
        ),
        "semantic_review_required_result": tuple(
            sorted(
                semantic_review_required_result(
                    schema_version="kcs_mcp_tool_result_v1",
                    semantic_review_ref="sem-1",
                )
            )
        ),
        "split_required_result": tuple(
            sorted(
                split_required_result(
                    [
                        {
                            "item_ref": "item-a",
                            "article_type": "howto_qa",
                            "recommended_action": "create_candidate",
                            "problem_statement": "Problem A",
                        },
                        {
                            "item_ref": "item-b",
                            "article_type": "howto_qa",
                            "recommended_action": "create_candidate",
                            "problem_statement": "Problem B",
                        },
                    ],
                    schema_version="kcs_mcp_tool_result_v1",
                )
                or {}
            )
        ),
    }

    assert snapshots == {
        "compact_draft_result": (
            "article_type",
            "auto_publish_allowed",
            "blockers",
            "bundle_ref",
            "bundle_storage_hint",
            "bundle_storage_ref",
            "debug_code",
            "draft_generated",
            "draft_request_ready",
            "existing_article_review",
            "failure_stage",
            "html_path",
            "html_sha256",
            "item_ref",
            "kcs_ready",
            "manifest_path",
            "network_calls",
            "ok",
            "pipeline_ok",
            "provider_calls",
            "public_output_approved",
            "quality_gaps",
            "ready_for_real_ticket_use",
            "ready_for_reviewer",
            "recommended_action",
            "result_kind",
            "reuse_search_status",
            "reviewer_bundle_written",
            "reviewer_only_html",
            "schema_version",
            "selected_reuse_match",
            "should_be_kcs_article",
            "validation_ok",
            "writes_files",
        ),
        "quality_blocked_result": (
            "article_type",
            "auto_publish_allowed",
            "blockers",
            "debug_code",
            "draft_generated",
            "draft_request_ready",
            "failure_stage",
            "item_ref",
            "kcs_ready",
            "manual_draft_allowed",
            "network_calls",
            "next_required_action",
            "ok",
            "pipeline_ok",
            "provider_calls",
            "public_output_approved",
            "quality_gaps",
            "ready_for_real_ticket_use",
            "ready_for_reviewer",
            "recommended_action",
            "result_kind",
            "reuse_search_status",
            "review_summary",
            "reviewer_bundle_written",
            "schema_version",
            "should_be_kcs_article",
            "validation_ok",
            "writes_files",
        ),
        "draft_author_failure_result": (
            "article_type",
            "atomic_item",
            "auto_publish_allowed",
            "blockers",
            "case_ref",
            "checks",
            "debug_code",
            "draft_request_ready",
            "evidence_valid",
            "failure_stage",
            "input_safety_ok",
            "network_calls",
            "ok",
            "open_questions",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "original_recommended_action",
            "pipeline_ok",
            "provider_calls",
            "public_output_approved",
            "quality_gaps",
            "ready_for_real_ticket_use",
            "ready_for_reviewer",
            "recommended_action",
            "result_kind",
            "review_summary",
            "schema_version",
            "should_be_kcs_article",
            "validation_ok",
            "writes_files",
        ),
        "semantic_review_required_result": (
            "article_type",
            "atomic_item",
            "auto_publish_allowed",
            "blockers",
            "case_ref",
            "checks",
            "debug_code",
            "draft_generated",
            "draft_request_ready",
            "evidence_valid",
            "failure_stage",
            "input_safety_ok",
            "manual_draft_allowed",
            "network_calls",
            "next_arguments",
            "next_required_action",
            "next_tool",
            "ok",
            "open_questions",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "original_recommended_action",
            "pipeline_ok",
            "provider_calls",
            "public_output_approved",
            "quality_gaps",
            "ready_for_real_ticket_use",
            "ready_for_reviewer",
            "recommended_action",
            "result_kind",
            "review_summary",
            "reviewer_bundle_written",
            "schema_version",
            "semantic_review_ref",
            "should_be_kcs_article",
            "validation_ok",
            "workflow_state",
            "writes_files",
        ),
        "split_required_result": (
            "article_type",
            "atomic_item",
            "auto_publish_allowed",
            "automatic_item_retry_allowed",
            "blockers",
            "case_ref",
            "checks",
            "debug_code",
            "draft_request_ready",
            "evidence_valid",
            "failure_stage",
            "input_safety_ok",
            "item_candidates",
            "manual_draft_allowed",
            "network_calls",
            "next_required_action",
            "ok",
            "open_questions",
            "operator_choice_options",
            "operator_prompt",
            "operator_prompt_style",
            "original_article_type",
            "original_decision_status",
            "original_readiness_state",
            "original_recommended_action",
            "pipeline_ok",
            "provider_calls",
            "public_output_approved",
            "quality_gaps",
            "ready_for_real_ticket_use",
            "ready_for_reviewer",
            "recommended_action",
            "result_kind",
            "review_summary",
            "schema_version",
            "should_be_kcs_article",
            "validation_ok",
            "writes_files",
        ),
    }


def test_frozen_contract_paths_have_no_uncommitted_diff() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD", "--", *FROZEN_CONTRACT_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert not result.stdout.strip(), result.stdout
