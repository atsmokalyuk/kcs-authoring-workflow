from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

import kcs_core
from kcs_core.errors import ContractValidationError
from kcs_core.models import ArticleType, NormalizedTicketEvidencePacket
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    CandidateKcsItem,
    CandidateSemanticExtraction,
    EolRole,
    KcsItemStatus,
    ProductRelation,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
    build_evidence_packet_from_semantic_extraction,
    normalize_candidate_semantic_extraction,
    propose_semantic_kcs_items,
    validate_candidate_semantic_extraction,
)
from kcs_core.validation import validate_evidence_packet


def _item(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "article_type_hint": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": "item-001",
        "confirmed_facts": ["A safe Plesk backup setting is disabled."],
        "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
        "product_relation": ProductRelation.PLESK_OWNED.value,
        "source_refs": ["semantic-source-item-001"],
        "summary": "Plesk backup task fails with a synthetic safe status.",
        "supportability": Supportability.SUPPORTED.value,
        "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
        "supported_cause": "A required backup setting is disabled.",
        "supported_resolution_or_workaround": (
            "Enable the required backup setting."
        ),
        "symptoms": ["Backup task fails with a synthetic safe status."],
        "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
    }
    item.update(overrides)
    return item


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "case_ref": "semantic-case-001",
        "extraction_source_ref": "semantic-run-001",
        "items": [_item()],
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": ["semantic-source-001"],
    }
    payload.update(overrides)
    return payload


def _issue_candidates(payload: Mapping[str, object]) -> list[dict[str, object]]:
    export_payload = normalize_candidate_semantic_extraction(payload)
    candidates = export_payload["issue_candidates"]
    assert isinstance(candidates, list)
    return candidates


def _contract_item_with_malformed_fields(**overrides: object) -> CandidateKcsItem:
    values: dict[str, object] = {
        "article_type_hint": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": "item-001",
        "confirmed_facts": ("A safe Plesk backup setting is disabled.",),
        "environment": {},
        "eol_role": EolRole.UNCLEAR.value,
        "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
        "open_questions": (),
        "product_relation": ProductRelation.PLESK_OWNED.value,
        "question": None,
        "resolution_steps": (),
        "source_refs": ("semantic-source-item-001",),
        "summary": "Plesk backup task fails with a synthetic safe status.",
        "supportability": Supportability.SUPPORTED.value,
        "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
        "supported_answer": None,
        "supported_cause": "A required backup setting is disabled.",
        "supported_resolution_or_workaround": (
            "Enable the required backup setting."
        ),
        "symptoms": ("Backup task fails with a synthetic safe status.",),
        "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
    }
    values.update(overrides)
    item = object.__new__(CandidateKcsItem)
    for key, value in values.items():
        object.__setattr__(item, key, value)
    return item


def test_builds_evidence_packet_from_valid_semantic_extraction() -> None:
    packet = build_evidence_packet_from_semantic_extraction(_payload())

    assert isinstance(packet, NormalizedTicketEvidencePacket)
    assert packet.case_ref == "semantic-case-001"
    assert packet.issue_candidates[0]["candidate_id"] == "item-001"
    assert validate_evidence_packet(packet).ok is True


def test_multi_item_extraction_preserves_atomic_candidates() -> None:
    packet = build_evidence_packet_from_semantic_extraction(
        _payload(
            items=[
                _item(candidate_id="item-001"),
                _item(
                    candidate_id="item-002",
                    summary="Plesk mail service has a second safe symptom.",
                    source_refs=["semantic-source-item-002"],
                    symptoms=["Mail service has a synthetic safe symptom."],
                ),
            ]
        )
    )

    assert [item["candidate_id"] for item in packet.issue_candidates] == [
        "item-001",
        "item-002",
    ]
    assert set(validate_evidence_packet(packet).blockers) == {
        "missing_confirmed_facts",
        "missing_supported_resolution",
        "missing_symptoms",
        "multi_issue",
    }


def test_plesk_shipped_component_is_not_generic_third_party() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    product_relation=(
                        ProductRelation.PLESK_SHIPPED_OR_BUNDLED_COMPONENT.value
                    ),
                    summary="Bundled component has a safe synthetic issue.",
                )
            ]
        )
    )

    assert candidates[0]["kcs_applicable"] is True
    assert candidates[0]["third_party_only"] is False
    assert candidates[0]["third_party_generic"] is False


