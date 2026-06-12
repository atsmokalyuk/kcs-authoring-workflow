"""Safety and evidence gates for normalized KCS input packets."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from ipaddress import ip_address, ip_network
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.models import NormalizedTicketEvidencePacket


class InputClass(StrEnum):
    """Allowed normalized evidence input classes."""

    SYNTHETIC_FIXTURE = "synthetic_fixture"
    APPROVED_SANITIZED_FIXTURE = "approved_sanitized_fixture"
    NORMALIZED_ZENDESK_EVIDENCE = "normalized_zendesk_evidence"
    OPERATOR_SANITIZED_SUMMARY = "operator_sanitized_summary"


class EvidenceVisibility(StrEnum):
    """Allowed data visibility classes for normalized evidence."""

    PUBLIC_CUSTOMER_SAFE = "public_customer_safe"
    CUSTOMER_CONTEXT_ONLY = "customer_context_only"
    INTERNAL_REVIEWER_ONLY = "internal_reviewer_only"
    UNSAFE_PRIVATE = "unsafe_private"


class SafetyBlocker(StrEnum):
    """Code-like safety blocker values safe for logs and reports."""

    UNKNOWN_INPUT_CLASS = "unknown_input_class"
    UNKNOWN_VISIBILITY_CLASS = "unknown_visibility_class"
    UNSAFE_VISIBILITY = "unsafe_visibility"
    INTERNAL_EVIDENCE_NOT_APPROVED = "internal_evidence_not_approved"
    SANITIZER_NOT_PASSED = "sanitizer_not_passed"
    UNSAFE_SOURCE_REF = "unsafe_source_ref"
    UNSAFE_TEXT = "unsafe_text"


@dataclass(frozen=True)
class SafetyGateResult:
    """Value-only safety gate result."""

    ok: bool
    blockers: tuple[str, ...]

    def to_json_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "blockers": list(self.blockers)}


FORBIDDEN_SOURCE_REF_FRAGMENTS = (
    ".private/",
    ".knowledge/",
    "raw_zendesk",
    "raw ticket",
    "raw_ticket",
    "internal_comment",
    "raw_internal",
    "raw_query_text",
    "snippet body",
    "snippet_body",
    "chunk body",
    "chunk_body",
    "vector values",
    "vector_values",
    "credential",
    "token",
    "private path",
    "hostname",
    "license id",
    "ticket id",
)

UNSAFE_SANITIZER_FLAGS = (
    "contains_private_data",
    "contains_customer_identifiers",
    "contains_raw_zendesk_json",
    "contains_raw_ticket_data",
    "contains_raw_internal_comments",
    "contains_credentials",
    "contains_secrets",
    "contains_live_infrastructure_identifiers",
    "contains_private_paths",
)

PASSING_SANITIZER_STATUSES = frozenset({"passed", "safe", "clean"})
UNSAFE_SANITIZER_STATUS_VALUES = frozenset({"failed", "blocked", "unsafe", "dirty"})

_EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b",
    re.I,
)
_DOMAIN_RE = re.compile(
    r"\b(?!example\.(?:com|net|org)\b)"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,63}\b",
    re.I,
)
_PRIVATE_PATH_RE = re.compile(
    r"(?:/Users/|/home/|/var/www/vhosts/|C:\\Users\\)", re.I
)
_LICENSE_RE = re.compile(r"\b(?:PLSK|EXT)\.\d{8}\.\d{4}\b", re.I)
_RAW_TICKET_ID_RE = re.compile(r"\b(?:ticket|zendesk|zd)[-_ #:]?\d{4,}\b", re.I)
_SECRET_RE = re.compile(
    r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=]\s*\S+"
    r"|authorization:\s*bearer\s+\S+",
    re.I,
)
_IP_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9_-])"
    r"(?:\d{1,3}(?:\.\d{1,3}){3}|[0-9A-Fa-f:]*:[0-9A-Fa-f:.]*)"
    r"(?![A-Za-z0-9_-])"
)
_SAFE_IP_NETWORKS = (
    ip_network("192.0.2.0/24"),
    ip_network("198.51.100.0/24"),
    ip_network("203.0.113.0/24"),
    ip_network("2001:db8::/32"),
)


def validate_evidence_safety(
    packet: NormalizedTicketEvidencePacket,
) -> SafetyGateResult:
    """Return fail-closed safety validation for normalized evidence."""

    blockers: list[SafetyBlocker] = []
    _add_input_class_blockers(packet, blockers)
    _add_sanitizer_blockers(packet.sanitizer_report, blockers)
    _add_visibility_blockers(packet.visibility_summary, blockers)
    _add_source_ref_blockers(packet.source_refs, blockers)
    _add_text_blockers(packet, blockers)
    return SafetyGateResult(
        ok=not blockers,
        blockers=tuple(blocker.value for blocker in _dedupe(blockers)),
    )


def ensure_evidence_safe(packet: NormalizedTicketEvidencePacket) -> None:
    """Raise when normalized evidence is unsafe for decision or drafting."""

    result = validate_evidence_safety(packet)
    if not result.ok:
        raise ContractValidationError(
            f"unsafe normalized evidence: {', '.join(result.blockers)}"
        )


def _add_input_class_blockers(
    packet: NormalizedTicketEvidencePacket, blockers: list[SafetyBlocker]
) -> None:
    try:
        InputClass(packet.input_class)
    except ValueError:
        blockers.append(SafetyBlocker.UNKNOWN_INPUT_CLASS)


def _add_sanitizer_blockers(
    report: Mapping[str, Any], blockers: list[SafetyBlocker]
) -> None:
    if _sanitizer_has_negative_indicator(report):
        blockers.append(SafetyBlocker.SANITIZER_NOT_PASSED)
        return
    if _sanitizer_has_pass_marker(report):
        return
    blockers.append(SafetyBlocker.SANITIZER_NOT_PASSED)


def _add_visibility_blockers(
    summary: Mapping[str, Any], blockers: list[SafetyBlocker]
) -> None:
    classes = _visibility_classes(summary)
    if not classes:
        blockers.append(SafetyBlocker.UNKNOWN_VISIBILITY_CLASS)
        return
    unknown = [name for name in classes if not _is_known_visibility(name)]
    if unknown:
        blockers.append(SafetyBlocker.UNKNOWN_VISIBILITY_CLASS)
    if EvidenceVisibility.UNSAFE_PRIVATE.value in classes:
        blockers.append(SafetyBlocker.UNSAFE_VISIBILITY)
    if _has_unapproved_internal_visibility(classes, summary):
        blockers.append(SafetyBlocker.INTERNAL_EVIDENCE_NOT_APPROVED)


def _add_source_ref_blockers(
    source_refs: Iterable[str], blockers: list[SafetyBlocker]
) -> None:
    if any(_contains_forbidden_source_ref(source_ref) for source_ref in source_refs):
        blockers.append(SafetyBlocker.UNSAFE_SOURCE_REF)


def _add_text_blockers(
    packet: NormalizedTicketEvidencePacket, blockers: list[SafetyBlocker]
) -> None:
    if any(_contains_unsafe_identifier(value) for value in _packet_text_values(packet)):
        blockers.append(SafetyBlocker.UNSAFE_TEXT)


def _visibility_classes(summary: Mapping[str, Any]) -> tuple[str, ...]:
    value = summary.get("classes", summary.get("visibility_classes"))
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple) and all(
        isinstance(item, str) for item in value
    ):
        return tuple(value)
    visibility = summary.get("visibility")
    if isinstance(visibility, str):
        return (visibility,)
    return ()


def _is_known_visibility(value: str) -> bool:
    try:
        EvidenceVisibility(value)
    except ValueError:
        return False
    return True


def _has_unapproved_internal_visibility(
    classes: tuple[str, ...], summary: Mapping[str, Any]
) -> bool:
    return (
        EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value in classes
        and summary.get("internal_only_evidence_approved") is not True
    )


def _contains_forbidden_source_ref(value: str) -> bool:
    normalized = value.casefold().replace("\\", "/")
    return any(
        fragment in normalized for fragment in FORBIDDEN_SOURCE_REF_FRAGMENTS
    ) or _contains_unsafe_identifier(value)


def _packet_text_values(packet: NormalizedTicketEvidencePacket) -> tuple[str, ...]:
    return (
        packet.supported_cause or "",
        packet.supported_resolution_or_workaround or "",
        *_strings_from(packet.issue_candidates),
        *_strings_from(packet.environment),
        *packet.symptoms,
        *packet.confirmed_facts,
        *packet.open_questions,
        *_strings_from(packet.visibility_summary),
        *_strings_from(packet.sanitizer_report),
    )


def _strings_from(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Mapping):
        return tuple(
            item for nested in value.values() for item in _strings_from(nested)
        )
    if isinstance(value, list | tuple):
        return tuple(item for nested in value for item in _strings_from(nested))
    return ()


def _contains_unsafe_identifier(value: str) -> bool:
    if not value:
        return False
    return (
        bool(_SECRET_RE.search(value))
        or bool(_EMAIL_RE.search(value))
        or bool(_DOMAIN_RE.search(value))
        or bool(_PRIVATE_PATH_RE.search(value))
        or bool(_LICENSE_RE.search(value))
        or bool(_RAW_TICKET_ID_RE.search(value))
        or _contains_unsafe_ip(value)
    )


def _contains_unsafe_ip(value: str) -> bool:
    return any(
        not any(address in network for network in _SAFE_IP_NETWORKS)
        for address in _ip_addresses(value)
    )


def _ip_addresses(value: str) -> tuple[object, ...]:
    addresses: list[object] = []
    for candidate in _IP_CANDIDATE_RE.findall(value):
        try:
            addresses.append(ip_address(candidate.strip("[](),.;")))
        except ValueError:
            continue
    return tuple(addresses)


def _has_positive_finding_count(report: Mapping[str, Any]) -> bool:
    for count_key in ("finding_count", "residual_finding_count", "pii_finding_count"):
        count = report.get(count_key)
        if isinstance(count, int) and not isinstance(count, bool) and count > 0:
            return True
    return False


def _sanitizer_has_negative_indicator(report: Mapping[str, Any]) -> bool:
    status = report.get("status")
    return (
        any(report.get(flag) is True for flag in UNSAFE_SANITIZER_FLAGS)
        or report.get("ok") is False
        or report.get("blocked") is True
        or _has_positive_finding_count(report)
        or (
            isinstance(status, str)
            and status.casefold() in UNSAFE_SANITIZER_STATUS_VALUES
        )
    )


def _sanitizer_has_pass_marker(report: Mapping[str, Any]) -> bool:
    status = report.get("status")
    return (
        isinstance(status, str) and status.casefold() in PASSING_SANITIZER_STATUSES
    ) or report.get("safe_for_kcs_core") is True


def _dedupe(blockers: Iterable[SafetyBlocker]) -> tuple[SafetyBlocker, ...]:
    result: list[SafetyBlocker] = []
    for blocker in blockers:
        if blocker not in result:
            result.append(blocker)
    return tuple(result)
