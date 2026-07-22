from __future__ import annotations

from copy import deepcopy

import pytest

from kcs_adapters.desktop_authoring_pipeline import author_result, execute_pipeline
from kcs_adapters.desktop_draft_arguments import (
    draft_article_authoring_args_from_candidate,
)
from kcs_adapters.desktop_semantic_candidates import (
    ProjectedIssue,
    ProjectedIssueSet,
    SemanticProjectionLedgerEntry,
    desktop_candidate_set_from_semantic_issue_proposal,
    project_semantic_issue_proposals,
    semantic_projection_requires_terminal_review,
    semantic_projection_shadow_comparison,
)
from kcs_adapters.desktop_workflow import ApprovedSummaryPipelineStageError
from kcs_core.errors import ContractValidationError
from kcs_core.semantic_extraction import SemanticIssueProposalPacket


def _observation(text: str, *source_refs: str) -> dict[str, object]:
    return {"source_refs": list(source_refs), "text": text}


def _proposal_packet() -> dict[str, object]:
    return {
        "case_ref": "case-synthetic-001",
        "coverage_records": [],
        "extraction_source_ref": "extraction-synthetic-001",
        "issues": [
            {
                "answer_evidence": [],
                "cause_evidence": [
                    _observation("A required component is unavailable.", "excerpt-002")
                ],
                "context_evidence": [],
                "error_evidence": [
                    _observation(
                        "The expected service response is absent.",
                        "excerpt-001",
                    )
                ],
                "issue_ref": "issue-001",
                "question": None,
                "resolution_evidence": [
                    _observation("Restore the component and verify it.", "excerpt-003")
                ],
                "summary": _observation(
                    "A synthetic service task fails.", "excerpt-001"
                ),
                "symptoms": [
                    _observation(
                        "The expected service response is absent.", "excerpt-001"
                    )
                ],
                "verification_evidence": [],
            }
        ],
        "schema_version": "semantic_issue_proposal_v1",
        "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
    }


def _role_index() -> dict[str, dict[str, object]]:
    return {
        "excerpt-001": {
            "content_sha256": "1" * 64,
            "provenance_trusted": True,
            "roles": ["reported_symptom"],
            "visibility": "public_customer_safe",
        },
        "excerpt-002": {
            "content_sha256": "2" * 64,
            "provenance_trusted": True,
            "roles": ["supported_cause"],
            "visibility": "public_customer_safe",
        },
        "excerpt-003": {
            "content_sha256": "3" * 64,
            "provenance_trusted": True,
            "roles": ["supported_resolution"],
            "visibility": "public_customer_safe",
        },
    }


def _neutral_runtime_role_index() -> dict[str, dict[str, object]]:
    roles = _role_index()
    for entry in roles.values():
        entry["provenance_trusted"] = False
        entry["roles"] = ["unclassified_evidence"]
        entry["visibility"] = "internal_reviewer_only"
    return roles


def _two_issue_packet(
    *,
    identity_overlap: bool,
) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    packet = _proposal_packet()
    first_issue = packet["issues"][0]
    assert isinstance(first_issue, dict)
    second_cause_ref = "excerpt-002" if identity_overlap else "excerpt-004"
    second_issue = deepcopy(first_issue)
    second_issue.update(
        {
            "cause_evidence": [
                _observation("A second component state failed.", second_cause_ref)
            ],
            "issue_ref": "issue-002",
            "resolution_evidence": [
                _observation("Restore the second component.", "excerpt-005")
            ],
            "summary": _observation(
                "A second synthetic service task fails.", "excerpt-001"
            ),
        }
    )
    packet["issues"] = [first_issue, second_issue]
    extra_refs = ["excerpt-005"]
    if not identity_overlap:
        extra_refs.insert(0, "excerpt-004")
    packet["source_refs"] = [*packet["source_refs"], *extra_refs]
    roles = _role_index()
    if not identity_overlap:
        roles["excerpt-004"] = {
            "content_sha256": "4" * 64,
            "provenance_trusted": True,
            "roles": ["supported_cause"],
            "visibility": "public_customer_safe",
        }
    roles["excerpt-005"] = {
        "content_sha256": "5" * 64,
        "provenance_trusted": True,
        "roles": ["supported_resolution"],
        "visibility": "public_customer_safe",
    }
    return packet, roles


