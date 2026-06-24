"""Deterministic sanitized-input checks for KCS evidence building."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from math import isfinite
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict

_PRIVATE_VALUE_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I),
    re.compile(r"https?://[^\s\"']+", re.I),
    re.compile(
        r"\b(?!example\.(?:com|net|org|invalid)\b)"
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63}\b",
        re.I,
    ),
    re.compile(r"(?:/Users/|/home/|C:\\Users\\)", re.I),
    re.compile(r"\b(?:PLSK|EXT)[-_.]?\d{4,}(?:[-_.]?\d+)*\b", re.I),
    re.compile(r"\b(?:ticket|zendesk|zd)[-_ #:]?\d{4,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+",
        re.I,
    ),
    re.compile(r"\bauthorization:\s*bearer\s+\S+", re.I),
)
_SAFE_FILENAME_RE = re.compile(
    r"\b[A-Za-z0-9][A-Za-z0-9_-]*\."
    r"(?:conf|ini|cnf|yaml|yml|json|xml|php|log|local|pid|bak|backup|disabled|orig|old)"
    r"(?:\.(?:bak|backup|disabled|orig|old))?\b"
)
_SAFE_PUBLIC_SUPPORT_URL_RE = re.compile(
    r"https://support\.plesk\.com/hc/en-us/articles/[0-9A-Za-z_-]+"
)
_SAFE_PUBLIC_SUPPORT_EMAIL_RE = re.compile(r"\bcs@plesk\.com\b", re.I)
_SAFE_PUBLIC_PLESK_HOST_RE = re.compile(r"\bmy\.plesk\.com\b", re.I)
_RAW_ID_VALUE_RE = re.compile(r"\d{6,}")
_SAFE_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}")
_SAFE_ID_KEYS = frozenset({"candidate_id"})
_RAW_ID_KEY_COMPACT_NAMES = frozenset(
    {
        "accountid",
        "assigneeid",
        "customerid",
        "externalid",
        "id",
        "licenseid",
        "organizationid",
        "requesterid",
        "submitterid",
        "ticketid",
        "userid",
        "zendeskid",
    }
)
_UNSAFE_RAW_KEY_FRAGMENTS = (
    ".knowledge",
    ".private",
    "account_id",
    "api_key",
    "article_body",
    "authorization",
    "chunk_body",
    "chunk_text",
    "comments",
    "credential",
    "customer_id",
    "external_id",
    "full_text",
    "hostname",
    "internal_comment",
    "license_id",
    "organization_id",
    "private_path",
    "raw_html",
    "raw_internal",
    "raw_ticket",
    "raw_zendesk",
    "redaction_map",
    "secret",
    "snippet_body",
    "snippet_text",
    "ticket.redacted.md",
    "ticket_id",
    "ticket.txt",
    "token",
    "vector",
    "zendesk_id",
)
_UNSAFE_RAW_VALUE_FRAGMENTS = (
    ".knowledge",
    ".private",
    "article_body",
    "chunk_body",
    "chunk_text",
    "full_text",
    "raw_html",
    "raw_internal",
    "raw_ticket",
    "raw_zendesk",
    "redaction_map",
    "snippet_body",
    "snippet_text",
    "ticket.redacted.md",
    "ticket.txt",
)


def ensure_safe_sanitized_payload(value: object) -> None:
    """Reject raw/private markers before evidence packet construction."""

    _ensure_strict_json_value(value)
    if _contains_private_raw_value(value):
        raise ContractValidationError("sanitized input contains unsafe value")


def ensure_allowed_keys(
    payload: Mapping[str, Any], allowed_keys: Iterable[str], *, label: str
) -> None:
    """Reject unknown object keys without echoing the key value."""

    allowed = set(allowed_keys)
    if any(key not in allowed for key in payload):
        raise ContractValidationError(f"{label} contains unsupported field")


def ensure_safe_ref(value: str, *, label: str) -> str:
    """Return an opaque safe reference or raise a value-free error."""

    normalized = normalize_optional_string(value)
    if normalized is None or not _SAFE_REF_RE.fullmatch(normalized):
        raise ContractValidationError(f"{label} must be an opaque safe reference")
    ensure_safe_sanitized_payload(normalized)
    return normalized


def normalize_optional_string(value: object) -> str | None:
    """Normalize a safe optional string."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError("expected string value")
    normalized = value.strip()
    if not normalized:
        return None
    ensure_safe_sanitized_payload(normalized)
    return normalized


