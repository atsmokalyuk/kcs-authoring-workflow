"""Draft-article argument normalization helpers for Desktop MCP."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_adapters import desktop_payload as _desktop_payload
from kcs_adapters.desktop_operator_selection import PendingDraftSelection
from kcs_adapters.desktop_workflow_results import (
    selection_error_result,
    split_required_result,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, require_json_object
from kcs_core.sanitizer import ensure_safe_sanitized_payload

# Internal/canonical compatibility helpers only. Do not use this broad allowed
# set to validate the Claude Desktop alias path; primary Desktop calls must use
# DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS and fail closed on any other argument.
DRAFT_ARTICLE_ARGS = frozenset(
    {
        "approved_summary_text",
        "auto_publish_allowed",
        "case_ref",
        "customer_replies",
        "debug",
        "item",
        "item_candidates",
        "network_calls",
        "operator_choice_confirmed",
        "operator_selected_item_ref",
        "operator_selection_ref",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "ready_for_real_ticket_use",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "ticket_ref",
        "writes_files",
    }
)
DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS = frozenset(
    {
        "approved_summary_text",
        "debug",
        "operator_selected_item_ref",
        "operator_selection_ref",
        "ticket_ref",
    }
)
_DRAFT_ARTICLE_ITEM_CANDIDATE_FIELDS = frozenset(
    {
        "applicable_to",
        "article_type",
        "confirmed_facts",
        "environment",
        "item_ref",
        "question",
        "reason",
        "resolution_steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "summary",
        "symptoms",
        "title",
    }
)
_DRAFT_ARTICLE_ITEM_METADATA_FIELDS = frozenset({"item_ref", "reason"})
_APPROVED_SUMMARY_ITEM_FIELDS = _desktop_payload.APPROVED_SUMMARY_ITEM_FIELDS
_APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS = (
    _desktop_payload.APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS
)


class DraftArticleArgumentError(ValueError):
    """Draft-article argument shape error."""


def draft_article_arguments(arguments: Mapping[str, Any]) -> Mapping[str, Any]:
    require_args(arguments, DRAFT_ARTICLE_ARGS, required=frozenset())
    try:
        _desktop_payload.require_approved_summary_false_only_args(arguments)
    except ContractValidationError:
        raise
    normalized = draft_article_with_normalized_item(arguments)
    if "item_candidates" not in arguments:
        return normalized
    candidates = draft_article_item_candidates(arguments["item_candidates"])
    normalized["item_candidates"] = candidates
    if len(candidates) == 1 and "item" not in normalized:
        candidate_item = {
            key: value
            for key, value in candidates[0].items()
            if key in _APPROVED_SUMMARY_ITEM_FIELDS
        }
        if candidate_item:
            normalized["item"] = candidate_item
    return normalized


def draft_article_authoring_args_from_candidate(
    *,
    approved_summary_text: str,
    candidate: Mapping[str, Any],
    debug: bool,
    approved_summary_source_kind: str | None = None,
) -> JsonDict:
    arguments: JsonDict = {
        "approved_summary_text": approved_summary_text,
        "debug": debug,
        "item": dict(candidate),
    }
    if approved_summary_source_kind == "approved_clean_ticket":
        arguments["_approved_summary_text_source"] = (
            _desktop_payload.APPROVED_SUMMARY_TEXT_SOURCE_APPROVED_CLEAN_TICKET
        )
    return draft_article_with_normalized_item(arguments)


def draft_article_candidates_with_refs(
    candidates: list[JsonDict],
) -> list[JsonDict]:
    normalized: list[JsonDict] = []
    for index, candidate in enumerate(candidates, start=1):
        candidate_with_ref = dict(candidate)
        item_ref = candidate_with_ref.get("item_ref")
        if not isinstance(item_ref, str) or not item_ref:
            candidate_with_ref["item_ref"] = f"candidate-{index:03d}"
        normalized.append(candidate_with_ref)
    return normalized


def draft_article_with_normalized_item(
    arguments: Mapping[str, Any],
) -> JsonDict:
    normalized = dict(arguments)
    if "item" not in normalized:
        return normalized
    try:
        item = dict(require_json_object(normalized["item"]))
    except ContractValidationError as exc:
        raise DraftArticleArgumentError("Invalid draft article item.") from exc
    item_ref = item.pop("item_ref", None)
    for metadata_field in _DRAFT_ARTICLE_ITEM_METADATA_FIELDS - {"item_ref"}:
        item.pop(metadata_field, None)
    if (
        isinstance(item_ref, str)
        and item_ref
        and "candidate_id" not in item
    ):
        item["candidate_id"] = item_ref
    normalized["item"] = item
    return normalized


def draft_article_without_operator_selection_fields(
    arguments: Mapping[str, Any],
) -> Mapping[str, Any]:
    return {
        key: value
        for key, value in arguments.items()
        if key
        not in {
            "operator_choice_confirmed",
            "operator_selected_item_ref",
            "operator_selection_ref",
            "item_candidates",
        }
    }


def draft_article_without_uploaded_ticket_ref(
    arguments: Mapping[str, Any],
) -> Mapping[str, Any]:
    if "approved_summary_text" not in arguments or "ticket_ref" not in arguments:
        return arguments
    cleaned = dict(arguments)
    cleaned.pop("ticket_ref", None)
    return cleaned


def draft_article_selection_error_result(
    arguments: Mapping[str, Any],
    pending_selection: PendingDraftSelection,
    *,
    schema_version: str,
    submit_tool: str,
) -> JsonDict | None:
    return selection_error_result(
        arguments,
        pending_selection,
        schema_version=schema_version,
        submit_tool=submit_tool,
    )


def draft_article_item_candidates(value: object) -> list[JsonDict]:
    if not isinstance(value, list):
        raise DraftArticleArgumentError("Invalid item candidates.")
    candidates: list[JsonDict] = []
    for candidate in value:
        if not isinstance(candidate, Mapping):
            raise DraftArticleArgumentError("Invalid item candidate.")
        if any(key not in _DRAFT_ARTICLE_ITEM_CANDIDATE_FIELDS for key in candidate):
            raise DraftArticleArgumentError("Unexpected item candidate field.")
        candidate_json = dict(candidate)
        ensure_safe_sanitized_payload(candidate_json)
        candidates.append(candidate_json)
    return candidates


def draft_article_split_required_result(
    arguments: Mapping[str, Any],
    *,
    schema_version: str,
) -> JsonDict | None:
    if draft_article_has_confirmed_operator_selection(arguments):
        return None
    candidates = arguments.get("item_candidates")
    if not isinstance(candidates, list) or len(candidates) <= 1:
        return None
    return split_required_result(
        candidates,
        schema_version=schema_version,
    )


def draft_article_has_confirmed_operator_selection(
    arguments: Mapping[str, Any],
) -> bool:
    return (
        arguments.get("operator_choice_confirmed") is True
        and isinstance(arguments.get("operator_selection_ref"), str)
        and isinstance(arguments.get("operator_selected_item_ref"), str)
    )


def has_approved_summary_authoring_input(arguments: Mapping[str, Any]) -> bool:
    if "approved_summary_text" in arguments:
        return True
    if "item" in arguments:
        return True
    return any(key in arguments for key in _APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS)


def has_structured_approved_summary_item_input(arguments: Mapping[str, Any]) -> bool:
    if "item" in arguments:
        return True
    return any(key in arguments for key in _APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS)


def require_args(
    arguments: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    required: frozenset[str],
) -> None:
    if any(key not in allowed for key in arguments):
        raise DraftArticleArgumentError("Unexpected tool argument.")
    if any(key not in arguments for key in required):
        raise DraftArticleArgumentError("Missing tool argument.")


__all__ = [
    "DRAFT_ARTICLE_ARGS",
    "DRAFT_ARTICLE_DESKTOP_PRIMARY_ARGS",
    "DraftArticleArgumentError",
    "draft_article_arguments",
    "draft_article_authoring_args_from_candidate",
    "draft_article_candidates_with_refs",
    "draft_article_has_confirmed_operator_selection",
    "draft_article_item_candidates",
    "draft_article_selection_error_result",
    "draft_article_split_required_result",
    "draft_article_with_normalized_item",
    "draft_article_without_operator_selection_fields",
    "draft_article_without_uploaded_ticket_ref",
    "has_approved_summary_authoring_input",
    "has_structured_approved_summary_item_input",
    "require_args",
]
