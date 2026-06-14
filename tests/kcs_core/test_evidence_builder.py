from __future__ import annotations

import pytest

import kcs_core
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import (
    APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
    EvidenceBuildPolicy,
    build_evidence_packet_from_zendesk_export,
)
from kcs_core.json_payload import dump_json_dict
from kcs_core.models import (
    ArticleType,
    NormalizedTicketEvidencePacket,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.readiness import build_validation_report
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import (
    EvidenceVisibility,
    InputClass,
    validate_evidence_safety,
)
from kcs_core.validation import validate_evidence_packet


def _export_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
        "input_class": InputClass.NORMALIZED_ZENDESK_EVIDENCE.value,
        "source_refs": ["approved-export-source-001"],
        "environment": {
            "component": "Backup",
            "platform": "Linux",
            "product": "Plesk",
        },
        "symptoms": ["Backup task fails with a synthetic safe status."],
        "confirmed_facts": ["A safe backup setting is disabled."],
        "supported_cause": "A required backup setting is disabled.",
        "supported_resolution_or_workaround": (
            "Enable the required backup setting."
        ),
        "open_questions": [],
        "visibility_summary": {
            "classes": [EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value],
        },
        "sanitizer_report": {"status": "passed"},
        "issue_candidates": [
            {
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "atomic": True,
                "candidate_id": "item-001",
                "confirmed_facts": ["A safe backup setting is disabled."],
                "customer_reported": True,
                "kcs_applicable": True,
                "public_solution_safe": True,
                "resolution_state": "solved",
                "resolution_steps": [
                    "Open backup settings.",
                    "Enable the required backup setting.",
                    "Rerun the backup task.",
                ],
                "reuse_search_status": "checked",
                "source_refs": ["approved-export-source-item-001"],
                "summary": "Backup task fails with a synthetic safe status.",
                "supported_cause": "A required backup setting is disabled.",
                "supported_resolution_or_workaround": (
                    "Enable the required backup setting."
                ),
                "symptoms": ["Backup task fails with a synthetic safe status."],
                "title": "Synthetic backup task failure",
            }
        ],
    }
    payload.update(overrides)
    return payload


def _policy(**overrides: object) -> EvidenceBuildPolicy:
    values = {
        "input_class": InputClass.NORMALIZED_ZENDESK_EVIDENCE.value,
        "assume_sanitized": False,
        "allow_internal_reviewer_only": False,
    }
    values.update(overrides)
    return EvidenceBuildPolicy(**values)


def _reuse_results() -> ReuseSearchResultsPacket:
    return ReuseSearchResultsPacket(
        search_run_ref="reuse-run-001",
        searched=True,
        search_source="fixture",
        matches=[],
        blockers=[],
    )


def test_builds_evidence_packet_from_approved_exported_json() -> None:
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(),
        case_ref="approved-export-001",
        policy=_policy(),
    )

    assert isinstance(packet, NormalizedTicketEvidencePacket)
    assert packet.schema_version == NormalizedTicketEvidencePacket.SCHEMA_VERSION
    assert packet.case_ref == "approved-export-001"
    assert packet.input_class == InputClass.NORMALIZED_ZENDESK_EVIDENCE.value
    assert packet.issue_candidates[0]["candidate_id"] == "item-001"
    assert validate_evidence_safety(packet).ok is True


def test_builds_approved_sanitized_sample() -> None:
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(input_class=InputClass.APPROVED_SANITIZED_FIXTURE.value),
        case_ref="approved-sample-001",
        policy=_policy(input_class=InputClass.APPROVED_SANITIZED_FIXTURE.value),
    )

    assert packet.input_class == InputClass.APPROVED_SANITIZED_FIXTURE.value
    assert validate_evidence_packet(packet).ok is True


def test_builds_copied_sanitized_support_example() -> None:
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(
            input_class=InputClass.OPERATOR_SANITIZED_SUMMARY.value,
            sanitizer_report=None,
        ),
        case_ref="copied-support-example-001",
        policy=_policy(
            input_class=InputClass.OPERATOR_SANITIZED_SUMMARY.value,
            assume_sanitized=True,
        ),
    )

    assert packet.input_class == InputClass.OPERATOR_SANITIZED_SUMMARY.value
    assert packet.sanitizer_report == {"status": "passed", "source": "kcs7_policy"}
    assert validate_evidence_safety(packet).ok is True


