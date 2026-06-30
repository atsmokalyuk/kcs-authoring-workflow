"""Desktop reviewer-only draft preview, quality, and reference coverage helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from kcs_adapters.desktop_workflow_status import approved_summary_reuse_was_checked
from kcs_adapters.zendesk_markup_quality import review_reviewer_only_html
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType, KcsReviewerPacket, RecommendedAction
from kcs_core.sanitizer import ensure_safe_sanitized_payload

_EXISTING_KB_AS_RESOLUTION_RE = re.compile(
    r"\b(?:open|use|follow|refer\s+to|apply)\b[^.?!\n]{0,180}"
    r"https://support\.plesk\.com/hc/en-us/articles/[A-Za-z0-9_-]+|"
    r"https://support\.plesk\.com/hc/en-us/articles/[A-Za-z0-9_-]+"
    r"[^.?!\n]{0,180}\b(?:apply|documented\s+fix|existing\s+(?:kb|knowledge\s+base))\b",
    re.I,
)


def approved_summary_reviewer_only_draft(execution: Any) -> JsonDict:
    """Return compact reviewer-only draft sections for Desktop output."""

    candidate = approved_summary_public_candidate(execution.reviewer_packet)
    source_candidate = approved_summary_source_candidate(execution)
    resolution_steps = safe_candidate_list(candidate, "resolution_steps")
    return {
        "applicable_to": approved_summary_applicable_to(candidate),
        "cause": safe_candidate_string(candidate, "cause"),
        "resolution": safe_candidate_string(
            source_candidate, "supported_resolution_or_workaround"
        )
        or safe_candidate_string(source_candidate, "supported_answer")
        or safe_candidate_string(candidate, "resolution")
        or " ".join(resolution_steps),
        "resolution_steps": resolution_steps,
        "status": "reviewer_only",
        "symptoms": safe_candidate_list(candidate, "symptoms"),
        "title": safe_candidate_string(candidate, "title"),
    }


def approved_summary_reviewer_only_html(execution: Any) -> str:
    """Return reviewer-only Zendesk HTML from the reviewer packet."""

    html = execution.reviewer_packet.zendesk_source_html
    if not isinstance(html, str):
        return ""
    return html


def approved_summary_reviewer_only_preview(draft: Mapping[str, Any]) -> JsonDict:
    """Return structured preview fields for a reviewer-only draft."""

    return {
        "applicable_to": safe_candidate_list(draft, "applicable_to"),
        "cause": safe_candidate_string(draft, "cause"),
        "resolution": safe_candidate_string(draft, "resolution"),
        "resolution_steps": safe_candidate_list(draft, "resolution_steps"),
        "status": safe_candidate_string(draft, "status"),
        "symptoms": safe_candidate_list(draft, "symptoms"),
        "title": safe_candidate_string(draft, "title"),
    }


def approved_summary_reviewer_only_preview_text(
    draft: Mapping[str, Any],
) -> str:
    """Return plain-text reviewer preview for a reviewer-only draft."""

    preview = approved_summary_reviewer_only_preview(draft)
    lines = [
        f"Title: {preview['title']}",
        f"Status: {preview['status']}",
        "",
        "Applicable to:",
        *numbered_or_bulleted_lines(preview["applicable_to"], bullet="-"),
        "",
        "Symptoms:",
        *numbered_or_bulleted_lines(preview["symptoms"], bullet="1."),
        "",
        "Cause:",
        str(preview["cause"]),
        "",
        "Resolution:",
        str(preview["resolution"]),
        "",
        "Resolution steps:",
        *numbered_or_bulleted_lines(preview["resolution_steps"], bullet="1."),
    ]
    return "\n".join(line for line in lines if line is not None).strip()


def numbered_or_bulleted_lines(values: object, *, bullet: str) -> list[str]:
    """Return simple preview lines for list-like values."""

    if not isinstance(values, list) or not values:
        return ["-"]
    if bullet == "1.":
        return [f"{index}. {value}" for index, value in enumerate(values, start=1)]
    return [f"{bullet} {value}" for value in values]


def approved_summary_quality_gaps(
    execution: Any,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Return adapter-facing quality gaps for reviewer-only Desktop output."""

    gaps: list[JsonDict] = []
    is_howto = execution.decision.article_type == ArticleType.HOWTO_QA.value
    if not safe_candidate_list(draft, "applicable_to"):
        gaps.append({"kind": "missing_applicable_to", "severity": "blocker"})
    if not safe_candidate_list(draft, "symptoms"):
        gaps.append({"kind": "missing_symptoms", "severity": "blocker"})
    if not is_howto and not safe_candidate_string(draft, "cause"):
        gaps.append({"kind": "missing_cause", "severity": "blocker"})
    if not safe_candidate_string(draft, "resolution"):
        gaps.append({"kind": "missing_resolution", "severity": "blocker"})
    reference_text = approved_summary_reference_text(execution.arguments)
    if reference_text is None:
        gaps.append({"kind": "reference_not_provided", "severity": "info"})
    else:
        gaps.extend(approved_summary_reference_section_gaps(reference_text, draft))
    gaps.extend(
        approved_summary_existing_article_resolution_gaps_for_execution(
            execution, draft
        )
    )
    if not approved_summary_reuse_was_checked(execution.arguments):
        gaps.append({"kind": "reuse_search_skipped", "severity": "warning"})
    gaps.extend(approved_summary_html_quality_gaps(execution))
    return gaps


