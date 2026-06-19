"""Local Zendesk HTML quality checks for reviewer-only KCS drafts."""

from __future__ import annotations

import re
from html import unescape

from kcs_core.json_payload import JsonDict

_HTML_CAUSE_SECTION_RE = re.compile(
    r"<h2>\s*Cause\s*</h2>(?P<body>.*?)(?=<h2\b|$)",
    re.I | re.S,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_CAUSE_RESOLUTION_ACTION_RE = re.compile(
    r"\b(?:back\s+up|backup|remove|restart|run\s+|fix(?:es|ed|ing)?|"
    r"resolv(?:e|es|ed|ing)|workaround|solution|mitigat(?:e|ion))\b",
    re.I,
)
_TRANSCRIPT_PLACEHOLDER_RE = re.compile(
    r"\{\{[A-Z_]+_\d+\}\}|(?:PERSON_NAME|SHELL_USERHOST|EMAIL|IP_ADDRESS)_\d+",
    re.I,
)


def review_reviewer_only_html(source_html: str) -> list[JsonDict]:
    """Return low-noise blocker-style quality gaps for Zendesk reviewer HTML."""

    cause = _html_section_text(source_html, section="cause")
    gaps: list[JsonDict] = []
    if cause:
        if len(cause.split()) > 90:
            gaps.append({"kind": "cause_too_wordy", "severity": "blocker"})
        if _CAUSE_RESOLUTION_ACTION_RE.search(cause):
            gaps.append(
                {"kind": "cause_contains_resolution_action", "severity": "blocker"}
            )
    if _TRANSCRIPT_PLACEHOLDER_RE.search(_strip_html_text(source_html)):
        gaps.append(
            {
                "kind": "transcript_placeholder_in_public_body",
                "severity": "blocker",
            }
        )
    return gaps


def _html_section_text(html: str, *, section: str) -> str:
    if section != "cause":
        return ""
    match = _HTML_CAUSE_SECTION_RE.search(html)
    if match is None:
        return ""
    return _strip_html_text(match.group("body"))


def _strip_html_text(html: str) -> str:
    return " ".join(unescape(_HTML_TAG_RE.sub(" ", html)).split())
