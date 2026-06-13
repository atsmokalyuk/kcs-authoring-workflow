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
    payload = {
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
        "auto_publish_allowed": True,
    }

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
    payload = {
        "schema_version": KcsValidationReportPacket.SCHEMA_VERSION,
        "case_ref": "CASE-SYNTH-READY",
        "ok": ok,
        "ready_for_reviewer": ready_for_reviewer,
        "state": state,
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

    with pytest.raises(ContractValidationError):
        KcsValidationReportPacket.from_json_dict(payload)


def test_readiness_api_is_exported_from_package() -> None:
    assert kcs_core.KcsValidationReportPacket is KcsValidationReportPacket
    assert kcs_core.ReadinessState.READY_FOR_REVIEWER.value == "ready_for_reviewer"
    assert kcs_core.RequiredNextStep.FIX_EVIDENCE.value == "fix_evidence"
    assert kcs_core.build_validation_report is build_validation_report
    assert kcs_core.ensure_ready_for_reviewer is ensure_ready_for_reviewer


def _packet_hash(packet: KcsReviewerPacket) -> str:
    return hashlib.sha256(dumps_payload(packet).encode("utf-8")).hexdigest()


def _html_hash(packet: KcsReviewerPacket) -> str:
    assert packet.zendesk_source_html is not None
    return hashlib.sha256(packet.zendesk_source_html.encode("utf-8")).hexdigest()
