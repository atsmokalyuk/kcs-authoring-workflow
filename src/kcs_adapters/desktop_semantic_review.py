"""Controlled semantic-review state and packet helpers for Desktop."""

from __future__ import annotations

import json
import re
import secrets
import time
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

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
_SUBMIT_FORBIDDEN_TEXT_RE = re.compile(r"```", re.I | re.M)
_SUBMIT_FORBIDDEN_HTML_TAG_RE = re.compile(
    r"</?\s*(?:"
    r"a|blockquote|body|br|code|div|em|h[1-6]|html|iframe|img|li|ol|p|pre|"
    r"script|span|strong|style|table|tbody|td|th|thead|tr|ul"
    r")(?:\s|/?>)",
    re.I | re.M,
)
_SUBMIT_MARKDOWN_BLOCKQUOTE_RE = re.compile(r"^\s*>\s+\S.*$", re.M)
_SUBMIT_MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S.*$", re.M)
_SUBMIT_CONFIG_TEXT_RE = re.compile(r"\bCONFIG_TEXT:", re.I)
_SUBMIT_CONFIG_COMMENT_PATH_RE = re.compile(
    r"^\s*#{1,6}\s+/[A-Za-z0-9_./:-]+", re.M
)
_SUBMIT_SHELL_PROMPT_COMMAND_RE = re.compile(
    r"^\s*#\s+[a-z0-9_./-]+(?:\s|$)", re.M
)
_SAFE_CONFIG_PLACEHOLDER_RE = re.compile(
    r"<(?:"
    r"DOMAIN|EMAIL|HOST|HOSTNAME|IP|IPV4|IPV6|PERSON_NAME|SERVER|URL|USER|"
    r"domain|email|host|hostname|ip|ipv4|ipv6|server|url|user"
    r")>",
    re.I,
)
_SUBMIT_FORBIDDEN_LOCAL_PATH_RE = re.compile(
    r"(?:file://|~[/\\]|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\[^\\\s]+\\[^\\\s]+|"
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
_SUBMIT_ALLOWED_PLATFORM_VALUES = frozenset(
    {
        "Linux",
        "Plesk for Linux",
        "Plesk for Windows",
        "Windows",
    }
)
_SUBMIT_ALLOWED_PRODUCT_VALUES = frozenset({"Plesk"})
_SUBMIT_ALLOWED_APPLICABLE_TO_VALUES = frozenset(
    {
        "Plesk for Linux",
        "Plesk for Windows",
    }
)
_SEMANTIC_CONTRACT_DEBUG_CODE_RULES = (
    ("unsupported semantic article_type_hint", "semantic_review_article_type_invalid"),
    (
        "unsupported semantic product_relation",
        "semantic_review_product_relation_invalid",
    ),
    (
        "semantic extraction product relation invalid",
        "semantic_review_product_relation_invalid",
    ),
    (
        "unsupported semantic supportability_basis",
        "semantic_review_supportability_basis_invalid",
    ),
    ("unsupported semantic supportability", "semantic_review_supportability_invalid"),
    ("unsupported semantic kcs_item_status", "semantic_review_item_status_invalid"),
    ("unsupported semantic visibility_hint", "semantic_review_visibility_hint_invalid"),
    ("unsupported semantic eol_role", "semantic_review_eol_role_invalid"),
    ("semantic item environment invalid", "semantic_review_environment_invalid"),
    ("semantic extraction requires items", "semantic_review_items_missing"),
    (
        "semantic extraction source refs invalid",
        "semantic_review_top_level_source_refs_missing",
    ),
    ("source_refs", "semantic_review_source_refs_invalid"),
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

    _ensure_bounded_submit_payload(candidate_semantic_extraction)
    _ensure_plain_string_submit_arrays(candidate_semantic_extraction)
    _ensure_no_forbidden_submit_values(candidate_semantic_extraction)
    shape_debug_code = _semantic_extraction_shape_debug_code(
        candidate_semantic_extraction
    )
    if shape_debug_code is not None:
        raise SemanticReviewError(shape_debug_code)
    ensure_safe_sanitized_payload(candidate_semantic_extraction)
    try:
        extraction = (
            candidate_semantic_extraction
            if isinstance(candidate_semantic_extraction, CandidateSemanticExtraction)
            else CandidateSemanticExtraction.from_json_dict(
                candidate_semantic_extraction
            )
        )
    except ContractValidationError as exc:
        raise SemanticReviewError(
            _semantic_contract_debug_code(str(exc))
        ) from exc
    if extraction.case_ref != pending.packet.get("case_ref"):
        raise SemanticReviewError("semantic_review_case_ref_invalid")
    _ensure_submit_environment_values(extraction)
    _ensure_submit_candidate_count(extraction)
    _ensure_submit_source_refs(
        extraction,
        allowed_source_refs=set(pending.allowed_source_refs),
    )
    _ensure_submit_excerpt_coverage(
        extraction,
        required_source_refs=set(pending.allowed_source_refs),
    )
    _ensure_bounded_submit_text(extraction.to_json_dict())
    return extraction


def _semantic_contract_debug_code(message: str) -> str:
    normalized = message.casefold()
    for needle, debug_code in _SEMANTIC_CONTRACT_DEBUG_CODE_RULES:
        if needle in normalized:
            return debug_code
    return "semantic_review_submission_invalid"


def _semantic_extraction_shape_debug_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return "semantic_review_submit_payload_not_object"
    debug_code = _semantic_extraction_top_level_debug_code(value)
    if debug_code is not None:
        return debug_code
    items = value["items"]
    if not isinstance(items, list) or not items:
        return "semantic_review_items_missing"
    for item in items:
        item_debug_code = _semantic_item_shape_debug_code(item)
        if item_debug_code is not None:
            return item_debug_code
    return None


def _semantic_extraction_top_level_debug_code(
    value: dict[object, object],
) -> str | None:
    allowed_top_level = {
        "case_ref",
        "extraction_source_ref",
        "items",
        "schema_version",
        "source_refs",
    }
    if not set(value).issubset(allowed_top_level):
        return "semantic_review_forbidden_field"
    if value.get("schema_version") != CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION:
        return "semantic_review_schema_version_invalid"
    if not isinstance(value.get("case_ref"), str):
        return "semantic_review_case_ref_missing"
    if not isinstance(value.get("extraction_source_ref"), str):
        return "semantic_review_extraction_source_ref_missing"
    if not _is_plain_string_list(value.get("source_refs")):
        return "semantic_review_top_level_source_refs_missing"
    return None


def _semantic_item_shape_debug_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return "semantic_review_item_invalid"
    allowed_item = {
        "article_type_hint",
        "answer_steps",
        "candidate_id",
        "confirmed_facts",
        "eol_role",
        "environment",
        "item_type_hint",
        "kcs_item_status",
        "open_questions",
        "product_relation",
        "question",
        "resolution_steps",
        "source_refs",
        "summary",
        "supportability",
        "supportability_basis",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "visibility_hint",
    }
    if not set(value).issubset(allowed_item):
        return "semantic_review_forbidden_field"
    required_strings = (
        "candidate_id",
        "kcs_item_status",
        "product_relation",
        "summary",
        "supportability",
    )
    if any(not isinstance(value.get(field), str) for field in required_strings):
        return "semantic_review_item_required_field_missing"
    if not _is_plain_string_list(value.get("source_refs")):
        return "semantic_review_item_source_refs_missing"
    return None


def _is_plain_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) for item in value
    )


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
                raise SemanticReviewError("semantic_review_forbidden_field")
        _ensure_no_forbidden_submit_values(item)


