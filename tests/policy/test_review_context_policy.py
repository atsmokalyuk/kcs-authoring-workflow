from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PROTOCOL = (
    ROOT / "docs" / "internal" / "engineering-process" / "review-context-protocol.md"
)
PROMOTION_CANDIDATES = (
    ROOT / "docs" / "internal" / "engineering-process" / "promotion-candidates.md"
)
REVIEW_NOTES = (
    ROOT / "docs" / "internal" / "engineering-process" / "kcs-14-review-notes.md"
)
ENFORCEMENT_FEATURE_NOTE = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-4-enforcement-ladder-feature-note.md"
)
COMPLEX_FEATURE_NOTES = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-1-agent-operable-workflow-feature-note.md",
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-2-local-tool-entrypoints-feature-note.md",
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-3-functional-test-from-behavior-feature-note.md",
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-4-review-context-protocol-feature-note.md",
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-5-code-review-graph-baseline-feature-note.md",
    ENFORCEMENT_FEATURE_NOTE,
)
REVIEW_PACKET_DIR = (
    ROOT / "docs" / "internal" / "engineering-process" / "review-packets"
)
PROMOTION_CODE_RE = re.compile(r"\bKCS14-PROMO-\d{3}\b")

REQUIRED_PACKET_SECTIONS = (
    "Review Task",
    "Slice Intent",
    "Changed Files",
    "Affected Contracts",
    "Relevant Tests",
    "Validation",
    "Known Deferred Risks",
    "Must Not Change",
    "Stale Context To Ignore",
    "Promotion Candidates",
    "Questions For Reviewer",
)

REQUIRED_PROMOTION_FIELDS = (
    "Finding code",
    "Rule / finding",
    "Seen in",
    "Evidence",
    "Trigger",
    "Manual correction needed",
    "Can be checked mechanically",
    "False-positive risk",
    "KCS-specific or generic",
    "Promotion target",
    "Target layer",
    "Decision",
    "Owner slice",
    "Scope",
    "Validation",
    "Approval",
    "Status",
)

FORBIDDEN_REVIEW_PACKET_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"/Users/[^/\\\s]+"),
    re.compile(r"C:\\Users\\[^\\\s]+"),
    re.compile(r"\b(?:password|passwd|token|secret|api[_-]?key)\s*[:=]", re.I),
    re.compile(r"\braw_ticket\b", re.I),
    re.compile(r"\bprovider_payload\b", re.I),
    re.compile(r"BEGIN REVIEWER BUNDLE", re.I),
)


def test_review_context_protocol_defines_required_packet_sections() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    missing = [section for section in REQUIRED_PACKET_SECTIONS if section not in text]

    assert not missing, "\n".join(missing)


def test_review_context_protocol_defines_forbidden_content_and_output_budget() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    required = (
        "Forbidden Content",
        "Output Budget",
        "raw ticket text",
        "selected semantic-review excerpt text",
        "reviewer bundle bodies",
        "provider payloads",
        "private filesystem",
        "full logs or full HTML",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_promotion_candidate_registry_defines_required_fields() -> None:
    text = PROMOTION_CANDIDATES.read_text(encoding="utf-8")

    missing = [field for field in REQUIRED_PROMOTION_FIELDS if field not in text]

    assert not missing, "\n".join(missing)


def test_promotion_protocol_keeps_automation_after_stability() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    required = (
        "Once = note.",
        "Twice = review checklist item.",
        "Three times = candidate for test/tool/check.",
        "Stable across KCS-14 and KCS-15 = reusable infrastructure candidate.",
        "Do not automate design judgment with blocking regex checks.",
        "Agent Promotion Responsibility",
        "Promotion discovery is automatic.",
        "Promotion implementation is approval-gated.",
        "operator should not need to remember",
        "development agent must surface a promotion candidate",
        "Promotion implementation should be its own small scoped",
        "action or commit",
        "Promotion Checkpoints",
        "before starting a refactor target",
        "during staged-diff review",
        "during slice closeout before commit",
        "after repeated validation or review failure with the same cause",
        "Promotion candidates: none",
        "Counts must come from",
        "The agent must not rely on chat memory",
        "report that it checked these durable sources",
        "stable value-safe finding codes",
        "Promotion Readiness Gates",
        "Implicit approval is allowed only when",
        "model output never grants",
        "implicit approval",
        "Probation And Demotion",
        "false positive must be demoted to advisory",
        "expire after three completed slices without new evidence",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_promotion_registry_uses_unique_finding_codes() -> None:
    text = PROMOTION_CANDIDATES.read_text(encoding="utf-8")

    codes = PROMOTION_CODE_RE.findall(text)

    assert codes
    assert len(codes) == len(set(codes))


def test_enforcement_ladder_feature_note_connects_grounding_and_scope() -> None:
    text = ENFORCEMENT_FEATURE_NOTE.read_text(encoding="utf-8")

    required = (
        "Feature Note: Enforcement Ladder And Promotion Workflow",
        "tracked Markdown rule",
        "policy test",
        "tool entrypoint",
        "code map / freeze-list / hash check",
        "Registry As Memory",
        "Probation And Demotion",
        "Not In Scope",
        "Implemented In Slice 4",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_complex_kcs14_feature_notes_have_required_shape() -> None:
    failures: list[str] = []
    required = (
        "## Problem",
        "## Decision",
        "## Not In Scope",
        "## Implemented In Slice",
        "## Later Use",
    )

    for path in COMPLEX_FEATURE_NOTES:
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in required if phrase not in text]
        if missing:
            rel_path = path.relative_to(ROOT)
            failures.append(f"{rel_path}: missing {missing}")

    assert not failures, "\n".join(failures)


def test_review_note_promotion_codes_exist_in_registry() -> None:
    registry = set(PROMOTION_CODE_RE.findall(PROMOTION_CANDIDATES.read_text()))
    notes = set(PROMOTION_CODE_RE.findall(REVIEW_NOTES.read_text()))

    missing = sorted(notes - registry)

    assert not missing, "\n".join(missing)


def test_file_based_review_packets_have_required_sections() -> None:
    packet_paths = sorted(REVIEW_PACKET_DIR.glob("*.md"))
    assert packet_paths

    failures: list[str] = []
    for path in packet_paths:
        text = path.read_text(encoding="utf-8")
        missing = [
            section for section in REQUIRED_PACKET_SECTIONS if section not in text
        ]
        if missing:
            rel_path = path.relative_to(ROOT)
            failures.append(f"{rel_path}: missing {missing}")

    assert not failures, "\n".join(failures)


def test_file_based_review_packets_do_not_include_forbidden_content() -> None:
    failures: list[str] = []

    for path in sorted(REVIEW_PACKET_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_REVIEW_PACKET_PATTERNS:
            if pattern.search(text):
                rel_path = path.relative_to(ROOT)
                failures.append(f"{rel_path}: matched {pattern.pattern}")

    assert not failures, "\n".join(failures)
