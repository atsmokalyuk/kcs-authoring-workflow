from __future__ import annotations

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.semantic_extraction import (
    SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS,
    SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    SemanticCoverageRecord,
    SemanticIssueProposalPacket,
)


def _observation(text: str, *source_refs: str) -> dict[str, object]:
    return {"source_refs": list(source_refs), "text": text}


def _issue() -> dict[str, object]:
    return {
        "answer_evidence": [],
        "cause_evidence": [
            _observation(
                "A confirmed configuration state caused the failure.",
                "excerpt-002",
            )
        ],
        "context_evidence": [],
        "error_evidence": [
            _observation("The operation returns a visible error.", "excerpt-001")
        ],
        "issue_ref": "issue-001",
        "question": None,
        "resolution_evidence": [
            _observation(
                "Support applied a bounded corrective procedure.",
                "excerpt-002",
            )
        ],
        "summary": _observation(
            "A customer-visible product operation fails.",
            "excerpt-001",
        ),
        "symptoms": [
            _observation("The operation returns a visible error.", "excerpt-001")
        ],
        "verification_evidence": [],
    }


def _packet() -> dict[str, object]:
    return {
        "case_ref": "semantic-case-001",
        "coverage_records": [
            {
                "coverage_ref": "coverage-001",
                "duplicate_of_source_ref": None,
                "reason_code": "internal_workflow_note",
                "source_refs": ["excerpt-003"],
            }
        ],
        "extraction_source_ref": "semantic-proposal-001",
        "issues": [_issue()],
        "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
        "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
    }


def _question_issue() -> dict[str, object]:
    return {
        "answer_evidence": [
            _observation(
                "Support provided a bounded answer grounded in the case.",
                "excerpt-005",
            )
        ],
        "cause_evidence": [],
        "context_evidence": [],
        "error_evidence": [],
        "issue_ref": "issue-002",
        "question": _observation(
            "The customer asks how to restore an expected setting.",
            "excerpt-004",
        ),
        "resolution_evidence": [],
        "summary": _observation(
            "An expected setting needs a documented restoration path.",
            "excerpt-004",
        ),
        "symptoms": [],
        "verification_evidence": [],
    }


def test_proposal_packet_accepts_observations_and_separate_coverage() -> None:
    packet = SemanticIssueProposalPacket.from_json_dict(_packet())

    assert packet.schema_version == "semantic_issue_proposal_v1"
    assert [issue.issue_ref for issue in packet.issues] == ["issue-001"]
    assert packet.issues[0].source_refs() == ("excerpt-001", "excerpt-002")
    assert packet.coverage_records[0].reason_code == "internal_workflow_note"
    assert packet.to_json_dict() == _packet()


def test_proposal_packet_accepts_omitted_optional_error_evidence() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue.pop("error_evidence")

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert packet.issues[0].error_evidence == ()
    assert packet.to_json_dict()["issues"][0]["error_evidence"] == []


def test_proposal_packet_accepts_omitted_empty_answer_evidence() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue.pop("answer_evidence")

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert packet.issues[0].answer_evidence == ()
    assert packet.to_json_dict()["issues"][0]["answer_evidence"] == []


