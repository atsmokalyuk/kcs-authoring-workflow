"""Desktop operator-selection state and choice payload helpers."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import (
    ensure_safe_sanitized_payload,
    normalize_optional_string,
)

_DRAFT_SELECTION_REF_BYTES = 12


@dataclass(frozen=True)
class PendingDraftSelection:
    """Opaque pending operator selection state."""

    selection_ref: str
    approved_summary_text: str
    approved_summary_source_kind: str | None
    candidate_refs: tuple[str, ...]
    item_candidates: tuple[JsonDict, ...]
    item_candidate_cards: tuple[JsonDict, ...]
    semantic_item_outcomes: tuple[JsonDict, ...]
    selected_candidate_refs: tuple[str, ...]
    expires_at: float


def new_pending_draft_selection(
    item_candidates: list[JsonDict],
    *,
    approved_summary_text: str,
    approved_summary_source_kind: str | None = None,
    semantic_item_outcomes: list[JsonDict] | None = None,
    ttl_seconds: float,
) -> PendingDraftSelection:
    """Create opaque in-memory selection state for one split-required result."""

    item_candidate_cards = split_candidate_cards(item_candidates)
    return PendingDraftSelection(
        selection_ref=(
            "operator-selection-"
            f"{secrets.token_urlsafe(_DRAFT_SELECTION_REF_BYTES)}"
        ),
        approved_summary_text=approved_summary_text,
        approved_summary_source_kind=approved_summary_source_kind,
        candidate_refs=tuple(
            candidate["item_ref"]
            for candidate in item_candidates
            if isinstance(candidate.get("item_ref"), str)
        ),
        item_candidates=tuple(dict(candidate) for candidate in item_candidates),
        item_candidate_cards=tuple(item_candidate_cards),
        semantic_item_outcomes=tuple(
            dict(item) for item in semantic_item_outcomes or item_candidate_cards
        ),
        selected_candidate_refs=(),
        expires_at=time.monotonic() + ttl_seconds,
    )


def split_candidate_cards(candidates: list[JsonDict]) -> list[JsonDict]:
    """Return compact operator-facing cards for split candidate choices."""

    cards: list[JsonDict] = []
    for index, candidate in enumerate(candidates, start=1):
        item_ref = candidate.get("item_ref")
        title = candidate.get("title")
        card: JsonDict = {
            "item_ref": (
                item_ref if isinstance(item_ref, str) and item_ref else f"item-{index}"
            ),
            "title": _safe_choice_text(title, fallback=f"Item {index}"),
        }
        article_type = candidate.get("article_type")
        if isinstance(article_type, str) and article_type:
            card["article_type"] = article_type
        ensure_safe_sanitized_payload(card)
        cards.append(card)
    return cards


def operator_choice_request(
    pending_selection: PendingDraftSelection,
    *,
    submit_tool: str,
) -> JsonDict:
    """Return deterministic operator choice request payload."""

    options = operator_choice_submit_options(pending_selection)
    request: JsonDict = {
        "all_submit_arguments": [
            option["submit_arguments"] for option in options
        ],
        "automatic_item_retry_allowed": False,
        "manual_draft_allowed": False,
        "mode": "single_select",
        "options": options,
        "presentation": "native_choice_popup_preferred",
        "prose_only_choice_allowed": False,
        "selection_ref": pending_selection.selection_ref,
        "submit_tool": submit_tool,
    }
    ensure_safe_sanitized_payload(request)
    return request


def operator_choice_submit_options(
    pending_selection: PendingDraftSelection,
) -> list[JsonDict]:
    """Return exact per-option submit arguments for deterministic fallback."""

    return [
        {
            "label": str(candidate.get("title") or candidate["item_ref"]),
            "submit_arguments": {
                "operator_selected_item_ref": candidate["item_ref"],
                "operator_selection_ref": pending_selection.selection_ref,
            },
            "value": candidate["item_ref"],
        }
        for candidate in _remaining_candidate_cards(pending_selection)
    ]


def operator_choice_review_summary(
    pending_selection: PendingDraftSelection,
) -> JsonDict:
    """Return compact review summary for a pending operator choice."""

    remaining_count = len(
        [
            candidate_ref
            for candidate_ref in pending_selection.candidate_refs
            if candidate_ref not in pending_selection.selected_candidate_refs
        ]
    )
    return {
        "mode": "single_select",
        "option_count": remaining_count,
        "presentation": "native_choice_popup_preferred",
        "prose_only_choice_allowed": False,
        "selection_ref": pending_selection.selection_ref,
    }


def attach_pending_selection(
    result: JsonDict,
    pending_selection: PendingDraftSelection,
    *,
    submit_tool: str,
) -> None:
    """Attach deterministic pending selection refs and choice request."""

    result["item_candidates"] = list(pending_selection.item_candidate_cards)
    choice_request = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    result["operator_choice_options"] = choice_request["options"]
    result["operator_choice_request"] = choice_request
    result["operator_choice_submit_options"] = choice_request["options"]
    result["operator_all_submit_arguments"] = choice_request[
        "all_submit_arguments"
    ]
    result["operator_selection_ref"] = pending_selection.selection_ref
    result["operator_choice_confirmed"] = False
    result["semantic_item_outcomes"] = list(pending_selection.semantic_item_outcomes)
    result["review_summary"]["operator_selection_ref"] = pending_selection.selection_ref
    result["review_summary"]["operator_choice_request"] = (
        operator_choice_review_summary(pending_selection)
    )
    result["review_summary"]["semantic_item_outcomes"] = list(
        pending_selection.semantic_item_outcomes
    )


def selected_pending_candidate(
    pending_selection: PendingDraftSelection,
    selected_item_ref: object,
) -> JsonDict:
    """Return the selected pending candidate or raise a contract error."""

    if selected_item_ref in pending_selection.selected_candidate_refs:
        raise ContractValidationError("operator selection already used")
    for candidate in pending_selection.item_candidates:
        if candidate.get("item_ref") == selected_item_ref:
            return dict(candidate)
    raise ContractValidationError("operator selection invalid")


def pending_selection_after_draft(
    pending_selection: PendingDraftSelection,
    selected_item_ref: str,
) -> PendingDraftSelection | None:
    """Return updated pending state after one selected candidate was drafted."""

    selected_refs = tuple(
        dict.fromkeys((*pending_selection.selected_candidate_refs, selected_item_ref))
    )
    if all(ref in selected_refs for ref in pending_selection.candidate_refs):
        return None
    return PendingDraftSelection(
        selection_ref=pending_selection.selection_ref,
        approved_summary_text=pending_selection.approved_summary_text,
        approved_summary_source_kind=(
            pending_selection.approved_summary_source_kind
        ),
        candidate_refs=pending_selection.candidate_refs,
        item_candidates=pending_selection.item_candidates,
        item_candidate_cards=pending_selection.item_candidate_cards,
        semantic_item_outcomes=pending_selection.semantic_item_outcomes,
        selected_candidate_refs=selected_refs,
        expires_at=pending_selection.expires_at,
    )


def remaining_operator_choice_status(
    pending_selection: PendingDraftSelection,
    *,
    submit_tool: str,
) -> JsonDict:
    """Return compact next-choice metadata for remaining candidates."""

    remaining_candidates = _remaining_candidate_cards(pending_selection)
    choice_request = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    status: JsonDict = {
        "next_required_action": "operator_select_remaining_item",
        "next_tool": submit_tool,
        "remaining_item_candidates": remaining_candidates,
        "remaining_operator_choice_request": choice_request,
        "remaining_operator_choice_submit_options": choice_request["options"],
        "remaining_selection_ref": pending_selection.selection_ref,
        "semantic_item_outcomes": list(pending_selection.semantic_item_outcomes),
    }
    if len(remaining_candidates) == 1:
        status["next_arguments"] = choice_request["options"][0]["submit_arguments"]
    ensure_safe_sanitized_payload(status)
    return status


def _remaining_candidate_cards(
    pending_selection: PendingDraftSelection,
) -> list[JsonDict]:
    return [
        candidate
        for candidate in pending_selection.item_candidate_cards
        if candidate["item_ref"] not in pending_selection.selected_candidate_refs
    ]


def _safe_choice_text(value: object, *, fallback: str) -> str:
    text = normalize_optional_string(value)
    if text is None:
        return fallback
    text = text[:140].strip()
    if not text:
        return fallback
    try:
        ensure_safe_sanitized_payload(text)
    except ContractValidationError:
        return fallback
    return text


__all__ = [
    "PendingDraftSelection",
    "attach_pending_selection",
    "new_pending_draft_selection",
    "operator_choice_request",
    "operator_choice_review_summary",
    "operator_choice_submit_options",
    "pending_selection_after_draft",
    "remaining_operator_choice_status",
    "selected_pending_candidate",
    "split_candidate_cards",
]
