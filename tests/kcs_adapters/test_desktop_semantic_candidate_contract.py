from __future__ import annotations

import pytest

from kcs_adapters import desktop_semantic_review
from kcs_adapters.desktop_semantic_candidate_contract import (
    semantic_contract_debug_code,
    semantic_issue_proposal_contract_metadata,
    semantic_submission_correction,
    semantic_submission_correction_stage,
)
from kcs_adapters.desktop_semantic_review import (
    SemanticReviewError,
    semantic_issue_proposal_contract_packet,
    semantic_review_packet,
)
from kcs_adapters.desktop_tool_results import (
    tool_result_text,
    validate_tool_structured_content,
)
from kcs_adapters.desktop_tool_schemas import tool_output_schema
from kcs_core.errors import ContractValidationError
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS,
    SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    SemanticIssueProposalPacket,
)


@pytest.mark.parametrize(
    ("debug_code", "expected_stage"),
    [
        ("semantic_observation_shape_invalid", "structure"),
        ("semantic_observation_text_not_extractive", "grounding"),
        ("semantic_issue_entry_speaker_incompatible", "grounding"),
        ("semantic_review_submission_invalid", None),
    ],
)
def test_semantic_corrections_have_bounded_stages(
    debug_code: str,
    expected_stage: str | None,
) -> None:
    assert semantic_submission_correction_stage(debug_code) == expected_stage


def _proposal_payload() -> dict[str, object]:
    return {
        "case_ref": "semantic-case-001",
        "coverage_records": [],
        "extraction_source_ref": "semantic-proposal-001",
        "issues": [
            {
                "answer_evidence": [],
                "cause_evidence": [],
                "context_evidence": [],
                "issue_ref": "issue-001",
                "question": None,
                "resolution_evidence": [],
                "summary": {
                    "source_refs": ["excerpt-001"],
                    "text": "A bounded synthetic issue summary.",
                },
                "symptoms": [],
                "verification_evidence": [],
            }
        ],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": ["excerpt-001"],
    }


@pytest.mark.parametrize(
    "value",
    [
        "not-json",
        "[]",
        '"json scalar"',
        "```json\n{}\n```",
    ],
)
def test_semantic_proposal_transport_rejects_non_object_json(value: str) -> None:
    with pytest.raises(ContractValidationError, match="payload must be a JSON object"):
        desktop_semantic_review._normalized_semantic_issue_proposal(value)


def test_issue_proposal_contract_exposes_only_canonical_closed_fields() -> None:
    metadata = semantic_issue_proposal_contract_metadata()

    assert metadata["schema_version"] == SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION
    assert metadata["proposal_field_contracts"] == {
        "reason_code": {
            "accepted_values": [
                "internal_workflow_note",
                "ticket_metadata",
                "duplicate_excerpt",
                "formatting_artifact",
            ],
            "invalid_debug_code": "semantic_coverage_reason_invalid",
        },
    }
    assert metadata["proposal_shape_contracts"]["observation"] == {
        "source_refs": "non_empty_allowed_source_ref_list",
        "text": "exact_text_from_one_referenced_selected_excerpt_except_summary",
    }
    assert metadata["issue_boundary_contract"]["technical_issue_identity"] == (
        "supported_cause_and_supported_resolution_or_workaround_pair"
    )
    boundary_contract = metadata["issue_boundary_contract"]
    assert boundary_contract["resolved_problem_rule"] == (
        "If one problem is resolved before a distinct failure remains, "
        "propose separate issues even when the later diagnostic or repair "
        "action was triggered by the first problem."
    )
    assert boundary_contract["causal_chain_rule"] == (
        "Treat a symptom, intermediate diagnostic fact, and confirmed cause "
        "as one issue when the evidence links them to one resolution outcome. "
        "Do not propose stages of that causal chain as separate issues."
    )
    assert boundary_contract["final_partition_check"] == [
        "compare_every_proposed_issue_with_every_other_issue_before_submit",
        (
            "group_evidence_by_independently_searchable_problem_or_question_"
            "and_its_linked_resolution_outcome"
        ),
        (
            "attach_diagnostic_or_repair_output_to_parent_when_it_is_part_of_"
            "the_same_causal_chain_and_has_no_independent_issue_identity"
        ),
        (
            "keep_independent_unresolved_customer_problem_separate_even_"
            "without_resolution_evidence"
        ),
        "do_not_merge_distinct_issues_only_to_complete_evidence_shape",
    ]
    assert (
        "same_linked_causal_chain_and_resolution_outcome"
        in boundary_contract["merge_signals"]
    )
    assert (
        "one_problem_resolved_before_distinct_failure_remains"
        in boundary_contract["split_signals"]
    )
    assert (
        "later_diagnostic_or_repair_action_triggered_by_earlier_issue"
        in boundary_contract["not_issue_identity_by_itself"]
    )
    assert boundary_contract["not_split_by_itself"] == [
        "different_wording_for_stages_of_one_linked_causal_chain",
        "intermediate_diagnostic_fact_within_one_linked_causal_chain",
    ]
    assert metadata["issue_shape_contract"]["ambiguous_shape"] == "fail_closed"


