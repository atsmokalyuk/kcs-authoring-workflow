"""Clean-ticket metadata for controlled Desktop semantic review."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from kcs_core.json_payload import JsonDict

CLEAN_TICKET_METADATA_FILE_NAME = "clean.ticket.meta.json"
CLEAN_TICKET_METADATA_SCHEMA_VERSION = "kcs_clean_ticket_metadata_v1"
CLEAN_TICKET_SOURCE_CLAUDE_VISIBLE_REGISTRATION = "claude_visible_registration"
CLEAN_TICKET_SOURCE_CLEANUP_FORM = "cleanup_form"

_ALLOWED_SOURCE_KINDS = frozenset(
    {
        CLEAN_TICKET_SOURCE_CLAUDE_VISIBLE_REGISTRATION,
        CLEAN_TICKET_SOURCE_CLEANUP_FORM,
    }
)
_ALLOWED_METADATA_KEYS = frozenset(
    {
        "clean_ticket_sha256",
        "schema_version",
        "semantic_review_allowed",
        "source_kind",
        "ticket_ref",
    }
)


class CleanTicketMetadataError(ValueError):
    """Value-safe clean-ticket metadata error."""

    def __init__(self, debug_code: str) -> None:
        super().__init__("clean ticket metadata invalid")
        self.debug_code = debug_code


def clean_ticket_sha256(text: str) -> str:
    """Return the SHA-256 digest for a clean ticket transcript."""

    return sha256(text.encode("utf-8")).hexdigest()


def clean_ticket_metadata_payload(
    *,
    ticket_ref: str,
    text: str,
    semantic_review_allowed: bool,
    source_kind: str,
) -> JsonDict:
    """Build metadata bound to the exact clean ticket text."""

    if source_kind not in _ALLOWED_SOURCE_KINDS:
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    return {
        "clean_ticket_sha256": clean_ticket_sha256(text),
        "schema_version": CLEAN_TICKET_METADATA_SCHEMA_VERSION,
        "semantic_review_allowed": semantic_review_allowed,
        "source_kind": source_kind,
        "ticket_ref": ticket_ref,
    }


def write_clean_ticket_metadata(path: Path, payload: Mapping[str, Any]) -> None:
    """Write clean-ticket metadata without following symlink targets."""

    try:
        _validate_metadata_shape(payload)
        if path.is_symlink():
            raise CleanTicketMetadataError("clean_ticket_metadata_write_invalid")
        if path.parent.exists() and path.parent.is_symlink():
            raise CleanTicketMetadataError("clean_ticket_metadata_write_invalid")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(dict(payload), sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
    except CleanTicketMetadataError:
        raise
    except OSError:
        raise CleanTicketMetadataError("clean_ticket_metadata_write_failed") from None


def read_clean_ticket_metadata(path: Path) -> JsonDict:
    """Read clean-ticket metadata from a non-symlink JSON file."""

    try:
        if not path.is_file() or path.is_symlink():
            raise CleanTicketMetadataError("clean_ticket_metadata_missing")
        if path.stat().st_size > 4096:
            raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except CleanTicketMetadataError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid") from None
    if not isinstance(payload, dict):
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    return payload


def validate_clean_ticket_metadata_for_semantic_review(
    *,
    path: Path,
    ticket_ref: str,
    text: str,
) -> JsonDict:
    """Validate metadata before any Claude-visible semantic-review output."""

    payload = read_clean_ticket_metadata(path)
    _validate_metadata_shape(payload)
    if payload["ticket_ref"] != ticket_ref:
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    if payload["clean_ticket_sha256"] != clean_ticket_sha256(text):
        raise CleanTicketMetadataError("clean_ticket_hash_mismatch")
    if payload["semantic_review_allowed"] is not True:
        raise CleanTicketMetadataError("clean_ticket_semantic_review_not_allowed")
    return dict(payload)


def _validate_metadata_shape(payload: Mapping[str, Any]) -> None:
    if any(key not in _ALLOWED_METADATA_KEYS for key in payload):
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    if payload.get("schema_version") != CLEAN_TICKET_METADATA_SCHEMA_VERSION:
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    if not isinstance(payload.get("ticket_ref"), str) or not payload["ticket_ref"]:
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    digest = payload.get("clean_ticket_sha256")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(char not in "0123456789abcdef" for char in digest)
    ):
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    if not isinstance(payload.get("semantic_review_allowed"), bool):
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")
    if payload.get("source_kind") not in _ALLOWED_SOURCE_KINDS:
        raise CleanTicketMetadataError("clean_ticket_metadata_invalid")


__all__ = [
    "CLEAN_TICKET_METADATA_FILE_NAME",
    "CLEAN_TICKET_METADATA_SCHEMA_VERSION",
    "CLEAN_TICKET_SOURCE_CLAUDE_VISIBLE_REGISTRATION",
    "CLEAN_TICKET_SOURCE_CLEANUP_FORM",
    "CleanTicketMetadataError",
    "clean_ticket_metadata_payload",
    "clean_ticket_sha256",
    "read_clean_ticket_metadata",
    "validate_clean_ticket_metadata_for_semantic_review",
    "write_clean_ticket_metadata",
]