def _legacy_extraction() -> dict[str, object]:
    return {
        "case_ref": "case-synthetic-001",
        "extraction_source_ref": "legacy-extraction-synthetic-001",
        "items": [
            {
                "article_type_hint": "technical_scr",
                "candidate_id": "candidate-001",
                "candidate_origin": "customer_reported",
                "confirmed_facts": ["A required component is unavailable."],
                "environment": {},
                "kcs_item_status": "candidate_allowed",
                "product_relation": "plesk_owned",
                "resolution_steps": ["Restore the component and verify it."],
                "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
                "summary": "A synthetic service task fails.",
                "supportability": "supported",
                "supportability_basis": "not_checked",
                "supported_cause": "A required component is unavailable.",
                "supported_resolution_or_workaround": (
                    "Restore the component and verify it."
                ),
                "symptoms": ["The expected service response is absent."],
                "visibility_hint": "public_customer_safe",
            }
        ],
        "schema_version": "candidate_semantic_extraction_v1",
        "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
    }


def test_projection_derives_customer_issue_without_kcs_action_authority() -> None:
    projected = project_semantic_issue_proposals(_proposal_packet(), _role_index())

    assert projected.selectable_issue_refs == ("issue-001",)
    assert projected.issues[0].preliminary_article_type == "technical_scr"
    assert projected.issues[0].candidate_origin == "customer_reported"
    assert projected.issues[0].visibility_class == "public_customer_safe"
    assert projected.blocked_proposals == ()
    assert projected.unassigned_evidence == ()
    assert set(projected.issues[0].to_json_dict()) == {
        "candidate_origin",
        "issue_ref",
        "preliminary_article_type",
        "semantic_sha256",
        "source_refs",
        "summary",
        "visibility_class",
    }


def test_untrusted_runtime_provenance_stays_internal() -> None:
    roles = _role_index()
    for entry in roles.values():
        entry["provenance_trusted"] = False
        entry["visibility"] = "internal_reviewer_only"

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.selectable_issue_refs == ("issue-001",)
    assert projected.issues[0].candidate_origin == "support_discovered"
    assert projected.issues[0].visibility_class == "internal_reviewer_only"


def test_complete_grouped_issue_accepts_model_neutral_runtime_evidence() -> None:
    projected = project_semantic_issue_proposals(
        _proposal_packet(),
        _neutral_runtime_role_index(),
    )

    assert projected.selectable_issue_refs == ("issue-001",)
    assert projected.issues[0].candidate_origin == "support_discovered"
    assert projected.issues[0].visibility_class == "internal_reviewer_only"
    assert projected.blocked_proposals == ()


def test_neutral_runtime_evidence_does_not_bypass_required_resolution() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["resolution_evidence"] = []
    issue["context_evidence"] = [
        _observation("The third source remains bounded context.", "excerpt-003")
    ]

    projected = project_semantic_issue_proposals(
        packet,
        _neutral_runtime_role_index(),
    )

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == "evidence_shape_invalid"


def test_deterministic_non_issue_roles_cannot_form_grouped_issue() -> None:
    roles = _neutral_runtime_role_index()
    for entry in roles.values():
        entry["roles"] = ["internal_workflow_note"]

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == "source_role_missing"


