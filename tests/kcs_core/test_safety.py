from __future__ import annotations

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.models import NormalizedTicketEvidencePacket
from kcs_core.safety import (
    EvidenceVisibility,
    InputClass,
    SafetyBlocker,
    ensure_evidence_safe,
    validate_evidence_safety,
)
from kcs_core.sanitizer import ensure_safe_sanitized_payload


def _safe_packet(**overrides: object) -> NormalizedTicketEvidencePacket:
    values = {
        "case_ref": "CASE-SYNTH-SAFE",
        "input_class": InputClass.SYNTHETIC_FIXTURE.value,
        "source_refs": ["source-ref-synth-safe"],
        "issue_candidates": [
            {
                "candidate_id": "candidate-synth-safe",
                "summary": "Mail delivery returns a generic queue error.",
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


@pytest.mark.parametrize("input_class", [item.value for item in InputClass])
def test_accepts_allowed_input_classes(input_class: str) -> None:
    packet = _safe_packet(input_class=input_class)

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


def test_rejects_unknown_input_class() -> None:
    packet = _safe_packet(input_class="raw_zendesk_json")

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNKNOWN_INPUT_CLASS.value in result.blockers


def test_rejects_sanitizer_without_affirmative_pass() -> None:
    packet = _safe_packet(sanitizer_report={})

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.SANITIZER_NOT_PASSED.value in result.blockers


def test_rejects_sanitizer_unsafe_flags() -> None:
    packet = _safe_packet(
        sanitizer_report={
            "status": "passed",
            "contains_private_data": True,
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.SANITIZER_NOT_PASSED.value in result.blockers


def test_rejects_failed_sanitizer_status_even_with_safe_flag() -> None:
    packet = _safe_packet(
        sanitizer_report={
            "status": "failed",
            "safe_for_kcs_core": True,
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.SANITIZER_NOT_PASSED.value in result.blockers


def test_rejects_positive_sanitizer_finding_count() -> None:
    packet = _safe_packet(
        sanitizer_report={
            "status": "passed",
            "finding_count": 1,
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.SANITIZER_NOT_PASSED.value in result.blockers


def test_accepts_sanitizer_safe_for_kcs_core_flag() -> None:
    packet = _safe_packet(sanitizer_report={"safe_for_kcs_core": True})

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


def test_rejects_unknown_visibility_class() -> None:
    packet = _safe_packet(visibility_summary={"classes": ["public_draft_ready"]})

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNKNOWN_VISIBILITY_CLASS.value in result.blockers


def test_rejects_missing_visibility_class() -> None:
    packet = _safe_packet(visibility_summary={})

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNKNOWN_VISIBILITY_CLASS.value in result.blockers


def test_rejects_unsafe_private_visibility_class() -> None:
    packet = _safe_packet(
        visibility_summary={"classes": [EvidenceVisibility.UNSAFE_PRIVATE.value]}
    )

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNSAFE_VISIBILITY.value in result.blockers


def test_rejects_unapproved_internal_visibility_class() -> None:
    packet = _safe_packet(
        visibility_summary={
            "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.INTERNAL_EVIDENCE_NOT_APPROVED.value in result.blockers


def test_accepts_approved_internal_visibility_class() -> None:
    packet = _safe_packet(
        visibility_summary={
            "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
            "internal_only_evidence_approved": True,
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


def test_accepts_tuple_visibility_classes() -> None:
    packet = _safe_packet(
        visibility_summary={
            "classes": (EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value,),
        }
    )

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


def test_rejects_forbidden_source_ref_labels() -> None:
    packet = _safe_packet(source_refs=["raw_zendesk_json"])

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNSAFE_SOURCE_REF.value in result.blockers


def test_rejects_public_url_in_source_refs() -> None:
    packet = _safe_packet(source_refs=["https://support.plesk.com/hc/example"])

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNSAFE_SOURCE_REF.value in result.blockers


def test_case_ref_is_metadata_not_public_text() -> None:
    packet = _safe_packet(case_ref="ticket-123456")

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


@pytest.mark.parametrize(
    "unsafe_value",
    [
        "Contact user@example.invalid for details.",
        "Contact person@example.com for details.",
        "The failing host is customer-host.invalid.",
        "The server IP is 10.0.0.8.",
        "The server IPv6 address is fe80::1.",
        "Config lives under /Users/example/private.conf.",
        "License PLSK.12345678.1234 is affected.",
        "The api_key=secret-value was present.",
        "Authorization: Bearer secret-value was present.",
        "The source ticket-123456 was copied into evidence text.",
    ],
)
def test_rejects_unsafe_text_values(unsafe_value: str) -> None:
    packet = _safe_packet(symptoms=[unsafe_value])

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert SafetyBlocker.UNSAFE_TEXT.value in result.blockers


@pytest.mark.parametrize(
    "safe_value",
    [
        "Customer cannot reset password after confirming ownership.",
        "API token rotation fails with a generic validation error.",
    ],
)
def test_allows_secret_related_topics_without_secret_values(safe_value: str) -> None:
    packet = _safe_packet(symptoms=[safe_value])

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


def test_allows_documentation_reserved_identifiers() -> None:
    packet = _safe_packet(
        symptoms=[
            "Use example.com and 192.0.2.10 in documentation-only reproduction.",
            "IPv6 documentation address 2001:db8::1 is safe.",
        ]
    )

    result = validate_evidence_safety(packet)

    assert result.ok is True
    assert result.blockers == ()


@pytest.mark.parametrize(
    "filename",
    [
        "setup.php",
        "service.log",
        "application.ini",
        "worker-process.pid",
        "service.conf",
        "02component-feature.conf",
        "settings.yaml",
        "metadata.json",
    ],
)
def test_allows_standalone_safe_filenames_in_sanitized_summary(
    filename: str,
) -> None:
    value = f"The sanitized diagnostic summary references {filename}."

    ensure_safe_sanitized_payload(value)
    result = validate_evidence_safety(_safe_packet(symptoms=[value]))

    assert result.ok is True
    assert result.blockers == ()


def test_safe_filename_allowlist_does_not_allow_customer_domain_or_url() -> None:
    with pytest.raises(ContractValidationError):
        ensure_safe_sanitized_payload("Open https://customer.example.net/index.php")

    result = validate_evidence_safety(
        _safe_packet(symptoms=["Open customer.example.net/index.php"])
    )

    assert result.ok is False
    assert result.blockers == (SafetyBlocker.UNSAFE_TEXT.value,)


def test_ensure_evidence_safe_raises_for_blocked_packet() -> None:
    packet = _safe_packet(symptoms=["The server IP is 10.0.0.8."])

    with pytest.raises(ContractValidationError):
        ensure_evidence_safe(packet)


def test_safety_result_does_not_echo_email_value() -> None:
    email = "person@example.invalid"
    packet = _safe_packet(symptoms=[f"Contact {email} for details."])

    result = validate_evidence_safety(packet)

    assert result.ok is False
    assert email not in repr(result.to_json_dict())
    assert result.blockers == (SafetyBlocker.UNSAFE_TEXT.value,)


def test_exception_does_not_echo_secret_value() -> None:
    secret = "token=secret-value"
    packet = _safe_packet(symptoms=[f"The report copied {secret}."])

    with pytest.raises(ContractValidationError) as exc_info:
        ensure_evidence_safe(packet)

    message = str(exc_info.value)
    assert SafetyBlocker.UNSAFE_TEXT.value in message
    assert secret not in message
