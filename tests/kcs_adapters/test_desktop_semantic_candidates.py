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


def test_semantic_extraction_howto_normalizes_first_person_question_title() -> None:
    payload = _extraction_payload()
    item = dict(payload["items"][0])
    item.update(
        {
            "article_type_hint": ArticleType.HOWTO_QA.value,
            "question": "How can I check OPcache in Plesk?",
            "supported_answer": "Open Plesk > Domains > example.com > PHP Settings.",
            "supported_cause": None,
            "supported_resolution_or_workaround": None,
            "symptoms": [],
            "summary": "Checking OPcache in Plesk",
        }
    )
    payload["items"] = [item]

    candidates = desktop_item_candidates_from_semantic_extraction(payload)

    assert candidates[0]["title"] == "How to check OPcache in Plesk?"
    assert candidates[0]["summary"] == "How to check OPcache in Plesk?"
    assert candidates[0]["question"] == "How to check OPcache in Plesk?"


def test_semantic_extraction_howto_preserves_customer_error_question() -> None:
    payload = _extraction_payload()
    item = dict(payload["items"][0])
    question = (
        "Can we create an account to manage our licence when my.plesk.com says "
        "the email address does not exist or our message is considered spam?"
    )
    item.update(
        {
            "article_type_hint": ArticleType.HOWTO_QA.value,
            "question": question,
            "supported_answer": "Contact Customer Success at cs@plesk.com.",
            "supported_cause": None,
            "supported_resolution_or_workaround": None,
            "symptoms": [],
            "summary": (
                "Licensing or my.plesk.com account issue forwarded to "
                "Customer Success"
            ),
        }
    )
    payload["items"] = [item]

    candidates = desktop_item_candidates_from_semantic_extraction(payload)

    assert candidates[0]["title"] == (
        "Can we create an account to manage our licence?"
    )
    assert candidates[0]["summary"] == (
        "Can we create an account to manage our licence?"
    )
    assert candidates[0]["question"] == question
    assert "Customer Success" not in candidates[0]["title"]
    assert "Customer Success" in candidates[0]["supported_answer"]


def test_semantic_extraction_action_like_cause_with_question_becomes_howto() -> None:
    payload = _extraction_payload()
    item = dict(payload["items"][0])
    item.update(
        {
            "article_type_hint": ArticleType.TECHNICAL_SCR.value,
            "question": (
                "How to disable Nextcloud maintenance mode using the OCC "
                "command on a Plesk server?"
            ),
            "resolution_steps": [
                (
                    "Run: sudo -u system-user /var/www/vhosts/example.com/occ "
                    "maintenance:mode --off"
                ),
            ],
            "supported_answer": "Run OCC as the domain system user.",
            "supported_cause": (
                "Use the correct system user or PHP version on the Plesk server."
            ),
            "supported_resolution_or_workaround": None,
            "symptoms": [],
            "summary": (
                "How to disable Nextcloud maintenance mode using the OCC command "
                "on a Plesk server"
            ),
        }
    )
    payload["items"] = [item]

    candidates = desktop_item_candidates_from_semantic_extraction(payload)

    assert candidates[0]["article_type"] == ArticleType.HOWTO_QA.value
    assert candidates[0]["title"] == (
        "How to disable Nextcloud maintenance mode using the OCC command on "
        "a Plesk server?"
    )
    assert "supported_cause" not in candidates[0]
    assert candidates[0]["answer_steps"] == item["resolution_steps"]


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