@pytest.mark.parametrize(
    "reason_code",
    [
        "source_role_missing",
        "untrusted_provenance_visibility",
        "visibility_ambiguous",
    ],
)
def test_packet_level_safety_blocker_stays_terminal_with_valid_issue(
    reason_code: str,
) -> None:
    projected = ProjectedIssueSet(
        issues=(
            ProjectedIssue(
                issue_ref="issue-valid",
                summary="A valid synthetic issue.",
                preliminary_article_type="technical_scr",
                candidate_origin="support_discovered",
                visibility_class="internal_reviewer_only",
                source_refs=("excerpt-001",),
                semantic_sha256="1" * 64,
            ),
        ),
        coverage_ledger=(),
        unassigned_evidence=(),
        blocked_proposals=(
            SemanticProjectionLedgerEntry(
                record_ref="issue-blocked",
                outcome="proposal_blocked",
                reason_code=reason_code,
                source_refs=("excerpt-002",),
            ),
        ),
        selectable_issue_refs=("issue-valid",),
    )

    assert semantic_projection_requires_terminal_review(projected) is True


def test_untrusted_runtime_provenance_cannot_be_projected_as_public() -> None:
    roles = _role_index()
    for entry in roles.values():
        entry["provenance_trusted"] = False

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == (
        "untrusted_provenance_visibility"
    )


def test_projected_candidate_preserves_error_and_verification_observations() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["verification_evidence"] = [
        _observation("Confirm the operation now succeeds.", "excerpt-003")
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())

    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )

    assert candidates[0]["symptoms"] == ["The expected service response is absent."]
    assert candidates[0]["resolution_steps"] == [
        "Restore the component and verify it.",
        "Confirm the operation now succeeds.",
    ]
    assert set(projected.to_json_dict()) == {
        "blocked_proposals",
        "coverage_ledger",
        "issues",
        "selectable_issue_refs",
        "unassigned_evidence",
    }
    serialized = str(projected.to_json_dict())
    for forbidden in (
        "recommended_action",
        "reuse_search_status",
        "kcs_ready",
        "public_output_approved",
    ):
        assert forbidden not in serialized


def test_projection_separates_resolution_narrative_from_executable_steps() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["resolution_evidence"] = [
        _observation("The product address was corrected.", "excerpt-003"),
        _observation("Run plesk repair web.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())

    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )

    candidate = candidates[0]
    assert candidate["resolution_steps"] == ["Run plesk repair web."]
    assert candidate["supported_resolution_or_workaround"] == (
        "The product address was corrected.\n\nRun plesk repair web."
    )
    assert candidate["supported_resolution_or_workaround"].split("\n\n") == [
        "The product address was corrected.",
        "Run plesk repair web.",
    ]

    authoring_candidate = dict(candidate)
    authoring_candidate.pop("candidate_origin")
    authoring_candidate["environment"] = {"product": "Synthetic product"}
    execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=authoring_candidate,
            debug=False,
        )
    )


def test_projected_candidate_keeps_full_summary_and_bounds_display_title() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    long_summary = (
        "A synthetic operation returns no result after a configuration change "
        "and reports several related symptoms while the confirmed component "
        "state and supported recovery procedure remain part of one searchable "
        "technical issue."
    )
    assert len(long_summary) > 180
    issue["summary"] = _observation(long_summary, "excerpt-001")
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())

    candidates, outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )

    assert candidates[0]["summary"] == long_summary
    assert len(candidates[0]["title"]) <= 180
    assert outcomes[0]["title"] == candidates[0]["title"]


def test_projected_resolution_reference_uses_existing_article_review() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    issue["resolution_evidence"] = [
        _observation(
            f"The existing public support article is {public_url}.",
            "excerpt-003",
        ),
        _observation("Perform the supplied change.", "excerpt-003"),
        _observation("Confirm the expected result.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}
    execution = execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=candidate,
            debug=False,
        )
    )
    result = author_result(execution, schema_version="test")

    assert result["recommended_action"] == "flag_existing"
    assert result["reuse_search_status"] == "checked"
    assert result["selected_reuse_match"]["match_ref"] == "kb-123456789"
    assert result["existing_article_review"]["do_not_create_duplicate"] is True
    assert result["auto_publish_allowed"] is False
    assert result["public_output_approved"] is False


def test_projected_grounded_fix_reference_uses_existing_article_review() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    issue["resolution_evidence"] = [
        _observation(
            f"The supported fix is documented at {public_url}.",
            "excerpt-003",
        ),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}

    execution = execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=candidate,
            debug=False,
        )
    )
    result = author_result(execution, schema_version="test")

    assert result["recommended_action"] == "flag_existing"
    assert result["reuse_search_status"] == "checked"
    assert result["existing_article_review"]["do_not_create_duplicate"] is True


