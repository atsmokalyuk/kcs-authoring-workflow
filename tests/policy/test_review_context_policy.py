from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PROTOCOL = (
    ROOT / "docs" / "internal" / "engineering-process" / "review-context-protocol.md"
)
PULL_REQUEST_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
PROMOTION_CANDIDATES = (
    ROOT / "docs" / "internal" / "engineering-process" / "promotion-candidates.md"
)
FINAL_CLOSEOUT = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-final-closeout.md"
)
PROMOTION_CODE_RE = re.compile(r"\bKCS14-PROMO-\d{3}\b")

REQUIRED_PACKET_SECTIONS = (
    "Review Task",
    "Active Slice Plan",
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
REQUIRED_COMPLEXITY_FIELDS = (
    "functions_total",
    "cc_average",
    "max_cc",
    "high_complexity_functions",
    "mi_average",
    "import_edges",
    "public_defs",
    "all_exports",
)

def test_review_context_protocol_defines_required_packet_sections() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    missing = [section for section in REQUIRED_PACKET_SECTIONS if section not in text]

    assert not missing, "\n".join(missing)


def test_review_context_protocol_links_material_diff_to_authorized_plan() -> None:
    text = " ".join(REVIEW_PROTOCOL.read_text(encoding="utf-8").split())

    required = (
        "## Active Slice Plan Gate",
        "Path: docs/internal/engineering-process/slice-plans/<plan>.md",
        "Authorized Delivery phase:",
        "Still locked:",
        "Plan/diff alignment: pass | revise | blocked",
        "included in the intended/staged diff",
        "still-locked phases",
        "named human-review verdict",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_default_pull_request_template_carries_active_slice_plan_handoff() -> None:
    text = PULL_REQUEST_TEMPLATE.read_text(encoding="utf-8")

    required = (
        "## Active Slice Plan",
        "Path: `docs/internal/engineering-process/slice-plans/<plan>.md`",
        "Authorized Delivery phase:",
        "Still locked:",
        "Plan/diff alignment:",
        "pass",
        "revise",
        "blocked",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)
    missing_sections = [
        section
        for section in REQUIRED_PACKET_SECTIONS
        if f"## {section}" not in text
    ]

    assert not missing_sections, "\n".join(missing_sections)

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


def test_promotion_protocol_keeps_aggregate_automation_after_stability() -> None:
    text = " ".join(REVIEW_PROTOCOL.read_text(encoding="utf-8").split())

    required = (
        "Once = review note, not a registry entry.",
        "Twice = review checklist item.",
        "Three times = candidate for test/tool/check.",
        "Stable across KCS-14 and KCS-15 = reusable infrastructure candidate.",
        "Do not automate design judgment with blocking regex checks.",
        "Agent Promotion Responsibility",
        "Promotion discovery is automatic at aggregate closeout",
        "Promotion implementation is approval-gated.",
        "operator should not need to remember",
        "development agent must surface a promotion candidate",
        "Promotion implementation should be its own small scoped",
        "action or commit",
        "Promotion Checkpoints",
        "during aggregate review or aggregate closeout",
        "Staged-diff review may attach evidence",
        "after repeated validation or review failure with the same cause",
        "Promotion candidates: none",
        "Counts must come from",
        "The agent must not rely on chat memory",
        "Micro-batch closeouts only mention promotion",
        "stable value-safe finding codes",
        "Promotion Readiness Gates",
        "Implicit approval is allowed only when",
        "model output never grants",
        "implicit approval",
        "Promotion Scope",
        "runtime and contract defects go directly to focused regression tests",
        "No probation, demotion, or time-based expiry state machine",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_promotion_registry_uses_unique_finding_codes() -> None:
    text = PROMOTION_CANDIDATES.read_text(encoding="utf-8")

    codes = PROMOTION_CODE_RE.findall(text)

    assert codes
    assert len(codes) == len(set(codes))


def test_review_protocol_requires_full_complexity_delta_block() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    required = (
        "If a refactor closeout cites the complexity sensor",
        "full summary/delta block",
        *REQUIRED_COMPLEXITY_FIELDS,
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_review_protocol_requires_behavior_drift_mapping_evidence() -> None:
    text = REVIEW_PROTOCOL.read_text(encoding="utf-8")

    required = (
        "Behavior Drift Check",
        "Reviewed drift risks",
        "<old behavior element -> new location -> evidence>",
        "<new element -> old source or intentional-change note -> evidence>",
        "every removed behavior element maps to a new location",
        "every new field, branch, condition, or helper maps back to old behavior",
        "no drift found by listed checks; residual risks listed above",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_final_closeout_records_full_complexity_summary() -> None:
    text = FINAL_CLOSEOUT.read_text(encoding="utf-8")

    required = (
        "Final Full-Repo Sensor Snapshot",
        *REQUIRED_COMPLEXITY_FIELDS,
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_promotion_registry_records_contract_term_table_guidance() -> None:
    text = PROMOTION_CANDIDATES.read_text(encoding="utf-8")

    required = (
        "Contract-term/spec-table extraction",
        "all-quantified checks",
        "not a blanket instruction",
        "checklist-item",
        "Behavior Drift Mapping Support",
        "Full Complexity Delta Closeout",
        "KCS14-PROMO-006",
        "KCS14-PROMO-007",
        "KCS14-PROMO-008",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)
