"""Controlled semantic-review state and packet helpers for Desktop."""

from __future__ import annotations

import json
import re
import secrets
import time
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from kcs_adapters.desktop_semantic_candidate_contract import (
    semantic_contract_debug_code,
    semantic_issue_proposal_contract_metadata,
)
from kcs_adapters.desktop_semantic_review_submission import (
    SemanticReviewSubmissionError,
    ensure_extractively_grounded_observations,
    ensure_issue_entry_speaker_compatibility,
    ensure_no_forbidden_semantic_submit_values,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_ref, ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS,
    SEMANTIC_ISSUE_PROPOSAL_MAX_TOTAL_BYTES,
    SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
    SemanticIssueProposalPacket,
)

SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION = "kcs_semantic_review_packet_v1"
SEMANTIC_REVIEW_REF_BYTES = 12
SEMANTIC_REVIEW_MAX_EXCERPTS = SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS
SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS = 12
SEMANTIC_REVIEW_MAX_EXCERPT_BYTES = 12_000
SEMANTIC_REVIEW_MAX_TOTAL_BYTES = 144_000
SEMANTIC_REVIEW_MAX_CANDIDATES = 5
_SEMANTIC_REVIEW_CORE_ROLE_COUNT = 3
_SEMANTIC_REVIEW_MAX_CORE_ROLE_SEGMENTS = (
    SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS // _SEMANTIC_REVIEW_CORE_ROLE_COUNT
)
_SEMANTIC_REVIEW_EDGE_ANCHOR_MIN_SCORE = 200

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")
_INLINE_TICKET_TURN_RE = re.compile(
    r"(?=\b(?:Client|Support(?::| Internal)?|Avatar\s+\{\{PERSON_NAME_\d+\}\})"
    r"\s*•\s+[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+\d{2}:\d{2})"
)
_CUSTOMER_TURN_RE = re.compile(r"^Client\s*•")
_SUPPORT_TURN_RE = re.compile(r"^Support(?::| Internal)?\s*•")
_INTERNAL_SUPPORT_TURN_RE = re.compile(r"^Support Internal\s*•")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_SYMPTOM_RE = re.compile(
    r"\b(?:customer|error|fail(?:ed|s|ure)?|issue|problem|symptoms?|"
    r"reported|shows?|unable)\b",
    re.I,
)
_CAUSE_RE = re.compile(
    r"\b(?:because|caus(?:e|ed|es)|confirmed|found|root\s+cause|"
    r"reason)\b",
    re.I,
)
_RESOLUTION_RE = re.compile(
    r"\b(?:back(?:ed)?\s+up|disabled|enabled|fixed|restarted|resolution|"
    r"resolved|solution|workaround)\b",
    re.I,
)
_QUESTION_TASK_RE = re.compile(
    r"\b(?:ask(?:ed|s)?|question|how\s+(?:can|do|does|to)|"
    r"(?:can|could|should)\s+(?:i|we|the\s+customer)|"
    r"where\s+(?:can|to)|who\s+(?:can|handles?)|what\s+(?:is|are)|"
    r"check(?:ing)?|enable|disable|activate|modify|configure|"
    r"settings?|option)\b",
    re.I,
)
_FACT_RE = re.compile(
    r"(?:\b(?:command|config(?:uration)?|path|service|verified)\b|"
    r"\b[a-z][a-z0-9_.-]+\s+(?:restart|status)\b|/[A-Za-z0-9_.-]+)",
    re.I,
)
_EXPLICIT_SYMPTOM_ROLE_RE = re.compile(
    r"\b(?:customer[- ]reported\s+)?symptoms?\s*:",
    re.I,
)
_EXPLICIT_CAUSE_ROLE_RE = re.compile(
    r"\b(?:confirmed|root|supported)\s+cause\s*:",
    re.I,
)
_EXPLICIT_RESOLUTION_ROLE_RE = re.compile(
    r"\b(?:supported\s+)?(?:resolution|workaround)"
    r"(?:\s+and\s+verification)?\s*:",
    re.I,
)
_EXPLICIT_QUESTION_ROLE_RE = re.compile(
    r"^\s*customer\s+(?:question|task)\s*:\s*$",
    re.I | re.M,
)
_EXPLICIT_ANSWER_ROLE_RE = re.compile(
    r"^\s*(?:supported\s+)?answer\s*:\s*$",
    re.I | re.M,
)
_EXPLICIT_INTERNAL_WORKFLOW_NOTE_RE = re.compile(
    r"^\s*internal\s+workflow\s+note\s*:\s*$",
    re.I | re.M,
)
_DETERMINISTIC_NON_ISSUE_ROLES = frozenset(
    {
        "duplicate_excerpt",
        "formatting_artifact",
        "internal_workflow_note",
        "ticket_metadata",
    }
)
_UNCLASSIFIED_EVIDENCE_ROLE = "unclassified_evidence"
_ISSUE_OBSERVATION_LIST_FIELDS = (
    "answer_evidence",
    "cause_evidence",
    "context_evidence",
    "error_evidence",
    "resolution_evidence",
    "symptoms",
    "verification_evidence",
)
_PUBLIC_SUPPORT_ARTICLE_URL_RE = re.compile(
    r"https://support\.plesk\.com/hc/en-us/articles/[A-Za-z0-9_-]+",
    re.I,
)


