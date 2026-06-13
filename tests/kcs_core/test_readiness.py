from __future__ import annotations

import hashlib

import pytest

import kcs_core
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import dumps_payload
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    KcsValidationReportPacket,
    NormalizedTicketEvidencePacket,
    OperatorOverrideMode,
    OverrideStatus,
    ReadinessState,
    RecommendedAction,
    RequiredNextStep,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report, ensure_ready_for_reviewer
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import EvidenceVisibility, InputClass
from kcs_core.validation import EvidenceBlocker


def _evidence(**overrides: object) -> NormalizedTicketEvidencePacket:
    values = {
        "case_ref": "CASE-SYNTH-READY",
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "source_refs": ["SRC-SYNTH-READY"],
        "issue_candidates": [
            {
                "candidate_id": "ISSUE-SYNTH-READY",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk mail task fails: safe queue error",
                "summary": "Mail delivery returns a safe queue error.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "resolution_steps": [
                    "Log in to Plesk.",
                    "Go to Mail > Mail Settings.",
                    "Enable the required mail setting.",
                ],
            }
        ],
        "environment": {
            "product": "Plesk",
            "platform": "Linux",
            "component": "Mail",
        },
        "symptoms": ["Mail delivery returns a safe queue error."],
        "confirmed_facts": ["A safe product setting is disabled."],
        "supported_cause": "A required mail setting is disabled.",
        "supported_resolution_or_workaround": "Enable the required mail setting.",
        "open_questions": [],
        "visibility_summary": {
            "classes": [EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value],
        },
        "sanitizer_report": {"status": "passed"},
    }
    values.update(overrides)
    return NormalizedTicketEvidencePacket(**values)


def _reuse_results(**overrides: object) -> ReuseSearchResultsPacket:
    values = {
        "search_run_ref": "SEARCH-SYNTH-READY",
        "searched": True,
        "search_source": "synthetic_fixture",
        "matches": [],
        "blockers": [],
    }
    values.update(overrides)
    return ReuseSearchResultsPacket(**values)


def _reuse_match(
    content_status: str = "complete", **overrides: object
) -> dict[str, object]:
    values = {
        "match_ref": "KB-SYNTH-READY",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": content_status,
    }
    values.update(overrides)
    return values


def _no_article_evidence() -> NormalizedTicketEvidencePacket:
    return _evidence(
        issue_candidates=[
            {
                **_evidence().issue_candidates[0],
                "kcs_applicable": False,
            }
        ]
    )


def test_ready_create_candidate_report_is_ready_for_reviewer() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)
    payload = report.to_json_dict()

    assert report.schema_version == KcsValidationReportPacket.SCHEMA_VERSION
    assert report.ok is True
    assert report.ready_for_reviewer is True
    assert report.state == ReadinessState.READY_FOR_REVIEWER.value
    assert report.required_next_step == RequiredNextStep.NONE.value
    assert report.blockers == []
    assert "renderer_validation_checked" in report.checks
    assert report.reviewer_packet_sha256 == _packet_hash(reviewer_packet)
    assert report.zendesk_source_sha256 == _html_hash(reviewer_packet)
    assert KcsValidationReportPacket.from_json_dict(payload).to_json_dict() == payload
    ensure_ready_for_reviewer(report)


def test_reuse_existing_without_public_draft_can_be_ready_for_reviewer() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[_reuse_match("complete")]),
    )
    reviewer_packet = render_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value
    assert reviewer_packet.public_article_candidate is None
    assert reviewer_packet.zendesk_source_html is None
    assert report.state == ReadinessState.READY_FOR_REVIEWER.value
    assert report.required_next_step == RequiredNextStep.NONE.value


def test_update_existing_report_is_ready_for_reviewer() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[_reuse_match("incomplete")]),
    )
    reviewer_packet = render_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert reviewer_packet.public_article_candidate is not None
    assert reviewer_packet.zendesk_source_html is not None
    assert report.state == ReadinessState.READY_FOR_REVIEWER.value
    assert report.required_next_step == RequiredNextStep.NONE.value
    assert report.blockers == []


