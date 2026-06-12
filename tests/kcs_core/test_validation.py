from __future__ import annotations

import pytest

import kcs_core
from kcs_core.errors import ContractValidationError
from kcs_core.models import NormalizedTicketEvidencePacket
from kcs_core.safety import EvidenceVisibility, InputClass
from kcs_core.validation import (
    EvidenceBlocker,
    EvidenceWarning,
    ensure_evidence_ready,
    validate_evidence_packet,
)


def _ready_packet(**overrides: object) -> NormalizedTicketEvidencePacket:
    values = {
        "case_ref": "CASE-SYNTH-READY",
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "source_refs": ["SRC-SYNTH-READY"],
        "issue_candidates": [
            {
                "candidate_id": "ISSUE-SYNTH-READY",
                "summary": "Mail delivery returns a generic queue error.",
                "atomic": True,
            }
        ],
        "environment": {"product_area": "mail"},
        "symptoms": ["Mail delivery returns a generic queue error."],
        "confirmed_facts": ["The queue retry fails after configuration change."],
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


def test_ready_sanitized_evidence_passes() -> None:
    packet = _ready_packet()

    result = validate_evidence_packet(packet)

    assert result.ok is True
    assert result.blockers == ()
    assert result.warnings == ()
    assert result.to_json_dict() == {
        "ok": True,
        "blockers": [],
        "warnings": [],
    }


def test_validation_api_is_exported_from_package() -> None:
    assert kcs_core.EvidenceBlocker.UNSAFE_INPUT.value == "unsafe_input"
    assert kcs_core.EvidenceWarning.MISSING_SUPPORTED_CAUSE.value == (
        "missing_supported_cause"
    )
    assert kcs_core.validate_evidence_packet is validate_evidence_packet
    assert kcs_core.ensure_evidence_ready is ensure_evidence_ready


def test_validation_does_not_mutate_packet() -> None:
    packet = _ready_packet()
    before = packet.to_json_dict()

    validate_evidence_packet(packet)

    assert packet.to_json_dict() == before


def test_unsafe_packet_blocks_with_value_free_code() -> None:
    email = "person@example.com"
    packet = _ready_packet(symptoms=[f"Contact {email} for details."])

    result = validate_evidence_packet(packet)

    assert result.ok is False
    assert result.blockers == (EvidenceBlocker.UNSAFE_INPUT.value,)
    assert email not in repr(result.to_json_dict())


@pytest.mark.parametrize(
    ("overrides", "blocker"),
    [
        ({"source_refs": []}, EvidenceBlocker.MISSING_SOURCE_REF.value),
        ({"source_refs": ["   "]}, EvidenceBlocker.MISSING_SOURCE_REF.value),
        ({"issue_candidates": []}, EvidenceBlocker.MISSING_ISSUE_CANDIDATE.value),
        ({"symptoms": []}, EvidenceBlocker.MISSING_SYMPTOMS.value),
        ({"confirmed_facts": []}, EvidenceBlocker.MISSING_CONFIRMED_FACTS.value),
        (
            {"supported_resolution_or_workaround": None},
            EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value,
        ),
        (
            {"supported_resolution_or_workaround": "   "},
            EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value,
        ),
        (
            {"open_questions": ["Need confirmation of the exact safe error text."]},
            EvidenceBlocker.OPEN_QUESTIONS_PRESENT.value,
        ),
    ],
)
def test_blocks_missing_or_incomplete_evidence(
    overrides: dict[str, object], blocker: str
) -> None:
    packet = _ready_packet(**overrides)

    result = validate_evidence_packet(packet)

    assert result.ok is False
    assert blocker in result.blockers


def test_blocks_multiple_issue_candidates() -> None:
    packet = _ready_packet(
        issue_candidates=[
            {"candidate_id": "ISSUE-SYNTH-1", "summary": "First issue."},
            {"candidate_id": "ISSUE-SYNTH-2", "summary": "Second issue."},
        ]
    )

    result = validate_evidence_packet(packet)

    assert result.ok is False
    assert result.blockers == (EvidenceBlocker.MULTI_ISSUE.value,)


@pytest.mark.parametrize(
    "candidate",
    [
        {"candidate_id": "ISSUE-SYNTH-SPLIT", "split_required": True},
        {"candidate_id": "ISSUE-SYNTH-NONATOMIC", "atomic": False},
    ],
)
def test_blocks_non_atomic_candidate(candidate: dict[str, object]) -> None:
    packet = _ready_packet(issue_candidates=[candidate])

    result = validate_evidence_packet(packet)

    assert result.ok is False
    assert result.blockers == (EvidenceBlocker.EVIDENCE_NOT_ATOMIC.value,)


def test_missing_supported_cause_is_warning_only() -> None:
    packet = _ready_packet(supported_cause=None)

    result = validate_evidence_packet(packet)

    assert result.ok is True
    assert result.blockers == ()
    assert result.warnings == (EvidenceWarning.MISSING_SUPPORTED_CAUSE.value,)


def test_ensure_evidence_ready_raises_without_echoing_values() -> None:
    question = "Need confirmation of the exact safe error text."
    packet = _ready_packet(open_questions=[question])

    with pytest.raises(ContractValidationError) as exc_info:
        ensure_evidence_ready(packet)

    message = str(exc_info.value)
    assert EvidenceBlocker.OPEN_QUESTIONS_PRESENT.value in message
    assert question not in message


def test_ensure_evidence_ready_raises_for_unsafe_input_without_echoing_values() -> None:
    email = "person@example.com"
    packet = _ready_packet(symptoms=[f"Contact {email} for details."])

    with pytest.raises(ContractValidationError) as exc_info:
        ensure_evidence_ready(packet)

    message = str(exc_info.value)
    assert EvidenceBlocker.UNSAFE_INPUT.value in message
    assert email not in message
