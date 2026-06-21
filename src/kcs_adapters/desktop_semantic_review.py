"""Controlled semantic-review state and packet helpers for Desktop."""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    CandidateSemanticExtraction,
    validate_candidate_semantic_extraction,
)

SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION = "kcs_semantic_review_packet_v1"
SEMANTIC_REVIEW_REF_BYTES = 12
SEMANTIC_REVIEW_MAX_EXCERPTS = 12
SEMANTIC_REVIEW_MAX_EXCERPT_BYTES = 12_000
SEMANTIC_REVIEW_MAX_TOTAL_BYTES = 144_000
SEMANTIC_REVIEW_MAX_CANDIDATES = 5

_BLANK_LINE_RE = re.compile(r"\n\s*\n+")
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
_FACT_RE = re.compile(
    r"(?:\b(?:command|config(?:uration)?|path|service|verified)\b|"
    r"\b[a-z][a-z0-9_.-]+\s+(?:restart|status)\b|/[A-Za-z0-9_.-]+)",
    re.I,
)
_SUBMIT_FORBIDDEN_TEXT_RE = re.compile(
    r"</?\s*[a-z][a-z0-9:-]*(?:\s|/?>)|```",
    re.I | re.M,
)
_SUBMIT_MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S.*$", re.M)
_SUBMIT_CONFIG_TEXT_RE = re.compile(r"\bCONFIG_TEXT:", re.I)
_SUBMIT_CONFIG_COMMENT_PATH_RE = re.compile(
    r"^\s*#{1,6}\s+/[A-Za-z0-9_./:-]+", re.M
)
_SAFE_CONFIG_PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_:-]{1,40}>")
_SUBMIT_FORBIDDEN_LOCAL_PATH_RE = re.compile(
    r"(?:file://|~[/\\]|[A-Za-z]:[\\/]|\\\\[^\\\s]+\\[^\\\s]+|"
    r"(?<![A-Za-z0-9])/(?:Users|private|tmp)(?:/[A-Za-z0-9._~+-]+)*|"
    r"(?<![A-Za-z0-9])local-data/(?:approved-summaries|reviewer-bundles)"
    r"(?:/[A-Za-z0-9._~+-]+)*)",
    re.I,
)
_SUBMIT_FORBIDDEN_COMPACT_KEYS = frozenset(
    {
        "autopublishallowed",
        "candidateextraction",
        "file",
        "filepath",
        "item",
        "itemcandidates",
        "localpath",
        "path",
        "publicoutputapproved",
        "recommendedaction",
        "revieweronlyhtml",
    }
)
_SUBMIT_PLAIN_STRING_ARRAY_FIELDS = frozenset(
    {
        "confirmed_facts",
        "open_questions",
        "resolution_steps",
        "source_refs",
        "symptoms",
    }
)
SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES = 4000
SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES = 64_000


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
    allowed_source_refs: tuple[str, ...]
    approved_summary_text: str
    packet: JsonDict
    packet_prepared: bool
    expires_at: float


def new_pending_semantic_review(
    *,
    approved_summary_text: str,
    ticket_ref: str,
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
        ticket_ref=ticket_ref,
    )
    return PendingSemanticReview(
        allowed_source_refs=tuple(excerpt["source_ref"] for excerpt in excerpts),
        approved_summary_text=approved_summary_text,
        expires_at=time.monotonic() + ttl_seconds,
        packet=packet,
        packet_prepared=False,
        semantic_review_ref=semantic_review_ref,
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
        packet=pending.packet,
        packet_prepared=True,
        semantic_review_ref=pending.semantic_review_ref,
        ticket_ref=pending.ticket_ref,
    )