def test_no_article_with_renderer_packet_is_ready_without_public_html() -> None:
    evidence = _no_article_evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert decision.recommended_action == RecommendedAction.NO_ARTICLE.value
    assert reviewer_packet.public_article_candidate is None
    assert reviewer_packet.zendesk_source_html is None
    assert report.state == ReadinessState.READY_FOR_REVIEWER.value
    assert report.required_next_step == RequiredNextStep.NONE.value
    assert report.blockers == []


def test_no_article_with_unexpected_renderer_blocker_blocks_review() -> None:
    evidence = _no_article_evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=True,
        public_article_candidate=None,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "blockers": ["renderer_failed"],
        },
        zendesk_source_html=None,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["renderer_failed"]


def test_unsafe_evidence_blocks_without_echoing_private_value() -> None:
    private_value = "person@example.com"
    evidence = _evidence(symptoms=[f"Contact {private_value} for details."])
    decision = decide_kcs_action(evidence, _reuse_results())

    report = build_validation_report(evidence, decision)
    payload = report.to_json_dict()

    assert report.ready_for_reviewer is False
    assert report.state == ReadinessState.BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_EVIDENCE.value
    assert EvidenceBlocker.UNSAFE_INPUT.value in report.blockers
    assert private_value not in repr(payload)
    with pytest.raises(ContractValidationError, match="blocked"):
        ensure_ready_for_reviewer(report)


def test_missing_reviewer_packet_requires_draft() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())

    report = build_validation_report(evidence, decision)

    assert report.state == ReadinessState.DRAFT_REQUIRED.value
    assert report.required_next_step == RequiredNextStep.RENDER_REVIEWER_PACKET.value
    assert report.blockers == ["reviewer_packet_missing"]
    assert report.reviewer_packet_sha256 == ""
    assert report.zendesk_source_sha256 == ""


def test_missing_reuse_search_blocks_with_reuse_search_next_step() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results(searched=False))

    report = build_validation_report(evidence, decision)

    assert report.state == ReadinessState.BLOCKED.value
    assert report.required_next_step == RequiredNextStep.RUN_REUSE_SEARCH.value
    assert "possible_duplicate_not_checked" in report.blockers


def test_split_required_waits_for_split_item_review() -> None:
    first = dict(_evidence().issue_candidates[0])
    first["candidate_id"] = "ISSUE-SYNTH-FIRST"
    second = dict(first)
    second["candidate_id"] = "ISSUE-SYNTH-SECOND"
    evidence = _evidence(issue_candidates=[first, second])
    decision = decide_kcs_action(evidence, _reuse_results())

    report = build_validation_report(evidence, decision)

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.REVIEW_SPLIT_ITEMS.value
    assert report.blockers == ["split_required"]


def test_split_required_does_not_mask_unsafe_evidence() -> None:
    private_value = "person@example.com"
    first = dict(_evidence().issue_candidates[0])
    first["candidate_id"] = "ISSUE-SYNTH-FIRST"
    second = dict(first)
    second["candidate_id"] = "ISSUE-SYNTH-SECOND"
    evidence = _evidence(
        issue_candidates=[first, second],
        symptoms=[f"Contact {private_value} for details."],
    )
    decision = KcsActionDecisionPacket(
        candidate_id=evidence.case_ref,
        recommended_action=RecommendedAction.SPLIT_REQUIRED.value,
        article_type=ArticleType.NONE.value,
        confidence=0.0,
        blockers=["multi_issue"],
        evidence_basis={},
        status=DecisionStatus.SPLIT_REQUIRED.value,
    )

    report = build_validation_report(evidence, decision)
    payload = report.to_json_dict()

    assert report.state == ReadinessState.BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_EVIDENCE.value
    assert EvidenceBlocker.UNSAFE_INPUT.value in report.blockers
    assert private_value not in repr(payload)


def test_reviewer_packet_action_mismatch_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    mismatched_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=RecommendedAction.NO_ARTICLE.value,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report=reviewer_packet.validation_report,
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, mismatched_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["reviewer_packet_decision_mismatch"]