def test_projected_unrelated_fix_and_url_do_not_flag_existing_article() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    issue["resolution_evidence"] = [
        _observation("The issue was fixed manually.", "excerpt-003"),
        _observation(f"Public URL: {public_url}.", "excerpt-003"),
        _observation("Run plesk repair web.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}

    execution = execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=candidate,
            debug=False,
        )
    )
    result = author_result(execution, schema_version="test")

    assert result["recommended_action"] != "flag_existing"
    assert "existing_article_review" not in result


def test_projected_same_observation_fix_and_url_do_not_flag_existing_article() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    public_url = "https://support.plesk.com/hc/en-us/articles/123456789"
    issue["resolution_evidence"] = [
        _observation(
            f"The issue was fixed manually. Public URL: {public_url}.",
            "excerpt-003",
        ),
        _observation("Run plesk repair web.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}

    execution = execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=candidate,
            debug=False,
        )
    )
    result = author_result(execution, schema_version="test")

    assert result["recommended_action"] != "flag_existing"
    assert "existing_article_review" not in result


def test_projected_summary_only_article_reference_does_not_flag_existing() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation(
        "Follow https://support.plesk.com/hc/en-us/articles/123456789.",
        "excerpt-001",
    )
    issue["resolution_evidence"] = [
        _observation("Run plesk repair web.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}

    execution = execute_pipeline(
        draft_article_authoring_args_from_candidate(
            approved_summary_text="Approved sanitized synthetic summary.",
            candidate=candidate,
            debug=False,
        )
    )
    result = author_result(execution, schema_version="test")

    assert result["recommended_action"] != "flag_existing"
    assert "existing_article_review" not in result


@pytest.mark.parametrize(
    ("invalid_case", "expected_debug_code"),
    [
        ("missing_environment", "approved_summary_environment_required"),
        ("uncertain_cause", "approved_summary_supported_cause_uncertain"),
        ("destructive_step", "approved_summary_resolution_step_destructive"),
    ],
)
def test_projected_resolution_reference_keeps_safety_validation(
    invalid_case: str,
    expected_debug_code: str,
) -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["resolution_evidence"] = [
        _observation(
            "Use the existing public support article at "
            "https://support.plesk.com/hc/en-us/articles/123456789.",
            "excerpt-003",
        ),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}
    if invalid_case == "missing_environment":
        candidate["environment"] = {}
    elif invalid_case == "uncertain_cause":
        candidate["supported_cause"] = "The component is possibly unavailable."
    else:
        candidate["resolution_steps"] = [
            *candidate["resolution_steps"],
            "Run rm -rf /usr/local/synthetic/ before continuing.",
        ]

    with pytest.raises(ApprovedSummaryPipelineStageError) as exc_info:
        execute_pipeline(
            draft_article_authoring_args_from_candidate(
                approved_summary_text="Approved sanitized synthetic summary.",
                candidate=candidate,
                debug=False,
            )
        )

    assert exc_info.value.debug_code == expected_debug_code


def test_projected_unrelated_public_url_still_requires_resolution_detail() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = [
        _observation(
            "A product configuration requires a supported fix.",
            "excerpt-002",
        )
    ]
    issue["resolution_evidence"] = [
        _observation(
            "Public URL: "
            "https://support.plesk.com/hc/en-us/articles/123456789.",
            "excerpt-003",
        ),
        _observation("Perform the supplied change.", "excerpt-003"),
        _observation("Confirm the expected result.", "excerpt-003"),
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, _role_index())
    candidates, _outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )
    candidate = dict(candidates[0])
    candidate.pop("candidate_origin")
    candidate["environment"] = {"product": "Synthetic product"}

    with pytest.raises(ApprovedSummaryPipelineStageError) as exc_info:
        execute_pipeline(
            draft_article_authoring_args_from_candidate(
                approved_summary_text="Approved sanitized synthetic summary.",
                candidate=candidate,
                debug=False,
            )
        )

    assert exc_info.value.debug_code == "approved_summary_resolution_steps_incomplete"


def test_projection_derives_howto_from_question_and_resolution_shape() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = []
    issue["error_evidence"] = []
    issue["symptoms"] = []
    issue["question"] = _observation("How can the task be completed?", "excerpt-001")
    issue["answer_evidence"] = []
    issue["context_evidence"] = [
        _observation("The supported context was recorded.", "excerpt-002")
    ]

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues[0].preliminary_article_type == "howto_qa"


def test_neutral_runtime_evidence_projects_complete_howto_shape() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = []
    issue["error_evidence"] = []
    issue["symptoms"] = []
    issue["question"] = _observation("How can the task be completed?", "excerpt-001")
    issue["answer_evidence"] = [
        _observation(
            "Use the supported operation and verify the outcome.",
            "excerpt-002",
            "excerpt-003",
        )
    ]
    issue["resolution_evidence"] = []
    issue["context_evidence"] = []

    projected = project_semantic_issue_proposals(
        packet,
        _neutral_runtime_role_index(),
    )

    assert projected.selectable_issue_refs == ("issue-001",)
    assert projected.issues[0].preliminary_article_type == "howto_qa"
    assert projected.blocked_proposals == ()


def test_projection_keeps_question_for_same_problem_as_technical_scr() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["question"] = _observation(
        "How can the reported failure be resolved?",
        "excerpt-001",
    )

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues[0].preliminary_article_type == "technical_scr"


def test_projection_keeps_question_with_generic_symptom_as_howto() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["error_evidence"] = []
    issue["question"] = _observation(
        "How can the reported condition be resolved?",
        "excerpt-001",
    )

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues[0].preliminary_article_type == "howto_qa"


def test_projection_keeps_problem_without_literal_error_as_technical() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["error_evidence"] = []

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues[0].preliminary_article_type == "technical_scr"


def test_projection_blocks_resolution_without_problem_or_question() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = []
    issue["error_evidence"] = []
    issue["symptoms"] = []
    issue["question"] = None
    issue["answer_evidence"] = []
    issue["context_evidence"] = [
        _observation("Supporting context only.", "excerpt-001", "excerpt-002")
    ]

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues == ()
    assert projected.blocked_proposals[0].reason_code == "evidence_shape_invalid"


def test_projection_blocks_verification_without_problem_or_question() -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = []
    issue["error_evidence"] = []
    issue["symptoms"] = []
    issue["question"] = None
    issue["answer_evidence"] = []
    issue["resolution_evidence"] = []
    issue["verification_evidence"] = [
        _observation("A verification was recorded.", "excerpt-003")
    ]
    issue["context_evidence"] = [
        _observation("Supporting context only.", "excerpt-001", "excerpt-002")
    ]

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.issues == ()
    assert projected.blocked_proposals[0].reason_code == "evidence_shape_invalid"


@pytest.mark.parametrize("missing_field", ["cause_evidence", "resolution_evidence"])
def test_projection_blocks_technical_issue_without_identity_pair(
    missing_field: str,
) -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue[missing_field] = []
    missing_ref = {
        "cause_evidence": "excerpt-002",
        "resolution_evidence": "excerpt-003",
    }[missing_field]
    issue["context_evidence"] = [
        _observation("The omitted field remains source-covered.", missing_ref)
    ]

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == "evidence_shape_invalid"


def test_projection_blocks_symptomless_technical_issue_and_preserves_sibling() -> None:
    packet, roles = _two_issue_packet(identity_overlap=False)
    issues = packet["issues"]
    assert isinstance(issues, list)
    first_issue = issues[0]
    assert isinstance(first_issue, dict)
    first_issue["symptoms"] = []
    first_issue["error_evidence"] = []

    proposal = SemanticIssueProposalPacket.from_json_dict(packet)
    projected = project_semantic_issue_proposals(proposal, roles)
    candidates, outcomes = desktop_candidate_set_from_semantic_issue_proposal(
        proposal,
        projected,
    )

    assert projected.selectable_issue_refs == ("issue-002",)
    assert projected.blocked_proposals[0].record_ref == "issue-001"
    assert projected.blocked_proposals[0].reason_code == "evidence_shape_invalid"
    assert semantic_projection_requires_terminal_review(projected) is False
    assert [candidate["item_ref"] for candidate in candidates] == ["issue-002"]
    assert candidates[0]["symptoms"]
    assert any(
        outcome["item_ref"] == "issue-001"
        and outcome["outcome"] == "blocked_need_more_evidence"
        for outcome in outcomes
    )


def test_error_evidence_contributes_to_shadow_semantic_fingerprint() -> None:
    baseline = project_semantic_issue_proposals(_proposal_packet(), _role_index())
    changed_packet = _proposal_packet()
    issue = changed_packet["issues"][0]
    assert isinstance(issue, dict)
    issue["error_evidence"] = [
        _observation("A different grounded failure is visible.", "excerpt-001")
    ]

    changed = project_semantic_issue_proposals(changed_packet, _role_index())

    assert baseline.issues[0].semantic_sha256 != changed.issues[0].semantic_sha256


def test_projection_derives_support_discovered_origin_without_suppression() -> None:
    roles = _role_index()
    roles["excerpt-001"]["roles"] = ["supported_cause"]

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.issues[0].candidate_origin == "support_discovered"
    assert projected.selectable_issue_refs == ("issue-001",)


@pytest.mark.parametrize(
    ("reason_code", "trusted_role"),
    [
        ("internal_workflow_note", "internal_workflow_note"),
        ("ticket_metadata", "ticket_metadata"),
        ("formatting_artifact", "formatting_artifact"),
    ],
)
def test_projection_auto_accepts_only_matching_deterministic_coverage(
    reason_code: str,
    trusted_role: str,
) -> None:
    packet = _proposal_packet()
    packet["source_refs"].append("excerpt-004")
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": reason_code,
            "source_refs": ["excerpt-004"],
        }
    ]
    roles = _role_index()
    roles["excerpt-004"] = {
        "content_sha256": "4" * 64,
        "provenance_trusted": True,
        "roles": [trusted_role],
        "visibility": "internal_reviewer_only",
    }

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.coverage_ledger[0].outcome == "coverage_accepted"
    assert projected.coverage_ledger[0].reason_code == reason_code
    assert projected.unassigned_evidence == ()


