from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ACTIVE_DOCS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs" / "internal").rglob("*.md")),
    *sorted((ROOT / "engineering-playbook").rglob("*.md")),
]

REFERENCE_ONLY_DOCS = {
    ROOT / "docs" / "internal" / "engineering-process" / "references.md",
}

PROCESS_DOCS = [
    ROOT / "AGENTS.md",
    *sorted((ROOT / "docs" / "internal" / "engineering-process").rglob("*.md")),
    *sorted((ROOT / "engineering-playbook").rglob("*.md")),
]

KCS14_STYLE_RE = re.compile(
    r"KCS-14[^\n]*(style|markup|parity)|"
    r"KCS-14[^\n]*(Style|Markup|Parity)|"
    r"KCS-14[^\n]*(KCS Style)",
)

PATH_RE = re.compile(
    r"`("
    r"(?:AGENTS\.md|README\.md|CONTRIBUTING\.md|pyproject\.toml)"
    r"|(?:docs|engineering-playbook|scripts|tests|src)/[^`]+"
    r")`"
)

ALLOWED_KCS14_STYLE_CONTEXT = (
    "historical",
    "pre-renumbering",
    "older kcs-14",
    "unmarked active",
    "grep check",
    "not leave",
)

PLANNED_OR_OPTIONAL_CONTEXT = (
    "planned",
    "future",
    "once created",
    "after slice",
    "after kcs-14",
    "after kcs-15",
    "later",
    "optional",
)

UNSUPPORTED_HARNESS_CONTEXT = (
    "not described as active",
    "unsupported-harness",
    "unavailable",
    "not active",
)


def _line_context(lines: list[str], index: int) -> str:
    start = max(0, index - 2)
    end = min(len(lines), index + 3)
    return " ".join(lines[start:end]).lower()


def test_active_docs_do_not_define_kcs14_as_style_or_markup_parity() -> None:
    violations: list[str] = []

    for path in ACTIVE_DOCS:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if not KCS14_STYLE_RE.search(line):
                continue
            context = _line_context(lines, index)
            if any(marker in context for marker in ALLOWED_KCS14_STYLE_CONTEXT):
                continue
            rel_path = path.relative_to(ROOT)
            violations.append(f"{rel_path}:{index + 1}: {line}")

    assert not violations, "\n".join(violations)


def test_tracked_policy_docs_reference_existing_repo_paths() -> None:
    missing: list[str] = []

    for path in PROCESS_DOCS:
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            for match in PATH_RE.finditer(line):
                referenced = match.group(1).rstrip(".,;:")
                target = ROOT / referenced
                if target.exists():
                    continue
                context = _line_context(lines, index)
                if any(marker in context for marker in PLANNED_OR_OPTIONAL_CONTEXT):
                    continue
                rel_path = path.relative_to(ROOT)
                missing.append(f"{rel_path}:{index + 1}: {referenced}")

    assert not missing, "\n".join(missing)


def test_active_docs_do_not_list_claude_code_as_active_harness() -> None:
    violations: list[str] = []

    for path in ACTIVE_DOCS:
        if path in REFERENCE_ONLY_DOCS or not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "Claude Code" not in line:
                continue
            context = _line_context(lines, index)
            if any(marker in context for marker in UNSUPPORTED_HARNESS_CONTEXT):
                continue
            rel_path = path.relative_to(ROOT)
            violations.append(f"{rel_path}:{index + 1}: {line}")

    assert not violations, "\n".join(violations)


def test_agent_workflow_is_tracked_authoritative_process() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    workflow_path = (
        "docs/internal/engineering-process/agent-operable-engineering-workflow.md"
    )
    workflow = (ROOT / workflow_path).read_text(encoding="utf-8")

    assert workflow_path in agents
    assert "Status: authoritative KCS-14 development-agent workflow" in workflow
    assert "visible compact checkpoint" in agents
    assert "Minimum visible checkpoint" in workflow
    assert "Stale context to ignore" in workflow


def test_engineering_rule_portability_registry_structure_and_links() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    registry_path = "docs/internal/engineering-process/engineering-rule-portability.md"
    registry = (ROOT / registry_path).read_text(encoding="utf-8")
    promotions = (
        ROOT / "docs/internal/engineering-process/promotion-candidates.md"
    ).read_text(encoding="utf-8")

    assert registry_path in agents
    assert "## Rule Families" in registry
    assert "### Enforcement Ladder" in registry
    assert "### Portability Ladder" in registry
    assert "## Candidate Registry" in registry
    assert "KCS-14.5, completed" in registry
    assert "KCS-16b owns extraction decisions" in registry
    assert "KCS-17 owns the handoff and initiation" in registry
    assert "The separate kit project owns agent roles" in registry
    assert "local enforcement maturity" in promotions
    assert registry_path in promotions