def test_article_action_with_decision_blockers_blocks_readiness() -> None:
    evidence = _evidence()
    decision = KcsActionDecisionPacket(
        candidate_id="ISSUE-SYNTH-READY",
        recommended_action=RecommendedAction.CREATE_CANDIDATE.value,
        article_type=ArticleType.TECHNICAL_SCR.value,
        confidence=0.6,
        blockers=["unsafe_input"],
        evidence_basis={},
        status=DecisionStatus.DECISION_READY.value,
    )
    reviewer_packet = _valid_article_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert "decision_blockers_present" in report.blockers


@pytest.mark.parametrize(
    "bad_status",
    [
        "no_public_article_output",
        "zendesk_html_not_generated",
        "split_required",
        "not_run",
    ],
)
def test_create_candidate_with_renderer_status_mismatch_blocks_review(
    bad_status: str,
) -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = _with_renderer_status(reviewer_packet, bad_status)

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert "renderer_status_mismatch" in report.blockers


def test_update_existing_with_renderer_status_mismatch_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[_reuse_match("incomplete")]),
    )
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = _with_renderer_status(
        reviewer_packet,
        "no_public_article_output",
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert "renderer_status_mismatch" in report.blockers


def test_flag_existing_with_renderer_status_mismatch_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(
            matches=[_reuse_match("incomplete", publication_status="public")]
        ),
    )
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = _with_renderer_status(
        reviewer_packet,
        "zendesk_html_generated",
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert "renderer_status_mismatch" in report.blockers


def test_invalid_renderer_blocker_list_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    invalid_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "blockers": [123],
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, invalid_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["renderer_validation_report_invalid"]
    assert report.renderer_validation["blockers"] == [
        "renderer_validation_report_invalid"
    ]


def test_raw_renderer_blocker_value_blocks_without_echo() -> None:
    private_value = "/private/raw"
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    invalid_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "blockers": [private_value],
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, invalid_packet)
    payload = report.to_json_dict()

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["blockers_unsafe_report_code"]
    assert private_value not in repr(payload)


@pytest.mark.parametrize("field", ["checks", "warnings"])
def test_invalid_renderer_checks_or_warnings_block_review(field: str) -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    invalid_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            field: [123],
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, invalid_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["renderer_validation_report_invalid"]
    assert report.renderer_validation["blockers"] == [
        "renderer_validation_report_invalid"
    ]


