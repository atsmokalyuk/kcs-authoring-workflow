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
    registry_path = (
        "docs/internal/engineering-process/engineering-rule-portability.md"
    )
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