def test_design_uncertainty_protocol_required_anchors() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    process_root = ROOT / "docs/internal/engineering-process"
    playbook_root = process_root / "spec-first-engineering-playbook"
    clarifications = (playbook_root / "01-clarifications.md").read_text(
        encoding="utf-8"
    )
    how_to = (playbook_root / "00-how-to-use.md").read_text(encoding="utf-8")
    feature_playbook = (process_root / "feature-engineering-playbook.md").read_text(
        encoding="utf-8"
    )
    agent_instructions = (process_root / "codex-agent-instructions.md").read_text(
        encoding="utf-8"
    )

    for approval_state in (
        "Outcome agreement",
        "Design selection",
        "Delivery authorization",
    ):
        assert approval_state in clarifications

    for readiness_field in (
        "Decision",
        "Visible information",
        "Sufficiency",
        "Options",
        "Consequences",
        "Uncertainty / failure path",
    ):
        assert f"| {readiness_field} |" in clarifications

    assert "Design selection does not authorize Delivery" in agent_instructions
    assert "Design selection does not authorize" in agents
    assert "new behavior-changing slice" in agents
    assert "`select` means that a design was selected" in how_to
    assert "Enabling-slice success proves feasibility only" in feature_playbook
    assert "does not define a Designer role" in clarifications


def test_material_slice_design_is_tracked_before_delivery() -> None:
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    process_root = ROOT / "docs/internal/engineering-process"
    how_to = (
        process_root / "spec-first-engineering-playbook/00-how-to-use.md"
    ).read_text(encoding="utf-8")
    clarifications = (
        process_root / "spec-first-engineering-playbook/01-clarifications.md"
    ).read_text(encoding="utf-8")
    feature_playbook = (process_root / "feature-engineering-playbook.md").read_text(
        encoding="utf-8"
    )
    instructions = (process_root / "codex-agent-instructions.md").read_text(
        encoding="utf-8"
    )
    workflow = (process_root / "agent-operable-engineering-workflow.md").read_text(
        encoding="utf-8"
    )
    review_protocol = (process_root / "review-context-protocol.md").read_text(
        encoding="utf-8"
    )
    review_checklist = (
        process_root / "spec-first-engineering-playbook/06-review-checklist.md"
    ).read_text(encoding="utf-8")
    portability = (process_root / "engineering-rule-portability.md").read_text(
        encoding="utf-8"
    )

    for text in (
        agents,
        how_to,
        clarifications,
        feature_playbook,
        instructions,
        workflow,
    ):
        assert "tracked" in text
        assert "slice-plans/" in text
        assert "Delivery" in text

    assert "Chat-only design is not a Delivery-ready record" in clarifications
    assert "Chat is a compact decision surface" in instructions
    assert "## Tracked Material Design Gate" in feature_playbook
    assert "## Active Slice Plan Gate" in review_protocol
    assert "Plan/diff alignment: pass | revise | blocked" in review_protocol
    assert "still-locked" in review_checklist
    assert "Active Slice Plan path" in workflow
    assert "ENG-PORT-DES-010" in portability


def test_ousterhout_material_review_gate_anchors_are_tracked() -> None:
    process_root = ROOT / "docs/internal/engineering-process"
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    instructions = (process_root / "codex-agent-instructions.md").read_text(
        encoding="utf-8"
    )
    checklist = (
        process_root / "spec-first-engineering-playbook/06-review-checklist.md"
    ).read_text(encoding="utf-8")
    review_protocol = (process_root / "review-context-protocol.md").read_text(
        encoding="utf-8"
    )
    promotions = (process_root / "promotion-candidates.md").read_text(encoding="utf-8")
    portability = (process_root / "engineering-rule-portability.md").read_text(
        encoding="utf-8"
    )

    assert "material implementation" in agents
    assert "compact Ousterhout gate" in instructions
    assert "## Compact Ousterhout Review Gate" in checklist
    assert "small leaf behavior correction" in checklist
    assert "named human-review gate" in checklist
    assert "For a valid leaf exception, record only" in checklist
    assert "Not-triggered reason:" in checklist
    assert "A large internal change is reviewed" in checklist
    assert (
        "For a small leaf change, use only the short exception form" in review_protocol
    )
    assert "Not-triggered reason:" in review_protocol

    for field in (
        "Ousterhout gate: reviewed",
        "Trigger:",
        "Complexity hidden:",
        "Owner and what it must not know:",
        "Interface depth and caller cognitive load:",
        "Information leakage and change amplification:",
        "Complexity removed, moved, or added:",
        "Residual design risk:",
        "Verdict: pass | revise | reject",
    ):
        assert field in checklist
        assert field in review_protocol

    assert "must not claim to judge module depth or design quality" in checklist
    assert "KCS14-PROMO-014" in promotions
    assert "ENG-PORT-DES-009" in portability


def test_exact_integration_feasibility_gate_is_tracked() -> None:
    process_root = ROOT / "docs/internal/engineering-process"
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    instructions = (process_root / "codex-agent-instructions.md").read_text(
        encoding="utf-8"
    )
    clarifications = (
        process_root / "spec-first-engineering-playbook/01-clarifications.md"
    ).read_text(encoding="utf-8")
    checklist = (
        process_root / "spec-first-engineering-playbook/06-review-checklist.md"
    ).read_text(encoding="utf-8")
    feature_playbook = (process_root / "feature-engineering-playbook.md").read_text(
        encoding="utf-8"
    )
    promotions = (process_root / "promotion-candidates.md").read_text(encoding="utf-8")
    portability = (process_root / "engineering-rule-portability.md").read_text(
        encoding="utf-8"
    )

    for text in (agents, instructions, clarifications, checklist, feature_playbook):
        assert "exact endpoint" in text
        assert "bounded" in text
    assert "nominal" in clarifications
    assert "operational proof" in clarifications
    assert "One successful smoke proves only" in clarifications
    assert "KCS14-PROMO-015" in promotions
    assert "ENG-PORT-DISC-006" in portability