def test_semantic_issue_contract_packet_has_no_migration_or_candidate_fields() -> None:
    packet = semantic_issue_proposal_contract_packet(
        allowed_source_refs=("excerpt-001", "excerpt-002"),
        semantic_review_ref="semantic-review-contract-001",
    )

    assert packet["proposal_field_contracts"]
    assert packet["required_submit_shape"] == {
        "semantic_issue_proposal": {
            "case_ref": "semantic-review-contract-001",
            "coverage_records": [],
            "extraction_source_ref": "semantic-proposal-submit-001",
            "issues": [],
            "schema_version": "semantic_issue_proposal_v1",
            "source_refs": ["excerpt-001", "excerpt-002"],
        }
    }
    for retired_field in (
        "active_output_schema",
        "allowed_output_schema",
        "candidate_field_contracts",
        "runtime_default",
        "shadow_mode",
    ):
        assert retired_field not in packet


def test_semantic_review_packet_uses_only_issue_proposal_shape() -> None:
    packet = semantic_review_packet(
        excerpts=[
            {
                "role": "reported_symptom",
                "source_ref": "excerpt-001",
                "text": "Synthetic customer-visible issue.",
            }
        ],
        semantic_review_ref="semantic-review-active-001",
    )

    assert packet["result_kind"] == "semantic_review_packet"
    assert "semantic_issue_proposal" in packet["required_submit_shape"]
    assert "candidate_semantic_extraction" not in packet["required_submit_shape"]
    assert packet["manual_draft_allowed"] is False
    assert packet["public_output_approved"] is False
    assert "Do not add local workstation paths" in packet["task"]
    assert "absent from selected_excerpts" in packet["task"]


@pytest.mark.parametrize(
    "source_refs",
    [
        tuple(
            f"excerpt-{index:03d}"
            for index in range(SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS + 1)
        ),
        ("excerpt-001", "excerpt-001"),
        ("unsafe/source-ref",),
    ],
)
def test_issue_proposal_contract_packet_applies_source_ref_bounds(
    source_refs: tuple[str, ...],
) -> None:
    with pytest.raises(SemanticReviewError) as captured:
        semantic_issue_proposal_contract_packet(
            allowed_source_refs=source_refs,
            semantic_review_ref="semantic-review-contract-001",
        )

    assert captured.value.debug_code == "semantic_issue_source_refs_invalid"


def test_issue_proposal_contract_packet_reports_invalid_review_ref() -> None:
    with pytest.raises(SemanticReviewError) as captured:
        semantic_issue_proposal_contract_packet(
            allowed_source_refs=("excerpt-001",),
            semantic_review_ref="unsafe/review-ref",
        )

    assert captured.value.debug_code == "semantic_issue_review_ref_invalid"


@pytest.mark.parametrize(
    ("message", "debug_code", "field_name"),
    [
        (
            "unsupported semantic reason_code",
            "semantic_coverage_reason_invalid",
            "reason_code",
        ),
    ],
)
def test_issue_proposal_enum_failures_have_bounded_corrections(
    message: str,
    debug_code: str,
    field_name: str,
) -> None:
    assert semantic_contract_debug_code(message) == debug_code
    correction = semantic_submission_correction(debug_code)

    assert correction is not None
    assert correction["field_name"] == field_name
    assert correction["accepted_values"]
    assert "suggested_value" not in correction


@pytest.mark.parametrize(
    ("message", "debug_code"),
    [
        ("semantic coverage source refs invalid", "semantic_coverage_shape_invalid"),
        (
            "semantic duplicate coverage source ref invalid",
            "semantic_coverage_shape_invalid",
        ),
        (
            "semantic issue proposal refs invalid",
            "semantic_issue_proposal_shape_invalid",
        ),
        (
            "sanitized input contains unsafe value",
            "semantic_review_unsafe_value_blocked",
        ),
        (
            "issue_ref must be an opaque safe reference",
            "semantic_ref_shape_invalid",
        ),
        (
            "semantic source_refs invalid",
            "semantic_source_refs_shape_invalid",
        ),
        (
            "payload must be a JSON object",
            "semantic_issue_proposal_shape_invalid",
        ),
    ],
)
def test_issue_proposal_shape_failures_have_no_guessed_correction(
    message: str,
    debug_code: str,
) -> None:
    assert semantic_contract_debug_code(message) == debug_code
    assert semantic_submission_correction(debug_code) is None


@pytest.mark.parametrize(
    "message",
    [
        "semantic resolution_evidence invalid",
        "text must be a non-empty string",
    ],
)
def test_observation_shape_failures_share_one_static_correction(
    message: str,
) -> None:
    debug_code = semantic_contract_debug_code(message)
    correction = semantic_submission_correction(debug_code)

    assert debug_code == "semantic_observation_shape_invalid"
    assert correction is not None
    assert correction["field_name"] == "observation_fields"
    assert "non-empty" in correction["instruction"]
    assert "suggested_value" not in correction


