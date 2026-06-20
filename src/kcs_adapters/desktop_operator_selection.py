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
    candidate_refs: tuple[str, ...]
    item_candidates: tuple[JsonDict, ...]
    item_candidate_cards: tuple[JsonDict, ...]
    expires_at: float


def new_pending_draft_selection(
    item_candidates: list[JsonDict],
    *,
    approved_summary_text: str,
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
        candidate_refs=tuple(
            candidate["item_ref"]
            for candidate in item_candidates
            if isinstance(candidate.get("item_ref"), str)
        ),
        item_candidates=tuple(dict(candidate) for candidate in item_candidates),
        item_candidate_cards=tuple(item_candidate_cards),
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

    options = [
        {
            "label": str(candidate.get("title") or candidate["item_ref"]),
            "submit_arguments": {
                "operator_selected_item_ref": candidate["item_ref"],
                "operator_selection_ref": pending_selection.selection_ref,
            },
            "value": candidate["item_ref"],
        }
        for candidate in pending_selection.item_candidate_cards
    ]
    request: JsonDict = {
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


def operator_choice_review_summary(
    pending_selection: PendingDraftSelection,
) -> JsonDict:
    """Return compact review summary for a pending operator choice."""

    return {
        "mode": "single_select",
        "option_count": len(pending_selection.item_candidate_cards),
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
    result["operator_choice_options"] = list(pending_selection.item_candidate_cards)
    result["operator_choice_request"] = operator_choice_request(
        pending_selection,
        submit_tool=submit_tool,
    )
    result["operator_selection_ref"] = pending_selection.selection_ref
    result["operator_choice_confirmed"] = False
    result["review_summary"]["operator_selection_ref"] = pending_selection.selection_ref
    result["review_summary"]["operator_choice_request"] = (
        operator_choice_review_summary(pending_selection)
    )


def selected_pending_candidate(
    pending_selection: PendingDraftSelection,
    selected_item_ref: object,
) -> JsonDict:
    """Return the selected pending candidate or raise a contract error."""

    for candidate in pending_selection.item_candidates:
        if candidate.get("item_ref") == selected_item_ref:
            return dict(candidate)
    raise ContractValidationError("operator selection invalid")


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
    "selected_pending_candidate",
    "split_candidate_cards",
]