def test_howto_answer_steps_are_accepted_as_resolution_steps() -> None:
    payload = _payload(
        items=[
            _item(
                article_type_hint=ArticleType.HOWTO_QA.value,
                answer_steps=["Open the Plesk page and check the setting."],
                confirmed_facts=[],
                question="How to check a Plesk setting?",
                resolution_steps=[],
                supported_answer="Check the setting in Plesk.",
                supported_cause=None,
                supported_resolution_or_workaround=None,
                symptoms=[],
            )
        ]
    )

    assert validate_candidate_semantic_extraction(payload).ok is True
    candidates = _issue_candidates(payload)
    assert candidates[0]["resolution_steps"] == [
        "Open the Plesk page and check the setting."
    ]


def test_generic_third_party_guidance_maps_to_no_article_flags() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    article_type_hint=ArticleType.NONE.value,
                    kcs_item_status=KcsItemStatus.NO_ARTICLE.value,
                    product_relation=ProductRelation.GENERIC_THIRD_PARTY.value,
                    summary="Generic third-party application behavior.",
                )
            ]
        )
    )

    assert candidates[0]["kcs_applicable"] is False
    assert candidates[0]["third_party_only"] is True
    assert candidates[0]["third_party_generic"] is True


def test_generic_third_party_candidate_allowed_is_rejected() -> None:
    payload = _payload(
        items=[
            _item(
                kcs_item_status=KcsItemStatus.CANDIDATE_ALLOWED.value,
                product_relation=ProductRelation.GENERIC_THIRD_PARTY.value,
            )
        ]
    )

    with pytest.raises(ContractValidationError, match="product relation"):
        CandidateSemanticExtraction.from_json_dict(payload)


def test_customer_environment_specific_item_must_be_no_article() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    article_type_hint=ArticleType.NONE.value,
                    kcs_item_status=KcsItemStatus.NO_ARTICLE.value,
                    product_relation=ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value,
                    summary="Customer-specific website code issue.",
                )
            ]
        )
    )

    assert candidates[0]["customer_specific"] is True
    assert candidates[0]["kcs_applicable"] is False


def test_customer_environment_specific_candidate_allowed_is_rejected() -> None:
    payload = _payload(
        items=[
            _item(
                kcs_item_status=KcsItemStatus.CANDIDATE_ALLOWED.value,
                product_relation=ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value,
            )
        ]
    )

    with pytest.raises(ContractValidationError, match="product relation"):
        CandidateSemanticExtraction.from_json_dict(payload)


def test_non_plesk_support_solution_defaults_to_internal_only_candidate() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    kcs_item_status=KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,
                    product_relation=(
                        ProductRelation.NON_PLESK_OWNED_BUT_SUPPORT_PROVIDED_SOLUTION.value
                    ),
                    summary="Support provided a reusable scoped diagnostic.",
                    visibility_hint=VisibilityHint.INTERNAL_REVIEWER_ONLY.value,
                )
            ]
        )
    )

    assert candidates[0]["kcs_applicable"] is True
    assert candidates[0]["public_solution_safe"] is False
    assert candidates[0]["unsupported_public_article"] is True


def test_non_plesk_support_solution_cannot_be_public_candidate() -> None:
    payload = _payload(
        items=[
            _item(
                kcs_item_status=KcsItemStatus.CANDIDATE_ALLOWED.value,
                product_relation=(
                    ProductRelation.NON_PLESK_OWNED_BUT_SUPPORT_PROVIDED_SOLUTION.value
                ),
                visibility_hint=VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
            )
        ]
    )

    with pytest.raises(ContractValidationError, match="product relation"):
        CandidateSemanticExtraction.from_json_dict(payload)


def test_blocked_need_more_evidence_maps_to_unsolved_candidate() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    kcs_item_status=KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value,
                    open_questions=["Which safe component is affected?"],
                    supported_cause=None,
                    supported_resolution_or_workaround=None,
                )
            ]
        )
    )

    assert candidates[0]["resolution_state"] == "unsolved"
    assert candidates[0]["kcs_applicable"] is False