def test_single_candidate_fields_can_be_promoted_to_top_level_evidence() -> None:
    payload = _export_payload(
        symptoms=[],
        confirmed_facts=[],
        supported_cause=None,
        supported_resolution_or_workaround=None,
    )

    packet = build_evidence_packet_from_zendesk_export(
        payload,
        case_ref="approved-export-002",
        policy=_policy(),
    )

    assert packet.symptoms == ["Backup task fails with a synthetic safe status."]
    assert packet.confirmed_facts == ["A safe backup setting is disabled."]
    assert packet.supported_cause == "A required backup setting is disabled."
    assert (
        packet.supported_resolution_or_workaround
        == "Enable the required backup setting."
    )
    assert validate_evidence_packet(packet).ok is True


def test_pipeline_consumes_builder_output() -> None:
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(),
        case_ref="pipeline-export-001",
        policy=_policy(),
    )

    decision = decide_kcs_action(packet, _reuse_results())
    reviewer_packet = render_reviewer_packet(packet, decision)
    report = build_validation_report(packet, decision, reviewer_packet)

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert reviewer_packet.auto_publish_allowed is False
    assert report.ready_for_reviewer is True
    assert "auto_publish_allowed" not in dump_json_dict(packet)


def test_multi_issue_output_can_flow_to_split_required_decision() -> None:
    candidates = [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "atomic": True,
            "candidate_id": "item-001",
            "confirmed_facts": ["Synthetic fact for item one."],
            "customer_reported": True,
            "kcs_applicable": True,
            "public_solution_safe": True,
            "resolution_state": "solved",
            "resolution_steps": ["Apply synthetic fix one."],
            "reuse_search_status": "checked",
            "source_refs": ["approved-export-source-item-001"],
            "summary": "Synthetic issue one",
            "supported_cause": "Synthetic cause one.",
            "supported_resolution_or_workaround": "Apply synthetic fix one.",
            "symptoms": ["Synthetic issue one"],
            "title": "Synthetic issue one",
        },
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "atomic": True,
            "candidate_id": "item-002",
            "confirmed_facts": ["Synthetic fact for item two."],
            "customer_reported": True,
            "kcs_applicable": True,
            "public_solution_safe": True,
            "resolution_state": "solved",
            "resolution_steps": ["Apply synthetic fix two."],
            "reuse_search_status": "checked",
            "source_refs": ["approved-export-source-item-002"],
            "summary": "Synthetic issue two",
            "supported_cause": "Synthetic cause two.",
            "supported_resolution_or_workaround": "Apply synthetic fix two.",
            "symptoms": ["Synthetic issue two"],
            "title": "Synthetic issue two",
        },
    ]
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(
            confirmed_facts=["Multiple safe synthetic issues are present."],
            issue_candidates=candidates,
            supported_cause="Multiple synthetic causes are present.",
            supported_resolution_or_workaround="Evaluate each item separately.",
            symptoms=["Synthetic issue one", "Synthetic issue two"],
        ),
        case_ref="split-export-001",
        policy=_policy(),
    )

    decision = decide_kcs_action(packet, _reuse_results())

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert len(decision.split_items) == 2


def test_malformed_schema_fails_closed() -> None:
    with pytest.raises(ContractValidationError, match="schema_version"):
        build_evidence_packet_from_zendesk_export(
            _export_payload(schema_version="wrong"),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_unknown_top_level_field_fails_closed() -> None:
    with pytest.raises(ContractValidationError, match="unsupported field"):
        build_evidence_packet_from_zendesk_export(
            _export_payload(raw_note="ignored raw-like field"),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_unknown_issue_candidate_field_fails_closed() -> None:
    candidate = dict(_export_payload()["issue_candidates"][0])  # type: ignore[index]
    candidate["unexpected_structured_field"] = "safe synthetic value"

    with pytest.raises(ContractValidationError, match="unsupported field"):
        build_evidence_packet_from_zendesk_export(
            _export_payload(issue_candidates=[candidate]),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_unsafe_issue_candidate_key_fails_without_echo() -> None:
    private_value = "person@example.com"
    candidate = dict(_export_payload()["issue_candidates"][0])  # type: ignore[index]
    candidate["raw_ticket"] = private_value

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(issue_candidates=[candidate]),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("requester_id", 12345678),
        ("user_id", "12345678"),
        ("organization_id", 12345678),
        ("external_id", "12345678"),
    ],
)
def test_nested_raw_id_like_values_fail_closed(key: str, value: object) -> None:
    private_value = str(value)

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(environment={"component": "Backup", key: value}),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("requesterId", 12345678),
        ("userId", "12345678"),
        ("ticketId", 12345678),
        ("organizationId", 12345678),
        ("externalId", "12345678"),
    ],
)
def test_nested_camel_case_raw_id_values_fail_closed(
    key: str,
    value: object,
) -> None:
    private_value = str(value)

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(environment={"component": "Backup", key: value}),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "private_key",
    [
        "person@example.com",
        "https://customer.example.net/private",
        "customer.example.net",
        "PLSK-12345678-1234",
        "ticket-123456",
    ],
)
def test_nested_private_like_keys_fail_closed(private_key: str) -> None:
    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(
                environment={"component": "Backup", private_key: "safe"}
            ),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_key not in str(captured.value)