def test_neutral_runtime_evidence_cannot_be_reclassified_as_metadata() -> None:
    packet = _proposal_packet()
    packet["source_refs"].append("excerpt-004")
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "ticket_metadata",
            "source_refs": ["excerpt-004"],
        }
    ]
    roles = _neutral_runtime_role_index()
    roles["excerpt-004"] = {
        "content_sha256": "4" * 64,
        "provenance_trusted": False,
        "roles": ["unclassified_evidence"],
        "visibility": "internal_reviewer_only",
    }

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.coverage_ledger[0].outcome == "coverage_rejected"
    assert projected.coverage_ledger[0].reason_code == "coverage_role_incompatible"
    assert projected.unassigned_evidence[0].source_ref == "excerpt-004"


def test_projection_auto_accepts_duplicate_only_with_matching_hash() -> None:
    packet = _proposal_packet()
    packet["source_refs"].append("excerpt-004")
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": "excerpt-001",
            "reason_code": "duplicate_excerpt",
            "source_refs": ["excerpt-004"],
        }
    ]
    roles = _role_index()
    roles["excerpt-004"] = {
        "content_sha256": "1" * 64,
        "provenance_trusted": True,
        "roles": ["duplicate_excerpt"],
        "visibility": "public_customer_safe",
    }

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.coverage_ledger[0].outcome == "coverage_accepted"
    assert projected.unassigned_evidence == ()


