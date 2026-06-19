"""Repository-local approved ticket summary reference loading for Desktop."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from hashlib import sha256
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
APPROVED_TICKET_CLEAN_TEXT_FILE_NAME = "clean.ticket.txt"
APPROVED_TICKET_STORE_ROOT_ENV = "KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT"
APPROVED_TICKET_STORAGE_HINT_ENV = "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_HINT"
APPROVED_TICKET_STORAGE_REF_ENV = "KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_REF"
MAX_APPROVED_TICKET_FILE_BYTES = 512 * 1024

_SAFE_APPROVED_TICKET_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")
_REGISTER_CLEAN_TICKET_ARGS = frozenset({"clean_ticket_text", "debug", "ticket_ref"})
_CLEAN_TICKET_TRUNCATION_RE = re.compile(
    r"\[(?:debug\s+)?output\s+truncated\]|\boutput\s+truncated\b",
    re.I,
)
_CLEAN_TICKET_INCOMPLETE_TAIL_RE = re.compile(
    r"\bshow\s+more\b|"
    r"\binvestigation\s+continues\b|"
    r"\bupdate\s+you\s+once\s+(?:there'?s\s+)?more\s+information\b|"
    r"\bwill\s+update\s+you\s+once\s+(?:there'?s\s+)?more\s+information\b",
    re.I,
)
_CLEAN_TICKET_TOOL_ARTIFACT_RE = re.compile(
    r"</?\s*(?:function|parameter|tool_call)\b|<\s*parameter\s+name\s*=",
    re.I,
)
_FINAL_EVIDENCE_MARKERS = (
    "backed up",
    "disabled",
    "fixed",
    "confirmed",
    "resolution",
    "resolved",
    "restarted",
    "root cause",
)


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


def register_clean_ticket_arguments(arguments: Mapping[str, Any]) -> JsonDict:
    """Write one approved clean ticket transcript and return an opaque ref."""

    _require_known_args(arguments, _REGISTER_CLEAN_TICKET_ARGS)
    text = _checked_clean_ticket_text(arguments.get("clean_ticket_text"))
    ticket_ref = _register_ticket_ref(arguments.get("ticket_ref"), text)
    path = approved_ticket_clean_text_path(ticket_ref)
    _write_clean_ticket_text(path, text)
    digest = sha256(text.encode("utf-8")).hexdigest()
    return {
        "auto_publish_allowed": False,
        "byte_length": len(text.encode("utf-8")),
        "clean_ticket_sha256": digest,
        "clean_ticket_store_ref": "approved-summary-clean-ticket",
        **_clean_ticket_storage_fields(),
        "network_calls": False,
        "next_arguments": {"ticket_ref": ticket_ref},
        "next_tool_name": "kcs_draft_article",
        "ok": True,
        "public_output_approved": False,
        "ready_for_real_ticket_use": False,
        "result_kind": "clean_ticket_registered",
        "schema_version": "kcs_mcp_tool_result_v1",
        "ticket_ref": ticket_ref,
        "writes_files": True,
    }


def checked_approved_ticket_ref(value: object) -> str:
    if not isinstance(value, str) or not _SAFE_APPROVED_TICKET_REF_RE.fullmatch(value):
        raise ApprovedSummaryInputError("approved_ticket_ref_invalid")
    ensure_safe_sanitized_payload(value)
    return value


def _checked_clean_ticket_text(value: object) -> str:
    if not isinstance(value, str):
        raise ApprovedSummaryInputError("clean_ticket_text_invalid")
    text = value.strip()
    if not text:
        raise ApprovedSummaryInputError("clean_ticket_text_invalid")
    if len(text.encode("utf-8")) > MAX_APPROVED_TICKET_FILE_BYTES:
        raise ApprovedSummaryInputError("clean_ticket_text_invalid")
    ensure_safe_sanitized_payload(text)
    if _clean_ticket_text_has_tool_artifact(text):
        raise ApprovedSummaryInputError("clean_ticket_text_invalid")
    if _clean_ticket_text_looks_incomplete(text):
        raise ApprovedSummaryInputError("clean_ticket_text_incomplete")
    return text


def _clean_ticket_text_has_tool_artifact(text: str) -> bool:
    return bool(_CLEAN_TICKET_TOOL_ARTIFACT_RE.search(text))


def _clean_ticket_text_looks_incomplete(text: str) -> bool:
    matches = [
        *list(_CLEAN_TICKET_TRUNCATION_RE.finditer(text)),
        *list(_CLEAN_TICKET_INCOMPLETE_TAIL_RE.finditer(text)),
    ]
    if not matches:
        return False
    matches.sort(key=lambda match: match.start())
    last_marker_end = matches[-1].end()
    if last_marker_end < len(text) * 0.75:
        return False
    tail = text[last_marker_end:].casefold()
    return not any(marker in tail for marker in _FINAL_EVIDENCE_MARKERS)


def _register_ticket_ref(value: object, text: str) -> str:
    if value in (None, ""):
        return f"ticket-{sha256(text.encode('utf-8')).hexdigest()[:12]}"
    return checked_approved_ticket_ref(value)


def _write_clean_ticket_text(path: Path, text: str) -> None:
    try:
        if path.exists() and path.is_symlink():
            raise ApprovedSummaryInputError("clean_ticket_write_invalid")
        if path.parent.exists() and path.parent.is_symlink():
            raise ApprovedSummaryInputError("clean_ticket_write_invalid")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except ApprovedSummaryInputError:
        raise
    except OSError:
        raise ApprovedSummaryInputError("clean_ticket_write_failed") from None


def approved_ticket_file_payload(ticket_ref: str) -> JsonDict:
    path = approved_ticket_summary_path(ticket_ref)
    if path.is_file() or path.is_symlink():
        payload = _read_approved_ticket_file_payload(path)
    else:
        payload = _read_approved_ticket_clean_text_payload(
            approved_ticket_clean_text_path(ticket_ref),
            ticket_ref=ticket_ref,
        )
    _validate_approved_ticket_file_payload(payload, ticket_ref=ticket_ref)
    return payload


def approved_ticket_summary_path(ticket_ref: str) -> Path:
    root = approved_ticket_repo_root()
    return root / APPROVED_TICKET_SUMMARY_DIR / f"{ticket_ref}.json"


def approved_ticket_clean_text_path(ticket_ref: str) -> Path:
    root = approved_ticket_repo_root()
    return (
        root
        / APPROVED_TICKET_SUMMARY_DIR
        / ticket_ref
        / APPROVED_TICKET_CLEAN_TEXT_FILE_NAME
    )


def approved_ticket_repo_root() -> Path:
    value = os.environ.get(APPROVED_TICKET_STORE_ROOT_ENV) or os.environ.get(
        "KCS_AUTHORING_MVP_REPO_ROOT"
    )
    root = Path(value) if value else Path.cwd()
    return root.resolve(strict=False)


def _clean_ticket_storage_fields() -> JsonDict:
    storage_hint = os.environ.get(APPROVED_TICKET_STORAGE_HINT_ENV, "").strip()
    storage_ref = os.environ.get(APPROVED_TICKET_STORAGE_REF_ENV, "").strip()
    fields: JsonDict = {}
    if storage_hint:
        fields["clean_ticket_storage_hint"] = storage_hint
    if storage_ref:
        fields["clean_ticket_storage_ref"] = storage_ref
    return fields


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


def _read_approved_ticket_clean_text_payload(
    path: Path,
    *,
    ticket_ref: str,
) -> JsonDict:
    try:
        if not path.is_file() or path.is_symlink():
            raise ApprovedSummaryInputError("approved_ticket_summary_not_found")
        if path.stat().st_size > MAX_APPROVED_TICKET_FILE_BYTES:
            raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
        text = path.read_text(encoding="utf-8")
    except ApprovedSummaryInputError:
        raise
    except (OSError, UnicodeDecodeError):
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid") from None
    if not text.strip():
        raise ApprovedSummaryInputError("approved_ticket_summary_invalid")
    ensure_safe_sanitized_payload(text)
    return {
        "approved_summary_text": text,
        "schema_version": APPROVED_TICKET_FILE_SCHEMA_VERSION,
        "ticket_ref": ticket_ref,
    }


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
