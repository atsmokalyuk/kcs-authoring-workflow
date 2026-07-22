"""Controlled semantic-review state and packet helpers for Desktop."""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256

from kcs_adapters.desktop_semantic_review_submission import (
    SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES,
    SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES,
    SemanticReviewSubmissionError,
    validated_semantic_review_submission,
)
from kcs_adapters.desktop_semantic_review_submission import (
    ensure_no_forbidden_submit_values as _submission_ensure_no_forbidden_values,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    CandidateSemanticExtraction,
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
        ticket_ref=ticket_ref,
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
            "question",
            "supported_cause",
            "supported_answer",
            "supported_resolution_or_workaround",
            "resolution_steps",
            "answer_steps",
            "environment",
        ],
        "candidate_environment_field_names": [
            "applicable_to",
            "platform",
            "product",
        ],
        "candidate_count_policy": (
            "Return every separately searchable KCS item candidate visible in "
            "selected_excerpts, up to max_candidates. Do not choose the first "
            "candidate yourself. If selected_excerpts contain two unrelated "
            "customer-visible issues, submit two items in one "
            "candidate_semantic_extraction_v1 payload. Also include supported "
            "routing or ownership answers, such as licensing or account issues "
            "redirected to Customer Success or a licensing team, even when "
            "they should not become a new technical draft. Python will return "
            "the operator choice request and a per-item outcome ledger."
        ),
        "excerpt_coverage_policy": (
            "Every allowed_source_ref from selected_excerpts must be cited by "
            "at least one submitted item. If an excerpt is not draftable, still "
            "submit a no_article or blocked_need_more_evidence item for it so "
            "Python can include it in the outcome ledger. Do not silently omit "
            "a selected excerpt."
        ),
        "candidate_plain_string_array_fields": [
            "source_refs",
            "symptoms",
            "confirmed_facts",
            "resolution_steps",
            "answer_steps",
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
        "howto_qa_submit_item_shape": {
            "article_type_hint": "howto_qa",
            "answer_steps": [
                "Plain string answer step grounded in excerpt refs.",
            ],
            "candidate_id": "candidate-002",
            "confirmed_facts": [
                "Plain string fact grounded in excerpt refs.",
            ],
            "environment": {},
            "kcs_item_status": "candidate_allowed",
            "open_questions": [
                "Plain string open question when evidence is unclear.",
            ],
            "product_relation": "plesk_owned",
            "question": "Plain string customer question grounded in excerpt refs.",
            "resolution_steps": [
                "Plain string answer step grounded in excerpt refs.",
            ],
            "source_refs": ["excerpt-001"],
            "summary": "Short customer-visible question or task.",
            "supportability": "supported",
            "supportability_basis": "explicit_input_mention",
            "supported_answer": (
                "Plain string supported answer grounded in excerpt refs."
            ),
            "symptoms": [],
            "visibility_hint": "public_customer_safe",
        },
        "resolution_step_requirements": [
            "Use article_type_hint='technical_scr' only when selected_excerpts "
            "contain a confirmed supported_cause. If the item is a task, "
            "question, contact route, verification step, setting check, or "
            "supported answer without a confirmed root cause, use "
            "article_type_hint='howto_qa' instead.",
            "If the candidate is primarily procedural, such as 'How to ...' "
            "or a command usage question, and selected_excerpts do not provide "
            "a relevant customer-visible error/failure plus confirmed cause, "
            "submit it as howto_qa. Do not invent supported_cause only to "
            "force a task article into technical_scr.",
            "For howto_qa candidates, populate question and supported_answer. "
            "Use answer_steps for ordered actions when the excerpts provide "
            "them; resolution_steps may mirror answer_steps for compatibility.",
            "For howto_qa summary/title/question, preserve the customer's "
            "original action and visible error wording so the article remains "
            "findable by customer words. Do not replace 'create an account to "
            "manage a licence shows an email does not exist / message "
            "considered spam error' with a generic routing title such as "
            "'Who handles licensing questions'. Put routing or ownership "
            "answers, including Customer Success or licensing team handoff, in "
            "supported_answer / answer_steps instead.",
            "Keep howto_qa summary/title brief but descriptive. Put the full "
            "customer wording and visible error details in question; do not "
            "make the title a long sentence with every example/error clause.",
            "Do not omit a separately searchable question only because its "
            "answer is a support route, ownership boundary, or licensing/team "
            "handoff. Submit it as howto_qa when it is a reusable supported "
            "answer, or mark it no_article / blocked_need_more_evidence when "
            "it should be reported in the item outcome ledger but not drafted.",
            "Cover every allowed_source_ref from selected_excerpts. If a "
            "source excerpt is not a draftable KCS item, cite it in a "
            "no_article or blocked_need_more_evidence item rather than "
            "omitting it.",
            "Do not invent a root cause only to make a howto_qa candidate fit "
            "technical_scr.",
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
            "Use environment only for normalized product/platform metadata: "
            "product may be 'Plesk'; platform may be 'Linux', 'Windows', "
            "'Plesk for Linux', or 'Plesk for Windows'; applicable_to may "
            "contain only 'Plesk for Linux' or 'Plesk for Windows'. Put IPv4, "
            "IPv6, ports, services, and log paths in confirmed_facts or "
            "resolution_steps when excerpt-grounded, not in environment.",
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
            "article, choose a KCS action, choose a candidate yourself, or "
            "produce Zendesk HTML."
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
    selected.extend(_top_question_task_segments(segments))
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

    try:
        return validated_semantic_review_submission(
            allowed_source_refs=set(pending.allowed_source_refs),
            candidate_semantic_extraction=candidate_semantic_extraction,
            expected_case_ref=pending.packet.get("case_ref"),
            max_candidates=SEMANTIC_REVIEW_MAX_CANDIDATES,
        )
    except SemanticReviewSubmissionError as exc:
        raise SemanticReviewError(exc.debug_code) from exc


def _ensure_no_forbidden_submit_values(value: object) -> None:
    """Compatibility shim for frozen tests; implementation lives in submit owner."""

    try:
        _submission_ensure_no_forbidden_values(value)
    except SemanticReviewSubmissionError as exc:
        raise SemanticReviewError(exc.debug_code) from exc


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


def _score_segment(text: str, matcher: re.Pattern[str]) -> int:
    return len(matcher.findall(text)) * 100 + min(len(text), 500)


def _dedupe_selected(
    selected: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]]:
    seen: set[int] = set()
    seen_text: set[str] = set()
    deduped: list[tuple[int, str, str]] = []
    for index, role, text in selected:
        text_key = _WHITESPACE_RE.sub(" ", text).casefold()
        if index in seen or text_key in seen_text:
            continue
        seen.add(index)
        seen_text.add(text_key)
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
        excerpt = {"role": role, "source_ref": source_ref, "text": text}
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
