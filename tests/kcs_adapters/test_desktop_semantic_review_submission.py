from __future__ import annotations

import pytest

from kcs_adapters.desktop_semantic_review_submission import (
    SemanticReviewSubmissionError,
    ensure_extractively_grounded_observations,
    ensure_issue_entry_speaker_compatibility,
    ensure_no_forbidden_semantic_submit_values,
    ensure_no_forbidden_submit_values,
)
from kcs_core.semantic_extraction import SemanticIssueProposalPacket


def _proposal(
    *,
    symptom: str,
    question: str | None = None,
    issue_entry_source_ref: str = "excerpt-001",
) -> SemanticIssueProposalPacket:
    return SemanticIssueProposalPacket.from_json_dict(
        {
            "case_ref": "semantic-review-synthetic-001",
            "coverage_records": [],
            "extraction_source_ref": "semantic-proposal-synthetic-001",
            "issues": [
                {
                    "answer_evidence": [],
                    "cause_evidence": [
                        {
                            "source_refs": ["excerpt-002"],
                            "text": "The service is stopped.",
                        }
                    ],
                    "context_evidence": [],
                    "error_evidence": [],
                    "issue_ref": "issue-001",
                    "question": (
                        {
                            "source_refs": [issue_entry_source_ref],
                            "text": question,
                        }
                        if question is not None
                        else None
                    ),
                    "resolution_evidence": [
                        {
                            "source_refs": ["excerpt-003"],
                            "text": "Run systemctl restart synthetic-service.",
                        }
                    ],
                    "summary": {
                        "source_refs": ["excerpt-001", "excerpt-002"],
                        "text": "A generated semantic issue summary.",
                    },
                    "symptoms": [
                        {
                            "source_refs": [issue_entry_source_ref],
                            "text": symptom,
                        }
                    ],
                    "verification_evidence": [],
                }
            ],
            "schema_version": "semantic_issue_proposal_v1",
            "source_refs": ["excerpt-001", "excerpt-002", "excerpt-003"],
        }
    )


def _excerpt_text_by_ref() -> dict[str, str]:
    return {
        "excerpt-001": (
            "Client: The operation returns no result. "
            "How can I restore the operation?"
        ),
        "excerpt-002": "Support: The service is stopped.",
        "excerpt-003": "Support: Run systemctl restart synthetic-service.",
    }


def test_extractively_grounded_observations_preserve_original_words() -> None:
    ensure_extractively_grounded_observations(
        _proposal(
            symptom="The operation returns no result.",
            question="How can I restore the operation?",
        ),
        _excerpt_text_by_ref(),
    )


@pytest.mark.parametrize(
    ("symptom", "question"),
    [
        ("The operation does not return anything.", None),
        (
            "The operation returns no result.",
            "What should the customer do to restore it?",
        ),
    ],
)
def test_paraphrased_customer_evidence_is_rejected(
    symptom: str,
    question: str | None,
) -> None:
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_extractively_grounded_observations(
            _proposal(symptom=symptom, question=question),
            _excerpt_text_by_ref(),
        )

    assert captured.value.debug_code == "semantic_observation_text_not_extractive"
    assert captured.value.field_paths


def test_generative_summary_does_not_require_extractive_match() -> None:
    ensure_extractively_grounded_observations(
        _proposal(symptom="The operation returns no result."),
        _excerpt_text_by_ref(),
    )


def test_whitespace_only_difference_remains_extractively_grounded() -> None:
    ensure_extractively_grounded_observations(
        _proposal(
            symptom="The operation\nreturns   no result.",
        ),
        _excerpt_text_by_ref(),
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "answer_evidence",
        "cause_evidence",
        "context_evidence",
        "error_evidence",
        "resolution_evidence",
        "symptoms",
        "verification_evidence",
    ],
)
def test_every_non_summary_observation_field_requires_extractive_text(
    field_name: str,
) -> None:
    payload = _proposal(
        symptom="The operation returns no result.",
    ).to_json_dict()
    issue = payload["issues"][0]
    assert isinstance(issue, dict)
    issue[field_name] = [
        {
            "source_refs": ["excerpt-002", "excerpt-003"],
            "text": "A paraphrased observation that is absent from the excerpt.",
        }
    ]
    proposal = SemanticIssueProposalPacket.from_json_dict(payload)

    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_extractively_grounded_observations(
            proposal,
            _excerpt_text_by_ref(),
        )

    assert captured.value.debug_code == "semantic_observation_text_not_extractive"


def test_explicit_support_text_cannot_own_customer_issue_entry_fields() -> None:
    proposal = _proposal(
        symptom="The service is stopped.",
        issue_entry_source_ref="excerpt-002",
    )

    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_issue_entry_speaker_compatibility(
            proposal,
            _excerpt_text_by_ref(),
            {
                "excerpt-001": "customer",
                "excerpt-002": "support",
                "excerpt-003": "support",
            },
        )

    assert captured.value.debug_code == "semantic_issue_entry_speaker_incompatible"