class SemanticReviewError(ValueError):
    """Value-safe semantic-review workflow error."""

    def __init__(self, debug_code: str) -> None:
        super().__init__("semantic review unavailable")
        self.debug_code = debug_code


@dataclass(frozen=True)
class PendingSemanticReview:
    """Opaque pending semantic-review packet state."""

    semantic_review_ref: str
    ticket_ref: str
    source_kind: str | None
    allowed_source_refs: tuple[str, ...]
    approved_summary_text: str
    packet: JsonDict
    packet_prepared: bool
    expires_at: float
    failed_submit_attempts: int = 0


def new_pending_semantic_review(
    *,
    approved_summary_text: str,
    ticket_ref: str,
    source_kind: str | None,
    ttl_seconds: float,
) -> PendingSemanticReview:
    """Create a bounded semantic-review packet and pending state."""

    excerpts = selected_semantic_review_excerpts(approved_summary_text)
    if not excerpts:
        raise SemanticReviewError("semantic_review_packet_unavailable")
    semantic_review_ref = (
        f"semantic-review-{secrets.token_urlsafe(SEMANTIC_REVIEW_REF_BYTES)}"
    )
    packet = semantic_review_packet(
        excerpts=excerpts,
        semantic_review_ref=semantic_review_ref,
    )
    return PendingSemanticReview(
        allowed_source_refs=tuple(excerpt["source_ref"] for excerpt in excerpts),
        approved_summary_text=approved_summary_text,
        expires_at=time.monotonic() + ttl_seconds,
        packet=packet,
        packet_prepared=False,
        semantic_review_ref=semantic_review_ref,
        source_kind=source_kind,
        ticket_ref=ticket_ref,
    )


def prepared_pending_semantic_review(
    pending: PendingSemanticReview,
) -> PendingSemanticReview:
    """Return the same pending review marked as prepared for submit."""

    return PendingSemanticReview(
        allowed_source_refs=pending.allowed_source_refs,
        approved_summary_text=pending.approved_summary_text,
        expires_at=pending.expires_at,
        failed_submit_attempts=pending.failed_submit_attempts,
        packet=pending.packet,
        packet_prepared=True,
        semantic_review_ref=pending.semantic_review_ref,
        source_kind=pending.source_kind,
        ticket_ref=pending.ticket_ref,
    )


def semantic_review_packet(
    *,
    excerpts: list[JsonDict],
    semantic_review_ref: str,
) -> JsonDict:
    """Return the Claude-visible bounded semantic-review packet."""

    return _semantic_issue_proposal_packet(
        excerpts=excerpts,
        semantic_review_ref=semantic_review_ref,
    )


def _semantic_issue_proposal_packet(
    *,
    excerpts: list[JsonDict],
    semantic_review_ref: str,
) -> JsonDict:
    """Return the active observation-only semantic-review packet."""

    allowed_source_refs = tuple(str(excerpt["source_ref"]) for excerpt in excerpts)
    contract = semantic_issue_proposal_contract_packet(
        allowed_source_refs=allowed_source_refs,
        semantic_review_ref=semantic_review_ref,
    )
    proposal_shape = contract["required_submit_shape"]["semantic_issue_proposal"]
    packet: JsonDict = {
        **contract,
        "auto_publish_allowed": False,
        "case_ref": semantic_review_ref,
        "excerpt_count": len(excerpts),
        "excerpt_total_bytes": sum(
            len(str(excerpt["text"]).encode("utf-8")) for excerpt in excerpts
        ),
        "manual_draft_allowed": False,
        "max_candidates": SEMANTIC_REVIEW_MAX_CANDIDATES,
        "network_calls": False,
        "ok": True,
        "public_output_approved": False,
        "required_submit_shape": {
            "semantic_issue_proposal": proposal_shape,
            "semantic_review_ref": semantic_review_ref,
        },
        "result_kind": "semantic_review_packet",
        "schema_correction_used": False,
        "schema_version": SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION,
        "selected_excerpts": excerpts,
        "submit_arguments": {"semantic_review_ref": semantic_review_ref},
        "submit_tool": "kcs_submit_semantic_review",
        "task": (
            "Propose observation-only issue boundaries and deterministic "
            "coverage records. Every technical issue must include its "
            "source-grounded cause evidence and all available source-grounded "
            "resolution evidence. Except for summary, copy every observation's "
            "text exactly from one of its referenced selected_excerpts; do not "
            "paraphrase, and do not omit explicit resolution steps, commands, "
            "URLs, questions, or symptoms. When speaker_kind identifies a "
            "customer turn, use customer-authored text for symptoms and "
            "question; do not use explicitly support-authored text for those "
            "fields. Summary remains generative. Do not add local workstation "
            "paths, storage hints, reviewer-file references, or tool-artifact "
            "paths that are absent from selected_excerpts. Do not choose an operator "
            "action, KCS action, reuse result, readiness state, renderer output, "
            "or workflow state."
        ),
        "writes_files": False,
    }
    packet["semantic_review_packet_sha256"] = _packet_sha256(packet)
    ensure_safe_sanitized_payload(packet)
    return packet


