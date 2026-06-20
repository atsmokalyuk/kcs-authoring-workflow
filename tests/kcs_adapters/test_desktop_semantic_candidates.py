from __future__ import annotations

import pytest

from kcs_adapters import desktop_workflow
from kcs_adapters.desktop_semantic_candidates import (
    desktop_item_candidates_from_semantic_extraction,
)
from kcs_core.errors import ContractValidationError
from kcs_core.models import ArticleType
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    KcsItemStatus,
    ProductRelation,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
)


def _extraction_payload() -> dict[str, object]:
    return {
        "case_ref": "desktop-candidate-case-001",
        "extraction_source_ref": "desktop-candidate-run-001",
        "items": [
            {
                "article_type_hint": ArticleType.TECHNICAL_SCR.value,
                "candidate_id": "candidate-001",
                "confirmed_facts": ["A safe Plesk fact is confirmed."],
                "environment": {
                    "applicable_to": ["Plesk for Linux"],
                    "platform": "Plesk for Linux",
                },
                "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
                "product_relation": ProductRelation.PLESK_OWNED.value,
                "resolution_steps": ["Run systemctl restart product-service."],
                "source_refs": ["desktop-candidate-source-item-001"],
                "summary": "Plesk task has a safe synthetic issue",
                "supportability": Supportability.SUPPORTED.value,
                "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
                "supported_cause": "A required product service is stopped.",
                "supported_resolution_or_workaround": (
                    "Restart the required product service."
                ),
                "symptoms": ["A safe Plesk task fails."],
                "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
            }
        ],
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": ["desktop-candidate-source-001"],
    }


def test_semantic_extraction_converts_to_desktop_candidates() -> None:
    candidates = desktop_item_candidates_from_semantic_extraction(
        _extraction_payload()
    )

    assert candidates == [
        {
            "applicable_to": ["Plesk for Linux"],
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "confirmed_facts": ["A safe Plesk fact is confirmed."],
            "environment": {
                "applicable_to": ["Plesk for Linux"],
                "platform": "Plesk for Linux",
            },
            "item_ref": "candidate-001",
            "resolution_steps": ["Run systemctl restart product-service."],
            "summary": "Plesk task has a safe synthetic issue",
            "supported_cause": "A required product service is stopped.",
            "supported_resolution_or_workaround": (
                "Restart the required product service."
            ),
            "symptoms": ["A safe Plesk task fails."],
            "title": "Plesk task has a safe synthetic issue",
        }
    ]


def test_semantic_extraction_howto_uses_question_as_symptom_fallback() -> None:
    payload = _extraction_payload()
    item = dict(payload["items"][0])
    item.update(
        {
            "article_type_hint": ArticleType.HOWTO_QA.value,
            "question": "How to restart a safe Plesk service?",
            "supported_answer": "Restart the safe service and verify the task.",
            "supported_cause": None,
            "supported_resolution_or_workaround": None,
            "symptoms": [],
        }
    )
    payload["items"] = [item]

    candidates = desktop_item_candidates_from_semantic_extraction(payload)

    assert candidates[0]["article_type"] == ArticleType.HOWTO_QA.value
    assert candidates[0]["symptoms"] == ["How to restart a safe Plesk service?"]
    assert candidates[0]["question"] == "How to restart a safe Plesk service?"
    assert candidates[0]["supported_answer"] == (
        "Restart the safe service and verify the task."
    )


def test_semantic_extraction_invalid_output_is_controlled() -> None:
    with pytest.raises(ContractValidationError):
        desktop_item_candidates_from_semantic_extraction(
            {"schema_version": "wrong", "items": []}
        )


def test_semantic_extraction_invalid_article_type_is_controlled() -> None:
    payload = _extraction_payload()
    item = dict(payload["items"][0])
    item["article_type_hint"] = "break-fix"
    payload["items"] = [item]

    with pytest.raises(ContractValidationError):
        desktop_item_candidates_from_semantic_extraction(payload)


def test_desktop_workflow_reexports_semantic_candidate_converter() -> None:
    assert (
        desktop_workflow.desktop_item_candidates_from_semantic_extraction
        is desktop_item_candidates_from_semantic_extraction
    )