def test_proposal_packet_bounds_error_evidence_like_other_observations() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["error_evidence"] = [
        _observation("A bounded error observation.", "excerpt-001") for _ in range(25)
    ]

    with pytest.raises(
        ContractValidationError,
        match="semantic error_evidence invalid",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_allows_pure_bookkeeping_without_fake_issue() -> None:
    payload = _packet()
    payload["issues"] = []
    payload["source_refs"] = ["excerpt-003"]

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert packet.issues == ()
    assert len(packet.coverage_records) == 1


def test_proposal_packet_rejects_model_owned_kcs_action_field() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["kcs_item_status"] = "no_article"

    with pytest.raises(ContractValidationError, match="unsupported field"):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_rejects_unsafe_observation_without_echo() -> None:
    private_value = "person@example.com"
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation(private_value, "excerpt-001")

    with pytest.raises(ContractValidationError) as captured:
        SemanticIssueProposalPacket.from_json_dict(payload)

    assert private_value not in str(captured.value)


def test_proposal_packet_rejects_oversized_observation_without_echo() -> None:
    oversized_value = "A" * 4_001
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation(oversized_value, "excerpt-001")

    with pytest.raises(
        ContractValidationError,
        match="semantic observation text invalid",
    ) as captured:
        SemanticIssueProposalPacket.from_json_dict(payload)

    assert oversized_value not in str(captured.value)


def test_proposal_packet_rejects_oversized_total_payload() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["context_evidence"] = [
        _observation("A" * 3_900, "excerpt-002") for _ in range(20)
    ]

    with pytest.raises(
        ContractValidationError,
        match="semantic issue proposal packet too large",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_rejects_too_many_source_refs() -> None:
    payload = _packet()
    source_refs = [
        f"excerpt-{index:03d}"
        for index in range(SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS + 1)
    ]
    payload["source_refs"] = source_refs
    payload["coverage_records"] = []
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation("A bounded issue summary.", *source_refs)
    issue["symptoms"] = []
    issue["cause_evidence"] = []
    issue["resolution_evidence"] = []

    with pytest.raises(
        ContractValidationError,
        match="semantic source_refs invalid",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    ("field_name", "item"),
    [
        ("issues", _issue()),
        (
            "coverage_records",
            {
                "coverage_ref": "coverage-001",
                "duplicate_of_source_ref": None,
                "reason_code": "internal_workflow_note",
                "source_refs": ["excerpt-001"],
            },
        ),
    ],
)
def test_proposal_packet_rejects_oversized_item_collections_before_parsing(
    field_name: str,
    item: dict[str, object],
) -> None:
    payload = _packet()
    payload["issues"] = []
    payload["coverage_records"] = []
    payload[field_name] = [dict(item) for _ in range(25)]

    with pytest.raises(ContractValidationError, match="items invalid"):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_rejects_unassigned_source_evidence() -> None:
    payload = _packet()
    coverage = payload["coverage_records"]
    assert isinstance(coverage, list)
    coverage.clear()

    with pytest.raises(
        ContractValidationError,
        match="semantic issue proposal coverage incomplete",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_rejects_observation_ref_outside_packet() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["summary"] = _observation("A bounded issue summary.", "excerpt-999")

    with pytest.raises(
        ContractValidationError,
        match="semantic issue proposal source refs invalid",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_proposal_packet_rejects_retired_boundary_uncertainties_field() -> None:
    payload = _packet()
    issues = payload["issues"]
    assert isinstance(issues, list)
    issue = issues[0]
    assert isinstance(issue, dict)
    issue["boundary_uncertainties"] = []

    with pytest.raises(
        ContractValidationError,
        match="semantic issue proposal contains unsupported field",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    ("reason_code", "duplicate_of_source_ref"),
    [
        ("duplicate_excerpt", None),
        ("ticket_metadata", "excerpt-001"),
    ],
)
def test_coverage_duplicate_reference_matches_reason(
    reason_code: str,
    duplicate_of_source_ref: str | None,
) -> None:
    with pytest.raises(ContractValidationError):
        SemanticCoverageRecord.from_json_dict(
            {
                "coverage_ref": "coverage-001",
                "duplicate_of_source_ref": duplicate_of_source_ref,
                "reason_code": reason_code,
                "source_refs": ["excerpt-003"],
            }
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("accepted", True),
        ("operator_excluded", True),
        ("kcs_item_status", "no_article"),
        ("public_output_approved", False),
    ],
)
def test_coverage_proposal_rejects_acceptance_and_action_authority(
    field_name: str,
    value: object,
) -> None:
    payload: dict[str, object] = {
        "coverage_ref": "coverage-001",
        "duplicate_of_source_ref": None,
        "reason_code": "internal_workflow_note",
        "source_refs": ["excerpt-003"],
        field_name: value,
    }

    with pytest.raises(ContractValidationError, match="unsupported field"):
        SemanticCoverageRecord.from_json_dict(payload)


def test_duplicate_coverage_must_reference_another_packet_source() -> None:
    payload = _packet()
    coverage = payload["coverage_records"]
    assert isinstance(coverage, list)
    record = coverage[0]
    assert isinstance(record, dict)
    record.update(
        {
            "duplicate_of_source_ref": "excerpt-999",
            "reason_code": "duplicate_excerpt",
        }
    )

    with pytest.raises(
        ContractValidationError,
        match="semantic duplicate coverage source ref invalid",
    ):
        SemanticIssueProposalPacket.from_json_dict(payload)


def test_issue_and_coverage_may_both_cite_same_source_without_suppression() -> None:
    payload = _packet()
    coverage = payload["coverage_records"]
    assert isinstance(coverage, list)
    record = coverage[0]
    assert isinstance(record, dict)
    record["source_refs"] = ["excerpt-001", "excerpt-003"]

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert "excerpt-001" in packet.issues[0].source_refs()
    assert "excerpt-001" in packet.coverage_records[0].source_refs


def test_split_golden_preserves_two_observation_only_issue_boundaries() -> None:
    payload = _packet()
    issues = payload["issues"]
    source_refs = payload["source_refs"]
    assert isinstance(issues, list)
    assert isinstance(source_refs, list)
    issues.append(_question_issue())
    source_refs.extend(["excerpt-004", "excerpt-005"])

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert [issue.issue_ref for issue in packet.issues] == [
        "issue-001",
        "issue-002",
    ]
    assert packet.issues[1].question is not None
    assert not ({"kcs_item_status", "article_type_hint"} & set(issues[1]))


def test_support_discovered_golden_remains_an_issue_without_model_action() -> None:
    payload = _packet()
    issue = _question_issue()
    issue["question"] = None
    issue["answer_evidence"] = []
    issue["resolution_evidence"] = [
        _observation(
            "Support identified and corrected a separately searchable state.",
            "excerpt-005",
        )
    ]
    payload["issues"] = [issue]
    payload["source_refs"] = ["excerpt-004", "excerpt-005"]
    payload["coverage_records"] = []

    packet = SemanticIssueProposalPacket.from_json_dict(payload)

    assert len(packet.issues) == 1
    assert packet.coverage_records == ()
    assert "candidate_origin" not in packet.issues[0].to_json_dict()
    assert "kcs_item_status" not in packet.issues[0].to_json_dict()