def _ensure_no_forbidden_submit_string(value: str) -> None:
    html_checked_value = _SAFE_CONFIG_PLACEHOLDER_RE.sub("", value)
    if _SUBMIT_FORBIDDEN_TEXT_RE.search(html_checked_value):
        raise SemanticReviewError("semantic_review_forbidden_html_or_markdown")
    if _SUBMIT_FORBIDDEN_HTML_TAG_RE.search(html_checked_value):
        raise SemanticReviewError("semantic_review_forbidden_html_or_markdown")
    if _submit_markdown_heading_forbidden(html_checked_value):
        raise SemanticReviewError("semantic_review_forbidden_html_or_markdown")
    if _submit_markdown_blockquote_forbidden(html_checked_value):
        raise SemanticReviewError("semantic_review_forbidden_html_or_markdown")
    if _SUBMIT_FORBIDDEN_LOCAL_PATH_RE.search(value):
        raise SemanticReviewError("semantic_review_local_ref_blocked")


def _submit_markdown_heading_forbidden(value: str) -> bool:
    matches = list(_SUBMIT_MARKDOWN_HEADING_RE.finditer(value))
    if not matches:
        return False
    if not _SUBMIT_CONFIG_TEXT_RE.search(value):
        return any(
            _SUBMIT_SHELL_PROMPT_COMMAND_RE.fullmatch(match.group(0)) is None
            for match in matches
        )
    return any(
        _SUBMIT_CONFIG_COMMENT_PATH_RE.fullmatch(match.group(0)) is None
        and _SUBMIT_SHELL_PROMPT_COMMAND_RE.fullmatch(match.group(0)) is None
        for match in matches
    )


def _submit_markdown_blockquote_forbidden(value: str) -> bool:
    """Reject Markdown blockquotes without blocking GUI breadcrumbs."""

    return bool(_SUBMIT_MARKDOWN_BLOCKQUOTE_RE.search(value))


def _ensure_submit_candidate_count(
    extraction: CandidateSemanticExtraction,
) -> None:
    if len(extraction.items) > SEMANTIC_REVIEW_MAX_CANDIDATES:
        raise SemanticReviewError("semantic_review_too_many_candidates")


def _ensure_submit_environment_values(
    extraction: CandidateSemanticExtraction,
) -> None:
    for item in extraction.items:
        environment = item.environment
        if not environment:
            continue
        if not isinstance(environment, dict):
            raise SemanticReviewError("semantic_review_environment_invalid")
        _ensure_optional_allowed_environment_text(
            environment.get("platform"),
            allowed_values=_SUBMIT_ALLOWED_PLATFORM_VALUES,
        )
        _ensure_optional_allowed_environment_text(
            environment.get("product"),
            allowed_values=_SUBMIT_ALLOWED_PRODUCT_VALUES,
        )
        applicable_to = environment.get("applicable_to")
        if applicable_to is None:
            continue
        values = [applicable_to] if isinstance(applicable_to, str) else applicable_to
        if not isinstance(values, list) or not values:
            raise SemanticReviewError("semantic_review_environment_invalid")
        for value in values:
            _ensure_optional_allowed_environment_text(
                value,
                allowed_values=_SUBMIT_ALLOWED_APPLICABLE_TO_VALUES,
            )


def _ensure_optional_allowed_environment_text(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> None:
    if value is None:
        return
    if not isinstance(value, str) or value not in allowed_values:
        raise SemanticReviewError("semantic_review_environment_invalid")


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


def _ensure_submit_excerpt_coverage(
    extraction: CandidateSemanticExtraction,
    *,
    required_source_refs: set[str],
) -> None:
    covered_source_refs: set[str] = set()
    for item in extraction.items:
        covered_source_refs.update(item.source_refs)
    if not required_source_refs.issubset(covered_source_refs):
        raise SemanticReviewError("semantic_review_excerpt_coverage_incomplete")


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
