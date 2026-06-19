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
    re.compile(r"(?:/Users/|/home/|C:\\Users\\)", re.I),
    re.compile(
        r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+",
        re.I,
    ),
    re.compile(r"\bauthorization:\s*bearer\s+\S+", re.I),
)
_SAFE_PUBLIC_TEXT_FILENAME_RE = re.compile(
    r"\b[A-Za-z0-9][A-Za-z0-9_-]*\."
    r"(?:conf|ini|cnf|yaml|yml|json|xml|php|log|pid|bak|backup|disabled|orig|old)"
    r"(?:\.(?:bak|backup|disabled|orig|old))?\b"
)
_INLINE_CODE_PATH_RE = re.compile(
    r"(?<![\w<])/(?:etc|usr|var|opt|root|tmp)/[A-Za-z0-9_./%:+-]+"
)
_INLINE_CODE_TOKEN_RE = re.compile(r"\b(?:DataDir|sw-collectd)\b")
_INLINE_CODE_COMMAND_RE = re.compile(
    r"\bRun\s+"
    r"(?P<command>"
    r"[A-Za-z0-9_./%-]+"
    r"(?:\s+(?:"
    r"-[A-Za-z0-9_.-]+|"
    r"/[A-Za-z0-9_./%:+-]+|"
    r"(?!(?:to|and|then)\b)[A-Za-z0-9_.:%=+-]+"
    r")){0,12}"
    r")"
    r"(?=(?:\s+to\b|\.|,|$))",
    re.I,
)
_SYSTEMCTL_RESTART_RE = re.compile(
    r"^systemctl\s+restart\s+(?P<service>[A-Za-z0-9_.@-]+)$",
    re.I,
)
_RUN_COMMAND_DESCRIPTION_SPLIT_RE = re.compile(r"\s+to\s+", re.I)
_PLESK_SSH_RESOLUTION_STEP = "Connect to the Plesk server via SSH."
_PLESK_SSH_RESOLUTION_URL = (
    "https://support.plesk.com/hc/en-us/articles/"
    "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH"
)
_PLESK_RDP_RESOLUTION_STEP = "Connect to the Plesk server via RDP."
_PLESK_RDP_RESOLUTION_URL = (
    "https://support.plesk.com/hc/en-us/articles/"
    "12377247797271-How-to-connect-to-a-Plesk-server-via-RDP-with-available-credentials"
)
_PLESK_SSH_STEP_RE = re.compile(r"\b(?:connect|log in).{0,80}\bssh\b", re.I)
_PLESK_RDP_STEP_RE = re.compile(r"\b(?:connect|log in).{0,80}\brdp\b", re.I)
_WINDOWS_SERVER_STEP_RE = re.compile(
    r"\b(?:powershell|cmd|iisreset|reg|sc|net|dir|plesk)\b|"
    r"[A-Z]:\\|%plesk_dir%|%plesk_bin%|program files",
    re.I,
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
    lines.extend(_resolution_ordered_list(_string_list(candidate.get("resolution_steps"))))
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
    return f"<p>{_inline_markup(value)}</p>"


def _applicable_to_html(values: list[str]) -> list[str]:
    if not values:
        return []
    return ["<h2>Applicable to</h2>", *_unordered_list(values)]


def _ordered_list(values: list[str], indent: int = 0) -> list[str]:
    _ensure_list_bound(values)
    prefix = " " * indent
    lines = [f"{prefix}<ol>"]
    lines.extend(f"{prefix}  {_ordered_list_item(value)}" for value in values)
    lines.append(f"{prefix}</ol>")
    return lines


def _resolution_ordered_list(values: list[str]) -> list[str]:
    _ensure_list_bound(values)
    lines = ["  <ol>"]
    for value in values:
        lines.extend(_resolution_ordered_list_item(value))
    lines.append("  </ol>")
    return lines


def _ordered_list_item(value: str) -> str:
    if value == _PLESK_SSH_RESOLUTION_STEP:
        return (
            "<li>"
            f'<a href="{_PLESK_SSH_RESOLUTION_URL}">{escape(value)}</a>'
            "</li>"
        )
    if value == _PLESK_RDP_RESOLUTION_STEP:
        return (
            "<li>"
            f'<a href="{_PLESK_RDP_RESOLUTION_URL}">{escape(value)}</a>'
            "</li>"
        )
    return f"<li>{_inline_markup(value)}</li>"


def _resolution_ordered_list_item(value: str) -> list[str]:
    linked = _linked_resolution_list_item(value)
    if linked is not None:
        return [f"    {linked}"]
    command_step = _run_command_step(value)
    if command_step is None:
        return [f"    {_ordered_list_item(value)}"]
    description, command = command_step
    return [
        "    <li>",
        f"      <p>{_inline_markup(description)}</p>",
        f"      <p><code># {escape(command)}</code></p>",
        "    </li>",
    ]


def _linked_resolution_list_item(value: str) -> str | None:
    if value == _PLESK_SSH_RESOLUTION_STEP:
        return (
            "<li>"
            f'<a href="{_PLESK_SSH_RESOLUTION_URL}">{escape(value)}</a>'
            "</li>"
        )
    if value == _PLESK_RDP_RESOLUTION_STEP:
        return (
            "<li>"
            f'<a href="{_PLESK_RDP_RESOLUTION_URL}">{escape(value)}</a>'
            "</li>"
        )
    return None


def _run_command_step(value: str) -> tuple[str, str] | None:
    text = value.strip()
    if not text.casefold().startswith("run "):
        return None
    command_text = text[4:].strip().rstrip(".")
    if not command_text:
        return None
    parts = _RUN_COMMAND_DESCRIPTION_SPLIT_RE.split(command_text, maxsplit=1)
    command = parts[0].strip()
    description_source = parts[1].strip() if len(parts) == 2 else None
    if not command:
        return None
    description = _command_step_description(command, description_source)
    return description, command


def _command_step_description(command: str, description: str | None) -> str:
    if description:
        return f"{_sentence_case(description.strip().rstrip('.'))}:"
    restart_match = _SYSTEMCTL_RESTART_RE.fullmatch(command)
    if restart_match is not None:
        return f"Restart {restart_match.group('service')}:"
    return "Run the following command:"


def _sentence_case(value: str) -> str:
    if not value:
        return value
    return value[0].upper() + value[1:]


def _unordered_list(values: list[str]) -> list[str]:
    _ensure_list_bound(values)
    return [
        "<ul>",
        *[f"  <li>{_inline_markup(value)}</li>" for value in values],
        "</ul>",
    ]


def _inline_markup(value: str) -> str:
    spans = _inline_code_spans(value)
    if not spans:
        return escape(value)
    parts: list[str] = []
    position = 0
    for start, end in spans:
        if start > position:
            parts.append(escape(value[position:start]))
        parts.append(f"<code>{escape(value[start:end])}</code>")
        position = end
    if position < len(value):
        parts.append(escape(value[position:]))
    return "".join(parts)


def _inline_code_spans(value: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _INLINE_CODE_COMMAND_RE.finditer(value):
        spans.append(_trim_inline_code_span(value, match.span("command")))
    for pattern in (_INLINE_CODE_PATH_RE, _INLINE_CODE_TOKEN_RE):
        for match in pattern.finditer(value):
            span = _trim_inline_code_span(value, match.span())
            if _span_overlaps(span, spans):
                continue
            spans.append(span)
    return sorted(spans)


def _trim_inline_code_span(value: str, span: tuple[int, int]) -> tuple[int, int]:
    start, end = span
    while end > start and value[end - 1] in ".,;:":
        end -= 1
    return start, end


def _span_overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(
        start < existing_end and end > existing_start
        for existing_start, existing_end in spans
    )


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
    text_without_safe_filenames = _SAFE_PUBLIC_TEXT_FILENAME_RE.sub("", value)
    return bool(text_without_safe_filenames) and any(
        pattern.search(text_without_safe_filenames)
        for pattern in _PRIVATE_PUBLIC_TEXT_PATTERNS
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
    environment_text = _environment_text_from_mapping(environment)
    if "plesk" in environment_text:
        platform = _plesk_platform(environment_text)
        if platform:
            version = _string(environment.get("version"))
            return [_plesk_applicable_to_label(platform=platform, version=version)]
    values: list[str] = []
    for key in ("product", "platform", "component", "version"):
        value = _string(environment.get(key))
        if value:
            values.extend(_applicable_to_values(value))
    return values


def _applicable_to_values(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
    values = parts or [value]
    return [_clean_applicable_to_value(item) for item in values]


def _clean_applicable_to_value(value: str) -> str:
    return value.strip().strip("[]").strip().strip("\"'")


def _plesk_platform(environment_text: str) -> str:
    if _looks_windows_environment(environment_text):
        return "Windows"
    if _looks_linux_environment(environment_text):
        return "Linux"
    return ""


def _plesk_applicable_to_label(*, platform: str, version: str) -> str:
    clean_version = _clean_applicable_to_value(version)
    if clean_version:
        if "plesk" in clean_version.casefold():
            return f"{clean_version} for {platform}"
        return f"Plesk {clean_version} for {platform}"
    return f"Plesk for {platform}"


def _environment_text_from_mapping(environment: Mapping[str, Any]) -> str:
    return " ".join(
        _string(value)
        for value in environment.values()
        if isinstance(value, str)
    ).casefold()


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
    steps = (
        _candidate_list(candidate, "resolution_steps")
        or _candidate_list(candidate, "supported_resolution_or_workaround")
        or _candidate_list(candidate, "supported_answer")
        or _string_as_list(evidence.supported_resolution_or_workaround)
    )
    return _resolution_steps_with_required_entry_point(evidence, steps)


def _resolution_steps_with_required_entry_point(
    evidence: NormalizedTicketEvidencePacket, steps: list[str]
) -> list[str]:
    if not steps:
        return steps
    if _is_windows_plesk_resolution(evidence, steps):
        if any(_PLESK_RDP_STEP_RE.search(step) for step in steps):
            return steps
        return [_PLESK_RDP_RESOLUTION_STEP, *steps]
    if not _is_linux_plesk_resolution(evidence):
        return steps
    if any(_PLESK_SSH_STEP_RE.search(step) for step in steps):
        return steps
    return [_PLESK_SSH_RESOLUTION_STEP, *steps]


def _is_linux_plesk_resolution(evidence: NormalizedTicketEvidencePacket) -> bool:
    environment_values = _environment_text(evidence)
    return "plesk" in environment_values and _looks_linux_environment(
        environment_values
    )


def _is_windows_plesk_resolution(
    evidence: NormalizedTicketEvidencePacket, steps: list[str]
) -> bool:
    environment_values = _environment_text(evidence)
    if "plesk" not in environment_values or not _looks_windows_environment(
        environment_values
    ):
        return False
    return any(_WINDOWS_SERVER_STEP_RE.search(step) for step in steps)


def _looks_linux_environment(value: str) -> bool:
    return any(
        marker in value
        for marker in (
            "linux",
            "rpm-based",
            "rpm based",
            "centos",
            "alma",
            "almalinux",
            "rhel",
            "red hat",
            "debian",
            "ubuntu",
            "sw-collectd",
            "systemctl",
            "/etc/",
        )
    )


def _looks_windows_environment(value: str) -> bool:
    return "windows" in value


def _environment_text(evidence: NormalizedTicketEvidencePacket) -> str:
    return _environment_text_from_mapping(evidence.environment)


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
