"""Evidence readiness validation for normalized KCS input packets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeVar

from kcs_core.errors import ContractValidationError
from kcs_core.models import NormalizedTicketEvidencePacket
from kcs_core.safety import validate_evidence_safety

T = TypeVar("T")


class EvidenceBlocker(StrEnum):
    """Value-free blocker codes for sanitized evidence readiness."""

    UNSAFE_INPUT = "unsafe_input"
    MISSING_SOURCE_REF = "missing_source_ref"
    MISSING_ISSUE_CANDIDATE = "missing_issue_candidate"
    MULTI_ISSUE = "multi_issue"
    MISSING_SYMPTOMS = "missing_symptoms"
    MISSING_CONFIRMED_FACTS = "missing_confirmed_facts"
    MISSING_SUPPORTED_RESOLUTION = "missing_supported_resolution"
    OPEN_QUESTIONS_PRESENT = "open_questions_present"
    EVIDENCE_NOT_ATOMIC = "evidence_not_atomic"


class EvidenceWarning(StrEnum):
    """Value-free warning codes for sanitized evidence readiness."""

    MISSING_SUPPORTED_CAUSE = "missing_supported_cause"


@dataclass(frozen=True)
class EvidenceValidationResult:
    """Value-free evidence readiness result."""

    ok: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def to_json_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def validate_evidence_packet(
    packet: NormalizedTicketEvidencePacket,
) -> EvidenceValidationResult:
    """Return fail-closed readiness validation for sanitized evidence."""

    blockers: list[EvidenceBlocker] = []
    warnings: list[EvidenceWarning] = []
    safety_result = validate_evidence_safety(packet)
    if not safety_result.ok:
        blockers.append(EvidenceBlocker.UNSAFE_INPUT)
    _add_required_evidence_blockers(packet, blockers)
    _add_issue_candidate_blockers(packet.issue_candidates, blockers)
    _add_open_question_blockers(packet, blockers)
    _add_evidence_warnings(packet, warnings)
    return EvidenceValidationResult(
        ok=not blockers,
        blockers=tuple(blocker.value for blocker in _dedupe(blockers)),
        warnings=tuple(warning.value for warning in _dedupe(warnings)),
    )


def ensure_evidence_ready(packet: NormalizedTicketEvidencePacket) -> None:
    """Raise when sanitized evidence is not ready for later KCS slices."""

    result = validate_evidence_packet(packet)
    if not result.ok:
        raise ContractValidationError(
            f"evidence is not ready: {', '.join(result.blockers)}"
        )


def _add_required_evidence_blockers(
    packet: NormalizedTicketEvidencePacket, blockers: list[EvidenceBlocker]
) -> None:
    if not _has_text(packet.source_refs):
        blockers.append(EvidenceBlocker.MISSING_SOURCE_REF)
    if not _has_text(packet.symptoms):
        blockers.append(EvidenceBlocker.MISSING_SYMPTOMS)
    if not _has_text(packet.confirmed_facts):
        blockers.append(EvidenceBlocker.MISSING_CONFIRMED_FACTS)
    if not _has_text(packet.supported_resolution_or_workaround):
        blockers.append(EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION)


def _add_issue_candidate_blockers(
    issue_candidates: list[Mapping[str, Any]], blockers: list[EvidenceBlocker]
) -> None:
    if not issue_candidates:
        blockers.append(EvidenceBlocker.MISSING_ISSUE_CANDIDATE)
        return
    if len(issue_candidates) > 1:
        blockers.append(EvidenceBlocker.MULTI_ISSUE)
        return
    candidate = issue_candidates[0]
    if candidate.get("split_required") is True or candidate.get("atomic") is False:
        blockers.append(EvidenceBlocker.EVIDENCE_NOT_ATOMIC)


def _add_open_question_blockers(
    packet: NormalizedTicketEvidencePacket, blockers: list[EvidenceBlocker]
) -> None:
    if _has_text(packet.open_questions):
        blockers.append(EvidenceBlocker.OPEN_QUESTIONS_PRESENT)


def _add_evidence_warnings(
    packet: NormalizedTicketEvidencePacket, warnings: list[EvidenceWarning]
) -> None:
    if not _has_text(packet.supported_cause):
        warnings.append(EvidenceWarning.MISSING_SUPPORTED_CAUSE)


def _has_text(value: str | Iterable[str] | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return any(item.strip() for item in value if isinstance(item, str))


def _dedupe(items: Iterable[T]) -> tuple[T, ...]:
    result: list[T] = []
    for item in items:
        if item not in result:
            result.append(item)
    return tuple(result)
