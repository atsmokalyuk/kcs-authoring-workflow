from __future__ import annotations

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    RecommendedAction,
)


def test_rejects_unknown_schema_version() -> None:
    payload = {
        "schema_version": "unknown_packet_v1",
        "case_ref": "CASE-SYNTH",
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "review_required": True,
        "public_article_candidate": None,
        "internal_reviewer_notes": [],
        "evidence_basis": {},
        "validation_report": {},
        "zendesk_source_html": None,
        "auto_publish_allowed": False,
    }

    with pytest.raises(ContractValidationError):
        KcsReviewerPacket.from_json_dict(payload)


def test_rejects_unknown_recommended_action() -> None:
    payload = {
        "schema_version": KcsReviewerPacket.SCHEMA_VERSION,
        "case_ref": "CASE-SYNTH",
        "recommended_action": "publish_now",
        "review_required": True,
        "public_article_candidate": None,
        "internal_reviewer_notes": [],
        "evidence_basis": {},
        "validation_report": {},
        "zendesk_source_html": None,
        "auto_publish_allowed": False,
    }

    with pytest.raises(ContractValidationError):
        KcsReviewerPacket.from_json_dict(payload)


def test_rejects_unknown_article_type() -> None:
    payload = {
        "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
        "candidate_id": "CANDIDATE-SYNTH",
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "article_type": "runbook",
        "confidence": 0.8,
        "blockers": [],
        "evidence_basis": {},
        "selected_reuse_match": None,
        "auto_publish_allowed": False,
    }

    with pytest.raises(ContractValidationError):
        KcsActionDecisionPacket.from_json_dict(payload)


def test_reviewer_packet_defaults_auto_publish_false() -> None:
    packet = KcsReviewerPacket(
        case_ref="CASE-SYNTH",
        recommended_action=RecommendedAction.CREATE_CANDIDATE.value,
        review_required=True,
    )

    assert packet.auto_publish_allowed is False
    assert packet.to_json_dict()["auto_publish_allowed"] is False


def test_reviewer_packet_rejects_auto_publish_true() -> None:
    payload = {
        "schema_version": KcsReviewerPacket.SCHEMA_VERSION,
        "case_ref": "CASE-SYNTH",
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "review_required": True,
        "public_article_candidate": None,
        "internal_reviewer_notes": [],
        "evidence_basis": {},
        "validation_report": {},
        "zendesk_source_html": None,
        "auto_publish_allowed": True,
    }

    with pytest.raises(ContractValidationError):
        KcsReviewerPacket.from_json_dict(payload)


def test_decision_packet_rejects_auto_publish_true() -> None:
    payload = {
        "schema_version": KcsActionDecisionPacket.SCHEMA_VERSION,
        "candidate_id": "CANDIDATE-SYNTH",
        "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "confidence": 0.8,
        "blockers": [],
        "evidence_basis": {},
        "selected_reuse_match": None,
        "auto_publish_allowed": True,
    }

    with pytest.raises(ContractValidationError):
        KcsActionDecisionPacket.from_json_dict(payload)


def test_decision_packet_accepts_known_article_type() -> None:
    packet = KcsActionDecisionPacket(
        candidate_id="CANDIDATE-SYNTH",
        recommended_action=RecommendedAction.CREATE_CANDIDATE.value,
        article_type=ArticleType.TECHNICAL_SCR.value,
        confidence=0.8,
    )

    assert packet.article_type == "technical_scr"
    assert (
        packet.to_json_dict()["schema_version"]
        == KcsActionDecisionPacket.SCHEMA_VERSION
    )