def semantic_review_packet(
    *,
    excerpts: list[JsonDict],
    semantic_review_ref: str,
    ticket_ref: str,
) -> JsonDict:
    """Return the Claude-visible bounded semantic-review packet."""

    excerpt_total_bytes = sum(
        len(str(excerpt["text"]).encode("utf-8")) for excerpt in excerpts
    )
    packet: JsonDict = {
        "allowed_output_schema": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "allowed_source_refs": [excerpt["source_ref"] for excerpt in excerpts],
        "auto_publish_allowed": False,
        "case_ref": semantic_review_ref,
        "excerpt_count": len(excerpts),
        "excerpt_total_bytes": excerpt_total_bytes,
        "manual_draft_allowed": False,
        "max_candidates": SEMANTIC_REVIEW_MAX_CANDIDATES,
        "network_calls": False,
        "ok": True,
        "public_output_approved": False,
        "candidate_item_field_names": [
            "candidate_id",
            "summary",
            "product_relation",
            "supportability",
            "supportability_basis",
            "kcs_item_status",
            "article_type_hint",
            "visibility_hint",
            "source_refs",
            "symptoms",
            "confirmed_facts",
            "open_questions",
            "supported_cause",
            "supported_resolution_or_workaround",
            "resolution_steps",
            "environment",
        ],
        "candidate_environment_field_names": [
            "applicable_to",
            "platform",
            "product",
        ],
        "candidate_plain_string_array_fields": [
            "source_refs",
            "symptoms",
            "confirmed_facts",
            "resolution_steps",
            "open_questions",
        ],
        "required_submit_shape": {
            "candidate_semantic_extraction": {
                "case_ref": semantic_review_ref,
                "extraction_source_ref": "semantic-review-submit-001",
                "items": [
                    {
                        "article_type_hint": "technical_scr",
                        "candidate_id": "candidate-001",
                        "confirmed_facts": [
                            "Plain string fact grounded in excerpt refs."
                        ],
                        "environment": {},
                        "kcs_item_status": "candidate_allowed",
                        "open_questions": [
                            "Plain string open question when evidence is unclear."
                        ],
                        "product_relation": "plesk_owned",
                        "resolution_steps": [
                            "Plain string executable step grounded in excerpt refs."
                        ],
                        "source_refs": ["excerpt-001"],
                        "summary": "",
                        "supportability": "supported",
                        "supportability_basis": "explicit_input_mention",
                        "supported_cause": "",
                        "supported_resolution_or_workaround": "",
                        "symptoms": [
                            "Plain string customer-visible symptom grounded "
                            "in excerpt refs."
                        ],
                        "visibility_hint": "public_customer_safe",
                    }
                ],
                "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
                "source_refs": [excerpt["source_ref"] for excerpt in excerpts],
            },
            "semantic_review_ref": semantic_review_ref,
        },
        "resolution_step_requirements": [
            "Use symptoms for issue discovery only: start with the customer's "
            "visible issue statement, then add only observed facts that narrow "
            "the issue to the supported cause. Do not put resolution outcomes "
            "such as 'CPU dropped after blocking traffic' in symptoms.",
            "Use candidate summary/title for the customer-visible problem, "
            "not for the fix. Do not include solution wording such as "
            "'mitigated with', 'fixed by', or 'resolved by' in summary/title.",
            "Each technical_scr candidate must include standalone executable "
            "resolution_steps.",
            "Use only actions and implementation details that are present in "
            "selected_excerpts. Do not fill missing commands, configuration "
            "content, rule bodies, or paths from general knowledge.",
            "Prefer command-level actions with command names and arguments "
            "when the excerpts provide them.",
            "When a step creates, edits, configures, enables, disables, or "
            "blocks a file, rule, filter, jail, service, port, or traffic, the "
            "step must include the exact command, exact configuration content, "
            "or an approved how-to link found in selected_excerpts.",
            "For multi-line configuration snippets, submit one resolution step "
            "as 'Describe the file/change: CONFIG_TEXT:' followed by the "
            "sanitized configuration lines from selected_excerpts. Do not use "
            "shell heredoc markers such as <<EOF in the semantic submission.",
            "Submit symptoms, confirmed_facts, resolution_steps, source_refs, "
            "and open_questions as arrays of plain strings only. Preserve "
            "resolution order by array order. Do not submit objects such as "
            "{order, action}, {text}, {label}, or nested step structures.",
            "Custom or risky mitigations such as custom filters, firewall "
            "rule changes, rate limits, or direct traffic blocks are allowed "
            "when selected_excerpts show they were the actual supported "
            "resolution. Include reviewer/public-vs-internal boundary and "
            "warning, backup, or rollback evidence only when selected_excerpts "
            "provide it; do not invent missing safety commands.",
            "Prefer a single linear main resolution path, but preserve staged "
            "or conditional mitigations when selected_excerpts show they were "
            "part of the actual ticket resolution.",
            "Use concrete ports, service names, rule names, and verification "
            "targets when they are present in selected_excerpts.",
            "Do not submit vague steps such as 'create a rule' or 'block the "
            "traffic' without the concrete action detail.",
            "Do not copy local workstation paths, reviewer-bundle paths, "
            "command output, or raw transcript text into the submission.",
            "Sanitized server configuration or log paths may be included only "
            "when needed for standalone executable resolution evidence.",
        ],
        "result_kind": "semantic_review_packet",
        "schema_version": SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION,
        "selected_excerpts": excerpts,
        "semantic_review_ref": semantic_review_ref,
        "submit_arguments": {"semantic_review_ref": semantic_review_ref},
        "submit_tool": "kcs_submit_semantic_review",
        "task": (
            "Identify atomic KCS item candidates only. Do not draft an "
            "article, choose a KCS action, or produce Zendesk HTML."
        ),
        "writes_files": False,
    }
    packet["semantic_review_packet_sha256"] = _packet_sha256(packet)
    ensure_safe_sanitized_payload(packet)
    return packet