def normalize_string_list(value: object, *, required: bool = False) -> list[str]:
    """Normalize a string or string list into a safe list."""

    if value is None:
        result: list[str] = []
    elif isinstance(value, str):
        normalized = normalize_optional_string(value)
        result = [normalized] if normalized else []
    elif isinstance(value, list | tuple):
        result = []
        for item in value:
            normalized = normalize_optional_string(item)
            if normalized:
                result.append(normalized)
    else:
        raise ContractValidationError("expected string list value")
    if required and not result:
        raise ContractValidationError("required string list is missing")
    return result


def normalize_json_object(value: object, *, required: bool = False) -> JsonDict:
    """Normalize a safe JSON object."""

    if value is None:
        if required:
            raise ContractValidationError("required object is missing")
        return {}
    if not isinstance(value, Mapping):
        raise ContractValidationError("expected object value")
    ensure_safe_sanitized_payload(value)
    return dict(value)


def normalize_json_object_list(value: object) -> list[JsonDict]:
    """Normalize a safe list of JSON objects."""

    if value is None:
        return []
    if not isinstance(value, list | tuple):
        raise ContractValidationError("expected object list value")
    result: list[JsonDict] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ContractValidationError("expected object list value")
        ensure_safe_sanitized_payload(item)
        result.append(dict(item))
    return result


def _contains_private_raw_value(value: object) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_private_raw_item(key, item) for key, item in value.items())
    if isinstance(value, list | tuple):
        return any(_contains_private_raw_value(item) for item in value)
    if isinstance(value, str):
        return _contains_private_raw_text(value)
    return False


def _ensure_strict_json_value(value: object) -> None:
    if isinstance(value, Mapping):
        _ensure_strict_json_object(value)
        return
    if isinstance(value, list):
        _ensure_strict_json_list(value)
        return
    if _is_strict_json_scalar(value):
        return
    raise ContractValidationError("sanitized input must be strict JSON")


def _ensure_strict_json_object(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("sanitized input must be strict JSON")
        _ensure_strict_json_value(item)


def _ensure_strict_json_list(value: list[object]) -> None:
    for item in value:
        _ensure_strict_json_value(item)


def _is_strict_json_scalar(value: object) -> bool:
    if value is None or isinstance(value, str | bool | int):
        return True
    if isinstance(value, float) and isfinite(value):
        return True
    return False


def _contains_private_raw_item(key: object, value: object) -> bool:
    return (
        _contains_private_raw_key(key)
        or _is_generic_raw_id_value(key, value)
        or _contains_private_raw_value(value)
    )


def _contains_private_raw_key(key: object) -> bool:
    if not isinstance(key, str):
        return _contains_private_raw_value(key)
    normalized = key.casefold()
    return any(
        fragment in normalized for fragment in _UNSAFE_RAW_KEY_FRAGMENTS
    ) or _contains_private_raw_text(key)


def _is_generic_raw_id_value(key: object, value: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.casefold()
    compact = normalized.replace("_", "").replace("-", "")
    if normalized in _SAFE_ID_KEYS:
        return False
    if (
        normalized == "id"
        or normalized.endswith("_id")
        or normalized.endswith("-id")
        or compact in _RAW_ID_KEY_COMPACT_NAMES
    ):
        return _looks_like_raw_numeric_id(value)
    return False


def _looks_like_raw_numeric_id(value: object) -> bool:
    if isinstance(value, int) and not isinstance(value, bool):
        return value >= 100000
    if isinstance(value, float) and isfinite(value):
        return value.is_integer() and value >= 100000
    if isinstance(value, str):
        return bool(_RAW_ID_VALUE_RE.fullmatch(value.strip()))
    return False


def _contains_private_raw_text(value: str) -> bool:
    normalized = value.casefold()
    if any(fragment in normalized for fragment in _UNSAFE_RAW_VALUE_FRAGMENTS):
        return True
    text_without_safe_public_urls = _SAFE_PUBLIC_SUPPORT_URL_RE.sub("", value)
    text_without_safe_public_contacts = _SAFE_PUBLIC_SUPPORT_EMAIL_RE.sub(
        "", text_without_safe_public_urls
    )
    text_without_safe_public_hosts = _SAFE_PUBLIC_PLESK_HOST_RE.sub(
        "", text_without_safe_public_contacts
    )
    text_without_safe_filenames = _SAFE_FILENAME_RE.sub(
        "", text_without_safe_public_hosts
    )
    return any(
        pattern.search(text_without_safe_filenames)
        for pattern in _PRIVATE_VALUE_PATTERNS
    )
