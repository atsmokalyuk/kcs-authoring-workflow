"""Deterministic checks for reviewer-only Zendesk KCS source HTML.

This module mirrors the proven `plesk_support` shape: collect local findings in
small rule groups, expose a typed report for tests/review, and keep the Desktop
workflow adapter contract as compact `quality_gaps`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Literal

from kcs_core.json_payload import JsonDict

KCS_ZENDESK_MARKUP_QUALITY_REPORT_SCHEMA_VERSION = (
    "kcs-zendesk-markup-quality-report-v1"
)
PLESK_SSH_HOWTO_URL = (
    "https://support.plesk.com/hc/en-us/articles/"
    "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH"
)

FindingSeverity = Literal["blocker", "warning", "info"]

_HTML_TITLE_RE = re.compile(r"<h1\b[^>]*>(?P<body>.*?)</h1>", re.I | re.S)
_HTML_FULL_ARTICLE_SECTION_RE = re.compile(
    r"<h2\b[^>]*>\s*(?:applicable\s+to|symptoms|cause|resolution)\s*</h2>",
    re.I,
)
_HTML_APPLICABLE_TO_RE = re.compile(
    r"<h2\b[^>]*>\s*applicable\s+to\s*</h2>",
    re.I,
)
_HTML_ISSUE_SECTION_RE = re.compile(r"<h2\b[^>]*>\s*issue\s*</h2>", re.I)
_HTML_ENVIRONMENT_SECTION_RE = re.compile(
    r"<h2\b[^>]*>\s*environment\s*</h2>",
    re.I,
)
_HTML_RESOLUTION_CONTAINER_RE = re.compile(
    r"<div\s+class=[\"']resolution[\"']\s*>",
    re.I,
)
_HTML_SECTION_TEMPLATE = (
    r"<h2\b[^>]*>\s*{name}\s*</h2>(?P<body>.*?)(?=<h2\b|$)"
)
_HTML_ORDERED_LIST_START_RE = re.compile(r"^\s*<ol\b", re.I)
_HTML_RESOLUTION_LIST_ITEM_RE = re.compile(
    r"<li\b[^>]*>(?P<body>.*?)</li>",
    re.I | re.S,
)
_HTML_STEP_HEADING_RE = re.compile(r"<h[1-6]\b[^>]*>\s*step\s+\d+\b", re.I)
_HTML_STEP_TEXT_RE = re.compile(r"^\s*(?:\d+\.\s+)?step\s+\d+\b", re.I | re.M)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PLESK_OBSIDIAN_VERSION_RE = re.compile(
    r"\bplesk\s+obsidian\s+(?P<version>\d+(?:\.\d+){2,3})\b",
    re.I,
)
_DOC_RANGE_PREFIXES = ("192.0.2.", "198.51.100.", "203.0.113.")
_PRIVATE_FRAGMENTS = (
    "ticket.txt",
    "ticket.redacted.md",
    "ticket.final.clean.md",
    ".private/",
    "/users/",
    "/home/customer",
    "authorization: bearer",
)
_TRANSCRIPT_PLACEHOLDER_RE = re.compile(
    r"\{\{[A-Z_]+_\d+\}\}|(?:PERSON_NAME|SHELL_USERHOST|EMAIL|IP_ADDRESS)_\d+",
    re.I,
)
_DIAGNOSTIC_TRANSCRIPT_RE = re.compile(
    r"(?:"
    r"\bdrwx|"
    r"\blogger=|"
    r"\blevel=|"
    r"\bmsg=|"
    r"plugin process exited|"
    r"\[.*?\]\#|"
    r"\bls\s+-|"
    r"\bstat\s+-c\b|"
    r"\bgetenforce\b|"
    r"\bps\s+aux\b|"
    r"\btest server\b|"
    r"\bclient server\b"
    r")",
    re.I,
)
_CAUSE_RESOLUTION_ACTION_RE = re.compile(
    r"\b(?:back\s+up|backup|remove|restart|run\s+|fix(?:es|ed|ing)?|"
    r"resolv(?:e|es|ed|ing)|workaround|solution|mitigat(?:e|ion))\b",
    re.I,
)
_CAUSE_CHAIN_MARKER_RE = re.compile(
    r"\b(?:because|does\s+not\s+match|before|after|therefore|so|"
    r"result(?:s|ing)?\s+in|lead(?:s|ing)?\s+to)\b",
    re.I,
)
_ACCESS_NEEDED_RE = re.compile(
    r"\b(?:systemctl|/etc/|/var/log/|plesk\s+bin|plesk\s+repair)\b",
    re.I,
)
_ESSENTIAL_STEP_RE = re.compile(
    r"\b(?:connect\s+to\s+the\s+plesk\s+server\s+via\s+ssh|"
    r"connect\s+to\s+the\s+plesk\s+server\s+via\s+rdp|"
    r"connect\s+to\s+the\s+server\s+via\s+ssh|"
    r"connect\s+to\s+the\s+server\s+via\s+rdp|"
    r"log\s+in\s+to\s+plesk)\b",
    re.I,
)
_CONNECT_TO_SSH_RE = re.compile(
    r"\bconnect\s+to\s+(?:the\s+)?(?:plesk\s+)?server\s+via\s+ssh\b",
    re.I,
)
_CONFIG_PATH_RE = re.compile(r"(/etc/[A-Za-z0-9_./-]+\.conf)\b")


@dataclass(frozen=True)
class KcsZendeskMarkupFinding:
    """One deterministic markup-quality finding."""

    rule_id: str
    severity: FindingSeverity
    message: str

    def to_quality_gap(self) -> JsonDict:
        return {"kind": self.rule_id, "severity": self.severity}


@dataclass(frozen=True)
class KcsZendeskMarkupQualityReport:
    """Quality report for reviewer-only Zendesk source."""

    schema_version: str
    ok: bool
    findings: tuple[KcsZendeskMarkupFinding, ...]

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "ok": self.ok,
            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity,
                    "message": finding.message,
                }
                for finding in self.findings
            ],
        }


def review_kcs_zendesk_markup_source(
    source_html: str,
    *,
    require_resolution_container: bool = True,
) -> KcsZendeskMarkupQualityReport:
    """Review Zendesk KCS source HTML against low-noise deterministic rules."""

    findings: list[KcsZendeskMarkupFinding] = []
    findings.extend(
        _shape_findings(
            source_html,
            require_resolution_container=require_resolution_container,
        )
    )
    findings.extend(_completeness_findings(source_html))
    findings.extend(_technical_resolution_findings(source_html))
    findings.extend(_cause_findings(source_html))
    findings.extend(_transcript_findings(source_html))
    findings.extend(_privacy_findings(source_html))
    return KcsZendeskMarkupQualityReport(
        schema_version=KCS_ZENDESK_MARKUP_QUALITY_REPORT_SCHEMA_VERSION,
        ok=not any(finding.severity == "blocker" for finding in findings),
        findings=tuple(findings),
    )


def review_reviewer_only_html(
    source_html: str,
    *,
    require_resolution_container: bool = True,
) -> list[JsonDict]:
    """Return adapter-facing quality gaps for reviewer-only KCS drafts."""

    report = review_kcs_zendesk_markup_source(
        source_html,
        require_resolution_container=require_resolution_container,
    )
    return [finding.to_quality_gap() for finding in report.findings]


def _shape_findings(
    source_html: str,
    *,
    require_resolution_container: bool,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    findings.extend(_section_shape_findings(source_html))
    findings.extend(
        _resolution_shape_findings(
            source_html,
            require_resolution_container=require_resolution_container,
        )
    )
    return tuple(findings)


def _section_shape_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    if _HTML_FULL_ARTICLE_SECTION_RE.search(source_html) and not _HTML_TITLE_RE.search(
        source_html
    ):
        findings.append(
            _finding(
                "source_title_missing",
                "blocker",
                "Full Zendesk source needs a specific <h1> title.",
            )
        )
    if _HTML_ISSUE_SECTION_RE.search(source_html):
        findings.append(
            _finding(
                "issue_section_used_instead_of_symptoms",
                "blocker",
                "Technical SCR articles must use Symptoms, not Issue.",
            )
        )
    if _HTML_ENVIRONMENT_SECTION_RE.search(source_html):
        findings.append(
            _finding(
                "environment_section_used_instead_of_applicable_to",
                "blocker",
                "Public article body should use Applicable to.",
            )
        )
    if _HTML_FULL_ARTICLE_SECTION_RE.search(
        source_html
    ) and not _HTML_APPLICABLE_TO_RE.search(source_html):
        findings.append(
            _finding(
                "applicable_to_section_missing",
                "blocker",
                "Full public article source should include Applicable to.",
            )
        )
    symptoms_body = _section_body(source_html, "symptoms")
    if symptoms_body and not _HTML_ORDERED_LIST_START_RE.search(symptoms_body):
        findings.append(
            _finding(
                "symptoms_not_numbered_list",
                "blocker",
                "Technical SCR Symptoms should use a numbered <ol> list.",
            )
        )
    return tuple(findings)


def _resolution_shape_findings(
    source_html: str,
    *,
    require_resolution_container: bool,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    if _HTML_STEP_HEADING_RE.search(source_html) or _HTML_STEP_TEXT_RE.search(
        _strip_html_text(source_html)
    ):
        findings.append(
            _finding(
                "resolution_step_word_prefix",
                "blocker",
                "Resolution steps should use plain numbering without Step labels.",
            )
        )
    if require_resolution_container and not _HTML_RESOLUTION_CONTAINER_RE.search(
        source_html
    ):
        findings.append(
            _finding(
                "resolution_container_missing",
                "blocker",
                'Resolution source must include <div class="resolution">.',
            )
        )
    return tuple(findings)


def _completeness_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    plain = _strip_html_text(source_html)
    findings: list[KcsZendeskMarkupFinding] = []
    if _ACCESS_NEEDED_RE.search(plain) and not _ESSENTIAL_STEP_RE.search(plain):
        findings.append(
            _finding(
                "resolution_missing_initial_access_step",
                "warning",
                "Resolution should start with SSH/RDP/Plesk access when needed.",
            )
        )
    if _CONNECT_TO_SSH_RE.search(plain) and _ssh_html_link_missing(source_html):
        findings.append(
            _finding(
                "resolution_ssh_howto_link_missing",
                "warning",
                "SSH access steps should link to the canonical Plesk SSH how-to.",
            )
        )
    return tuple(findings)


def _technical_resolution_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    resolution = _section_text(source_html, "resolution")
    findings: list[KcsZendeskMarkupFinding] = []
    if _file_action_commands_missing(resolution):
        findings.append(
            _finding(
                "resolution_missing_concrete_file_commands",
                "blocker",
                "File backup/disable/remove steps must include concrete commands "
                "for the referenced file.",
            )
        )
    if _service_restart_command_missing(resolution):
        findings.append(
            _finding(
                "resolution_missing_concrete_service_restart_command",
                "blocker",
                "Service restart steps must include the concrete restart command.",
            )
        )
    return tuple(findings)


def _cause_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    cause_body = _section_body(source_html, "cause")
    if not cause_body:
        return ()
    cause_plain = _strip_html_text(cause_body)
    paragraph_count = len(re.findall(r"<p\b[^>]*>", cause_body, flags=re.I))
    findings: list[KcsZendeskMarkupFinding] = []
    if len(cause_plain.split()) > 90 or paragraph_count > 2:
        findings.append(
            _finding(
                "cause_too_wordy",
                "blocker",
                "Cause should contain only necessary supported cause data.",
            )
        )
    if _CAUSE_RESOLUTION_ACTION_RE.search(cause_plain):
        findings.append(
            _finding(
                "cause_contains_resolution_action",
                "blocker",
                "Cause must not contain fix or resolution wording.",
            )
        )
    if paragraph_count > 1 and _CAUSE_CHAIN_MARKER_RE.search(cause_plain):
        findings.append(
            _finding(
                "cause_complex_not_chain_form",
                "blocker",
                "Complex causes should be a concise cause-to-consequence chain.",
            )
        )
    return tuple(findings)


def _transcript_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    plain = _strip_html_text(source_html)
    findings: list[KcsZendeskMarkupFinding] = []
    resolution = _section_text(source_html, "resolution")
    if resolution and _DIAGNOSTIC_TRANSCRIPT_RE.search(resolution):
        findings.append(
            _finding(
                "diagnostic_transcript_in_resolution",
                "blocker",
                "Resolution must not contain raw diagnostic transcript lines.",
            )
        )
    if _TRANSCRIPT_PLACEHOLDER_RE.search(plain):
        findings.append(
            _finding(
                "transcript_placeholder_in_public_body",
                "blocker",
                "Public article body must not contain transcript placeholders.",
            )
        )
    return tuple(findings)


def _privacy_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    lower = source_html.casefold()
    plain = _strip_html_text(source_html)
    allowed_version_spans = {
        match.span("version") for match in _PLESK_OBSIDIAN_VERSION_RE.finditer(plain)
    }
    findings: list[KcsZendeskMarkupFinding] = []
    for fragment in _PRIVATE_FRAGMENTS:
        if fragment in lower:
            findings.append(
                _finding(
                    "private_fragment_present",
                    "blocker",
                    f"Forbidden private fragment found: {fragment}",
                )
            )
    if _EMAIL_RE.search(source_html):
        findings.append(
            _finding("private_email_present", "blocker", "Email-like identifier found.")
        )
    for match in _IPV4_RE.finditer(plain):
        value = match.group(0)
        if (
            not value.startswith(_DOC_RANGE_PREFIXES)
            and match.span() not in allowed_version_spans
        ):
            findings.append(
                _finding(
                    "private_ipv4_present",
                    "blocker",
                    "Non-documentation IPv4 found.",
                )
            )
            break
    return tuple(findings)


def _title_text(source_html: str) -> str:
    match = _HTML_TITLE_RE.search(source_html)
    if match is None:
        return ""
    return _strip_html_text(match.group("body"))


def _section_body(source_html: str, section_name: str) -> str:
    pattern = re.compile(
        _HTML_SECTION_TEMPLATE.format(name=re.escape(section_name)),
        re.I | re.S,
    )
    match = pattern.search(source_html)
    return "" if match is None else match.group("body")


def _section_text(source_html: str, section_name: str) -> str:
    return _strip_html_text(_section_body(source_html, section_name))


def _strip_html_text(html: str) -> str:
    return " ".join(unescape(_HTML_TAG_RE.sub(" ", html)).split())


def _file_action_commands_missing(resolution: str) -> bool:
    paths = _CONFIG_PATH_RE.findall(resolution)
    if not paths:
        return False
    lowered = resolution.casefold()
    action_mentioned = re.search(
        r"\b(?:back\s+up|backup|disable|remove|move)\b",
        resolution,
        re.I,
    )
    if not action_mentioned:
        return False
    for path in set(paths):
        expected = (
            f"cp -a {path}".casefold(),
            f"mv {path}".casefold(),
        )
        if any(command in lowered for command in expected):
            return False
    return True


def _service_restart_command_missing(resolution: str) -> bool:
    lowered = resolution.casefold()
    if "restart" not in lowered:
        return False
    if "systemctl restart " in lowered:
        return False
    return bool(re.search(r"\brestart\s+[a-z][a-z0-9_.@-]+\b", resolution, re.I))


def _ssh_html_link_missing(source_html: str) -> bool:
    pattern = re.compile(
        rf"<a\b[^>]*href=[\"']{re.escape(PLESK_SSH_HOWTO_URL)}[\"'][^>]*>"
        r"[^<]*SSH[^<]*</a>",
        re.I,
    )
    return not bool(pattern.search(source_html))


def _finding(
    rule_id: str,
    severity: FindingSeverity,
    message: str,
) -> KcsZendeskMarkupFinding:
    return KcsZendeskMarkupFinding(
        rule_id=rule_id,
        severity=severity,
        message=message,
    )
