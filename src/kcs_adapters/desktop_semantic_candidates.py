"""Desktop candidate conversion from validated semantic extraction output."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from kcs_adapters.desktop_payload import (
    approved_summary_snippet,
    resolution_step_has_executable_detail,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType, CandidateOrigin
from kcs_core.safety import EvidenceVisibility
from kcs_core.sanitizer import (
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
)
from kcs_core.semantic_extraction import (
    CandidateSemanticExtraction,
    KcsItemStatus,
    SemanticCoverageReason,
    SemanticIssueProposal,
    SemanticIssueProposalPacket,
    validate_candidate_semantic_extraction,
)

_QUESTION_MARK_RE = re.compile(r"\?+\s*$")
_PUBLIC_URL_RE = re.compile(r"https?://\S+", re.I)
_HOW_FIRST_PERSON_RE = re.compile(
    r"^how\s+(?:can|do|does|should)\s+"
    r"(?:i|we|a\s+customer|the\s+customer|users?)\s+(?P<body>.+)$",
    re.I,
)
_CAUSE_ACTION_LANGUAGE_RE = re.compile(
    r"\b(?:apply|change|check|connect|disable|enable|execute|fix|follow|"
    r"log\s+in|open|repair|replace|restart|run|set|switch|try|use|verify)\b",
    re.I,
)
_CAUSE_EXPLANATORY_LANGUAGE_RE = re.compile(
    r"\b(?:because|caus(?:e|ed|es)|corrupt(?:ed|ion)|disabled|does\s+not|"
    r"empty|fail(?:ed|s|ure)?|incorrect|incompatible|invalid|missing|"
    r"mismatch|not\s+configured|wrong)\b",
    re.I,
)
_QUESTION_CONTEXT_CONNECTOR_RE = re.compile(
    r"\s*,?\s+(?:such as|for example|including|with error(?:s)?(?: like)?|"
    r"when)\s+.+$",
    re.I,
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_CUSTOMER_ROLES = frozenset({"customer_question", "reported_symptom"})
_SUPPORT_ROLES = frozenset({"supported_cause", "supported_resolution"})
_ISSUE_ROLES = _CUSTOMER_ROLES | _SUPPORT_ROLES
_ISSUE_EVIDENCE_ROLES = _ISSUE_ROLES | frozenset({"unclassified_evidence"})
_PER_ISSUE_DRAFTABILITY_BLOCKERS = frozenset({"evidence_shape_invalid"})
_PROJECTED_ISSUE_TITLE_MAX_LENGTH = 180
_COVERAGE_ROLE_BY_REASON = {
    SemanticCoverageReason.INTERNAL_WORKFLOW_NOTE.value: "internal_workflow_note",
    SemanticCoverageReason.TICKET_METADATA.value: "ticket_metadata",
    SemanticCoverageReason.FORMATTING_ARTIFACT.value: "formatting_artifact",
}
_TRUSTED_EXCERPT_ROLES = _ISSUE_ROLES | frozenset(
    {
        "confirmed_fact",
        "duplicate_excerpt",
        "formatting_artifact",
        "internal_workflow_note",
        "ticket_metadata",
        "unclassified_evidence",
    }
)


@dataclass(frozen=True)
class ProjectedIssue:
    """One operator-visible issue card derived without KCS action authority."""

    issue_ref: str
    summary: str
    preliminary_article_type: str
    candidate_origin: str
    visibility_class: str
    source_refs: tuple[str, ...]
    semantic_sha256: str

    def to_json_dict(self) -> JsonDict:
        return {
            "candidate_origin": self.candidate_origin,
            "issue_ref": self.issue_ref,
            "preliminary_article_type": self.preliminary_article_type,
            "semantic_sha256": self.semantic_sha256,
            "source_refs": list(self.source_refs),
            "summary": self.summary,
            "visibility_class": self.visibility_class,
        }


@dataclass(frozen=True)
class SemanticProjectionLedgerEntry:
    """Value-safe projection disposition for one issue, record, or source."""

    record_ref: str
    outcome: str
    reason_code: str
    source_refs: tuple[str, ...]

    @property
    def source_ref(self) -> str:
        return self.source_refs[0]

    def to_json_dict(self) -> JsonDict:
        return {
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "record_ref": self.record_ref,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class ProjectedIssueSet:
    """Shadow-only issue projection and its complete bounded ledgers."""

    issues: tuple[ProjectedIssue, ...]
    coverage_ledger: tuple[SemanticProjectionLedgerEntry, ...]
    unassigned_evidence: tuple[SemanticProjectionLedgerEntry, ...]
    blocked_proposals: tuple[SemanticProjectionLedgerEntry, ...]
    selectable_issue_refs: tuple[str, ...]

    def to_json_dict(self) -> JsonDict:
        return {
            "blocked_proposals": [
                entry.to_json_dict() for entry in self.blocked_proposals
            ],
            "coverage_ledger": [entry.to_json_dict() for entry in self.coverage_ledger],
            "issues": [issue.to_json_dict() for issue in self.issues],
            "selectable_issue_refs": list(self.selectable_issue_refs),
            "unassigned_evidence": [
                entry.to_json_dict() for entry in self.unassigned_evidence
            ],
        }


@dataclass(frozen=True)
class SemanticProjectionComparison:
    """Value-safe old/new shadow comparison without model-visible text."""

    codes: tuple[str, ...]
    legacy_sha256: str
    projected_sha256: str
    legacy_issue_count: int
    projected_issue_count: int
    legacy_selectable_count: int
    projected_selectable_count: int

    def to_json_dict(self) -> JsonDict:
        return {
            "codes": list(self.codes),
            "legacy_issue_count": self.legacy_issue_count,
            "legacy_selectable_count": self.legacy_selectable_count,
            "legacy_sha256": self.legacy_sha256,
            "projected_issue_count": self.projected_issue_count,
            "projected_selectable_count": self.projected_selectable_count,
            "projected_sha256": self.projected_sha256,
        }


@dataclass(frozen=True)
class _ExcerptRoleEvidence:
    roles: frozenset[str]
    visibility: str
    content_sha256: str | None
    provenance_trusted: bool


def project_semantic_issue_proposals(
    proposal_packet: SemanticIssueProposalPacket | Mapping[str, Any] | object,
    excerpt_role_index: Mapping[str, Mapping[str, Any]],
) -> ProjectedIssueSet:
    """Project validated observations into Python-owned operator issue cards."""

    packet = _validated_issue_proposal_packet(proposal_packet)
    role_index = _validated_excerpt_role_index(packet, excerpt_role_index)
    projected_issues: list[ProjectedIssue] = []
    blocked_proposals: list[SemanticProjectionLedgerEntry] = []
    issue_source_refs: set[str] = set()
    for issue in packet.issues:
        issue_source_refs.update(issue.source_refs())
        projected, blocked = _project_issue(issue, role_index)
        if projected is not None:
            projected_issues.append(projected)
        if blocked is not None:
            blocked_proposals.append(blocked)

    coverage_ledger, accepted_coverage_refs = _project_coverage_records(
        packet,
        role_index,
        issue_source_refs=issue_source_refs,
    )
    assigned_refs = issue_source_refs | accepted_coverage_refs
    result = ProjectedIssueSet(
        issues=tuple(projected_issues),
        coverage_ledger=tuple(coverage_ledger),
        unassigned_evidence=_unassigned_evidence(packet.source_refs, assigned_refs),
        blocked_proposals=tuple(blocked_proposals),
        selectable_issue_refs=tuple(issue.issue_ref for issue in projected_issues),
    )
    ensure_safe_sanitized_payload(result.to_json_dict())
    return result


def semantic_projection_requires_terminal_review(
    projected: ProjectedIssueSet,
) -> bool:
    """Return whether blocked proposals invalidate the whole semantic packet."""

    return bool(projected.blocked_proposals) and (
        not projected.issues
        or any(
            entry.reason_code not in _PER_ISSUE_DRAFTABILITY_BLOCKERS
            for entry in projected.blocked_proposals
        )
    )


def semantic_projection_shadow_comparison(
    *,
    legacy_extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    projected: ProjectedIssueSet,
) -> SemanticProjectionComparison:
    """Compare normalized legacy/new semantics using counts, codes, and hashes."""

    normalized = _validated_semantic_extraction(legacy_extraction)
    legacy_candidates, _legacy_outcomes = (
        desktop_candidate_set_from_semantic_extraction(normalized)
    )
    legacy_issue_items = tuple(
        item
        for item in normalized.items
        if item.kcs_item_status != KcsItemStatus.NO_ARTICLE.value
    )
    legacy_issue_count = len(legacy_issue_items)
    projected_issue_count = len(projected.issues) + len(projected.blocked_proposals)
    legacy_selectable_count = len(legacy_candidates)
    projected_selectable_count = len(projected.selectable_issue_refs)
    codes = _semantic_projection_comparison_codes(
        normalized,
        legacy_candidates=legacy_candidates,
        legacy_issue_items=legacy_issue_items,
        projected=projected,
    )
    result = SemanticProjectionComparison(
        codes=codes,
        legacy_sha256=_payload_sha256(normalized.to_json_dict()),
        projected_sha256=_payload_sha256(projected.to_json_dict()),
        legacy_issue_count=legacy_issue_count,
        projected_issue_count=projected_issue_count,
        legacy_selectable_count=legacy_selectable_count,
        projected_selectable_count=projected_selectable_count,
    )
    ensure_safe_sanitized_payload(result.to_json_dict())
    return result


def _semantic_projection_comparison_codes(
    normalized: CandidateSemanticExtraction,
    *,
    legacy_candidates: Sequence[Mapping[str, Any]],
    legacy_issue_items: Sequence[Any],
    projected: ProjectedIssueSet,
) -> tuple[str, ...]:
    return (
        _comparison_code(
            "shadow_issue_count",
            len(legacy_issue_items),
            len(projected.issues) + len(projected.blocked_proposals),
        ),
        _comparison_code(
            "shadow_selectable_count",
            len(legacy_candidates),
            len(projected.selectable_issue_refs),
        ),
        _comparison_code(
            "shadow_issue_source_mapping",
            _legacy_issue_source_mapping(legacy_issue_items),
            _projected_issue_source_mapping(projected),
        ),
        _comparison_code(
            "shadow_nonissue_source_mapping",
            _legacy_nonissue_source_mapping(normalized),
            _projected_nonissue_source_mapping(projected),
        ),
        _comparison_code(
            "shadow_blocked_source_mapping",
            _legacy_blocked_source_mapping(normalized),
            _projected_blocked_source_mapping(projected),
        ),
        _comparison_code(
            "shadow_origin_distribution",
            sorted(
                str(candidate.get("candidate_origin"))
                for candidate in legacy_candidates
            ),
            sorted(issue.candidate_origin for issue in projected.issues),
        ),
        _comparison_code(
            "shadow_article_type_distribution",
            sorted(
                str(candidate.get("article_type")) for candidate in legacy_candidates
            ),
            sorted(issue.preliminary_article_type for issue in projected.issues),
        ),
        _comparison_code(
            "shadow_visibility_distribution",
            sorted(
                item.visibility_hint
                for item in normalized.items
                if _is_draftable_semantic_item(item)
            ),
            sorted(issue.visibility_class for issue in projected.issues),
        ),
        _comparison_code(
            "shadow_semantic_content",
            sorted(_legacy_semantic_sha256(item) for item in legacy_issue_items),
            sorted(issue.semantic_sha256 for issue in projected.issues),
        ),
        _source_coverage_code(projected),
        _blocked_proposal_code(projected),
    )


def _source_coverage_code(projected: ProjectedIssueSet) -> str:
    if projected.unassigned_evidence:
        return "shadow_source_coverage_incomplete"
    return "shadow_source_coverage_complete"


def _blocked_proposal_code(projected: ProjectedIssueSet) -> str:
    if projected.blocked_proposals:
        return "shadow_blocked_proposals_present"
    return "shadow_blocked_proposals_absent"


def _validated_issue_proposal_packet(
    packet: SemanticIssueProposalPacket | Mapping[str, Any] | object,
) -> SemanticIssueProposalPacket:
    if isinstance(packet, SemanticIssueProposalPacket):
        return packet
    return SemanticIssueProposalPacket.from_json_dict(packet)


def _validated_excerpt_role_index(
    packet: SemanticIssueProposalPacket,
    role_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, _ExcerptRoleEvidence]:
    return _validated_role_index(packet.source_refs, role_index)


def _validated_role_index(
    source_refs: tuple[str, ...],
    role_index: Mapping[str, Mapping[str, Any]],
) -> dict[str, _ExcerptRoleEvidence]:
    if not isinstance(role_index, Mapping) or set(role_index) != set(source_refs):
        raise ContractValidationError("semantic excerpt role index invalid")
    normalized: dict[str, _ExcerptRoleEvidence] = {}
    for source_ref in source_refs:
        ensure_safe_ref(source_ref, label="source_ref")
        normalized[source_ref] = _validated_role_index_entry(role_index.get(source_ref))
    return normalized


def _validated_role_index_entry(value: object) -> _ExcerptRoleEvidence:
    if not isinstance(value, Mapping) or set(value) - {
        "content_sha256",
        "provenance_trusted",
        "roles",
        "visibility",
    }:
        raise ContractValidationError("semantic excerpt role index invalid")
    return _ExcerptRoleEvidence(
        roles=_validated_excerpt_roles(value.get("roles")),
        visibility=_validated_excerpt_visibility(value.get("visibility")),
        content_sha256=_validated_content_sha256(value.get("content_sha256")),
        provenance_trusted=_validated_provenance_trusted(
            value.get("provenance_trusted")
        ),
    )


def _validated_provenance_trusted(value: object) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError("semantic excerpt role index invalid")
    return value


def _validated_excerpt_roles(value: object) -> frozenset[str]:
    if (
        not isinstance(value, list | tuple)
        or not value
        or any(role not in _TRUSTED_EXCERPT_ROLES for role in value)
        or len(value) != len(set(value))
    ):
        raise ContractValidationError("semantic excerpt role index invalid")
    return frozenset(value)


def _validated_excerpt_visibility(value: object) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("semantic excerpt role index invalid")
    try:
        EvidenceVisibility(value)
    except ValueError as exc:
        raise ContractValidationError("semantic excerpt role index invalid") from exc
    return value


def _validated_content_sha256(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ContractValidationError("semantic excerpt role index invalid")
    return value


def _unassigned_evidence(
    source_refs: tuple[str, ...],
    assigned_refs: set[str],
) -> tuple[SemanticProjectionLedgerEntry, ...]:
    return tuple(
        SemanticProjectionLedgerEntry(
            f"unassigned-{ref}", "unassigned_evidence", "unassigned_evidence", (ref,)
        )
        for ref in source_refs
        if ref not in assigned_refs
    )


def _project_issue(
    issue: SemanticIssueProposal,
    role_index: Mapping[str, _ExcerptRoleEvidence],
) -> tuple[ProjectedIssue | None, SemanticProjectionLedgerEntry | None]:
    source_refs = issue.source_refs()
    reason_code = _issue_blocker_reason(issue, source_refs, role_index)
    if reason_code is not None:
        return None, SemanticProjectionLedgerEntry(
            record_ref=issue.issue_ref,
            outcome="proposal_blocked",
            reason_code=reason_code,
            source_refs=source_refs,
        )
    roles = frozenset(
        role for source_ref in source_refs for role in role_index[source_ref].roles
    )
    provenance_trusted = all(
        role_index[source_ref].provenance_trusted for source_ref in source_refs
    )
    origin = CandidateOrigin.SUPPORT_DISCOVERED.value
    if provenance_trusted and roles & _CUSTOMER_ROLES:
        origin = CandidateOrigin.CUSTOMER_REPORTED.value
    visibility = {role_index[source_ref].visibility for source_ref in source_refs}
    article_type = _preliminary_article_type(issue)
    projected = ProjectedIssue(
        issue_ref=issue.issue_ref,
        summary=issue.summary.text,
        preliminary_article_type=article_type,
        candidate_origin=origin,
        visibility_class=next(iter(visibility)),
        source_refs=source_refs,
        semantic_sha256=_projected_semantic_sha256(issue),
    )
    ensure_safe_sanitized_payload(projected.to_json_dict())
    return projected, None


def _issue_blocker_reason(
    issue: SemanticIssueProposal,
    source_refs: tuple[str, ...],
    role_index: Mapping[str, _ExcerptRoleEvidence],
) -> str | None:
    roles = frozenset(
        role for source_ref in source_refs for role in role_index[source_ref].roles
    )
    if not roles & _ISSUE_EVIDENCE_ROLES:
        return "source_role_missing"
    visibility = {role_index[source_ref].visibility for source_ref in source_refs}
    if not all(role_index[source_ref].provenance_trusted for source_ref in source_refs):
        if visibility != {EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value}:
            return "untrusted_provenance_visibility"
    if len(visibility) != 1 or EvidenceVisibility.UNSAFE_PRIVATE.value in visibility:
        return "visibility_ambiguous"
    article_type = _preliminary_article_type(issue, fail_closed=False)
    if article_type is None or _technical_identity_incomplete(issue, article_type):
        return "evidence_shape_invalid"
    return None


def _technical_identity_incomplete(
    issue: SemanticIssueProposal,
    article_type: str,
) -> bool:
    return article_type == ArticleType.TECHNICAL_SCR.value and (
        not (issue.symptoms or issue.error_evidence)
        or not issue.cause_evidence
        or not issue.resolution_evidence
    )


def _preliminary_article_type(
    issue: SemanticIssueProposal,
    *,
    fail_closed: bool = True,
) -> str | None:
    has_question_shape = issue.question is not None or bool(issue.answer_evidence)
    has_error_evidence = bool(issue.error_evidence)
    has_problem_shape = bool(
        issue.symptoms or issue.cause_evidence or has_error_evidence
    )
    if has_question_shape:
        if has_error_evidence:
            return ArticleType.TECHNICAL_SCR.value
        return ArticleType.HOWTO_QA.value
    if has_problem_shape:
        return ArticleType.TECHNICAL_SCR.value
    if fail_closed:
        raise ContractValidationError("semantic issue evidence shape invalid")
    return None


def _project_coverage_records(
    packet: SemanticIssueProposalPacket,
    role_index: Mapping[str, _ExcerptRoleEvidence],
    *,
    issue_source_refs: set[str],
) -> tuple[list[SemanticProjectionLedgerEntry], set[str]]:
    ledger: list[SemanticProjectionLedgerEntry] = []
    accepted_refs: set[str] = set()
    for record in packet.coverage_records:
        accepted, reason_code = _coverage_disposition(
            record.reason_code,
            record.source_refs,
            record.duplicate_of_source_ref,
            role_index,
            already_covered=issue_source_refs | accepted_refs,
        )
        if accepted:
            accepted_refs.update(record.source_refs)
        ledger.append(
            SemanticProjectionLedgerEntry(
                record_ref=record.coverage_ref,
                outcome="coverage_accepted" if accepted else "coverage_rejected",
                reason_code=reason_code,
                source_refs=record.source_refs,
            )
        )
    return ledger, accepted_refs


def _coverage_disposition(
    reason_code: str,
    source_refs: tuple[str, ...],
    duplicate_of_source_ref: str | None,
    role_index: Mapping[str, _ExcerptRoleEvidence],
    *,
    already_covered: set[str],
) -> tuple[bool, str]:
    roles = frozenset(
        role for source_ref in source_refs for role in role_index[source_ref].roles
    )
    if roles & _ISSUE_ROLES:
        return False, "customer_support_coverage_requires_review"
    if len(roles) != 1:
        return False, "coverage_role_incompatible"
    if reason_code == SemanticCoverageReason.DUPLICATE_EXCERPT.value:
        return _duplicate_coverage_disposition(
            source_refs,
            duplicate_of_source_ref,
            role_index,
            already_covered=already_covered,
        )
    expected_role = _COVERAGE_ROLE_BY_REASON.get(reason_code)
    if expected_role is None or any(
        role_index[source_ref].roles != frozenset({expected_role})
        for source_ref in source_refs
    ):
        return False, "coverage_role_incompatible"
    return True, reason_code


def _duplicate_coverage_disposition(
    source_refs: tuple[str, ...],
    duplicate_of_source_ref: str | None,
    role_index: Mapping[str, _ExcerptRoleEvidence],
    *,
    already_covered: set[str],
) -> tuple[bool, str]:
    if duplicate_of_source_ref not in already_covered:
        return False, "duplicate_proof_invalid"
    target_hash = role_index[duplicate_of_source_ref].content_sha256
    if target_hash is None or any(
        role_index[source_ref].content_sha256 != target_hash
        for source_ref in source_refs
    ):
        return False, "duplicate_proof_invalid"
    return True, SemanticCoverageReason.DUPLICATE_EXCERPT.value


def _comparison_code(prefix: str, legacy: object, projected: object) -> str:
    return f"{prefix}_{'match' if legacy == projected else 'mismatch'}"


def _legacy_issue_source_mapping(items: Sequence[Any]) -> list[tuple[str, ...]]:
    return sorted(tuple(sorted(item.source_refs)) for item in items)


def _projected_issue_source_mapping(
    projected: ProjectedIssueSet,
) -> list[tuple[str, ...]]:
    refs = [issue.source_refs for issue in projected.issues]
    refs.extend(entry.source_refs for entry in projected.blocked_proposals)
    return sorted(tuple(sorted(source_refs)) for source_refs in refs)


def _legacy_nonissue_source_mapping(
    extraction: CandidateSemanticExtraction,
) -> list[str]:
    return sorted(
        source_ref
        for item in extraction.items
        if item.kcs_item_status == KcsItemStatus.NO_ARTICLE.value
        for source_ref in item.source_refs
    )


def _projected_nonissue_source_mapping(projected: ProjectedIssueSet) -> list[str]:
    return sorted(
        source_ref
        for entry in projected.coverage_ledger
        if entry.outcome == "coverage_accepted"
        for source_ref in entry.source_refs
    )


def _legacy_blocked_source_mapping(
    extraction: CandidateSemanticExtraction,
) -> list[tuple[str, ...]]:
    return sorted(
        tuple(sorted(item.source_refs))
        for item in extraction.items
        if item.kcs_item_status == KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value
    )


def _projected_blocked_source_mapping(
    projected: ProjectedIssueSet,
) -> list[tuple[str, ...]]:
    return sorted(
        tuple(sorted(entry.source_refs)) for entry in projected.blocked_proposals
    )


def _legacy_semantic_sha256(item: Any) -> str:
    return _payload_sha256(
        {
            "answer": [item.supported_answer] if item.supported_answer else [],
            "cause": [item.supported_cause] if item.supported_cause else [],
            "question": item.question,
            "resolution": list(item.resolution_steps),
            "summary": item.summary,
            "symptoms": list(item.symptoms),
        }
    )


def _projected_semantic_sha256(issue: SemanticIssueProposal) -> str:
    symptom_texts = tuple(
        dict.fromkeys(
            [item.text for item in issue.symptoms]
            + [item.text for item in issue.error_evidence]
        )
    )
    return _payload_sha256(
        {
            "answer": [item.text for item in issue.answer_evidence],
            "cause": [item.text for item in issue.cause_evidence],
            "question": issue.question.text if issue.question else None,
            "resolution": [item.text for item in issue.resolution_evidence],
            "summary": issue.summary.text,
            "symptoms": list(symptom_texts),
        }
    )


def _payload_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def desktop_item_candidates_from_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> list[JsonDict]:
    """Convert validated core semantic candidates to Desktop draft candidates."""

    candidates, _outcomes = desktop_candidate_set_from_semantic_extraction(
        extraction,
        fallback_environment=fallback_environment,
    )
    return candidates


def desktop_candidate_set_from_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> tuple[list[JsonDict], list[JsonDict]]:
    """Return draftable candidates and a ledger for every semantic item."""

    normalized = _validated_semantic_extraction(extraction)
    outcomes = [_semantic_item_outcome_card(item) for item in normalized.items]
    candidates = [
        _desktop_candidate_from_semantic_item(
            item,
            fallback_environment=fallback_environment,
        )
        for item in normalized.items
        if _is_draftable_semantic_item(item)
    ]
    return candidates, outcomes


def desktop_candidate_set_from_semantic_issue_proposal(
    proposal_packet: SemanticIssueProposalPacket,
    projected: ProjectedIssueSet,
    *,
    fallback_environment: Mapping[str, Any] | None = None,
) -> tuple[list[JsonDict], list[JsonDict]]:
    """Return normal authoring candidates from one deterministic projection."""

    issue_by_ref = {issue.issue_ref: issue for issue in proposal_packet.issues}
    candidates = [
        _desktop_candidate_from_projected_issue(
            issue_by_ref[projected_issue.issue_ref],
            projected_issue,
            fallback_environment=fallback_environment,
        )
        for projected_issue in projected.issues
    ]
    outcomes = [
        _projected_issue_outcome_card(projected_issue)
        for projected_issue in projected.issues
    ]
    outcomes.extend(
        _projection_ledger_outcome_card(entry)
        for entries in (
            projected.blocked_proposals,
            projected.coverage_ledger,
            projected.unassigned_evidence,
        )
        for entry in entries
    )
    return candidates, outcomes


def _desktop_candidate_from_projected_issue(
    issue: SemanticIssueProposal,
    projected_issue: ProjectedIssue,
    *,
    fallback_environment: Mapping[str, Any] | None,
) -> JsonDict:
    article_type = projected_issue.preliminary_article_type
    resolution_evidence = _unique_observation_texts(
        (*issue.resolution_evidence, *issue.verification_evidence)
    )
    answer_evidence = _observation_texts(issue.answer_evidence)
    symptoms = _unique_observation_texts((*issue.symptoms, *issue.error_evidence))
    confirmed_facts = _unique_observation_texts(
        (*issue.context_evidence, *issue.cause_evidence, *issue.answer_evidence)
    )
    if not confirmed_facts:
        confirmed_facts = symptoms or (
            [issue.question.text] if issue.question is not None else []
        )
    title = _projected_issue_title(issue.summary.text)
    candidate: JsonDict = {
        "article_type": article_type,
        "candidate_origin": projected_issue.candidate_origin,
        "confirmed_facts": confirmed_facts,
        "environment": _merged_environment(
            {},
            fallback_environment=fallback_environment,
        ),
        "item_ref": projected_issue.issue_ref,
        "reason": "Python-projected semantic issue boundary.",
        "summary": issue.summary.text,
        "title": title,
    }
    if symptoms:
        candidate["symptoms"] = symptoms
    cause = _joined_observation_text(issue.cause_evidence)
    if cause is not None:
        candidate["supported_cause"] = cause
    if resolution_evidence:
        candidate["resolution_steps"] = _projected_resolution_steps(
            resolution_evidence
        )
        candidate["supported_resolution_or_workaround"] = "\n\n".join(
            resolution_evidence
        )
    if issue.question is not None:
        candidate["question"] = issue.question.text
    supported_answer = answer_evidence or (
        resolution_evidence if article_type == ArticleType.HOWTO_QA.value else []
    )
    if supported_answer:
        candidate["supported_answer"] = " ".join(supported_answer)
        candidate.setdefault("resolution_steps", supported_answer)
    ensure_safe_sanitized_payload(candidate)
    return candidate


def _observation_texts(observations: Sequence[Any]) -> list[str]:
    return [str(observation.text) for observation in observations]


def _unique_observation_texts(observations: Sequence[Any]) -> list[str]:
    return list(dict.fromkeys(_observation_texts(observations)))


def _projected_resolution_steps(resolution_evidence: list[str]) -> list[str]:
    detailed_steps = [
        text
        for text in resolution_evidence
        if resolution_step_has_executable_detail(_PUBLIC_URL_RE.sub(" URL", text))
    ]
    return detailed_steps or resolution_evidence


def _joined_observation_text(observations: Sequence[Any]) -> str | None:
    texts = _observation_texts(observations)
    return " ".join(texts) if texts else None


def _projected_issue_outcome_card(issue: ProjectedIssue) -> JsonDict:
    card: JsonDict = {
        "article_type": issue.preliminary_article_type,
        "candidate_origin": issue.candidate_origin,
        "item_ref": issue.issue_ref,
        "kcs_item_status": "candidate_allowed",
        "outcome": "draft_candidate",
        "title": _projected_issue_title(issue.summary),
    }
    ensure_safe_sanitized_payload(card)
    return card


def _projected_issue_title(summary: str) -> str:
    return approved_summary_snippet(
        summary,
        max_length=_PROJECTED_ISSUE_TITLE_MAX_LENGTH,
    )


def _projection_ledger_outcome_card(
    entry: SemanticProjectionLedgerEntry,
) -> JsonDict:
    blocked_need_more_evidence = (
        entry.outcome == "proposal_blocked"
        and entry.reason_code in _PER_ISSUE_DRAFTABILITY_BLOCKERS
    )
    card: JsonDict = {
        "article_type": ArticleType.NONE.value,
        "candidate_origin": CandidateOrigin.SUPPORT_DISCOVERED.value,
        "item_ref": entry.record_ref,
        "kcs_item_status": (
            KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value
            if blocked_need_more_evidence
            else KcsItemStatus.NO_ARTICLE.value
        ),
        "outcome": (
            "blocked_need_more_evidence"
            if blocked_need_more_evidence
            else entry.outcome
        ),
        "title": "Semantic evidence disposition",
    }
    ensure_safe_sanitized_payload(card)
    return card


def _validated_semantic_extraction(
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object,
) -> CandidateSemanticExtraction:
    validation = validate_candidate_semantic_extraction(extraction)
    if not validation.ok:
        raise ContractValidationError("semantic extraction output invalid")
    return (
        extraction
        if isinstance(extraction, CandidateSemanticExtraction)
        else CandidateSemanticExtraction.from_json_dict(extraction)
    )


def _desktop_candidate_from_semantic_item(
    item: Any,
    *,
    fallback_environment: Mapping[str, Any] | None,
) -> JsonDict:
    article_type = _effective_article_type(item)
    if article_type not in {
        ArticleType.TECHNICAL_SCR.value,
        ArticleType.HOWTO_QA.value,
    }:
        raise ContractValidationError("semantic article type invalid")
    environment = _merged_environment(
        item.environment,
        fallback_environment=fallback_environment,
    )
    title = _candidate_title(item, article_type=article_type)
    candidate: JsonDict = {
        "article_type": article_type,
        "candidate_origin": item.candidate_origin,
        "confirmed_facts": _confirmed_facts(item, article_type=article_type),
        "environment": environment,
        "item_ref": item.candidate_id,
        "summary": title,
        "title": title,
    }
    _attach_semantic_lists(
        candidate,
        item,
        article_type=article_type,
        environment=environment,
    )
    _attach_semantic_optional_fields(candidate, item)
    ensure_safe_sanitized_payload(candidate)
    return candidate


def _is_draftable_semantic_item(item: Any) -> bool:
    return item.kcs_item_status in {
        KcsItemStatus.CANDIDATE_ALLOWED.value,
        KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,
    }


def _semantic_item_outcome_card(item: Any) -> JsonDict:
    card: JsonDict = {
        "article_type": _safe_article_type_for_outcome(item),
        "candidate_origin": item.candidate_origin,
        "item_ref": item.candidate_id,
        "kcs_item_status": item.kcs_item_status,
        "outcome": _semantic_item_outcome(item),
        "title": _candidate_title(
            item,
            article_type=_safe_article_type_for_outcome(item),
        ),
    }
    if item.open_questions:
        card["open_questions"] = list(item.open_questions)
    ensure_safe_sanitized_payload(card)
    return card


def _safe_article_type_for_outcome(item: Any) -> str:
    try:
        return _effective_article_type(item)
    except Exception:
        return str(item.article_type_hint)


def _semantic_item_outcome(item: Any) -> str:
    if item.kcs_item_status == KcsItemStatus.CANDIDATE_ALLOWED.value:
        return "draft_candidate"
    if item.kcs_item_status == KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value:
        return "internal_candidate"
    if item.kcs_item_status == KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value:
        return "blocked_need_more_evidence"
    return "not_draftable"


def _effective_article_type(item: Any) -> str:
    """Treat explicit Q&A evidence as Q&A even when Claude labels it SCR."""

    article_type = item.article_type_hint
    if article_type != ArticleType.TECHNICAL_SCR.value:
        return str(article_type)
    if _has_supported_cause_for_scr(item):
        return str(article_type)
    if _has_text(item.question) or _has_text(item.supported_answer):
        return ArticleType.HOWTO_QA.value
    return str(article_type)


def _has_supported_cause_for_scr(item: Any) -> bool:
    if not _has_text(item.supported_cause):
        return False
    cause = str(item.supported_cause).strip()
    if _CAUSE_ACTION_LANGUAGE_RE.search(cause) and not (
        _CAUSE_EXPLANATORY_LANGUAGE_RE.search(cause)
    ):
        return False
    return True


def _has_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _merged_environment(
    environment: Mapping[str, Any],
    *,
    fallback_environment: Mapping[str, Any] | None,
) -> JsonDict:
    merged: JsonDict = {
        key: value
        for key, value in dict(fallback_environment or {}).items()
        if _environment_value_present(value)
    }
    merged.update(
        {
            key: value
            for key, value in dict(environment).items()
            if _environment_value_present(value)
        }
    )
    return merged


def _environment_value_present(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(isinstance(item, str) and item.strip() for item in value)
    return True


def _attach_semantic_lists(
    candidate: JsonDict,
    item: Any,
    *,
    article_type: str,
    environment: Mapping[str, Any],
) -> None:
    applicable_to = _applicable_to_from_environment(environment)
    if applicable_to:
        candidate["applicable_to"] = applicable_to
    symptoms = list(item.symptoms)
    if not symptoms and article_type == ArticleType.HOWTO_QA.value:
        symptoms = [item.question or item.summary]
    if symptoms:
        candidate["symptoms"] = symptoms
    if item.resolution_steps:
        candidate["resolution_steps"] = list(item.resolution_steps)
        if article_type == ArticleType.HOWTO_QA.value:
            candidate["answer_steps"] = list(item.resolution_steps)


def _attach_semantic_optional_fields(candidate: JsonDict, item: Any) -> None:
    optional_fields = ("supported_resolution_or_workaround", "supported_answer")
    for field_name in optional_fields:
        value = getattr(item, field_name)
        if value is not None:
            candidate[field_name] = value
    if candidate.get("article_type") != ArticleType.HOWTO_QA.value:
        value = getattr(item, "supported_cause")
        if value is not None:
            candidate["supported_cause"] = value
    question = _candidate_question(
        item,
        article_type=str(candidate.get("article_type", "")),
    )
    if question is not None:
        candidate["question"] = question


def _confirmed_facts(item: Any, *, article_type: str) -> list[str]:
    facts = list(item.confirmed_facts)
    if facts:
        return facts
    if article_type != ArticleType.HOWTO_QA.value:
        return facts
    for value in (item.question, item.supported_answer, item.summary):
        if isinstance(value, str) and value.strip():
            return [value.strip()]
    return facts


def _candidate_title(item: Any, *, article_type: str) -> str:
    if article_type == ArticleType.HOWTO_QA.value and _has_text(item.question):
        return _compact_howto_title(item.question)
    if article_type == ArticleType.HOWTO_QA.value and _has_text(item.summary):
        return _compact_howto_title(item.summary)
    return str(item.summary)


def _candidate_question(item: Any, *, article_type: str) -> str | None:
    if not _has_text(item.question):
        return item.question
    if article_type != ArticleType.HOWTO_QA.value:
        return item.question
    return _normalize_howto_question_text(item.question)


def _normalize_howto_question_text(value: str) -> str:
    text = _normalize_howto_base(value)
    if text.endswith("?"):
        return text
    return f"{text}?"


def _compact_howto_title(value: str) -> str:
    text = _normalize_howto_base(value)
    text = _QUESTION_CONTEXT_CONNECTOR_RE.sub("", text).strip()
    if not text:
        text = _normalize_howto_base(value)
    if text.endswith("?"):
        return text
    return f"{text}?"


def _normalize_howto_base(value: str) -> str:
    text = _QUESTION_MARK_RE.sub("", value.strip()).strip()
    match = _HOW_FIRST_PERSON_RE.match(text)
    if match is not None:
        return _how_to_phrase(match.group("body"))
    return text


def _how_to_phrase(body: str) -> str:
    body = body.strip()
    if not body:
        return "How to perform the requested task"
    return f"How to {body[0].lower()}{body[1:]}"


def _applicable_to_from_environment(environment: Mapping[str, Any]) -> list[str]:
    value = environment.get("applicable_to")
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if isinstance(value, list):
        return [
            item.strip() for item in value if isinstance(item, str) and item.strip()
        ]
    platform = environment.get("platform")
    if isinstance(platform, str) and platform.strip():
        return [platform.strip()]
    return []


__all__ = [
    "ProjectedIssue",
    "ProjectedIssueSet",
    "SemanticProjectionComparison",
    "SemanticProjectionLedgerEntry",
    "desktop_candidate_set_from_semantic_extraction",
    "desktop_candidate_set_from_semantic_issue_proposal",
    "desktop_item_candidates_from_semantic_extraction",
    "project_semantic_issue_proposals",
    "semantic_projection_requires_terminal_review",
    "semantic_projection_shadow_comparison",
]