def semantic_issue_proposal_contract_packet(
    *,
    allowed_source_refs: tuple[str, ...],
    semantic_review_ref: str,
) -> JsonDict:
    """Return the bounded contract shared by runtime and comparison tooling."""

    if (
        not allowed_source_refs
        or len(allowed_source_refs) > SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS
        or any(not isinstance(source_ref, str) for source_ref in allowed_source_refs)
        or len(allowed_source_refs) != len(set(allowed_source_refs))
    ):
        raise SemanticReviewError("semantic_issue_source_refs_invalid")
    if not isinstance(semantic_review_ref, str):
        raise SemanticReviewError("semantic_issue_review_ref_invalid")
    try:
        for source_ref in allowed_source_refs:
            ensure_safe_ref(source_ref, label="source_ref")
    except ContractValidationError as exc:
        raise SemanticReviewError("semantic_issue_source_refs_invalid") from exc
    try:
        ensure_safe_ref(semantic_review_ref, label="semantic_review_ref")
    except ContractValidationError as exc:
        raise SemanticReviewError("semantic_issue_review_ref_invalid") from exc
    metadata = semantic_issue_proposal_contract_metadata()
    shape_contracts = metadata["proposal_shape_contracts"]
    packet: JsonDict = {
        "allowed_source_refs": list(allowed_source_refs),
        "coverage_record_field_names": list(shape_contracts["coverage_record"]),
        "issue_boundary_contract": metadata["issue_boundary_contract"],
        "issue_shape_contract": metadata["issue_shape_contract"],
        "issue_field_names": list(shape_contracts["issue"]),
        "proposal_field_contracts": metadata["proposal_field_contracts"],
        "proposal_shape_contracts": shape_contracts,
        "required_submit_shape": {
            "semantic_issue_proposal": {
                "case_ref": semantic_review_ref,
                "coverage_records": [],
                "extraction_source_ref": "semantic-proposal-submit-001",
                "issues": [],
                "schema_version": SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION,
                "source_refs": list(allowed_source_refs),
            }
        },
        "semantic_review_ref": semantic_review_ref,
    }
    ensure_safe_sanitized_payload(packet)
    return packet


def selected_semantic_review_excerpts(text: str) -> list[JsonDict]:
    """Select bounded high-signal excerpts from a clean ticket transcript."""

    segment_records = _segment_records(text)
    has_speaker_transcript = any(
        speaker_kind != "unknown"
        for _, _, speaker_kind, _ in segment_records
    )
    complete_transcript = _complete_bounded_speaker_inventory(segment_records)
    if has_speaker_transcript:
        if complete_transcript is None:
            return []
        selected, speaker_kind_by_index = complete_transcript
        excerpts = _bounded_excerpts(
            _model_visible_evidence_roles(
                _safe_selected_segments(selected),
            ),
            speaker_kind_by_index=speaker_kind_by_index,
        )
        for excerpt in excerpts:
            ensure_safe_sanitized_payload(excerpt)
        return excerpts
    segments = [(index, value) for index, value, _, _ in segment_records]
    speaker_kind_by_index = {
        index: speaker_kind for index, _, speaker_kind, _ in segment_records
    }
    selected = _explicit_public_resolution_reference_segments(segments)
    selected.extend(
        (index, inherited_role, value)
        for index, value, _, inherited_role in segment_records
        if inherited_role is not None
    )
    selected.extend(_balanced_core_role_segments(segments))
    selected.extend(_top_question_task_segments(segments))
    selected.extend(
        _explicit_role_segments(
            segments,
            matcher=_EXPLICIT_ANSWER_ROLE_RE,
            role="supported_resolution",
        )
    )
    selected.extend(
        _explicit_role_segments(
            segments,
            matcher=_EXPLICIT_INTERNAL_WORKFLOW_NOTE_RE,
            role="internal_workflow_note",
        )
    )
    selected.extend(_top_fact_segments(segments))
    selected = _dedupe_selected(selected)
    selected = _safe_selected_segments(selected)
    selected = selected[:SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS]
    selected.sort(key=lambda item: item[0])
    selected = _model_visible_evidence_roles(selected)
    excerpts = _bounded_excerpts(
        selected,
        speaker_kind_by_index=speaker_kind_by_index,
    )
    for excerpt in excerpts:
        ensure_safe_sanitized_payload(excerpt)
    return excerpts