@pytest.mark.parametrize(
    "environment",
    [
        {"component": "Backup", "score": float("nan")},
        {"component": "Backup", "score": float("inf")},
        {1: "Backup"},
    ],
)
def test_builder_rejects_non_strict_json_nested_objects(
    environment: dict[object, object],
) -> None:
    with pytest.raises(ContractValidationError):
        build_evidence_packet_from_zendesk_export(
            _export_payload(environment=environment),
            case_ref="approved-export-001",
            policy=_policy(),
        )


@pytest.mark.parametrize("candidate_id", [True, None, 123])
def test_candidate_id_must_be_string(candidate_id: object) -> None:
    candidate = {
        **_export_payload()["issue_candidates"][0],  # type: ignore[index]
        "candidate_id": candidate_id,
    }

    with pytest.raises(ContractValidationError):
        build_evidence_packet_from_zendesk_export(
            _export_payload(issue_candidates=[candidate]),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_invalid_candidate_article_type_fails_closed() -> None:
    candidate = {
        **_export_payload()["issue_candidates"][0],  # type: ignore[index]
        "article_type": "not_an_article_type",
    }

    with pytest.raises(ContractValidationError, match="article_type"):
        build_evidence_packet_from_zendesk_export(
            _export_payload(issue_candidates=[candidate]),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_unsafe_candidate_source_ref_fails_closed_without_echo() -> None:
    private_value = "ticket-123456"
    candidate = {
        **_export_payload()["issue_candidates"][0],  # type: ignore[index]
        "source_refs": [private_value],
    }

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(issue_candidates=[candidate]),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


def test_failed_sanitizer_report_fails_closed_without_echo() -> None:
    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(
                sanitizer_report={
                    "status": "failed",
                    "finding_count": 1,
                },
            ),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert "sanitizer_not_passed" in str(captured.value)


def test_unsafe_sanitizer_report_value_fails_without_echo() -> None:
    private_value = "person@example.com"

    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(
                sanitizer_report={
                    "status": "passed",
                    "sample": private_value,
                },
            ),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "private_value",
    [
        "person@example.com",
        "https://customer.example.net/private",
        "/Users/customer/ticket.txt",
        "PLSK-12345678-1234",
        "token=abc123",
    ],
)
def test_unsafe_private_values_fail_without_echo(private_value: str) -> None:
    with pytest.raises(ContractValidationError) as captured:
        build_evidence_packet_from_zendesk_export(
            _export_payload(symptoms=[private_value]),
            case_ref="approved-export-001",
            policy=_policy(),
        )

    assert private_value not in str(captured.value)


def test_text_only_raw_narrative_does_not_trigger_semantic_extraction() -> None:
    with pytest.raises(ContractValidationError):
        build_evidence_packet_from_zendesk_export(
            {
                "schema_version": APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
                "text": "Synthetic narrative that has not been structured.",
            },
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_internal_visibility_blocks_by_default() -> None:
    with pytest.raises(ContractValidationError, match="internal evidence"):
        build_evidence_packet_from_zendesk_export(
            _export_payload(
                visibility_summary={
                    "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
                },
            ),
            case_ref="approved-export-001",
            policy=_policy(),
        )


def test_internal_visibility_can_be_approved_by_policy() -> None:
    packet = build_evidence_packet_from_zendesk_export(
        _export_payload(
            issue_candidates=[
                {
                    **_export_payload()["issue_candidates"][0],  # type: ignore[index]
                    "public_solution_safe": False,
                }
            ],
            visibility_summary={
                "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
            },
        ),
        case_ref="approved-export-001",
        policy=_policy(allow_internal_reviewer_only=True),
    )

    assert packet.visibility_summary["internal_only_evidence_approved"] is True
    assert validate_evidence_safety(packet).ok is True


def test_builder_api_is_exported_from_package_root() -> None:
    assert kcs_core.EvidenceBuildPolicy is EvidenceBuildPolicy
    assert (
        kcs_core.build_evidence_packet_from_zendesk_export
        is build_evidence_packet_from_zendesk_export
    )