def selected_semantic_review_excerpts(text: str) -> list[JsonDict]:
    """Select bounded high-signal excerpts from a clean ticket transcript."""

    selected: list[tuple[int, str, str]] = []
    segments = _segments(text)
    for role in ("reported_symptom", "supported_cause", "supported_resolution"):
        match = _best_segment_for_role(segments, role)
        if match is not None:
            selected.append(match)
    selected.extend(_top_fact_segments(segments))
    selected = _dedupe_selected(selected)
    selected.sort(key=lambda item: item[0])
    excerpts = _bounded_excerpts(selected)
    for excerpt in excerpts:
        ensure_safe_sanitized_payload(excerpt)
    return excerpts


def semantic_review_extraction_from_submission(
    *,
    pending: PendingSemanticReview,
    candidate_semantic_extraction: object,
) -> CandidateSemanticExtraction:
    """Validate Claude-proposed semantic extraction against prepared excerpts."""

    _ensure_bounded_submit_payload(candidate_semantic_extraction)
    _ensure_plain_string_submit_arrays(candidate_semantic_extraction)
    _ensure_no_forbidden_submit_values(candidate_semantic_extraction)
    ensure_safe_sanitized_payload(candidate_semantic_extraction)
    validation = validate_candidate_semantic_extraction(
        candidate_semantic_extraction
    )
    if not validation.ok:
        raise SemanticReviewError("semantic_review_submission_invalid")
    extraction = (
        candidate_semantic_extraction
        if isinstance(candidate_semantic_extraction, CandidateSemanticExtraction)
        else CandidateSemanticExtraction.from_json_dict(
            candidate_semantic_extraction
        )
    )
    if extraction.case_ref != pending.packet.get("case_ref"):
        raise SemanticReviewError("semantic_review_case_ref_invalid")
    _ensure_submit_candidate_count(extraction)
    _ensure_submit_source_refs(
        extraction,
        allowed_source_refs=set(pending.allowed_source_refs),
    )
    _ensure_bounded_submit_text(extraction.to_json_dict())
    return extraction