@pytest.mark.parametrize(
    "reason_code",
    [
        "internal_workflow_note",
        "ticket_metadata",
        "duplicate_excerpt",
        "formatting_artifact",
    ],
)
def test_customer_dialogue_never_auto_accepts_as_coverage(
    reason_code: str,
) -> None:
    packet = _proposal_packet()
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["cause_evidence"] = []
    issue["resolution_evidence"] = []
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": (
                "excerpt-001" if reason_code == "duplicate_excerpt" else None
            ),
            "reason_code": reason_code,
            "source_refs": ["excerpt-002", "excerpt-003"],
        }
    ]

    projected = project_semantic_issue_proposals(packet, _role_index())

    assert projected.coverage_ledger[0].outcome == "coverage_rejected"
    assert projected.coverage_ledger[0].reason_code == (
        "customer_support_coverage_requires_review"
    )
    assert {entry.source_ref for entry in projected.unassigned_evidence} == {
        "excerpt-002",
        "excerpt-003",
    }


def test_accepted_coverage_does_not_remove_issue_for_same_source() -> None:
    packet = _proposal_packet()
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "ticket_metadata",
            "source_refs": ["excerpt-001"],
        }
    ]
    roles = _role_index()
    roles["excerpt-001"]["roles"] = ["reported_symptom", "ticket_metadata"]

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.selectable_issue_refs == ("issue-001",)
    assert projected.coverage_ledger[0].outcome == "coverage_rejected"


