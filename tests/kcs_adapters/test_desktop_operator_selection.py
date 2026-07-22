from __future__ import annotations

import pytest

from kcs_adapters import desktop_workflow
from kcs_adapters.desktop_operator_selection import (
    attach_pending_selection,
    new_pending_draft_selection,
    operator_choice_request,
    operator_choice_review_summary,
    operator_choice_submit_options,
    selected_pending_candidate,
    split_candidate_cards,
)
from kcs_core.errors import ContractValidationError
from kcs_core.models import ArticleType, CandidateOrigin


def _candidate(
    item_ref: str,
    title: object,
    *,
    candidate_origin: str = CandidateOrigin.CUSTOMER_REPORTED.value,
) -> dict[str, object]:
    return {
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "candidate_origin": candidate_origin,
        "item_ref": item_ref,
        "title": title,
    }


def test_pending_selection_builds_choice_request() -> None:
    pending = new_pending_draft_selection(
        [_candidate("candidate-001", "Safe issue")],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    request = operator_choice_request(pending, submit_tool="kcs_draft_article")
    review_summary = operator_choice_review_summary(pending)

    assert pending.selection_ref.startswith("operator-selection-")
    assert pending.candidate_refs == ("candidate-001",)
    assert request["mode"] == "single_or_batch_select"
    assert request["options"][0]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": pending.selection_ref,
    }
    assert "all_submit_arguments" not in request
    assert [option["value"] for option in request["options"]] == ["candidate-001"]
    assert operator_choice_submit_options(pending) == request["options"]
    assert review_summary["selection_ref"] == pending.selection_ref


def test_pending_selection_exposes_native_all_option_with_exact_arguments() -> None:
    pending = new_pending_draft_selection(
        [
            _candidate("candidate-001", "First safe issue"),
            _candidate("candidate-002", "Second safe issue"),
        ],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    request = operator_choice_request(pending, submit_tool="kcs_draft_article")

    expected_arguments = {
        "operator_selected_item_refs": ["candidate-001", "candidate-002"],
        "operator_selection_ref": pending.selection_ref,
    }
    assert request["options"][-1] == {
        "label": "All candidates",
        "submit_arguments": expected_arguments,
        "value": "all",
    }


def test_pending_selection_rejects_duplicate_candidate_refs() -> None:
    with pytest.raises(
        ContractValidationError,
        match="operator candidate refs invalid",
    ):
        new_pending_draft_selection(
            [
                _candidate("candidate-001", "First safe issue"),
                _candidate("candidate-001", "Duplicate safe issue"),
            ],
            approved_summary_text="Approved sanitized summary.",
            ttl_seconds=900,
        )


def test_pending_selection_rejects_native_all_reserved_ref() -> None:
    with pytest.raises(
        ContractValidationError,
        match="operator candidate refs invalid",
    ):
        new_pending_draft_selection(
            [_candidate("all", "Reserved selection value")],
            approved_summary_text="Approved sanitized summary.",
            ttl_seconds=900,
        )


def test_pending_selection_omits_all_option_above_batch_limit() -> None:
    pending = new_pending_draft_selection(
        [
            _candidate(f"candidate-{index:03d}", f"Safe issue {index}")
            for index in range(1, 7)
        ],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    request = operator_choice_request(pending, submit_tool="kcs_draft_article")

    assert len(request["options"]) == 6
    assert "all_submit_arguments" not in request
    assert all(option["value"] != "all" for option in request["options"])


def test_support_discovered_candidate_is_marked_in_choice_ui() -> None:
    pending = new_pending_draft_selection(
        [
            _candidate(
                "candidate-001",
                "Repair file permissions",
                candidate_origin=CandidateOrigin.SUPPORT_DISCOVERED.value,
            )
        ],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    request = operator_choice_request(pending, submit_tool="kcs_draft_article")

    assert pending.item_candidate_cards[0]["candidate_origin"] == (
        "support_discovered"
    )
    assert request["options"][0]["label"] == (
        "Repair file permissions — Found by Support"
    )


def test_attach_pending_selection_updates_result() -> None:
    pending = new_pending_draft_selection(
        [_candidate("candidate-001", "Safe issue")],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )
    result = {
        "review_summary": {
            "draft_available": False,
            "reason": "multiple_kcs_items_detected",
        }
    }

    attach_pending_selection(result, pending, submit_tool="kcs_draft_article")

    assert result["operator_selection_ref"] == pending.selection_ref
    assert result["operator_choice_confirmed"] is False
    assert result["operator_choice_request"]["submit_tool"] == "kcs_draft_article"
    assert result["operator_choice_submit_options"] == result[
        "operator_choice_request"
    ]["options"]
    assert "operator_all_submit_arguments" not in result
    assert "all_submit_arguments" not in result["operator_choice_request"]
    assert (
        result["review_summary"]["operator_choice_request"]["selection_ref"]
        == pending.selection_ref
    )


def test_selected_pending_candidate_returns_safe_copy() -> None:
    pending = new_pending_draft_selection(
        [_candidate("candidate-001", "Safe issue")],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    selected = selected_pending_candidate(pending, "candidate-001")
    selected["title"] = "Changed"

    assert pending.item_candidates[0]["title"] == "Safe issue"


def test_split_candidate_cards_falls_back_for_blank_titles() -> None:
    cards = split_candidate_cards([_candidate("candidate-001", "  ")])

    assert cards == [
        {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "candidate_origin": "customer_reported",
            "item_ref": "candidate-001",
            "title": "Item 1",
        }
    ]


def test_selected_pending_candidate_invalid_ref_is_controlled() -> None:
    pending = new_pending_draft_selection(
        [_candidate("candidate-001", "Safe issue")],
        approved_summary_text="Approved sanitized summary.",
        ttl_seconds=900,
    )

    with pytest.raises(ContractValidationError):
        selected_pending_candidate(pending, "candidate-002")


def test_desktop_workflow_reexports_operator_selection_helpers() -> None:
    assert desktop_workflow.PendingDraftSelection.__module__.endswith(
        "desktop_operator_selection"
    )
    assert (
        desktop_workflow.new_pending_draft_selection
        is new_pending_draft_selection
    )
    assert desktop_workflow.operator_choice_request is operator_choice_request
    assert (
        desktop_workflow.operator_choice_submit_options
        is operator_choice_submit_options
    )
    assert (
        desktop_workflow.operator_choice_review_summary
        is operator_choice_review_summary
    )
    assert desktop_workflow.attach_pending_selection is attach_pending_selection
    assert desktop_workflow.selected_pending_candidate is selected_pending_candidate
    assert desktop_workflow.split_candidate_cards is split_candidate_cards