def test_reuse_existing_with_public_output_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[_reuse_match("complete")]),
    )
    malformed_packet = KcsReviewerPacket(
        case_ref=evidence.case_ref,
        recommended_action=decision.recommended_action,
        review_required=True,
        public_article_candidate={
            "title": "Should not exist",
            "auto_publish_allowed": False,
        },
        internal_reviewer_notes=[],
        evidence_basis=decision.evidence_basis,
        validation_report={
            "schema_version": "kcs_renderer_validation_report_v1",
            "renderer_status": "zendesk_html_generated",
            "checks": ["auto_publish_allowed_false"],
            "blockers": [],
            "warnings": [],
        },
        zendesk_source_html="<h1>Should not exist</h1>",
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert "unexpected_public_article_output" in report.blockers


def test_reviewer_packet_review_required_false_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=False,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report=reviewer_packet.validation_report,
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["review_required_not_true"]


def test_public_candidate_auto_publish_true_blocks_review() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    assert reviewer_packet.public_article_candidate is not None
    malformed_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=True,
        public_article_candidate={
            **reviewer_packet.public_article_candidate,
            "auto_publish_allowed": True,
        },
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report=reviewer_packet.validation_report,
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert report.blockers == ["public_candidate_auto_publish_allowed_not_false"]


def test_article_action_without_public_output_requires_draft() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = KcsReviewerPacket(
        case_ref=evidence.case_ref,
        recommended_action=decision.recommended_action,
        review_required=True,
        public_article_candidate=None,
        internal_reviewer_notes=[],
        evidence_basis=decision.evidence_basis,
        validation_report={
            "schema_version": "kcs_renderer_validation_report_v1",
            "renderer_status": "zendesk_html_not_generated",
            "checks": ["auto_publish_allowed_false"],
            "blockers": [],
            "warnings": [],
        },
        zendesk_source_html=None,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert report.state == ReadinessState.DRAFT_REQUIRED.value
    assert report.required_next_step == RequiredNextStep.RENDER_REVIEWER_PACKET.value
    assert report.blockers == ["public_article_output_missing"]


def test_flag_existing_renderer_warning_is_preserved() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(
        evidence,
        _reuse_results(
            matches=[_reuse_match("incomplete", publication_status="public")]
        ),
    )
    reviewer_packet = render_reviewer_packet(evidence, decision)

    report = build_validation_report(evidence, decision, reviewer_packet)

    assert decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    assert report.state == ReadinessState.READY_FOR_REVIEWER.value
    assert "flag_existing_requires_existing_article_review" in report.warnings


def test_report_sanitizes_unsafe_decision_blocker_code() -> None:
    private_value = "/Users/example/private-path"
    evidence = _evidence()
    decision = KcsActionDecisionPacket(
        candidate_id="ISSUE-SYNTH-READY",
        recommended_action=RecommendedAction.BLOCKED.value,
        article_type=ArticleType.NONE.value,
        confidence=0.0,
        blockers=[private_value],
        evidence_basis={},
        status=DecisionStatus.BLOCKED.value,
    )

    report = build_validation_report(evidence, decision)
    payload = report.to_json_dict()

    assert report.state == ReadinessState.BLOCKED.value
    assert report.blockers == ["blockers_unsafe_report_code"]
    assert private_value not in repr(payload)


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "PLSK.12345678.1234",
        "ZD123456",
        "ticket-123456",
        "customer.example.net",
        "10.0.0.1",
        "PLSK-12345678-1234",
        "EXT-12345678",
    ],
)
def test_decision_summary_does_not_echo_unsafe_candidate_id(
    unsafe_value: str,
) -> None:
    evidence = _evidence()
    decision = KcsActionDecisionPacket(
        candidate_id=unsafe_value,
        recommended_action=RecommendedAction.BLOCKED.value,
        article_type=ArticleType.NONE.value,
        confidence=0.0,
        blockers=["decision_blocked"],
        evidence_basis={},
        status=DecisionStatus.BLOCKED.value,
    )

    report = build_validation_report(evidence, decision)

    assert unsafe_value not in repr(report.to_json_dict())


def test_renderer_validation_does_not_echo_unsafe_status() -> None:
    private_value = "ticket-123456"
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "renderer_status": private_value,
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)

    assert report.renderer_validation["renderer_status"] == ""
    assert private_value not in repr(report.to_json_dict())


@pytest.mark.parametrize("bad_schema", ["wrong", "/private/raw", None])
def test_renderer_validation_schema_mismatch_blocks_review(
    bad_schema: object,
) -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    malformed_packet = KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "schema_version": bad_schema,
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )

    report = build_validation_report(evidence, decision, malformed_packet)
    payload = report.to_json_dict()

    assert report.state == ReadinessState.REVIEW_BLOCKED.value
    assert report.required_next_step == RequiredNextStep.FIX_REVIEWER_PACKET.value
    assert "renderer_validation_schema_mismatch" in report.blockers
    assert "/private/raw" not in repr(payload)


def test_report_does_not_mutate_inputs() -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results())
    reviewer_packet = render_reviewer_packet(evidence, decision)
    evidence_before = evidence.to_json_dict()
    decision_before = decision.to_json_dict()
    reviewer_before = reviewer_packet.to_json_dict()

    build_validation_report(evidence, decision, reviewer_packet)

    assert evidence.to_json_dict() == evidence_before
    assert decision.to_json_dict() == decision_before
    assert reviewer_packet.to_json_dict() == reviewer_before