def test_non_extractive_observation_has_bounded_exact_copy_correction() -> None:
    correction = semantic_submission_correction(
        "semantic_observation_text_not_extractive"
    )

    assert correction is not None
    assert correction["correction_kind"] == "submit_shape"
    assert correction["field_name"] == "observation_text"
    assert "exactly" in correction["instruction"]
    assert "summary" in correction["instruction"]
    assert "suggested_value" not in correction


def test_support_owned_issue_entry_has_bounded_speaker_correction() -> None:
    correction = semantic_submission_correction(
        "semantic_issue_entry_speaker_incompatible"
    )

    assert correction is not None
    assert correction["correction_kind"] == "submit_shape"
    assert correction["field_name"] == "symptoms_or_question_source_refs"
    assert "customer-authored" in correction["instruction"]
    assert "unknown" in correction["instruction"]
    assert "suggested_value" not in correction


@pytest.mark.parametrize(
    ("debug_code", "field_name"),
    [
        ("semantic_issue_case_ref_mismatch", "case_ref"),
        ("semantic_issue_candidate_limit_exceeded", "issues"),
        ("semantic_issue_coverage_incomplete", "source_coverage"),
        ("semantic_issue_top_level_source_refs_mismatch", "source_refs"),
        ("semantic_observation_shape_invalid", "observation_fields"),
    ],
)
def test_issue_proposal_submit_shape_failures_have_bounded_correction(
    debug_code: str,
    field_name: str,
) -> None:
    correction = semantic_submission_correction(debug_code)

    assert correction is not None
    assert correction["correction_kind"] == "submit_shape"
    assert correction["field_name"] == field_name
    assert correction["instruction"]


def test_parser_coverage_enum_failure_round_trips_through_correction() -> None:
    payload = _proposal_payload()
    payload["issues"] = []
    payload["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "unknown_coverage_reason",
            "source_refs": ["excerpt-001"],
        }
    ]

    with pytest.raises(ContractValidationError) as captured:
        SemanticIssueProposalPacket.from_json_dict(payload)

    debug_code = semantic_contract_debug_code(str(captured.value))
    correction = semantic_submission_correction(debug_code)
    assert correction is not None
    records = payload["coverage_records"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    record["reason_code"] = correction["accepted_values"][0]

    parsed = SemanticIssueProposalPacket.from_json_dict(payload)

    assert parsed.coverage_records[0].reason_code == "internal_workflow_note"


def test_contract_metadata_returns_fresh_payloads() -> None:
    first = semantic_issue_proposal_contract_metadata()
    first["proposal_field_contracts"]["reason_code"]["accepted_values"].append(
        "invalid"
    )

    second = semantic_issue_proposal_contract_metadata()

    assert (
        "invalid"
        not in second["proposal_field_contracts"]["reason_code"]["accepted_values"]
    )


@pytest.mark.parametrize(
    "debug_code",
    [
        "semantic_coverage_reason_invalid",
        "semantic_issue_entry_speaker_incompatible",
        "semantic_issue_case_ref_mismatch",
        "semantic_observation_text_not_extractive",
    ],
)
def test_correction_object_and_text_pass_output_safety_boundaries(
    debug_code: str,
) -> None:
    correction = semantic_submission_correction(debug_code)
    assert correction is not None
    correction["retry_allowed"] = True
    structured = {
        "auto_publish_allowed": False,
        "debug_code": debug_code,
        "draft_generated": False,
        "failure_stage": "semantic_extraction",
        "manual_draft_allowed": False,
        "next_required_action": "operator_review_semantic_submission_blocker",
        "ok": False,
        "public_output_approved": False,
        "recommended_action": "blocked",
        "result_kind": "draft_article_authoring",
        "reviewer_bundle_written": False,
        "schema_version": "kcs_authoring_mvp_v1",
        "semantic_submission_correction": correction,
        "workflow_state": "semantic_review_submit_blocked",
        "writes_files": False,
    }

    validate_tool_structured_content(structured, tool_output_schema())
    rendered_text = tool_result_text(structured)
    ensure_safe_sanitized_payload(correction)
    ensure_safe_sanitized_payload(rendered_text)
    assert "semantic_issue_proposal" in rendered_text


@pytest.mark.parametrize(
    "correction",
    [
        {
            "accepted_values": ["one"],
            "field_name": "unknown_field",
            "retry_allowed": True,
        },
        {
            "accepted_values": ["ticket_metadata", "invented"],
            "field_name": "reason_code",
            "invalid_debug_code": "semantic_coverage_reason_invalid",
            "retry_allowed": True,
        },
        {
            "correction_kind": "submit_shape",
            "field_name": "case_ref",
            "instruction": "Use a guessed reference.",
            "retry_allowed": True,
        },
    ],
)
def test_result_text_rejects_unknown_or_modified_correction(
    correction: dict[str, object],
) -> None:
    with pytest.raises(
        ContractValidationError,
        match="semantic correction contract invalid",
    ):
        tool_result_text(
            {
                "debug_code": "semantic_coverage_reason_invalid",
                "result_kind": "draft_article_authoring",
                "semantic_submission_correction": correction,
                "workflow_state": "semantic_review_submit_blocked",
            }
        )
