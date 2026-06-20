"""Controlled semantic-review state and packet helpers for Desktop."""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256

from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION

SEMANTIC_REVIEW_PACKET_SCHEMA_VERSION = "kcs_semantic_review_packet_v1"
SEMANTIC_REVIEW_REF_BYTES = 12
SEMANTIC_REVIEW_MAX_EXCERPTS = 10
SEMANTIC_REVIEW_MAX_EXCERPT_BYTES = 8000
SEMANTIC_REVIEW_MAX_TOTAL_BYTES = 64000
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
    packet: JsonDict
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
        expires_at=time.monotonic() + ttl_seconds,
        packet=packet,
        semantic_review_ref=semantic_review_ref,
        ticket_ref=ticket_ref,
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
        "case_ref": f"semantic-review-{ticket_ref}",
        "excerpt_count": len(excerpts),
        "excerpt_total_bytes": excerpt_total_bytes,
        "manual_draft_allowed": False,
        "max_candidates": SEMANTIC_REVIEW_MAX_CANDIDATES,
        "network_calls": False,
        "ok": True,
        "public_output_approved": False,
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
        "ticket_ref": ticket_ref,
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
    "SemanticReviewError",
    "new_pending_semantic_review",
    "selected_semantic_review_excerpts",
    "semantic_review_packet",
]
