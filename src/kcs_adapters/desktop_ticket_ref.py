"""Repository-local approved ticket summary reference loading for Desktop."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from kcs_adapters import desktop_payload
from kcs_adapters.desktop_payload import ApprovedSummaryInputError
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload

APPROVED_TICKET_ARGS = frozenset(
    {
        "debug",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "ticket_ref",
        *desktop_payload.APPROVED_SUMMARY_FALSE_ONLY_ARGS,
    }
)
APPROVED_TICKET_FILE_KEYS = frozenset(
    {
        "approved_summary_text",
        "case_ref",
        "item",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "schema_version",
        "ticket_ref",
    }
)
APPROVED_TICKET_FILE_SCHEMA_VERSION = "kcs_approved_ticket_summary_v1"
APPROVED_TICKET_SUMMARY_DIR = Path("local-data") / "approved-summaries"
MAX_APPROVED_TICKET_FILE_BYTES = 64 * 1024

_SAFE_APPROVED_TICKET_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")


def approved_ticket_author_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    """Load and merge an approved sanitized ticket summary by opaque ref."""

    try:
        _require_known_args(arguments, APPROVED_TICKET_ARGS)
        if "ticket_ref" not in arguments:
            raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
        desktop_payload.require_approved_summary_false_only_args(arguments)
        ticket_ref = checked_approved_ticket_ref(arguments["ticket_ref"])
        file_payload = approved_ticket_file_payload(ticket_ref)
        merged = approved_ticket_merged_arguments(
            ticket_ref=ticket_ref,
            file_payload=file_payload,
            arguments=arguments,
        )
        desktop_payload.require_approved_summary_false_only_args(merged)
        return merged
    except ApprovedSummaryInputError:
        raise
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid") from None


def approved_ticket_ref_from_arguments(arguments: Mapping[str, Any]) -> str:
    try:
        return checked_approved_ticket_ref(arguments.get("ticket_ref"))
    except (ApprovedSummaryInputError, ContractValidationError):
        return "invalid-ticket-ref"


def checked_approved_ticket_ref(value: object) -> str:
    if not isinstance(value, str) or not _SAFE_APPROVED_TICKET_REF_RE.fullmatch(value):
        raise ApprovedSummaryInputError("approved_ticket_ref_invalid")
    ensure_safe_sanitized_payload(value)
    return value


def approved_ticket_file_payload(ticket_ref: str) -> JsonDict:
    path = approved_ticket_summary_path(ticket_ref)
    payload = _read_approved_ticket_file_payload(path)
    _validate_approved_ticket_file_payload(payload, ticket_ref=ticket_ref)
    return payload


def approved_ticket_summary_path(ticket_ref: str) -> Path:
    root = approved_ticket_repo_root()
    return root / APPROVED_TICKET_SUMMARY_DIR / f"{ticket_ref}.json"


def approved_ticket_repo_root() -> Path:
    value = os.environ.get("KCS_AUTHORING_MVP_REPO_ROOT")
    root = Path(value) if value else Path.cwd()
    return root.resolve(strict=False)


def approved_ticket_merged_arguments(
    *,
    ticket_ref: str,
    file_payload: Mapping[str, Any],
    arguments: Mapping[str, Any],
) -> JsonDict:
    merged: JsonDict = {
        key: value
        for key, value in file_payload.items()
        if key not in {"schema_version", "ticket_ref"}
    }
    merged.setdefault("case_ref", f"approved-ticket-{ticket_ref}")
    for key in (
        "debug",
        "reference_article",
        "reference_article_html",
        "reference_article_text",
        "reuse_search_checked",
        "reuse_search_run_ref",
        *desktop_payload.APPROVED_SUMMARY_FALSE_ONLY_ARGS,
    ):
        if key in arguments:
            merged[key] = arguments[key]
    return merged


def _read_approved_ticket_file_payload(path: Path) -> JsonDict:
    try:
        if not path.is_file() or path.is_symlink():
            raise ApprovedSummaryInputError("approved_ticket_summary_not_found")
        if path.stat().st_size > MAX_APPROVED_TICKET_FILE_BYTES:
            raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle, parse_constant=_reject_json_constant)
    except ApprovedSummaryInputError:
        raise
    except (OSError, json.JSONDecodeError, ValueError):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid") from None
    if not isinstance(payload, dict):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    return payload


def _validate_approved_ticket_file_payload(
    payload: Mapping[str, Any],
    *,
    ticket_ref: str,
) -> None:
    if any(key not in APPROVED_TICKET_FILE_KEYS for key in payload):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    ensure_safe_sanitized_payload(payload)
    if payload.get("schema_version") != APPROVED_TICKET_FILE_SCHEMA_VERSION:
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    if payload.get("ticket_ref") != ticket_ref:
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")


def _require_known_args(
    arguments: Mapping[str, Any],
    allowed: frozenset[str],
) -> None:
    if any(key not in allowed for key in arguments):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value is not allowed: {value}")