def approved_summary_existing_article_resolution_gaps(
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Block new drafts that delegate the fix to an existing KB article."""

    resolution_text = "\n".join(
        [
            safe_candidate_string(draft, "resolution"),
            *safe_candidate_list(draft, "resolution_steps"),
        ]
    )
    if not _EXISTING_KB_AS_RESOLUTION_RE.search(resolution_text):
        return []
    return [
        {
            "kind": "resolution_delegates_to_existing_kb_article",
            "severity": "blocker",
        }
    ]


def approved_summary_existing_article_resolution_gaps_for_execution(
    execution: Any,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Return existing-KB delegation gaps only for new article candidates."""

    if (
        execution.decision.recommended_action
        != RecommendedAction.CREATE_CANDIDATE.value
    ):
        return []
    return approved_summary_existing_article_resolution_gaps(draft)


def approved_summary_html_quality_gaps(execution: Any) -> list[JsonDict]:
    """Return quality gaps from reviewer-only Zendesk HTML."""

    return review_reviewer_only_html(
        approved_summary_reviewer_only_html(execution),
        require_resolution_container=(
            execution.decision.article_type == ArticleType.TECHNICAL_SCR.value
        ),
    )


def approved_summary_reference_text(arguments: Mapping[str, Any]) -> str | None:
    """Return optional safe reference article text from authoring arguments."""

    reference_keys = (
        "reference_article",
        "reference_article_text",
        "reference_article_html",
    )
    for key in reference_keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            ensure_safe_sanitized_payload(value)
            return value.strip()
    return None


def approved_summary_reference_section_gaps(
    reference_text: str,
    draft: Mapping[str, Any],
) -> list[JsonDict]:
    """Return reference section coverage warnings for reviewer-only drafts."""

    gaps: list[JsonDict] = []
    reference = reference_text.casefold()
    section_checks = (
        (
            "applicable_to",
            "applicable to",
            safe_candidate_list(draft, "applicable_to"),
        ),
        ("symptoms", "symptoms", safe_candidate_list(draft, "symptoms")),
        ("cause", "cause", [safe_candidate_string(draft, "cause")]),
        ("resolution", "resolution", [safe_candidate_string(draft, "resolution")]),
    )
    for kind, marker, values in section_checks:
        if marker in reference and not any(values):
            gaps.append(
                {
                    "kind": f"reference_section_missing_{kind}",
                    "severity": "warning",
                }
            )
    if not gaps:
        gaps.append({"kind": "reference_section_coverage_ok", "severity": "info"})
    return gaps


def approved_summary_open_questions(execution: Any) -> list[str]:
    """Return safe open questions from the public candidate."""

    candidate = approved_summary_public_candidate(execution.reviewer_packet)
    return safe_candidate_list(candidate, "open_questions")


def approved_summary_public_candidate(packet: KcsReviewerPacket) -> JsonDict:
    """Return public article candidate as a JSON dict."""

    candidate = packet.public_article_candidate
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def approved_summary_applicable_to(candidate: Mapping[str, Any]) -> list[str]:
    """Return public Applicable To values, excluding internal refs."""

    values = safe_candidate_list(candidate, "applicable_to")
    return [
        value
        for value in values
        if not value.casefold().startswith("approved-summary-")
    ]


def approved_summary_source_candidate(execution: Any) -> JsonDict:
    """Return the source issue candidate from the approved-summary payload."""

    candidates = execution.payload.get("issue_candidates")
    if not isinstance(candidates, list) or not candidates:
        return {}
    candidate = candidates[0]
    if not isinstance(candidate, Mapping):
        return {}
    return dict(candidate)


def safe_candidate_string(candidate: Mapping[str, Any], key: str) -> str:
    """Return a string candidate field or empty string."""

    value = candidate.get(key)
    if isinstance(value, str):
        return value
    return ""


def safe_candidate_list(candidate: Mapping[str, Any], key: str) -> list[str]:
    """Return a normalized string list candidate field."""

    value = candidate.get(key)
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


__all__ = [
    "approved_summary_applicable_to",
    "approved_summary_html_quality_gaps",
    "approved_summary_existing_article_resolution_gaps",
    "approved_summary_existing_article_resolution_gaps_for_execution",
    "approved_summary_open_questions",
    "approved_summary_public_candidate",
    "approved_summary_quality_gaps",
    "approved_summary_reference_section_gaps",
    "approved_summary_reference_text",
    "approved_summary_reviewer_only_draft",
    "approved_summary_reviewer_only_html",
    "approved_summary_reviewer_only_preview",
    "approved_summary_reviewer_only_preview_text",
    "approved_summary_source_candidate",
    "numbered_or_bulleted_lines",
    "safe_candidate_list",
    "safe_candidate_string",
]