def test_report_rejects_auto_publish_true() -> None:
    payload = _report_payload(auto_publish_allowed=True)

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    ("ok", "ready_for_reviewer", "state"),
    [
        (False, False, ReadinessState.READY_FOR_REVIEWER.value),
        (True, True, ReadinessState.BLOCKED.value),
        (True, False, ReadinessState.READY_FOR_REVIEWER.value),
    ],
)
def test_report_rejects_inconsistent_readiness_booleans(
    ok: bool, ready_for_reviewer: bool, state: str
) -> None:
    payload = _report_payload(
        ok=ok,
        ready_for_reviewer=ready_for_reviewer,
        state=state,
        required_next_step=RequiredNextStep.NONE.value,
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_validation_report_rejects_ready_state_with_next_step_or_blockers() -> None:
    payload = _report_payload(
        required_next_step=RequiredNextStep.FIX_EVIDENCE.value,
        blockers=["some_blocker"],
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize("field", ["checks", "blockers", "warnings"])
def test_validation_report_rejects_unsafe_report_codes(field: str) -> None:
    payload = _report_payload(
        ok=False,
        ready_for_reviewer=False,
        state=ReadinessState.BLOCKED.value,
        required_next_step=RequiredNextStep.FIX_EVIDENCE.value,
        blockers=["decision_blocked"],
    )
    payload[field] = ["/private/raw"]

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_validation_report_rejects_unsafe_nested_summary_values() -> None:
    payload = _report_payload(
        decision_summary={"candidate_id": "/private/raw"},
        renderer_validation={"renderer_status": "ticket-123456"},
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "decision_summary_patch",
    [
        {"auto_publish_allowed": True},
        {"recommended_action": "not_an_action"},
        {"article_type": "not_an_article_type"},
        {"status": "not_a_status"},
        {"override_status": "not_an_override_status"},
        {"blockers": "bad"},
        {"candidate_id": 123456789},
        {"split_item_count": -1},
        {"has_selected_reuse_match": 1},
        {"operator_override_allowed": 1},
        {"allowed_override_modes": ["not_an_override_mode"]},
    ],
)
def test_validation_report_rejects_malformed_decision_summary(
    decision_summary_patch: dict[str, object],
) -> None:
    payload = _report_payload(
        decision_summary={
            **_decision_summary_payload(),
            **decision_summary_patch,
        },
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "evidence_validation_patch",
    [
        {"ok": 1},
        {"blockers": "bad"},
        {"warnings": "bad"},
        {"blockers": ["raw_ticket"]},
    ],
)
def test_validation_report_rejects_malformed_evidence_validation(
    evidence_validation_patch: dict[str, object],
) -> None:
    payload = _report_payload(
        evidence_validation={
            **_evidence_validation_payload(),
            **evidence_validation_patch,
        },
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize(
    "renderer_validation_patch",
    [
        {"schema_version": "wrong"},
        {"renderer_status": 123},
        {"renderer_status": "not_a_renderer_status"},
        {"has_public_article_candidate": 1},
        {"has_zendesk_source_html": 1},
        {"checks": "bad"},
        {"blockers": "bad"},
        {"warnings": "bad"},
        {"warnings": ["api_key"]},
    ],
)
def test_validation_report_rejects_malformed_renderer_validation(
    renderer_validation_patch: dict[str, object],
) -> None:
    payload = _report_payload(
        renderer_validation={
            **_renderer_validation_payload(),
            **renderer_validation_patch,
        },
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


@pytest.mark.parametrize("field", ["reviewer_packet_sha256", "zendesk_source_sha256"])
def test_validation_report_rejects_invalid_hash_fields(field: str) -> None:
    payload = _report_payload(**{field: "/private/raw"})

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_validation_report_rejects_not_ready_without_next_step() -> None:
    payload = _report_payload(
        ok=False,
        ready_for_reviewer=False,
        state=ReadinessState.BLOCKED.value,
        required_next_step=RequiredNextStep.NONE.value,
        blockers=["decision_blocked"],
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_validation_report_rejects_not_ready_without_blockers() -> None:
    payload = _report_payload(
        ok=False,
        ready_for_reviewer=False,
        state=ReadinessState.DRAFT_REQUIRED.value,
        required_next_step=RequiredNextStep.RENDER_REVIEWER_PACKET.value,
        blockers=[],
    )

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_not_ready_report_serialization_roundtrip() -> None:
    payload = _report_payload(
        ok=False,
        ready_for_reviewer=False,
        state=ReadinessState.REVIEW_BLOCKED.value,
        required_next_step=RequiredNextStep.FIX_REVIEWER_PACKET.value,
        blockers=["renderer_validation_report_invalid"],
    )

    assert KcsValidationReportPacket.from_json_dict(payload).to_json_dict() == payload


def test_readiness_api_is_exported_from_package() -> None:
    assert kcs_core.KcsValidationReportPacket is KcsValidationReportPacket
    assert kcs_core.ReadinessState.READY_FOR_REVIEWER.value == "ready_for_reviewer"
    assert kcs_core.RequiredNextStep.FIX_EVIDENCE.value == "fix_evidence"
    assert kcs_core.build_validation_report is build_validation_report
    assert kcs_core.ensure_ready_for_reviewer is ensure_ready_for_reviewer


def _report_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": KcsValidationReportPacket.SCHEMA_VERSION,
        "case_ref": "CASE-SYNTH-READY",
        "ok": True,
        "ready_for_reviewer": True,
        "state": ReadinessState.READY_FOR_REVIEWER.value,
        "required_next_step": RequiredNextStep.NONE.value,
        "checks": [],
        "blockers": [],
        "warnings": [],
        "evidence_validation": {},
        "decision_summary": {},
        "renderer_validation": {},
        "reviewer_packet_sha256": "",
        "zendesk_source_sha256": "",
        "auto_publish_allowed": False,
    }
    payload.update(overrides)
    return payload


def _evidence_validation_payload() -> dict[str, object]:
    return {
        "ok": True,
        "blockers": [],
        "warnings": [],
    }


def _decision_summary_payload() -> dict[str, object]:
    return {
        "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
        "candidate_id": "ISSUE-SYNTH-READY",
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "status": DecisionStatus.DECISION_READY.value,
        "blockers": [],
        "split_item_count": 0,
        "has_selected_reuse_match": False,
        "operator_override_allowed": False,
        "allowed_override_modes": [OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value],
        "override_status": OverrideStatus.NOT_REQUESTED.value,
        "auto_publish_allowed": False,
    }


def _renderer_validation_payload() -> dict[str, object]:
    return {
        "schema_version": "kcs_renderer_validation_report_v1",
        "renderer_status": "zendesk_html_generated",
        "checks": ["auto_publish_allowed_false"],
        "blockers": [],
        "warnings": [],
        "has_public_article_candidate": True,
        "has_zendesk_source_html": True,
    }


def _valid_article_reviewer_packet(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
) -> KcsReviewerPacket:
    clean_decision = decide_kcs_action(evidence, _reuse_results())
    clean_packet = render_reviewer_packet(evidence, clean_decision)
    return KcsReviewerPacket(
        case_ref=evidence.case_ref,
        recommended_action=decision.recommended_action,
        review_required=True,
        public_article_candidate=clean_packet.public_article_candidate,
        internal_reviewer_notes=clean_packet.internal_reviewer_notes,
        evidence_basis=clean_packet.evidence_basis,
        validation_report=clean_packet.validation_report,
        zendesk_source_html=clean_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )


def _with_renderer_status(
    reviewer_packet: KcsReviewerPacket,
    renderer_status: str,
) -> KcsReviewerPacket:
    return KcsReviewerPacket(
        case_ref=reviewer_packet.case_ref,
        recommended_action=reviewer_packet.recommended_action,
        review_required=reviewer_packet.review_required,
        public_article_candidate=reviewer_packet.public_article_candidate,
        internal_reviewer_notes=reviewer_packet.internal_reviewer_notes,
        evidence_basis=reviewer_packet.evidence_basis,
        validation_report={
            **reviewer_packet.validation_report,
            "renderer_status": renderer_status,
        },
        zendesk_source_html=reviewer_packet.zendesk_source_html,
        auto_publish_allowed=False,
    )


def _packet_hash(packet: KcsReviewerPacket) -> str:
    return hashlib.sha256(dumps_payload(packet).encode("utf-8")).hexdigest()


def _html_hash(packet: KcsReviewerPacket) -> str:
    assert packet.zendesk_source_html is not None
    return hashlib.sha256(packet.zendesk_source_html.encode("utf-8")).hexdigest()