def semantic_issue_proposal_from_submission(
    *,
    pending: PendingSemanticReview,
    semantic_issue_proposal: object,
) -> SemanticIssueProposalPacket:
    """Validate an active observation proposal against its prepared packet."""

    try:
        semantic_issue_proposal = _normalized_semantic_issue_proposal(
            semantic_issue_proposal
        )
        _ensure_bounded_proposal_payload(semantic_issue_proposal)
        ensure_no_forbidden_semantic_submit_values(semantic_issue_proposal)
        _ensure_prepared_proposal_identity(
            pending=pending,
            semantic_issue_proposal=semantic_issue_proposal,
        )
        proposal = SemanticIssueProposalPacket.from_json_dict(semantic_issue_proposal)
    except SemanticReviewSubmissionError as exc:
        raise SemanticReviewError(exc.debug_code) from exc
    except ContractValidationError as exc:
        raise SemanticReviewError(semantic_contract_debug_code(str(exc))) from exc
    expected_refs = set(pending.allowed_source_refs)
    if proposal.case_ref != pending.semantic_review_ref:
        raise SemanticReviewError("semantic_issue_case_ref_mismatch")
    if set(proposal.source_refs) != expected_refs:
        raise SemanticReviewError("semantic_issue_top_level_source_refs_mismatch")
    if len(proposal.issues) > SEMANTIC_REVIEW_MAX_CANDIDATES:
        raise SemanticReviewError("semantic_issue_candidate_limit_exceeded")
    try:
        excerpt_text_by_ref = _semantic_review_excerpt_text_index(pending)
        ensure_extractively_grounded_observations(
            proposal,
            excerpt_text_by_ref,
        )
        ensure_issue_entry_speaker_compatibility(
            proposal,
            excerpt_text_by_ref,
            _semantic_review_excerpt_speaker_index(pending),
        )
    except SemanticReviewSubmissionError as exc:
        raise SemanticReviewError(exc.debug_code) from exc
    return proposal


def _normalized_semantic_issue_proposal(value: object) -> object:
    """Canonicalize supported Desktop transport variations."""

    decoded = value
    if isinstance(value, str):
        if len(value.encode("utf-8")) > SEMANTIC_ISSUE_PROPOSAL_MAX_TOTAL_BYTES:
            raise ContractValidationError("semantic issue proposal packet too large")
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ContractValidationError("payload must be a JSON object") from exc
        if not isinstance(decoded, Mapping):
            raise ContractValidationError("payload must be a JSON object")
    if not isinstance(decoded, Mapping):
        return decoded
    return _normalized_issue_wire_shapes(decoded)


def _normalized_issue_wire_shapes(payload: Mapping[str, object]) -> JsonDict:
    """Canonicalize semantically empty issue fields before strict parsing."""

    issues = payload.get("issues")
    if not isinstance(issues, list):
        return dict(payload)
    normalized_issues: list[object] = []
    for issue in issues:
        if not isinstance(issue, Mapping):
            normalized_issues.append(issue)
            continue
        normalized_issue = dict(issue)
        for field_name in _ISSUE_OBSERVATION_LIST_FIELDS:
            normalized_issue.setdefault(field_name, [])
        normalized_issue.setdefault("question", None)
        summary = normalized_issue.get("summary")
        summary_source_refs = _issue_observation_source_refs(normalized_issue)
        if isinstance(summary, str) and summary_source_refs:
            normalized_issue["summary"] = {
                "source_refs": summary_source_refs,
                "text": summary,
            }
        normalized_issues.append(normalized_issue)
    normalized = dict(payload)
    normalized["issues"] = normalized_issues
    return normalized