def test_explicit_eol_affected_runtime_must_be_no_article() -> None:
    candidates = _issue_candidates(
        _payload(
            items=[
                _item(
                    article_type_hint=ArticleType.NONE.value,
                    eol_role=EolRole.AFFECTED_RUNTIME.value,
                    kcs_item_status=KcsItemStatus.NO_ARTICLE.value,
                    product_relation=ProductRelation.EOL_OR_UNSUPPORTED_ONLY.value,
                    supportability=Supportability.EOL_ONLY.value,
                    supportability_basis=(
                        SupportabilityBasis.EXPLICIT_INPUT_MENTION.value
                    ),
                )
            ]
        )
    )

    assert candidates[0]["kcs_applicable"] is False
    assert candidates[0]["unsupported_public_article"] is True


def test_eol_source_for_migration_can_be_candidate_allowed() -> None:
    packet = build_evidence_packet_from_semantic_extraction(
        _payload(
            items=[
                _item(
                    eol_role=EolRole.SOURCE_FOR_MIGRATION_OR_UPGRADE.value,
                    product_relation=ProductRelation.PLESK_OWNED.value,
                    summary="Migration from explicitly EOL source is supported.",
                    supportability=Supportability.EOL_ONLY.value,
                    supportability_basis=(
                        SupportabilityBasis.EXPLICIT_INPUT_MENTION.value
                    ),
                    supported_resolution_or_workaround=(
                        "Migrate the subscription to the supported target."
                    ),
                )
            ]
        )
    )

    assert packet.issue_candidates[0]["kcs_applicable"] is True
    assert validate_evidence_packet(packet).ok is True


def test_eol_historical_context_can_remain_candidate_allowed() -> None:
    packet = build_evidence_packet_from_semantic_extraction(
        _payload(
            items=[
                _item(
                    eol_role=EolRole.HISTORICAL_CONTEXT.value,
                    summary="Historical EOL context is not the affected runtime.",
                    supportability=Supportability.EOL_ONLY.value,
                    supportability_basis=(
                        SupportabilityBasis.EXPLICIT_INPUT_MENTION.value
                    ),
                )
            ]
        )
    )

    assert packet.issue_candidates[0]["kcs_applicable"] is True
    assert validate_evidence_packet(packet).ok is True


def test_eol_inference_without_explicit_input_basis_is_rejected() -> None:
    payload = _payload(
        items=[
            _item(
                eol_role=EolRole.AFFECTED_RUNTIME.value,
                kcs_item_status=KcsItemStatus.NO_ARTICLE.value,
                supportability=Supportability.EOL_ONLY.value,
                supportability_basis=SupportabilityBasis.NOT_CHECKED.value,
            )
        ]
    )

    result = validate_candidate_semantic_extraction(payload)

    assert result.ok is False
    assert result.blockers == ("invalid_semantic_extraction",)
    assert result.to_json_dict() == {
        "ok": False,
        "blockers": ["invalid_semantic_extraction"],
        "warnings": [],
    }


def test_eol_unclear_role_requires_more_evidence_status() -> None:
    payload = _payload(
        items=[
            _item(
                eol_role=EolRole.UNCLEAR.value,
                kcs_item_status=KcsItemStatus.CANDIDATE_ALLOWED.value,
                supportability=Supportability.UNSUPPORTED.value,
                supportability_basis=(
                    SupportabilityBasis.EXPLICIT_INPUT_MENTION.value
                ),
            )
        ]
    )

    with pytest.raises(ContractValidationError, match="eol status"):
        CandidateSemanticExtraction.from_json_dict(payload)


def test_semantic_extraction_rejects_kcs_action_output_field() -> None:
    item = _item()
    item["recommended_action"] = "create_candidate"

    with pytest.raises(ContractValidationError, match="unsupported field"):
        CandidateSemanticExtraction.from_json_dict(_payload(items=[item]))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("article_type_hint", "flag_existing"),
        ("kcs_item_status", "create_candidate"),
        ("product_relation", "reuse_existing"),
    ],
)
def test_semantic_extraction_rejects_kcs_action_values(
    field: str, value: str
) -> None:
    item = _item(**{field: value})

    with pytest.raises(ContractValidationError):
        CandidateSemanticExtraction.from_json_dict(_payload(items=[item]))


def test_semantic_extraction_rejects_unsafe_values_without_echo() -> None:
    private_value = "person@example.com"
    item = _item(summary=private_value)

    with pytest.raises(ContractValidationError) as captured:
        CandidateSemanticExtraction.from_json_dict(_payload(items=[item]))

    assert private_value not in str(captured.value)


