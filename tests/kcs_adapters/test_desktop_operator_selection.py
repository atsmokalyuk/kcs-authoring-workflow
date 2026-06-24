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
from kcs_core.models import ArticleType


def _candidate(item_ref: str, title: object) -> dict[str, object]:
    return {
        "article_type": ArticleType.TECHNICAL_SCR.value,
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
    assert request["mode"] == "single_select"
    assert request["options"][0]["submit_arguments"] == {
        "operator_selected_item_ref": "candidate-001",
        "operator_selection_ref": pending.selection_ref,
    }
    assert request["all_submit_arguments"] == [
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending.selection_ref,
        }
    ]
    assert operator_choice_submit_options(pending) == request["options"]
    assert review_summary["selection_ref"] == pending.selection_ref


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
    assert result["operator_all_submit_arguments"] == result[
        "operator_choice_request"
    ]["all_submit_arguments"]
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