def _issue_observation_source_refs(issue: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    observations: list[object] = []
    for field_name in _ISSUE_OBSERVATION_LIST_FIELDS:
        value = issue.get(field_name)
        if isinstance(value, list):
            observations.extend(value)
    question = issue.get("question")
    if question is not None:
        observations.append(question)
    for observation in observations:
        if not isinstance(observation, Mapping):
            continue
        source_refs = observation.get("source_refs")
        if not isinstance(source_refs, list):
            continue
        refs.extend(ref for ref in source_refs if isinstance(ref, str))
    return list(dict.fromkeys(refs))


def _ensure_prepared_proposal_identity(
    *,
    pending: PendingSemanticReview,
    semantic_issue_proposal: object,
) -> None:
    """Prioritize prepared-packet identity before internal coverage checks."""

    if not isinstance(semantic_issue_proposal, Mapping):
        return
    case_ref = semantic_issue_proposal.get("case_ref")
    if isinstance(case_ref, str) and case_ref != pending.semantic_review_ref:
        raise SemanticReviewError("semantic_issue_case_ref_mismatch")
    source_refs = semantic_issue_proposal.get("source_refs")
    if (
        isinstance(source_refs, list)
        and all(isinstance(source_ref, str) for source_ref in source_refs)
        and set(source_refs) != set(pending.allowed_source_refs)
    ):
        raise SemanticReviewError("semantic_issue_top_level_source_refs_mismatch")
    issues = semantic_issue_proposal.get("issues")
    if isinstance(issues, list) and len(issues) > SEMANTIC_REVIEW_MAX_CANDIDATES:
        raise SemanticReviewError("semantic_issue_candidate_limit_exceeded")


def semantic_review_excerpt_role_index(
    pending: PendingSemanticReview,
) -> dict[str, JsonDict]:
    """Return immutable semantic roles with fail-closed runtime provenance."""

    excerpts = pending.packet.get("selected_excerpts")
    if not isinstance(excerpts, list):
        raise SemanticReviewError("semantic_review_packet_unavailable")
    index: dict[str, JsonDict] = {}
    for excerpt in excerpts:
        if not isinstance(excerpt, dict):
            raise SemanticReviewError("semantic_review_packet_unavailable")
        source_ref = excerpt.get("source_ref")
        role = excerpt.get("role")
        text = excerpt.get("text")
        if not all(isinstance(value, str) for value in (source_ref, role, text)):
            raise SemanticReviewError("semantic_review_packet_unavailable")
        index[source_ref] = {
            "content_sha256": sha256(text.encode("utf-8")).hexdigest(),
            "provenance_trusted": False,
            "roles": [role],
            "visibility": "internal_reviewer_only",
        }
    return index


def _semantic_review_excerpt_text_index(
    pending: PendingSemanticReview,
) -> dict[str, str]:
    excerpts = pending.packet.get("selected_excerpts")
    if not isinstance(excerpts, list):
        raise SemanticReviewError("semantic_review_packet_unavailable")
    index: dict[str, str] = {}
    for excerpt in excerpts:
        if not isinstance(excerpt, dict):
            raise SemanticReviewError("semantic_review_packet_unavailable")
        source_ref = excerpt.get("source_ref")
        text = excerpt.get("text")
        if not isinstance(source_ref, str) or not isinstance(text, str):
            raise SemanticReviewError("semantic_review_packet_unavailable")
        index[source_ref] = text
    if set(index) != set(pending.allowed_source_refs):
        raise SemanticReviewError("semantic_review_packet_unavailable")
    return index


def _semantic_review_excerpt_speaker_index(
    pending: PendingSemanticReview,
) -> dict[str, str]:
    excerpts = pending.packet.get("selected_excerpts")
    if not isinstance(excerpts, list):
        raise SemanticReviewError("semantic_review_packet_unavailable")
    index: dict[str, str] = {}
    for excerpt in excerpts:
        if not isinstance(excerpt, dict):
            raise SemanticReviewError("semantic_review_packet_unavailable")
        source_ref = excerpt.get("source_ref")
        speaker_kind = excerpt.get("speaker_kind")
        if not isinstance(source_ref, str) or speaker_kind not in {
            "customer",
            "support",
            "unknown",
        }:
            raise SemanticReviewError("semantic_review_packet_unavailable")
        index[source_ref] = speaker_kind
    if set(index) != set(pending.allowed_source_refs):
        raise SemanticReviewError("semantic_review_packet_unavailable")
    return index


def _ensure_bounded_proposal_payload(value: object) -> None:
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise SemanticReviewError("semantic_issue_submission_invalid") from exc
    if len(payload.encode("utf-8")) > SEMANTIC_ISSUE_PROPOSAL_MAX_TOTAL_BYTES:
        raise SemanticReviewError("semantic_issue_submission_invalid")


def _segments(text: str) -> list[tuple[int, str]]:
    return [(index, value) for index, value, _, _ in _segment_records(text)]


def _segment_records(text: str) -> list[tuple[int, str, str, str | None]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    inline_chunks = _inline_ticket_turn_chunks(normalized)
    has_ticket_transcript = any(
        _speaker_kind(turn) != "unknown"
        or _INTERNAL_SUPPORT_TURN_RE.search(turn) is not None
        for turn in inline_chunks
    )
    chunks = [] if has_ticket_transcript else _explicit_labeled_chunks(normalized)
    chunk_records: list[tuple[str, str, str | None]]
    preserve_chunk_atoms = False
    if chunks:
        chunk_records = [
            (chunk, _speaker_kind(chunk), _inherited_explicit_role(chunk))
            for chunk in chunks
        ]
    else:
        chunks = [chunk.strip() for chunk in _BLANK_LINE_RE.split(normalized)]
        chunk_records, preserve_chunk_atoms = _unlabeled_chunk_records(
            normalized,
            chunks,
        )
    segments: list[tuple[int, str, str, str | None]] = []
    atomic_records = [
        (atom, speaker_kind, inherited_role)
        for chunk, speaker_kind, inherited_role in chunk_records
        for atom in ([chunk] if preserve_chunk_atoms else _sentence_atoms(chunk))
    ]
    for index, (atom, speaker_kind, inherited_role) in enumerate(atomic_records):
        safe = _clean_segment(atom)
        if safe:
            segments.append((index, safe, speaker_kind, inherited_role))
    return segments


def _unlabeled_chunk_records(
    normalized: str,
    chunks: list[str],
) -> tuple[list[tuple[str, str, str | None]], bool]:
    inline_chunks = _inline_ticket_turn_chunks(normalized)
    if any(
        _speaker_kind(turn) != "unknown"
        or _INTERNAL_SUPPORT_TURN_RE.search(turn) is not None
        for turn in inline_chunks
    ):
        records = [
            (chunk, _speaker_kind(turn), None)
            for turn in inline_chunks
            if _INTERNAL_SUPPORT_TURN_RE.search(turn) is None
            and _speaker_kind(turn) != "unknown"
            for chunk in _bounded_inline_turn_chunk(
                _WHITESPACE_RE.sub(" ", turn.strip())
            )
        ]
        return records, True
    if len(chunks) >= 3:
        return [(chunk, _speaker_kind(chunk), None) for chunk in chunks], False
    records = [
        (line, _speaker_kind(line), None)
        for line in (value.strip() for value in normalized.splitlines())
    ]
    return records, False


def _sentence_atoms(text: str) -> list[str]:
    starts = [0, *_sentence_start_offsets(text)]
    ends = [*starts[1:], len(text)]
    return [
        atom
        for start, end in zip(starts, ends, strict=True)
        if (atom := text[start:end].strip())
    ]


def _sentence_start_offsets(text: str) -> list[int]:
    starts: list[int] = []
    index = 0
    quote_delimiter: str | None = None
    while index < len(text):
        index, quote_delimiter, consumed = _advance_quoted_scan(
            text,
            index,
            quote_delimiter,
        )
        if consumed:
            continue
        if text[index] in ".!?" and _has_following_whitespace(text, index):
            index += 1
            while index < len(text) and text[index].isspace():
                index += 1
            starts.append(index)
            continue
        index += 1
    return starts


def _advance_quoted_scan(
    text: str,
    index: int,
    quote_delimiter: str | None,
) -> tuple[int, str | None, bool]:
    if quote_delimiter is not None:
        if text.startswith(quote_delimiter, index):
            return index + len(quote_delimiter), None, True
        step = 2 if text[index] == "\\" else 1
        return index + step, quote_delimiter, True
    opening_delimiter = _quote_delimiter_at(text, index)
    if opening_delimiter is None:
        return index, None, False
    return index + len(opening_delimiter), opening_delimiter, True


def _quote_delimiter_at(text: str, index: int) -> str | None:
    if not _can_open_quote(text, index):
        return None
    for delimiter in ('"""', "'''", "```", '"', "'", "`"):
        if not text.startswith(delimiter, index):
            continue
        return delimiter
    return None


def _can_open_quote(text: str, index: int) -> bool:
    return index == 0 or text[index - 1].isspace() or text[index - 1] in "([{=:,;"


def _has_following_whitespace(text: str, index: int) -> bool:
    return index + 1 < len(text) and text[index + 1].isspace()


def _explicit_labeled_chunks(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    label_count = sum(_explicit_label_role(line) is not None for line in lines)
    if label_count < 2:
        return []
    chunks: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                chunks.append("\n".join(current))
                current = []
            continue
        if _explicit_label_role(line) is not None and current:
            chunks.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _explicit_label_role(line: str) -> str | None:
    matchers = (
        ("reported_symptom", _EXPLICIT_SYMPTOM_ROLE_RE),
        ("supported_cause", _EXPLICIT_CAUSE_ROLE_RE),
        ("supported_resolution", _EXPLICIT_RESOLUTION_ROLE_RE),
        ("customer_question", _EXPLICIT_QUESTION_ROLE_RE),
        ("supported_resolution", _EXPLICIT_ANSWER_ROLE_RE),
        ("internal_workflow_note", _EXPLICIT_INTERNAL_WORKFLOW_NOTE_RE),
    )
    return next(
        (role for role, matcher in matchers if matcher.fullmatch(line)),
        None,
    )


def _inherited_explicit_role(chunk: str) -> str | None:
    first_line = next(
        (line.strip() for line in chunk.splitlines() if line.strip()),
        "",
    )
    return _explicit_label_role(first_line)


def _inline_ticket_turn_chunks(text: str) -> list[str]:
    return [
        chunk
        for value in _INLINE_TICKET_TURN_RE.split(text)
        if (chunk := value.strip())
    ]


def _bounded_inline_turn_chunk(turn: str) -> list[str]:
    if len(turn.encode("utf-8")) <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES:
        return [turn]
    chunks: list[str] = []
    current = ""
    for sentence in _sentence_atoms(turn):
        if len(sentence.encode("utf-8")) > SEMANTIC_REVIEW_MAX_EXCERPT_BYTES:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_bounded_words(sentence))
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate.encode("utf-8")) <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES:
            current = candidate
            continue
        chunks.append(current)
        current = sentence
    if current:
        chunks.append(current)
    return chunks


def _bounded_words(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if len(candidate.encode("utf-8")) <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = word
    if current:
        chunks.append(current)
    return chunks


def _speaker_kind(turn: str) -> str:
    if _CUSTOMER_TURN_RE.search(turn):
        return "customer"
    if _SUPPORT_TURN_RE.search(turn):
        return "support"
    return "unknown"


def _complete_bounded_speaker_inventory(
    records: list[tuple[int, str, str, str | None]],
) -> tuple[list[tuple[int, str, str]], dict[int, str]] | None:
    """Keep every original speaker block when the packet bounds allow it."""

    if not any(speaker_kind != "unknown" for _, _, speaker_kind, _ in records):
        return None
    selected = [
        (index, inherited_role or _UNCLASSIFIED_EVIDENCE_ROLE, text)
        for index, text, _, inherited_role in records
    ]
    speaker_kind_by_index = {
        index: speaker_kind for index, _, speaker_kind, _ in records
    }
    total_bytes = sum(len(text.encode("utf-8")) for _, _, text in selected)
    if (
        len(selected) > SEMANTIC_REVIEW_MAX_EXCERPTS
        or total_bytes > SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    ):
        return None
    return selected, speaker_kind_by_index


def _clean_segment(value: str) -> str:
    text = _WHITESPACE_RE.sub(" ", value.strip())
    if not text:
        return ""
    if len(text.encode("utf-8")) > SEMANTIC_REVIEW_MAX_EXCERPT_BYTES:
        text = _truncate_utf8_text(
            text,
            max_bytes=SEMANTIC_REVIEW_MAX_EXCERPT_BYTES,
            suffix=" [excerpt truncated]",
        )
    return text


def _balanced_core_role_segments(
    segments: list[tuple[int, str]],
) -> list[tuple[int, str, str]]:
    roles = ("reported_symptom", "supported_cause", "supported_resolution")
    ranked = {role: _top_segments_for_role(segments, role) for role in roles}
    return [
        ranked[role][rank]
        for rank in range(_SEMANTIC_REVIEW_MAX_CORE_ROLE_SEGMENTS)
        for role in roles
        if rank < len(ranked[role])
    ]


def _explicit_public_resolution_reference_segments(
    segments: list[tuple[int, str]],
) -> list[tuple[int, str, str]]:
    candidates = [
        (_score_segment(text, _RESOLUTION_RE), index, text)
        for index, text in segments
        if _PUBLIC_SUPPORT_ARTICLE_URL_RE.search(text)
        and _RESOLUTION_RE.search(text)
    ]
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [
        (index, "supported_resolution", text)
        for _, index, text in candidates[:1]
    ]


def _top_segments_for_role(
    segments: list[tuple[int, str]],
    role: str,
) -> list[tuple[int, str, str]]:
    matcher = {
        "reported_symptom": _SYMPTOM_RE,
        "supported_cause": _CAUSE_RE,
        "supported_resolution": _RESOLUTION_RE,
    }[role]
    scored = [
        (_score_segment(text, matcher), index, text)
        for index, text in segments
        if matcher.search(text)
    ]
    scored = _edge_anchored_segment_scores(scored)
    return [
        (index, role, text)
        for score, index, text in scored[:_SEMANTIC_REVIEW_MAX_CORE_ROLE_SEGMENTS]
        if score > 0
    ]


def _edge_anchored_segment_scores(
    scored: list[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    ranked = sorted(scored, key=lambda item: (item[0], item[1]), reverse=True)
    meaningful = [
        item for item in scored if item[0] >= _SEMANTIC_REVIEW_EDGE_ANCHOR_MIN_SCORE
    ]
    anchors = sorted(meaningful, key=lambda item: item[1])
    prioritized = [*(anchors[:1]), *(anchors[-1:]), *ranked]
    selected: list[tuple[int, int, str]] = []
    selected_indices: set[int] = set()
    for item in prioritized:
        if item[1] in selected_indices:
            continue
        selected_indices.add(item[1])
        selected.append(item)
    return selected


def _top_fact_segments(segments: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    scored = [
        (_score_segment(text, _FACT_RE), index, text)
        for index, text in segments
        if _FACT_RE.search(text)
    ]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [(index, "confirmed_fact", text) for _, index, text in scored[:4]]


def _top_question_task_segments(
    segments: list[tuple[int, str]],
) -> list[tuple[int, str, str]]:
    scored = [
        (_score_segment(text, _QUESTION_TASK_RE), index, text)
        for index, text in segments
        if _QUESTION_TASK_RE.search(text)
    ]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [(index, "customer_question", text) for _, index, text in scored[:4]]


def _explicit_role_segments(
    segments: list[tuple[int, str]],
    *,
    matcher: re.Pattern[str],
    role: str,
) -> list[tuple[int, str, str]]:
    return [(index, role, text) for index, text in segments if matcher.search(text)]


def _score_segment(text: str, matcher: re.Pattern[str]) -> int:
    return len(matcher.findall(text)) * 100 + min(len(text), 500)


def _dedupe_selected(
    selected: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    selected_position_by_index: dict[int, int] = {}
    selected_position_by_text: dict[str, int] = {}
    deduped: list[tuple[int, str, str]] = []
    for index, role, text in selected:
        text_key = _WHITESPACE_RE.sub(" ", text).casefold()
        position = selected_position_by_index.get(index)
        if position is None:
            position = selected_position_by_text.get(text_key)
        if position is not None:
            existing_index, existing_role, existing_text = deduped[position]
            deduped[position] = (
                existing_index,
                _preferred_duplicate_role(existing_role, role, existing_text),
                existing_text,
            )
            continue
        position = len(deduped)
        selected_position_by_index[index] = position
        selected_position_by_text[text_key] = position
        deduped.append((index, role, text))
    return deduped


def _safe_selected_segments(
    selected: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    safe: list[tuple[int, str, str]] = []
    for item in selected:
        try:
            ensure_safe_sanitized_payload(item[2])
        except ContractValidationError:
            continue
        safe.append(item)
    return safe


def _model_visible_evidence_roles(
    selected: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    return [
        (
            index,
            role
            if role in _DETERMINISTIC_NON_ISSUE_ROLES
            else _UNCLASSIFIED_EVIDENCE_ROLE,
            text,
        )
        for index, role, text in selected
    ]


def _preferred_duplicate_role(current: str, candidate: str, text: str) -> str:
    roles = {current, candidate}
    explicit_issue_role_count = sum(
        matcher.search(text) is not None
        for matcher in (
            _EXPLICIT_SYMPTOM_ROLE_RE,
            _EXPLICIT_CAUSE_ROLE_RE,
            _EXPLICIT_RESOLUTION_ROLE_RE,
        )
    )
    if "confirmed_fact" in roles and explicit_issue_role_count > 1:
        return "confirmed_fact"
    if "internal_workflow_note" in roles:
        return "internal_workflow_note"
    if "supported_resolution" in roles and _EXPLICIT_ANSWER_ROLE_RE.search(text):
        return "supported_resolution"
    if (
        "customer_question" in roles
        and current not in {"supported_cause", "supported_resolution"}
        and (
            explicit_issue_role_count == 0
            or _EXPLICIT_QUESTION_ROLE_RE.search(text)
        )
    ):
        return "customer_question"
    return current


def _bounded_excerpts(
    selected: list[tuple[int, str, str]],
    *,
    speaker_kind_by_index: Mapping[int, str],
) -> list[JsonDict]:
    excerpts: list[JsonDict] = []
    total_bytes = 0
    for index, role, text in selected:
        if len(excerpts) >= SEMANTIC_REVIEW_MAX_EXCERPTS:
            break
        text_bytes = len(text.encode("utf-8"))
        if total_bytes + text_bytes > SEMANTIC_REVIEW_MAX_TOTAL_BYTES:
            break
        source_ref = f"excerpt-{len(excerpts) + 1:03d}"
        excerpt = {
            "role": role,
            "source_ref": source_ref,
            "speaker_kind": speaker_kind_by_index.get(index, "unknown"),
            "text": text,
        }
        try:
            ensure_safe_sanitized_payload(excerpt)
        except ContractValidationError:
            continue
        excerpts.append(excerpt)
        total_bytes += text_bytes
    return excerpts


def _truncate_utf8_text(text: str, *, max_bytes: int, suffix: str) -> str:
    suffix_bytes = suffix.encode("utf-8")
    limit = max_bytes - len(suffix_bytes)
    if limit <= 0:
        return suffix[:max_bytes]
    encoded = text.encode("utf-8")[:limit]
    truncated = encoded.decode("utf-8", errors="ignore").rstrip()
    return f"{truncated}{suffix}"


def _packet_sha256(packet: JsonDict) -> str:
    payload = {
        key: value
        for key, value in packet.items()
        if key != "semantic_review_packet_sha256"
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = [
    "PendingSemanticReview",
    "SEMANTIC_REVIEW_MAX_CANDIDATES",
    "SEMANTIC_REVIEW_MAX_EXCERPT_BYTES",
    "SEMANTIC_REVIEW_MAX_EXCERPTS",
    "SEMANTIC_REVIEW_MAX_RANKED_EXCERPTS",
    "SEMANTIC_REVIEW_MAX_TOTAL_BYTES",
    "SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION",
    "SemanticReviewError",
    "new_pending_semantic_review",
    "prepared_pending_semantic_review",
    "selected_semantic_review_excerpts",
    "semantic_issue_proposal_contract_packet",
    "semantic_issue_proposal_from_submission",
    "semantic_review_excerpt_role_index",
    "semantic_review_packet",
]
