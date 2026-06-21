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
PLESK_LOGIN_HOWTO_URL = (
    "https://support.plesk.com/hc/en-us/articles/"
    "12377667582743-How-to-log-in-to-Plesk"
)
PLESK_FIREWALL_HOWTO_URL = (
    "https://support.plesk.com/hc/en-us/articles/"
    "12377519983511-How-to-manage-local-firewall-rules-using-Plesk-Firewall-in-Plesk-for-Linux"
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
_HTML_RELATED_ARTICLES_RE = re.compile(
    r"<h2\b[^>]*>\s*related\s+articles\s*</h2>",
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
_HTML_RESOLUTION_SUBHEADING_RE = re.compile(r"<h[3-6]\b[^>]*>", re.I)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_NON_STEP_LIST_ITEM_RE = re.compile(
    r"^\s*(?:#|\$|C:\\>|MYSQL_(?:LIN|WIN):?|CONFIG_TEXT:|SVM_(?:ERROR|INFO|WARN):?|"
    r"PLESK_(?:ERROR|INFO|WARN):?|Warning:|Note:|Important:)",
    re.I,
)
_OPTIONAL_OR_FALLBACK_RE = re.compile(
    r"\b(?:optional|fallback|if\b|when\b[^.?!\n]{0,80}\b(?:cannot|must|needs?|requires?))",
    re.I,
)
_IF_THEN_BRANCH_RE = re.compile(
    r"\bif\b[^.?!\n]{0,120}\b(?:then|continue|run|create|use|apply|restart|verify|check)\b",
    re.I,
)
_NON_EXPLANATORY_NOTE_RE = re.compile(
    r"^\s*(?:note|warning|important)\s*:|^\s*(?:#|\$|C:\\>|MYSQL_(?:LIN|WIN):?|"
    r"CONFIG_TEXT:|SVM_(?:ERROR|INFO|WARN):?|PLESK_(?:ERROR|INFO|WARN):?)",
    re.I,
)
_GENERIC_PRE_CODE_RE = re.compile(
    r"<pre\b[^>]*>\s*<code\b[^>]*>.*?</code>\s*</pre>",
    re.I | re.S,
)
_INCOMPLETE_EXTERNAL_COMMAND_REF_RE = re.compile(
    r"\b(?:see|refer to|use)\b[^.?!\n]{0,120}\b"
    r"(?:full commands?|internal kb|internal draft|elsewhere)\b",
    re.I,
)
_STANDALONE_PARAGRAPH_RE = re.compile(
    r"<p\b[^>]*>(?P<body>.*?)</p>",
    re.I | re.S,
)
_INTERNALDATA_RE = re.compile(
    r"<div\s+class=[\"']internaldata[\"']\s*>(?P<body>.*?)</div>",
    re.I | re.S,
)
_ACCORDION_RE = re.compile(
    r"<div\s+class=[\"'][^\"']*accordion[^\"']*[\"']\s*>(?P<body>.*?)</div>",
    re.I | re.S,
)
_ACCORDION_CONTENT_RE = re.compile(
    r"<div\s+class=[\"'](?:texto|accordion__item-content|tab\s+is-hidden)[\"']\s*>(?P<body>.*?)</div>",
    re.I | re.S,
)
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
    r"\b(?:fail2ban|iptables|systemctl|/etc/|/var/log/|plesk\s+bin|"
    r"plesk\s+firewall|plesk\s+repair|tools\s*&\s*settings\s*(?:&gt;|>)\s*firewall)\b",
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
_LOG_IN_TO_PLESK_RE = re.compile(r"\blog\s+in\s+to\s+plesk\b", re.I)
_PLESK_FIREWALL_PROCEDURE_RE = re.compile(
    r"\b(?:plesk\s+firewall|tools\s*&\s*settings\s*(?:&gt;|>)\s*firewall|"
    r"add\s+(?:a\s+)?(?:custom\s+)?firewall\s+rule)\b",
    re.I,
)
_CONFIG_PATH_RE = re.compile(r"(/etc/[A-Za-z0-9_./-]+\.conf)\b")
_TECHNICAL_ACTION_RE = re.compile(
    r"\b(?:add|allow|block|configure|create|disable|drop|edit|enable|set|write)\b"
    r"[^.?!\n]{0,120}\b(?:configuration|file|filter|firewall|jail|port|rule|service|traffic)\b",
    re.I,
)
_IMPLEMENTATION_DETAIL_RE = re.compile(
    r"(?:"
    r"<a\b[^>]*href=|"
    r"\b(?:cat|chmod|chown|cp|fail2ban-client|fail2ban-regex|firewall-cmd|"
    r"iptables|mkdir|mv|nft|plesk|sed|systemctl|ufw)\b\s+|"
    r"\b(?:enabled|filter|failregex|action|logpath|maxretry|findtime|bantime)\s*=|"
    r"\[[A-Za-z0-9_.:-]+\]|"
    r"\b(?:tcp|udp)\b[^.?!\n]{0,40}\b\d{2,5}\b"
    r")",
    re.I,
)
_RISKY_STEP_RE = re.compile(
    r"\b(?:update\s+psa|delete\s+from|insert\s+into|replace\s+into|drop\s+table|"
    r"truncate|alter\s+table|rm\s+-rf|plesk\s+db|iptables)\b",
    re.I,
)
_WARNING_OR_BACKUP_RE = re.compile(
    r"(?:\b(?:warning|note|important):|\b(?:backup|back\s+up|dump|rollback)\b)",
    re.I,
)
_CUSTOM_COMPLEX_MITIGATION_RE = re.compile(
    r"\b(?:custom\s+fail2ban|filter\.d/|jail\.d/|fail2ban-regex|f2b-[a-z0-9_-]+|"
    r"hashlimit|connlimit|iptables\s+.*(?:-m\s+multiport|--dports|--hashlimit|--connlimit))\b",
    re.I,
)
_INTERNAL_OR_REVIEWER_RE = re.compile(
    r"\b(?:internaldata|reviewer|approval|approved|r&d|ask-plesk|unsupported|customization)\b",
    re.I,
)
_GENERIC_TITLE_RE = re.compile(
    r"^\s*(?:plesk\s+)?(?:does\s+not\s+work|is\s+down|error|issue|problem|"
    r"not\s+working|fails?)\s*$",
    re.I,
)
_TITLE_ERROR_HINT_RE = re.compile(
    r"[:：]|(?:\b(?:error|warning|fail(?:ed|s|ure)?|unable|cannot|denied|"
    r"timeout|no\s+data|high\s+cpu|502|500|403|404)\b)",
    re.I,
)
_BROAD_ENVIRONMENT_RE = re.compile(
    r"\b(?:any\s+(?:recent\s+)?version|all\s+(?:supported\s+)?versions|latest\s+version)\b",
    re.I,
)
_GUI_SCREEN_MENTION_RE = re.compile(
    r"\b(?:Fail2Ban|Jails|Plesk\s+Firewall|Firewall|WP\s+Toolkit|Hosting\s+Settings|"
    r"Mail\s+Settings|DNS\s+Settings|Backup\s+Manager|Extensions|Tools\s*&(?:amp;)?\s*Settings)\b",
    re.I,
)
_GUI_PATH_RE = re.compile(
    r"(?:Plesk\s*(?:&gt;|>)\s*)?[A-Z][A-Za-z0-9 &/+-]+?\s*(?:&gt;|>)\s*"
    r"[A-Z][A-Za-z0-9 &/+-]+",
    re.I,
)
_TOOLS_SETTINGS_GUI_PATH_RE = re.compile(
    r"(?:Plesk\s*(?:&gt;|>)\s*)?Tools\s*&(?:amp;)?\s*Settings\s*(?:&gt;|>)\s*[^<\n]+",
    re.I,
)
_PLESK_INFO_ERROR_TRIGGER_RE = re.compile(
    r"\bPLESK_INFO:\s*(?:[45]\d\d\b|[^<\n]*(?:bad gateway|error|fail(?:ed|ure|s)?|"
    r"cannot|unable|denied|timeout|unavailable|not found|forbidden|exception|"
    r"warning|fatal|critical))",
    re.I,
)
_RAW_WINDOWS_PLESK_PATH_RE = re.compile(
    r"\b[A-Z]:\\(?:Program Files(?: \(x86\))?\\Plesk|Plesk|Inetpub\\vhosts|Windows)"
    r"\\[^\s<>\"]*",
    re.I,
)
_WINDOWS_PATH_PLACEHOLDERS = (
    "%plesk_dir%",
    "%plesk_bin%",
    "%plesk_cli%",
    "%plesk_vhosts%",
    "%windir%",
)
_EVIDENCE_TRIGGER_RE = re.compile(r"\b(?:PLESK_(?:ERROR|INFO|WARN)|CONFIG_TEXT):", re.I)
_POWERSHELL_REFERENCE_RE = re.compile(
    r"\b(?:powershell|Get-[A-Za-z]|Set-[A-Za-z]|New-[A-Za-z]|Remove-[A-Za-z])\b",
    re.I,
)
_POWERSHELL_TRIGGER_RE = re.compile(r"^\s*PS(?:\s|&gt;|>)", re.I | re.M)
_IMAGE_TAG_RE = re.compile(r"<img\b(?P<attrs>[^>]*)>", re.I | re.S)
_RESIZABLE_CLASS_RE = re.compile(
    r"\bclass\s*=\s*['\"][^'\"]*\bresizable\b[^'\"]*['\"]",
    re.I,
)
_DOWNLOAD_LINK_RE = re.compile(
    r"<a\b[^>]*href\s*=\s*['\"](?P<href>[^'\"]+)['\"][^>]*>(?P<body>.*?)</a>",
    re.I | re.S,
)
_ATTACHMENT_HINT_RE = re.compile(r"\b(?:download|attachment|attached|file)\b", re.I)
_APPROVED_ARCHIVE_RE = re.compile(r"\.(?:zip|tar\.gz)(?:[?#].*)?$", re.I)
_TAB_CLASS_RE = re.compile(r"\bclass\s*=\s*['\"][^'\"]*\btab", re.I)
_APPROVED_COMPACT_TABS_RE = re.compile(
    r"class\s*=\s*['\"]tabs['\"].*class\s*=\s*['\"]tabs-menu['\"].*tabs-link",
    re.I | re.S,
)
_APPROVED_STYLE_GUIDE_TABS_RE = re.compile(
    r"class\s*=\s*['\"]tabs-content['\"].*class\s*=\s*['\"]tab-header\s+current['\"].*"
    r"class\s*=\s*['\"]tab-content\s+active['\"]",
    re.I | re.S,
)
_ACCORDION_CLASS_RE = re.compile(r"\bclass\s*=\s*['\"][^'\"]*\baccordion", re.I)
_APPROVED_COMPACT_ACCORDION_RE = re.compile(
    r"class\s*=\s*['\"]accordion-container['\"].*class\s*=\s*['\"]accordion['\"].*"
    r"class\s*=\s*['\"]texto['\"]",
    re.I | re.S,
)
_APPROVED_STYLE_GUIDE_ACCORDION_RE = re.compile(
    r"class\s*=\s*['\"]accordion__item['\"].*class\s*=\s*['\"]accordion__item-title['\"].*"
    r"class\s*=\s*['\"]accordion__item-content['\"]",
    re.I | re.S,
)
_TABLE_RE = re.compile(r"<table\b", re.I)
_APPROVED_TABLE_WRAPPER_RE = re.compile(
    r"class\s*=\s*['\"]container-table100['\"].*class\s*=\s*['\"]wrap-table100['\"].*"
    r"class\s*=\s*['\"]table100\s+ver1['\"]",
    re.I | re.S,
)
_WEAK_CONFIDENCE_RE = re.compile(
    r"\b(?:may\s+be|maybe|probably|seems?|appears?|strange|unclear|unknown)\b",
    re.I,
)
_PERSONAL_PRONOUN_RE = re.compile(r"\b(?:we|our|ours|I|me|my)\b", re.I)
_DIMINISHING_PRODUCT_WORDING_RE = re.compile(
    r"\b(?:strange|weird|broken|bad|buggy|hanged)\b",
    re.I,
)
_WORDY_RESOLUTION_STEP_RE = re.compile(
    r"\b(?:in\s+order\s+to|the\s+following\s+command\s+was\s+executed)\b",
    re.I,
)
_NOT_CLEAR_RE = re.compile(r"\bnot\s+clear\b", re.I)


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
    findings.extend(_hidden_step_findings(source_html))
    findings.extend(_risky_step_findings(source_html))
    findings.extend(_wording_findings(source_html))
    findings.extend(_scope_findings(source_html))
    findings.extend(_style_guide_format_findings(source_html))
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
    findings.extend(_title_shape_findings(source_html))
    findings.extend(_body_section_shape_findings(source_html))
    return tuple(findings)


def _title_shape_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
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
    title = _title_text(source_html)
    if title and _title_is_too_generic(title):
        findings.append(
            _finding(
                "source_title_too_generic",
                "blocker",
                "Article title should identify the failing action or visible "
                "error; generic titles are not findable enough.",
            )
        )
    if title and _title_lacks_issue_detail(title):
        findings.append(
            _finding(
                "source_title_missing_error_or_issue_detail",
                "warning",
                "Technical article titles should include the visible error, "
                "behavior, or specific issue detail when available.",
            )
        )
    return tuple(findings)


def _body_section_shape_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
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
    if _HTML_RELATED_ARTICLES_RE.search(source_html):
        findings.append(
            _finding(
                "related_articles_section_present",
                "warning",
                "Avoid hub-style Related articles sections; keep required "
                "links in the relevant step.",
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
    resolution_body = _section_body(_remove_internaldata(source_html), "resolution")
    main_resolution_body = _remove_accordion(resolution_body)
    main_resolution_plain = _strip_html_text(main_resolution_body)
    findings.extend(
        _resolution_step_shape_findings(
            source_html=source_html,
            main_resolution_body=main_resolution_body,
        )
    )
    findings.extend(_resolution_branching_findings(main_resolution_plain))
    findings.extend(
        _resolution_source_shape_findings(
            source_html=source_html,
            main_resolution_body=main_resolution_body,
            main_resolution_plain=main_resolution_plain,
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


def _resolution_step_shape_findings(
    *,
    source_html: str,
    main_resolution_body: str,
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
    if _HTML_RESOLUTION_SUBHEADING_RE.search(main_resolution_body):
        findings.append(
            _finding(
                "resolution_steps_rendered_as_headings",
                "blocker",
                "Resolution steps should be plain numbered steps, not "
                "heading-sized subheaders.",
            )
        )
    if _has_numbered_command_or_note_step(main_resolution_body):
        findings.append(
            _finding(
                "resolution_command_or_note_numbered_as_step",
                "blocker",
                "Number only customer action steps; commands, warnings, "
                "notes, and output snippets should stay inside the step they "
                "implement.",
            )
        )
    return tuple(findings)


def _resolution_branching_findings(
    main_resolution_plain: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    if _IF_THEN_BRANCH_RE.search(main_resolution_plain):
        findings.append(
            _finding(
                "resolution_main_path_has_if_then_branching",
                "warning",
                "Main Resolution path should preferably stay linear. Keep "
                "conditional or staged mitigation only when it matches the "
                "actual supported ticket resolution.",
            )
        )
    if _OPTIONAL_OR_FALLBACK_RE.search(main_resolution_plain):
        findings.append(
            _finding(
                "optional_resolution_path_not_collapsed",
                "warning",
                "Optional, fallback, or conditional resolution paths should be "
                "collapsed or removed unless the ticket evidence shows they "
                "were part of the actual supported resolution.",
            )
        )
    return tuple(findings)


def _resolution_source_shape_findings(
    *,
    source_html: str,
    main_resolution_body: str,
    main_resolution_plain: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    if _has_standalone_resolution_explanation(main_resolution_body):
        findings.append(
            _finding(
                "resolution_contains_standalone_explanation",
                "blocker",
                "Resolution should keep the main path action-focused; move "
                "explanations to Symptoms/Cause/Notes unless they are required "
                "warnings.",
            )
        )
    if _INCOMPLETE_EXTERNAL_COMMAND_REF_RE.search(main_resolution_plain):
        findings.append(
            _finding(
                "resolution_delegates_required_steps_elsewhere",
                "blocker",
                "Resolution must contain the steps needed to fix the issue or "
                "an approved public how-to link; do not delegate required "
                "commands to an internal draft.",
            )
        )
    if _GENERIC_PRE_CODE_RE.search(source_html):
        findings.append(
            _finding(
                "zendesk_source_uses_generic_pre_code_block",
                "blocker",
                "Zendesk source should use KCS editor triggers such as #, "
                "C:\\>, MYSQL_LIN, or CONFIG_TEXT instead of generic "
                "<pre><code> blocks.",
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
    if _LOG_IN_TO_PLESK_RE.search(plain) and _plesk_login_html_link_missing(
        source_html
    ):
        findings.append(
            _finding(
                "resolution_plesk_login_howto_link_missing",
                "warning",
                "Plesk login steps should link to the canonical Plesk login how-to.",
            )
        )
    if _PLESK_FIREWALL_PROCEDURE_RE.search(plain) and _plesk_firewall_html_link_missing(
        source_html
    ):
        findings.append(
            _finding(
                "resolution_reusable_howto_missing_link",
                "blocker",
                "Reusable procedures such as adding a Plesk Firewall rule must "
                "link to the canonical how-to article instead of duplicating "
                "or underspecifying the steps.",
            )
        )
    return tuple(findings)


def _technical_resolution_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    resolution_body = _section_body(source_html, "resolution")
    resolution = _strip_html_text(resolution_body)
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
    if _technical_actions_lack_implementation_detail(resolution_body):
        findings.append(
            _finding(
                "resolution_action_missing_implementation_detail",
                "blocker",
                "Resolution steps that add, create, configure, edit, enable, "
                "disable, or block a technical object must include the exact "
                "command, configuration content, or approved how-to link from "
                "the ticket evidence.",
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


def _hidden_step_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    for match in _INTERNALDATA_RE.finditer(source_html):
        body = _strip_html_text(match.group("body"))
        if _ESSENTIAL_STEP_RE.search(body):
            findings.append(
                _finding(
                    "essential_step_hidden_in_internaldata",
                    "blocker",
                    "Do not hide required customer steps in internaldata.",
                )
            )
    for match in tuple(_ACCORDION_RE.finditer(source_html)) + tuple(
        _ACCORDION_CONTENT_RE.finditer(source_html)
    ):
        body = _strip_html_text(match.group("body"))
        if _ESSENTIAL_STEP_RE.search(body):
            findings.append(
                _finding(
                    "essential_step_hidden_in_accordion",
                    "blocker",
                    "Do not hide required customer access/setup steps in an accordion.",
                )
            )
    return tuple(findings)


def _risky_step_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    visible_source = _remove_internaldata(source_html)
    findings: list[KcsZendeskMarkupFinding] = []
    if _RISKY_STEP_RE.search(visible_source) and not _WARNING_OR_BACKUP_RE.search(
        visible_source
    ):
        findings.append(
            _finding(
                "risky_visible_step_without_warning_or_backup",
                "blocker",
                "Risky visible steps need a warning and backup/rollback "
                "guidance, or must be internal-only.",
            )
        )
    if _CUSTOM_COMPLEX_MITIGATION_RE.search(
        visible_source
    ) and not _INTERNAL_OR_REVIEWER_RE.search(visible_source):
        findings.append(
            _finding(
                "custom_complex_mitigation_needs_reviewer_boundary",
                "warning",
                "Custom or complex mitigations such as Fail2Ban filters, "
                "iptables chain ordering, or rate limits should get an "
                "explicit public/internal reviewer decision before KCS "
                "handoff.",
            )
        )
    return tuple(findings)


def _wording_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    public_plain = _strip_html_text(_remove_internaldata(source_html))
    if _PLESK_INFO_ERROR_TRIGGER_RE.search(source_html):
        findings.append(
            _finding(
                "plesk_info_used_for_error_message",
                "blocker",
                "Use PLESK_ERROR for Plesk GUI/Panel error messages; reserve "
                "PLESK_INFO for informational output.",
            )
        )
    if _WEAK_CONFIDENCE_RE.search(public_plain) or _NOT_CLEAR_RE.search(public_plain):
        findings.append(
            _finding(
                "language_confidence_weak",
                "warning",
                "Public article wording should avoid uncertain phrases such as "
                "probably, may be, seems, or strange unless uncertainty is the "
                "supported article state.",
            )
        )
    if _PERSONAL_PRONOUN_RE.search(public_plain):
        findings.append(
            _finding(
                "language_personal_pronoun_present",
                "warning",
                "Public article wording should be impersonal and avoid we, our, "
                "I, me, or my.",
            )
        )
    if _DIMINISHING_PRODUCT_WORDING_RE.search(public_plain):
        findings.append(
            _finding(
                "language_diminishing_product_wording",
                "warning",
                "Public article wording should avoid vague or diminishing words "
                "such as strange, weird, broken, buggy, or hanged.",
            )
        )
    resolution_body = _section_body(source_html, "resolution")
    if _WORDY_RESOLUTION_STEP_RE.search(_strip_html_text(resolution_body)):
        findings.append(
            _finding(
                "language_resolution_step_wordy",
                "warning",
                "Resolution steps should use short complete thoughts and avoid "
                "wordy phrases such as in order to.",
            )
        )
    return tuple(findings)


def _scope_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    if _BROAD_ENVIRONMENT_RE.search(source_html):
        return (
            _finding(
                "environment_scope_too_broad",
                "warning",
                "Applicable to should reflect the supported platform/scope, not "
                "a broad unvalidated version claim.",
            ),
        )
    return ()


def _style_guide_format_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    visible_source = _remove_internaldata(source_html)
    findings.extend(_path_and_trigger_findings(visible_source))
    findings.extend(_media_and_attachment_findings(visible_source))
    findings.extend(_interactive_markup_findings(visible_source))
    return tuple(findings)


def _path_and_trigger_findings(source_html: str) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    plain = _strip_html_text(source_html)
    if _has_raw_windows_plesk_path_without_placeholder(source_html):
        findings.append(
            _finding(
                "windows_plesk_path_placeholder_missing",
                "warning",
                "Windows Plesk paths should use placeholders such as "
                "%plesk_dir%, %plesk_bin%, %plesk_cli%, %plesk_vhosts%, or "
                "%windir% except inside exact error/output evidence.",
            )
        )
    powershell_without_trigger = _POWERSHELL_REFERENCE_RE.search(
        source_html
    ) and not _POWERSHELL_TRIGGER_RE.search(source_html)
    if powershell_without_trigger:
        findings.append(
            _finding(
                "powershell_trigger_missing",
                "warning",
                "PowerShell snippets should use the KCS PS trigger instead of "
                "generic prose or code markup.",
            )
        )
    if _GUI_SCREEN_MENTION_RE.search(plain) and not (
        _GUI_PATH_RE.search(source_html) or "https://support.plesk.com/" in source_html
    ):
        findings.append(
            _finding(
                "symptom_gui_screen_path_missing",
                "warning",
                "GUI references should include the exact Plesk path, link, or "
                "verification command when needed.",
            )
        )
    if _TOOLS_SETTINGS_GUI_PATH_RE.search(source_html) and not _gui_path_is_bold(
        source_html
    ):
        findings.append(
            _finding(
                "gui_path_not_bold",
                "warning",
                "Zendesk source should format GUI paths such as Plesk > Tools & "
                "Settings > Fail2Ban > Jails in bold.",
            )
        )
    return tuple(findings)


def _media_and_attachment_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    for match in _IMAGE_TAG_RE.finditer(source_html):
        if not _RESIZABLE_CLASS_RE.search(match.group("attrs")):
            findings.append(
                _finding(
                    "article_media_image_not_resizable",
                    "warning",
                    "Article images that should be enlarged in Zendesk should "
                    'use class="resizable".',
                )
            )
            break
    if _has_non_archive_attachment_link(source_html):
        findings.append(
            _finding(
                "attachment_archive_format_missing",
                "warning",
                "Downloadable article attachments should be archived as .zip "
                "for Windows or .tar.gz for Linux.",
            )
        )
    return tuple(findings)


def _interactive_markup_findings(
    source_html: str,
) -> tuple[KcsZendeskMarkupFinding, ...]:
    findings: list[KcsZendeskMarkupFinding] = []
    lower = source_html.casefold()
    if _TAB_CLASS_RE.search(source_html) and not (
        _APPROVED_COMPACT_TABS_RE.search(source_html)
        or _APPROVED_STYLE_GUIDE_TABS_RE.search(source_html)
    ):
        findings.append(
            _finding(
                "tabs_markup_unknown_shape",
                "warning",
                "Tabs should use an approved Zendesk tabs pattern, not an ad "
                "hoc tab class structure.",
            )
        )
    if _ACCORDION_CLASS_RE.search(source_html) and not (
        _APPROVED_COMPACT_ACCORDION_RE.search(source_html)
        or _APPROVED_STYLE_GUIDE_ACCORDION_RE.search(source_html)
    ):
        findings.append(
            _finding(
                "accordion_markup_unknown_shape",
                "warning",
                "Accordions should use an approved Zendesk accordion pattern, "
                "not an ad hoc class structure.",
            )
        )
    if _TABLE_RE.search(source_html) and "table100" not in lower:
        findings.append(
            _finding(
                "table_markup_wrapper_missing",
                "warning",
                "Complex Zendesk table source should use the approved table100 "
                "wrapper.",
            )
        )
    elif _TABLE_RE.search(source_html) and not _APPROVED_TABLE_WRAPPER_RE.search(
        source_html
    ):
        findings.append(
            _finding(
                "table_markup_wrapper_incomplete",
                "warning",
                "Complex Zendesk table source should include container-table100, "
                "wrap-table100, and table100 ver1 wrappers.",
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


def _technical_actions_lack_implementation_detail(resolution_body: str) -> bool:
    for match in _HTML_RESOLUTION_LIST_ITEM_RE.finditer(resolution_body):
        item_html = match.group("body")
        item_text = _strip_html_text(item_html)
        if not _TECHNICAL_ACTION_RE.search(item_text):
            continue
        if _IMPLEMENTATION_DETAIL_RE.search(item_html):
            continue
        return True
    return False


def _ssh_html_link_missing(source_html: str) -> bool:
    pattern = re.compile(
        rf"<a\b[^>]*href=[\"']{re.escape(PLESK_SSH_HOWTO_URL)}[\"'][^>]*>"
        r"[^<]*SSH[^<]*</a>",
        re.I,
    )
    return not bool(pattern.search(source_html))


def _plesk_login_html_link_missing(source_html: str) -> bool:
    pattern = re.compile(
        rf"<a\b[^>]*href=[\"']{re.escape(PLESK_LOGIN_HOWTO_URL)}[\"'][^>]*>"
        r"\s*Log\s+in\s+to\s+Plesk\s*</a>",
        re.I,
    )
    return not bool(pattern.search(source_html))


def _plesk_firewall_html_link_missing(source_html: str) -> bool:
    pattern = re.compile(
        rf"<a\b[^>]*href=[\"']{re.escape(PLESK_FIREWALL_HOWTO_URL)}[\"'][^>]*>",
        re.I,
    )
    return not bool(pattern.search(source_html))


def _title_is_too_generic(title: str) -> bool:
    return bool(_GENERIC_TITLE_RE.search(title))


def _title_lacks_issue_detail(title: str) -> bool:
    if len(title.split()) < 5:
        return True
    return not bool(_TITLE_ERROR_HINT_RE.search(title))


def _has_raw_windows_plesk_path_without_placeholder(source_html: str) -> bool:
    for match in _RAW_WINDOWS_PLESK_PATH_RE.finditer(source_html):
        line_start = source_html.rfind("\n", 0, match.start()) + 1
        line_end = source_html.find("\n", match.end())
        if line_end == -1:
            line_end = len(source_html)
        line = source_html[line_start:line_end]
        if any(
            placeholder in line.casefold()
            for placeholder in _WINDOWS_PATH_PLACEHOLDERS
        ):
            continue
        if not _EVIDENCE_TRIGGER_RE.search(line):
            return True
    return False


def _gui_path_is_bold(source_html: str) -> bool:
    for match in _TOOLS_SETTINGS_GUI_PATH_RE.finditer(source_html):
        if _is_inside_strong(source_html, match.start(), match.end()):
            return True
    return False


def _has_non_archive_attachment_link(source_html: str) -> bool:
    for match in _DOWNLOAD_LINK_RE.finditer(source_html):
        href = match.group("href")
        body = _strip_html_text(match.group("body"))
        combined = f"{href} {body}"
        if _ATTACHMENT_HINT_RE.search(combined) and not _APPROVED_ARCHIVE_RE.search(
            href
        ):
            return True
    return False


def _remove_internaldata(source_html: str) -> str:
    return _INTERNALDATA_RE.sub("", source_html)


def _remove_accordion(source_html: str) -> str:
    without_accordion = _ACCORDION_RE.sub("", source_html)
    return _ACCORDION_CONTENT_RE.sub("", without_accordion)


def _has_numbered_command_or_note_step(source_html: str) -> bool:
    for match in _HTML_RESOLUTION_LIST_ITEM_RE.finditer(source_html):
        body = _strip_html_text(match.group("body")).strip()
        if _NON_STEP_LIST_ITEM_RE.search(body):
            return True
    return False


def _has_standalone_resolution_explanation(source_html: str) -> bool:
    for match in _STANDALONE_PARAGRAPH_RE.finditer(source_html):
        if _is_inside_list_item(source_html, match.start(), match.end()):
            continue
        paragraph = _strip_html_text(match.group("body")).strip()
        if not paragraph or _NON_EXPLANATORY_NOTE_RE.search(paragraph):
            continue
        return True
    return False


def _is_inside_list_item(source_html: str, start: int, end: int) -> bool:
    open_start = source_html.rfind("<li", 0, start)
    close_start = source_html.rfind("</li>", 0, start)
    if open_start == -1 or close_start > open_start:
        return False
    close_end = source_html.find("</li>", end)
    return close_end != -1


def _is_inside_strong(source_html: str, start: int, end: int) -> bool:
    open_start = source_html.rfind("<strong", 0, start)
    close_start = source_html.rfind("</strong>", 0, start)
    if open_start == -1 or close_start > open_start:
        return False
    close_end = source_html.find("</strong>", end)
    return close_end != -1


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