def test_projection_ledger_entry_field_sets_are_stable() -> None:
    packet = _proposal_packet()
    packet["issues"] = []
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "ticket_metadata",
            "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
        }
    ]
    unassigned = project_semantic_issue_proposals(packet, _role_index())

    base_fields = {"outcome", "reason_code", "record_ref", "source_refs"}
    assert set(unassigned.coverage_ledger[0].to_json_dict()) == base_fields
    assert set(unassigned.unassigned_evidence[0].to_json_dict()) == base_fields


def test_shared_identity_evidence_does_not_create_runtime_guard() -> None:
    packet, roles = _two_issue_packet(identity_overlap=True)

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.selectable_issue_refs == ("issue-001", "issue-002")
    assert projected.blocked_proposals == ()


def test_shared_non_identity_evidence_remains_valid() -> None:
    packet, roles = _two_issue_packet(identity_overlap=False)

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.selectable_issue_refs == ("issue-001", "issue-002")
    assert projected.blocked_proposals == ()


def test_ambiguous_visibility_blocks_proposal() -> None:
    roles = _role_index()
    roles["excerpt-003"]["visibility"] = "internal_reviewer_only"

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == "visibility_ambiguous"


def test_unsafe_private_visibility_blocks_proposal() -> None:
    roles = _role_index()
    for entry in roles.values():
        entry["visibility"] = "unsafe_private"

    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    assert projected.selectable_issue_refs == ()
    assert projected.blocked_proposals[0].reason_code == "visibility_ambiguous"


def test_conflicting_bookkeeping_roles_fail_closed() -> None:
    packet = _proposal_packet()
    packet["source_refs"].append("excerpt-004")
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "ticket_metadata",
            "source_refs": ["excerpt-004"],
        }
    ]
    roles = _role_index()
    roles["excerpt-004"] = {
        "content_sha256": "4" * 64,
        "provenance_trusted": True,
        "roles": ["ticket_metadata", "formatting_artifact"],
        "visibility": "internal_reviewer_only",
    }

    projected = project_semantic_issue_proposals(packet, roles)

    assert projected.coverage_ledger[0].outcome == "coverage_rejected"
    assert projected.coverage_ledger[0].reason_code == "coverage_role_incompatible"
    assert projected.unassigned_evidence[0].source_ref == "excerpt-004"


def test_role_index_must_exactly_cover_packet_sources() -> None:
    roles = _role_index()
    roles.pop("excerpt-003")

    with pytest.raises(ContractValidationError, match="role index invalid"):
        project_semantic_issue_proposals(_proposal_packet(), roles)