def test_explicit_support_text_cannot_own_customer_question() -> None:
    proposal = _proposal(
        symptom="The operation returns no result.",
        question="The service is stopped.",
        issue_entry_source_ref="excerpt-002",
    )
    payload = proposal.to_json_dict()
    issue = payload["issues"][0]
    assert isinstance(issue, dict)
    symptoms = issue["symptoms"]
    assert isinstance(symptoms, list)
    symptoms[0] = {
        "source_refs": ["excerpt-001"],
        "text": "The operation returns no result.",
    }
    proposal = SemanticIssueProposalPacket.from_json_dict(payload)

    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_issue_entry_speaker_compatibility(
            proposal,
            _excerpt_text_by_ref(),
            {
                "excerpt-001": "customer",
                "excerpt-002": "support",
                "excerpt-003": "support",
            },
        )

    assert captured.value.debug_code == "semantic_issue_entry_speaker_incompatible"


def test_unknown_speaker_is_not_guessed_by_python() -> None:
    ensure_issue_entry_speaker_compatibility(
        _proposal(
            symptom="The service is stopped.",
            issue_entry_source_ref="excerpt-002",
        ),
        _excerpt_text_by_ref(),
        {
            "excerpt-001": "customer",
            "excerpt-002": "unknown",
            "excerpt-003": "support",
        },
    )


@pytest.mark.parametrize(
    "value",
    [
        "Use https://support.example.test/articles/123 for the supported procedure.",
        "Check /etc/example/service.conf on the server.",
        "Use <HOST> as the sanitized host placeholder.",
        "Update the file: CONFIG_TEXT:\n# /etc/example/service.conf\nmode=safe",
        "Run the recorded command:\n# examplectl",
        "Open Settings > Service > Status.",
    ],
)
def test_forbidden_value_guard_allows_supported_evidence(value: str) -> None:
    ensure_no_forbidden_submit_values(value)


@pytest.mark.parametrize(
    ("value", "debug_code"),
    [
        ("```json\n{}\n```", "semantic_review_forbidden_html_or_markdown"),
        ("<script>unsafe</script>", "semantic_review_forbidden_html_or_markdown"),
        ("# Draft article", "semantic_review_forbidden_html_or_markdown"),
        (
            "> quoted transcript text",
            "semantic_review_forbidden_html_or_markdown",
        ),
        ("Open ~/Documents/private.txt", "semantic_review_local_ref_blocked"),
        ("Open /private/tmp/reviewer.html", "semantic_review_local_ref_blocked"),
        (
            "Open local-data/reviewer-bundles/run-001/reviewer_only.html",
            "semantic_review_local_ref_blocked",
        ),
    ],
)
def test_forbidden_value_guard_rejects_non_semantic_surfaces(
    value: str,
    debug_code: str,
) -> None:
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_no_forbidden_submit_values(value)

    assert captured.value.debug_code == debug_code


@pytest.mark.parametrize(
    "field_name",
    [
        "auto_publish_allowed",
        "candidate_extraction",
        "item_candidates",
        "local_path",
        "recommended_action",
        "reviewer_only_html",
    ],
)
def test_forbidden_value_guard_rejects_control_fields(field_name: str) -> None:
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_no_forbidden_submit_values({field_name: "value"})

    assert captured.value.debug_code == "semantic_review_forbidden_field"


def test_semantic_guard_allows_heading_in_source_observation_text() -> None:
    ensure_no_forbidden_semantic_submit_values(
        {
            "issues": [
                {
                    "symptoms": [
                        {
                            "source_refs": ["excerpt-001"],
                            "text": "# Customer-reported symptom",
                        }
                    ]
                }
            ]
        }
    )


def test_source_heading_still_requires_exact_excerpt_grounding() -> None:
    proposal = _proposal(symptom="# Invented source heading")
    payload = proposal.to_json_dict()

    ensure_no_forbidden_semantic_submit_values(payload)
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_extractively_grounded_observations(
            proposal,
            _excerpt_text_by_ref(),
        )

    assert captured.value.debug_code == "semantic_observation_text_not_extractive"


def test_semantic_guard_rejects_heading_in_generated_summary() -> None:
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_no_forbidden_semantic_submit_values(
            {
                "issues": [
                    {
                        "summary": {
                            "source_refs": ["excerpt-001"],
                            "text": "# Generated article heading",
                        }
                    }
                ]
            }
        )

    assert captured.value.debug_code == "semantic_review_forbidden_html_or_markdown"


@pytest.mark.parametrize(
    ("value", "debug_code"),
    [
        ("```text\nsource\n```", "semantic_review_forbidden_html_or_markdown"),
        ("<div>source</div>", "semantic_review_forbidden_html_or_markdown"),
        ("> quoted source", "semantic_review_forbidden_html_or_markdown"),
        ("Open /private/tmp/source.txt", "semantic_review_local_ref_blocked"),
    ],
)
def test_semantic_guard_keeps_other_source_observation_blocks(
    value: str,
    debug_code: str,
) -> None:
    with pytest.raises(SemanticReviewSubmissionError) as captured:
        ensure_no_forbidden_semantic_submit_values(
            {
                "issues": [
                    {
                        "resolution_evidence": [
                            {
                                "source_refs": ["excerpt-001"],
                                "text": value,
                            }
                        ]
                    }
                ]
            }
        )

    assert captured.value.debug_code == debug_code