def test_invalid_enum_error_has_no_value_carrying_cause() -> None:
    payload = _payload(items=[_item(product_relation="not_a_relation")])

    with pytest.raises(ContractValidationError) as captured:
        CandidateSemanticExtraction.from_json_dict(payload)

    assert captured.value.__cause__ is None


def test_provider_failure_returns_value_safe_error() -> None:
    private_value = "person@example.com"

    class FailingProvider:
        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            raise RuntimeError(f"failed for {private_value}")

    with pytest.raises(ContractValidationError) as captured:
        propose_semantic_kcs_items(
            {"case_ref": "semantic-case-001"},
            provider=FailingProvider(),
        )

    assert str(captured.value) == "semantic extraction provider failed"
    assert private_value not in str(captured.value)


def test_provider_returned_contract_object_rejects_string_list_field_without_echo(
) -> None:
    private_value = "person@example.com"

    class ObjectProvider:
        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            item = CandidateKcsItem(
                candidate_id="item-001",
                kcs_item_status=KcsItemStatus.CANDIDATE_ALLOWED.value,
                product_relation=ProductRelation.PLESK_OWNED.value,
                summary="Safe synthetic summary.",
                supportability=Supportability.SUPPORTED.value,
                symptoms=private_value,  # type: ignore[arg-type]
            )
            return CandidateSemanticExtraction(
                case_ref="semantic-case-001",
                extraction_source_ref="semantic-run-001",
                items=(item,),
                source_refs=("semantic-source-001",),
            )

    with pytest.raises(ContractValidationError) as captured:
        propose_semantic_kcs_items(
            {"case_ref": "semantic-case-001"},
            provider=ObjectProvider(),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "item_kwargs",
    [
        {"summary": 123},
        {"supported_cause": 123},
        {"supported_resolution_or_workaround": 123},
        {"question": 123},
        {"supported_answer": 123},
        {"source_refs": ("not safe ref",)},
        {"article_type_hint": "flag_existing"},
    ],
)
def test_provider_returned_contract_object_rejects_malformed_object_fields(
    item_kwargs: dict[str, object],
) -> None:
    class ObjectProvider:
        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            return CandidateSemanticExtraction(
                case_ref="semantic-case-001",
                extraction_source_ref="semantic-run-001",
                items=(_contract_item_with_malformed_fields(**item_kwargs),),
                source_refs=("semantic-source-001",),
            )

    with pytest.raises(ContractValidationError) as captured:
        propose_semantic_kcs_items(
            {"case_ref": "semantic-case-001"},
            provider=ObjectProvider(),
        )

    assert captured.value.__cause__ is None


def test_provider_context_is_checked_before_call_without_echo() -> None:
    private_value = "person@example.com"

    class RecordingProvider:
        called = False

        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            self.called = True
            return _payload()

    provider = RecordingProvider()

    with pytest.raises(ContractValidationError) as captured:
        propose_semantic_kcs_items(
            {"case_ref": "semantic-case-001", "raw_context": private_value},
            provider=provider,
        )

    assert provider.called is False
    assert private_value not in str(captured.value)


def test_provider_context_must_be_object_before_call() -> None:
    class RecordingProvider:
        called = False

        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            self.called = True
            return _payload()

    provider = RecordingProvider()

    with pytest.raises(ContractValidationError, match="context"):
        propose_semantic_kcs_items(  # type: ignore[arg-type]
            ["semantic-case-001"],
            provider=provider,
        )

    assert provider.called is False


def test_provider_output_is_validated_before_return() -> None:
    class MappingProvider:
        def propose_candidates(self, context: Mapping[str, Any]) -> object:
            return _payload(case_ref="semantic-case-002")

    extraction = propose_semantic_kcs_items(
        {"case_ref": "semantic-case-002"},
        provider=MappingProvider(),
    )

    assert extraction.case_ref == "semantic-case-002"
    assert extraction.items[0].candidate_id == "item-001"


def test_root_exports_semantic_extraction_api() -> None:
    assert kcs_core.CandidateSemanticExtraction is CandidateSemanticExtraction
    assert kcs_core.ProductRelation is ProductRelation
    assert kcs_core.SupportabilityBasis is SupportabilityBasis
    assert (
        kcs_core.build_evidence_packet_from_semantic_extraction
        is build_evidence_packet_from_semantic_extraction
    )