def test_shadow_comparison_emits_only_codes_counts_and_hashes() -> None:
    projected = project_semantic_issue_proposals(_proposal_packet(), _role_index())
    comparison = semantic_projection_shadow_comparison(
        legacy_extraction=_legacy_extraction(),
        projected=projected,
    )

    assert comparison.codes == (
        "shadow_issue_count_match",
        "shadow_selectable_count_match",
        "shadow_issue_source_mapping_match",
        "shadow_nonissue_source_mapping_match",
        "shadow_blocked_source_mapping_match",
        "shadow_origin_distribution_match",
        "shadow_article_type_distribution_match",
        "shadow_visibility_distribution_match",
        "shadow_semantic_content_match",
        "shadow_source_coverage_complete",
        "shadow_blocked_proposals_absent",
    )
    payload = comparison.to_json_dict()
    assert len(payload["legacy_sha256"]) == 64
    assert len(payload["projected_sha256"]) == 64
    assert "Synthetic" not in str(payload)


def test_shadow_comparison_runs_legacy_and_projection_paths_side_by_side() -> None:
    projected = project_semantic_issue_proposals(_proposal_packet(), _role_index())

    comparison = semantic_projection_shadow_comparison(
        legacy_extraction=_legacy_extraction(),
        projected=projected,
    )

    assert comparison.codes[:2] == (
        "shadow_issue_count_match",
        "shadow_selectable_count_match",
    )


def test_shadow_comparison_maps_legacy_no_article_to_accepted_coverage() -> None:
    legacy = _legacy_extraction()
    legacy_item = deepcopy(legacy["items"][0])
    legacy_item.update(
        {
            "article_type_hint": "none",
            "candidate_id": "candidate-002",
            "kcs_item_status": "no_article",
            "product_relation": "customer_environment_specific",
            "resolution_steps": [],
            "source_refs": ["excerpt-004"],
            "supported_cause": None,
            "supported_resolution_or_workaround": None,
            "symptoms": [],
        }
    )
    legacy["items"].append(legacy_item)
    legacy["source_refs"].append("excerpt-004")
    packet = _proposal_packet()
    packet["source_refs"].append("excerpt-004")
    packet["coverage_records"] = [
        {
            "coverage_ref": "coverage-001",
            "duplicate_of_source_ref": None,
            "reason_code": "internal_workflow_note",
            "source_refs": ["excerpt-004"],
        }
    ]
    roles = _role_index()
    roles["excerpt-004"] = {
        "content_sha256": "4" * 64,
        "provenance_trusted": True,
        "roles": ["internal_workflow_note"],
        "visibility": "internal_reviewer_only",
    }
    projected = project_semantic_issue_proposals(packet, roles)

    comparison = semantic_projection_shadow_comparison(
        legacy_extraction=legacy,
        projected=projected,
    )

    assert "shadow_issue_count_match" in comparison.codes
    assert "shadow_nonissue_source_mapping_match" in comparison.codes


def test_shadow_comparison_codes_semantic_drift_when_counts_match() -> None:
    roles = _role_index()
    roles["excerpt-001"]["roles"] = ["supported_cause"]
    projected = project_semantic_issue_proposals(_proposal_packet(), roles)

    comparison = semantic_projection_shadow_comparison(
        legacy_extraction=_legacy_extraction(),
        projected=projected,
    )

    assert "shadow_issue_count_match" in comparison.codes
    assert "shadow_selectable_count_match" in comparison.codes
    assert "shadow_origin_distribution_mismatch" in comparison.codes


def test_projection_has_no_ticket_or_model_specific_branching_surface() -> None:
    first = project_semantic_issue_proposals(_proposal_packet(), _role_index())
    packet = deepcopy(_proposal_packet())
    issue = packet["issues"][0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation("A different synthetic task fails.", "excerpt-001")
    second = project_semantic_issue_proposals(packet, _role_index())

    assert first.issues[0].preliminary_article_type == (
        second.issues[0].preliminary_article_type
    )
    assert first.issues[0].candidate_origin == second.issues[0].candidate_origin
    assert first.selectable_issue_refs == second.selectable_issue_refs
