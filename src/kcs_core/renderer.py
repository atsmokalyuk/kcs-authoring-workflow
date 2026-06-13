"""Reviewer packet and Zendesk HTML rendering for KCS-4."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from html import escape
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    NormalizedTicketEvidencePacket,
    RecommendedAction,
)

_ARTICLE_HTML_ACTIONS = frozenset(
    {
        RecommendedAction.CREATE_CANDIDATE.value,
        RecommendedAction.UPDATE_EXISTING.value,
        RecommendedAction.FLAG_EXISTING.value,
    }
)
_TARGET_ARTICLE_ACTIONS = frozenset(
    {
        RecommendedAction.UPDATE_EXISTING.value,
        RecommendedAction.FLAG_EXISTING.value,
    }
)
_MAX_TITLE_LENGTH = 180
_MAX_LIST_ITEMS = 20
_MAX_LIST_ITEM_LENGTH = 600
_MAX_PARAGRAPH_LENGTH = 600
_MAX_HTML_LENGTH = 12_000
_MAX_METADATA_LENGTH = 180
_MAX_REPORT_CODE_LENGTH = 80
_PUBLIC_VISIBILITY_CLASS = "public_customer_safe"
_FLAG_EXISTING_WARNING = "flag_existing_requires_existing_article_review"
_SAFE_METADATA_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_:-]*")
_SAFE_METADATA_VALUE_RE = re.compile(r"[A-Za-z0-9_.:-]+")
_SAFE_REPORT_CODE_RE = re.compile(r"[a-z][a-z0-9_]*")
_PRIVATE_METADATA_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I),
    re.compile(
        r"\b[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,63}\b",
        re.I,
    ),
    re.compile(r"\b(?:PLSK|EXT)\.\d{8}\.\d{4}\b", re.I),
    re.compile(r"\b(?:ticket|zendesk|zd)[-_:]?\d{4,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)(?:[:=-])"
        r"[A-Za-z0-9_.:-]+",
        re.I,
    ),
    re.compile(r"\bauthorization:?bearer[A-Za-z0-9_.:-]+", re.I),
)
_PRIVATE_PUBLIC_TEXT_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.I),
    re.compile(
        r"\b(?!example\.(?:com|net|org)\b)"
        r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        r"(?:\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,63}\b",
        re.I,
    ),
    re.compile(r"\b(?:PLSK|EXT)\.\d{8}\.\d{4}\b", re.I),
    re.compile(r"\b(?:ticket|zendesk|zd)[-_ #:]?\d{4,}\b", re.I),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"(?:/Users/|/home/|/var/www/vhosts/|C:\\Users\\)", re.I),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+",
        re.I,
    ),
    re.compile(r"\bauthorization:\s*bearer\s+\S+", re.I),
)
_UNSAFE_METADATA_VALUE_FRAGMENTS = (
    "raw_ticket",
    "raw-zendesk",
    "raw_zendesk",
    "raw_internal",
    "internal_comment",
    "private_path",
    "credential",
    "api_key",
    "api-key",
    "token",
    "secret",
    "password",
    "passwd",
    "redaction_map",
)
_SAFE_REUSE_MATCH_FIELDS = (
    "match_ref",
    "article_type",
    "content_status",
    "publication_status",
)
_REQUIRED_REUSE_MATCH_FIELDS = frozenset(
    {
        "match_ref",
        "article_type",
        "content_status",
    }
)


def render_reviewer_packet(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
) -> KcsReviewerPacket:
    """Render the canonical reviewer packet for a KCS decision."""

    _ensure_decision_renderable(decision)
    candidate = _selected_candidate(evidence, decision)
    public_candidate = _public_article_candidate(evidence, decision, candidate)
    zendesk_html = _zendesk_html(public_candidate)
    _ensure_bounded_html(zendesk_html)
    return KcsReviewerPacket(
        case_ref=evidence.case_ref,
        recommended_action=decision.recommended_action,
        review_required=True,
        public_article_candidate=public_candidate,
        internal_reviewer_notes=_internal_reviewer_notes(candidate),
        evidence_basis=_safe_evidence_basis(decision.evidence_basis),
        validation_report=_validation_report(decision, zendesk_html),
        zendesk_source_html=zendesk_html,
        auto_publish_allowed=False,
    )


def _public_article_candidate(
    evidence: NormalizedTicketEvidencePacket,
    decision: KcsActionDecisionPacket,
    candidate: Mapping[str, Any],
) -> dict[str, object] | None:
    if decision.recommended_action not in _ARTICLE_HTML_ACTIONS:
        return None
    _ensure_public_renderable_visibility(evidence.visibility_summary)
    _ensure_candidate_public_solution_safe(candidate)
    article_type = _article_type(decision.article_type)
    if article_type == ArticleType.NONE:
        return None
    public_candidate: dict[str, object] = {
        "candidate_id": decision.candidate_id,
        "recommended_action": decision.recommended_action,
        "status": decision.status,
        "title": _title(candidate, article_type),
        "article_type": article_type.value,
        "applicable_to": _applicable_to(evidence.environment),
        "symptoms": _symptoms(evidence, candidate),
        "cause": _cause(evidence, candidate),
        "resolution_steps": _resolution_steps(evidence, candidate),
        "question": _question(candidate),
        "answer_steps": _answer_steps(evidence, candidate),
        "auto_publish_allowed": False,
    }
    _ensure_public_article_candidate_safe(public_candidate)
    return public_candidate


def _zendesk_html(public_candidate: Mapping[str, object] | None) -> str | None:
    if public_candidate is None:
        return None
    article_type = _article_type(_string(public_candidate.get("article_type")))
    if article_type == ArticleType.TECHNICAL_SCR:
        return _technical_scr_html(public_candidate)
    if article_type == ArticleType.HOWTO_QA:
        return _howto_qa_html(public_candidate)
    return None


def _ensure_decision_renderable(decision: KcsActionDecisionPacket) -> None:
    if decision.auto_publish_allowed is not False:
        raise ContractValidationError(
            "decision auto_publish_allowed must be false before rendering"
        )
    _safe_report_codes(decision.blockers, "blockers")
    _safe_evidence_basis(decision.evidence_basis)
    if decision.selected_reuse_match is not None:
        _safe_selected_reuse_match(decision.selected_reuse_match)
    if decision.recommended_action not in _ARTICLE_HTML_ACTIONS:
        return
    _ensure_article_decision_renderable(decision)


def _ensure_article_decision_renderable(decision: KcsActionDecisionPacket) -> None:
    if decision.status != DecisionStatus.DECISION_READY.value:
        raise ContractValidationError(
            "article rendering requires decision_ready status"
        )
    if decision.blockers:
        raise ContractValidationError(
            "article rendering requires empty decision blockers"
        )
    if decision.article_type == ArticleType.NONE.value:
        raise ContractValidationError(
            "article rendering requires an article type"
        )
    if decision.split_items:
        raise ContractValidationError(
            "article rendering requires a single selected candidate"
        )
    if decision.recommended_action in _TARGET_ARTICLE_ACTIONS:
        _safe_selected_reuse_match(decision.selected_reuse_match)


def _technical_scr_html(candidate: Mapping[str, object]) -> str:
    lines = [_h1(_string(candidate.get("title")))]
    lines.extend(_applicable_to_html(_string_list(candidate.get("applicable_to"))))
    lines.append("<h2>Symptoms</h2>")
    lines.extend(_ordered_list(_string_list(candidate.get("symptoms"))))
    cause = _string(candidate.get("cause"))
    if cause:
        lines.append("<h2>Cause</h2>")
        lines.append(_paragraph(cause, "cause"))
    lines.append("<h2>Resolution</h2>")
    lines.append('<div class="resolution">')
    lines.extend(_ordered_list(_string_list(candidate.get("resolution_steps")), 2))
    lines.append("</div>")
    return "\n".join(lines)


def _howto_qa_html(candidate: Mapping[str, object]) -> str:
    lines = [_h1(_string(candidate.get("title")))]
    lines.extend(_applicable_to_html(_string_list(candidate.get("applicable_to"))))
    lines.append("<h2>Question</h2>")
    lines.append(_paragraph(_string(candidate.get("question")), "question"))
    lines.append("<h2>Answer</h2>")
    answer_steps = _string_list(candidate.get("answer_steps"))
    if len(answer_steps) > 1:
        lines.extend(_ordered_list(answer_steps))
    elif answer_steps:
        lines.append(_paragraph(answer_steps[0], "answer"))
    else:
        lines.append("<p></p>")
    return "\n".join(lines)


def _h1(value: str) -> str:
    _ensure_text_bound("title", value, _MAX_TITLE_LENGTH)
    return f"<h1>{escape(value)}</h1>"


def _paragraph(value: str, field_name: str) -> str:
    _ensure_text_bound(field_name, value, _MAX_PARAGRAPH_LENGTH)
    return f"<p>{escape(value)}</p>"


def _applicable_to_html(values: list[str]) -> list[str]:
    if not values:
        return []
    return ["<h2>Applicable to</h2>", *_unordered_list(values)]


def _ordered_list(values: list[str], indent: int = 0) -> list[str]:
    _ensure_list_bound(values)
    prefix = " " * indent
    lines = [f"{prefix}<ol>"]
    lines.extend(f"{prefix}  <li>{escape(value)}</li>" for value in values)
    lines.append(f"{prefix}</ol>")
    return lines


def _unordered_list(values: list[str]) -> list[str]:
    _ensure_list_bound(values)
    return ["<ul>", *[f"  <li>{escape(value)}</li>" for value in values], "</ul>"]


def _ensure_list_bound(values: list[str]) -> None:
    if len(values) > _MAX_LIST_ITEMS:
        raise ContractValidationError("renderer list item count exceeds bound")
    for value in values:
        _ensure_text_bound("list item", value, _MAX_LIST_ITEM_LENGTH)


def _ensure_text_bound(field_name: str, value: str, max_length: int) -> None:
    if len(value) > max_length:
        raise ContractValidationError(f"renderer {field_name} exceeds bound")


def _ensure_bounded_html(zendesk_html: str | None) -> None:
    if zendesk_html is not None and len(zendesk_html) > _MAX_HTML_LENGTH:
        raise ContractValidationError("renderer HTML exceeds bound")


def _validation_report(
    decision: KcsActionDecisionPacket, zendesk_html: str | None
) -> dict[str, object]:
    warnings = _safe_report_codes(
        _renderer_warnings(decision, zendesk_html), "warnings"
    )
    return {
        "schema_version": "kcs_renderer_validation_report_v1",
        "renderer_status": _renderer_status(decision, zendesk_html),
        "checks": _renderer_checks(decision, zendesk_html),
        "blockers": _safe_report_codes(decision.blockers, "blockers"),
        "warnings": warnings,
        "selected_reuse_match": _validation_reuse_match(decision),
    }


def _renderer_status(
    decision: KcsActionDecisionPacket, zendesk_html: str | None
) -> str:
    if decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value:
        return "split_required"
    if (
        zendesk_html is not None
        and decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    ):
        return "flag_existing_review_required"
    if zendesk_html is not None:
        return "zendesk_html_generated"
    if decision.recommended_action in _ARTICLE_HTML_ACTIONS:
        return "zendesk_html_not_generated"
    return "no_public_article_output"


def _renderer_checks(
    decision: KcsActionDecisionPacket, zendesk_html: str | None
) -> list[str]:
    checks = [
        "auto_publish_allowed_false",
        "review_required_true",
        "safe_metadata_checked",
    ]
    if zendesk_html is None:
        checks.append("no_public_article_output")
        return checks
    checks.extend(
        [
            "decision_ready_checked",
            "empty_blockers_checked",
            "candidate_id_checked",
            "public_visibility_checked",
            "public_solution_safe_checked",
            "html_escaped",
            "html_bounded",
            "internal_notes_separated",
        ]
    )
    if decision.recommended_action in _TARGET_ARTICLE_ACTIONS:
        checks.append("selected_reuse_match_checked")
    return checks


def _renderer_warnings(
    decision: KcsActionDecisionPacket, zendesk_html: str | None
) -> list[str]:
    if (
        zendesk_html is not None
        and decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    ):
        return [_FLAG_EXISTING_WARNING]
    return []


def _validation_reuse_match(
    decision: KcsActionDecisionPacket,
) -> dict[str, str] | None:
    if decision.selected_reuse_match is None:
        return None
    return _safe_selected_reuse_match(decision.selected_reuse_match)


def _selected_candidate(
    evidence: NormalizedTicketEvidencePacket, decision: KcsActionDecisionPacket
) -> Mapping[str, Any]:
    for candidate in evidence.issue_candidates:
        if _string(candidate.get("candidate_id")) == decision.candidate_id:
            return candidate
    if decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value:
        return {}
    if decision.recommended_action not in _ARTICLE_HTML_ACTIONS:
        return {}
    raise ContractValidationError(
        "decision candidate_id must match an evidence issue candidate"
    )


def _ensure_public_renderable_visibility(summary: Mapping[str, Any]) -> None:
    classes = _visibility_classes(summary)
    if classes != (_PUBLIC_VISIBILITY_CLASS,):
        raise ContractValidationError(
            "public article rendering requires public_customer_safe visibility"
        )


def _ensure_candidate_public_solution_safe(candidate: Mapping[str, Any]) -> None:
    if candidate.get("public_solution_safe") is not True:
        raise ContractValidationError(
            "public article rendering requires public_solution_safe candidate"
        )


def _ensure_public_article_candidate_safe(
    public_candidate: Mapping[str, object],
) -> None:
    for value in _public_article_text_values(public_candidate):
        if _contains_private_public_text(value):
            raise ContractValidationError(
                "public article candidate contains unsafe value"
            )
    _ensure_safe_metadata_text(_string(public_candidate.get("candidate_id")))


def _public_article_text_values(
    public_candidate: Mapping[str, object],
) -> tuple[str, ...]:
    return (
        _string(public_candidate.get("title")),
        _string(public_candidate.get("cause")),
        _string(public_candidate.get("question")),
        *_string_list(public_candidate.get("applicable_to")),
        *_string_list(public_candidate.get("symptoms")),
        *_string_list(public_candidate.get("resolution_steps")),
        *_string_list(public_candidate.get("answer_steps")),
    )


def _contains_private_public_text(value: str) -> bool:
    return bool(value) and any(
        pattern.search(value) for pattern in _PRIVATE_PUBLIC_TEXT_PATTERNS
    )


def _visibility_classes(summary: Mapping[str, Any]) -> tuple[str, ...]:
    value = summary.get("classes", summary.get("visibility_classes"))
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list | tuple) and all(isinstance(item, str) for item in value):
        return tuple(value)
    visibility = summary.get("visibility")
    if isinstance(visibility, str):
        return (visibility,)
    return ()


def _safe_evidence_basis(evidence_basis: Mapping[str, Any]) -> dict[str, object]:
    _ensure_safe_metadata(evidence_basis)
    return dict(evidence_basis)


def _safe_report_codes(values: Iterable[str], field_name: str) -> list[str]:
    safe_values: list[str] = []
    for value in values:
        if (
            not isinstance(value, str)
            or len(value) > _MAX_REPORT_CODE_LENGTH
            or not _SAFE_REPORT_CODE_RE.fullmatch(value)
        ):
            raise ContractValidationError(f"renderer {field_name} contains unsafe code")
        safe_values.append(value)
    return safe_values


def _safe_selected_reuse_match(
    selected_reuse_match: Mapping[str, Any] | None,
) -> dict[str, str]:
    if selected_reuse_match is None:
        raise ContractValidationError(
            "selected reuse match is required for existing article rendering"
        )
    safe_match: dict[str, str] = {}
    for field_name in _SAFE_REUSE_MATCH_FIELDS:
        value = _string(selected_reuse_match.get(field_name))
        if value:
            _ensure_safe_metadata_text(value)
            safe_match[field_name] = value
    if not _REQUIRED_REUSE_MATCH_FIELDS.issubset(safe_match):
        raise ContractValidationError("selected reuse match metadata is incomplete")
    return safe_match


def _ensure_safe_metadata(value: object) -> None:
    if isinstance(value, str):
        _ensure_safe_metadata_text(value)
        return
    if isinstance(value, Mapping):
        _ensure_safe_metadata_mapping(value)
        return
    if isinstance(value, list | tuple):
        _ensure_safe_metadata_sequence(value)
        return
    if _is_safe_metadata_scalar(value):
        return
    raise ContractValidationError("renderer metadata must be JSON-safe")


def _ensure_safe_metadata_mapping(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("renderer metadata key contains unsafe value")
        _ensure_safe_metadata_key(key)
        _ensure_safe_metadata(item)


def _ensure_safe_metadata_sequence(value: Iterable[object]) -> None:
    for item in value:
        _ensure_safe_metadata(item)


def _is_safe_metadata_scalar(value: object) -> bool:
    return value is None or isinstance(value, bool)


def _ensure_safe_metadata_text(value: str) -> None:
    if (
        not value
        or len(value) > _MAX_METADATA_LENGTH
        or not _SAFE_METADATA_VALUE_RE.fullmatch(value)
        or _contains_private_metadata_value(value)
    ):
        raise ContractValidationError("renderer metadata contains unsafe value")


def _ensure_safe_metadata_key(value: str) -> None:
    if (
        not value
        or len(value) > _MAX_METADATA_LENGTH
        or not _SAFE_METADATA_KEY_RE.fullmatch(value)
        or _contains_private_metadata_value(value)
    ):
        raise ContractValidationError("renderer metadata key contains unsafe value")


def _contains_private_metadata_value(value: str) -> bool:
    normalized = value.casefold()
    return any(
        fragment in normalized for fragment in _UNSAFE_METADATA_VALUE_FRAGMENTS
    ) or any(pattern.search(value) for pattern in _PRIVATE_METADATA_PATTERNS)


def _article_type(value: str) -> ArticleType:
    try:
        return ArticleType(value)
    except ValueError:
        return ArticleType.NONE


def _title(candidate: Mapping[str, Any], article_type: ArticleType) -> str:
    for key in ("title", "summary", "question"):
        value = _string(candidate.get(key))
        if value:
            return value
    if article_type == ArticleType.HOWTO_QA:
        return "How-to article candidate"
    return "KCS article candidate"


def _applicable_to(environment: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("product", "platform", "component", "version"):
        value = _string(environment.get(key))
        if value:
            values.append(value)
    return values


def _symptoms(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> list[str]:
    return _candidate_list(candidate, "symptoms") or _candidate_list(
        candidate, "summary"
    ) or list(evidence.symptoms)


def _cause(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> str:
    return _string(candidate.get("supported_cause")) or (
        evidence.supported_cause or ""
    )


def _resolution_steps(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> list[str]:
    return (
        _candidate_list(candidate, "resolution_steps")
        or _candidate_list(candidate, "supported_resolution_or_workaround")
        or _candidate_list(candidate, "supported_answer")
        or _string_as_list(evidence.supported_resolution_or_workaround)
    )


def _answer_steps(
    evidence: NormalizedTicketEvidencePacket, candidate: Mapping[str, Any]
) -> list[str]:
    return (
        _candidate_list(candidate, "answer_steps")
        or _candidate_list(candidate, "supported_answer")
        or _resolution_steps(evidence, candidate)
    )


def _question(candidate: Mapping[str, Any]) -> str:
    return _string(candidate.get("question")) or _string(candidate.get("summary"))


def _internal_reviewer_notes(candidate: Mapping[str, Any]) -> list[str]:
    return _candidate_list(candidate, "internal_reviewer_notes")


def _candidate_list(candidate: Mapping[str, Any], key: str) -> list[str]:
    return _string_list(candidate.get(key))


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return _string_as_list(value)
    if isinstance(value, list | tuple) and all(isinstance(item, str) for item in value):
        return [item for item in value if item.strip()]
    return []


def _string_as_list(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _string(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""