def _segments(text: str) -> list[tuple[int, str]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = [chunk.strip() for chunk in _BLANK_LINE_RE.split(normalized)]
    if len(chunks) < 3:
        chunks = [line.strip() for line in normalized.splitlines()]
    segments: list[tuple[int, str]] = []
    for index, chunk in enumerate(chunks):
        safe = _clean_segment(chunk)
        if safe:
            segments.append((index, safe))
    return segments


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


def _best_segment_for_role(
    segments: list[tuple[int, str]],
    role: str,
) -> tuple[int, str, str] | None:
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
    if not scored:
        return None
    score, index, text = max(scored, key=lambda item: (item[0], item[1]))
    if score <= 0:
        return None
    return (index, role, text)


def _top_fact_segments(segments: list[tuple[int, str]]) -> list[tuple[int, str, str]]:
    scored = [
        (_score_segment(text, _FACT_RE), index, text)
        for index, text in segments
        if _FACT_RE.search(text)
    ]
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [(index, "confirmed_fact", text) for _, index, text in scored[:4]]


def _score_segment(text: str, matcher: re.Pattern[str]) -> int:
    return len(matcher.findall(text)) * 100 + min(len(text), 500)


def _dedupe_selected(
    selected: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    seen: set[int] = set()
    deduped: list[tuple[int, str, str]] = []
    for index, role, text in selected:
        if index in seen:
            continue
        seen.add(index)
        deduped.append((index, role, text))
    return deduped


def _bounded_excerpts(selected: list[tuple[int, str, str]]) -> list[JsonDict]:
    excerpts: list[JsonDict] = []
    total_bytes = 0
    for _, role, text in selected:
        if len(excerpts) >= SEMANTIC_REVIEW_MAX_EXCERPTS:
            break
        text_bytes = len(text.encode("utf-8"))
        if total_bytes + text_bytes > SEMANTIC_REVIEW_MAX_TOTAL_BYTES:
            break
        source_ref = f"excerpt-{len(excerpts) + 1:03d}"
        excerpts.append({"role": role, "source_ref": source_ref, "text": text})
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


def _ensure_no_forbidden_submit_values(value: object) -> None:
    if isinstance(value, dict):
        _ensure_no_forbidden_submit_mapping(value)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_no_forbidden_submit_values(item)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_submit_string(value)


def _ensure_plain_string_submit_arrays(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SUBMIT_PLAIN_STRING_ARRAY_FIELDS and isinstance(item, list):
                if any(not isinstance(member, str) for member in item):
                    raise SemanticReviewError(
                        "semantic_review_plain_string_arrays_required"
                    )
            _ensure_plain_string_submit_arrays(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_plain_string_submit_arrays(item)


def _ensure_no_forbidden_submit_mapping(value: dict[object, object]) -> None:
    for key, item in value.items():
        if isinstance(key, str):
            compact_key = key.replace("_", "").replace("-", "").casefold()
            if compact_key in _SUBMIT_FORBIDDEN_COMPACT_KEYS:
                raise SemanticReviewError("semantic_review_submission_forbidden")
        _ensure_no_forbidden_submit_values(item)


def _ensure_no_forbidden_submit_string(value: str) -> None:
    html_checked_value = _SAFE_CONFIG_PLACEHOLDER_RE.sub("", value)
    if _SUBMIT_FORBIDDEN_TEXT_RE.search(html_checked_value):
        raise SemanticReviewError("semantic_review_submission_forbidden")
    if _submit_markdown_heading_forbidden(html_checked_value):
        raise SemanticReviewError("semantic_review_submission_forbidden")
    if _SUBMIT_FORBIDDEN_LOCAL_PATH_RE.search(value):
        raise SemanticReviewError("semantic_review_submission_forbidden")


def _submit_markdown_heading_forbidden(value: str) -> bool:
    matches = list(_SUBMIT_MARKDOWN_HEADING_RE.finditer(value))
    if not matches:
        return False
    if not _SUBMIT_CONFIG_TEXT_RE.search(value):
        return True
    return any(
        _SUBMIT_CONFIG_COMMENT_PATH_RE.fullmatch(match.group(0)) is None
        for match in matches
    )


def _ensure_submit_candidate_count(
    extraction: CandidateSemanticExtraction,
) -> None:
    if len(extraction.items) > SEMANTIC_REVIEW_MAX_CANDIDATES:
        raise SemanticReviewError("semantic_review_too_many_candidates")


def _ensure_submit_source_refs(
    extraction: CandidateSemanticExtraction,
    *,
    allowed_source_refs: set[str],
) -> None:
    if not set(extraction.source_refs).issubset(allowed_source_refs):
        raise SemanticReviewError("semantic_review_source_refs_invalid")
    for item in extraction.items:
        if not item.source_refs:
            raise SemanticReviewError("semantic_review_source_refs_invalid")
        if not set(item.source_refs).issubset(allowed_source_refs):
            raise SemanticReviewError("semantic_review_source_refs_invalid")


def _ensure_bounded_submit_text(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _ensure_bounded_submit_text(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_bounded_submit_text(item)
        return
    if (
        isinstance(value, str)
        and len(value.encode("utf-8")) > SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES
    ):
        raise SemanticReviewError("semantic_review_submission_too_large")


def _ensure_bounded_submit_payload(value: object) -> None:
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise SemanticReviewError("semantic_review_submission_invalid") from exc
    if len(payload.encode("utf-8")) > SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES:
        raise SemanticReviewError("semantic_review_submission_too_large")


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
    "SEMANTIC_REVIEW_MAX_TOTAL_BYTES",
    "SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION",
    "SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES",
    "SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES",
    "SemanticReviewError",
    "new_pending_semantic_review",
    "prepared_pending_semantic_review",
    "selected_semantic_review_excerpts",
    "semantic_review_extraction_from_submission",
    "semantic_review_packet",
]
