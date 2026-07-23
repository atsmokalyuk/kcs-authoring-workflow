from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL_DOC = ROOT / "docs" / "internal" / "engineering-process" / "tool-entrypoints.md"

REQUIRED_COMMANDS = (
    "uv run pytest tests/policy/test_engineering_process_docs_policy.py -q",
    "uv run pytest tests/policy/test_review_context_policy.py -q",
    "uv run pytest tests/policy/test_code_review_graph_policy.py -q",
    "uv run pytest tests/policy/test_kcs14_freeze_snapshots.py -q",
    "uv run pytest <test-path> -q",
    "uv run ruff check <path>",
    "git diff --check",
    "git diff --cached --check",
    "git diff --cached --name-status",
    "uv run kcs-core --help",
    "uv run kcs-smoke-account --help",
    "uv run python scripts/build_kcs_mcpb.py --help",
    "uv run python scripts/build_kcs_cowork_plugin.py --help",
    "uv run python scripts/smoke_kcs_mcpb_stdio.py --help",
    "uv run python scripts/check_claude_kcs_desktop_log.py --help",
    "uv run python scripts/smoke_claude_desktop_ui_prompt.py --help",
    "uv run python scripts/rebaseline_semantic_issue_projection.py --help",
    "uv run python scripts/kcs14_langfuse_rebaseline.py --help",
    "uv run --extra dev python scripts/measure_complexity.py --help",
    (
        "uv run --extra dev python scripts/measure_complexity.py "
        "--paths src tests scripts"
    ),
)

REQUIRED_CLASSIFICATIONS = (
    "deterministic",
    "manual/local-side-effect",
    "deterministic-with-local-runtime",
    "manual/local-state",
    "manual/UI",
)

HELP_COMMANDS = (
    [sys.executable, "-m", "kcs_core.cli", "--help"],
    [sys.executable, "scripts/build_kcs_mcpb.py", "--help"],
    [sys.executable, "scripts/build_kcs_cowork_plugin.py", "--help"],
    [sys.executable, "scripts/smoke_kcs_mcpb_stdio.py", "--help"],
    [sys.executable, "scripts/check_claude_kcs_desktop_log.py", "--help"],
    [sys.executable, "scripts/smoke_claude_desktop_ui_prompt.py", "--help"],
    [sys.executable, "scripts/rebaseline_semantic_issue_projection.py", "--help"],
    [sys.executable, "scripts/kcs14_langfuse_rebaseline.py", "--help"],
    [
        "uv",
        "run",
        "--extra",
        "dev",
        "python",
        "scripts/measure_complexity.py",
        "--help",
    ],
)


def test_tool_entrypoints_doc_lists_supported_commands() -> None:
    text = TOOL_DOC.read_text(encoding="utf-8")

    missing = [command for command in REQUIRED_COMMANDS if command not in text]
    assert not missing, "\n".join(missing)


def test_tool_entrypoints_doc_classifies_deterministic_and_manual_commands() -> None:
    text = TOOL_DOC.read_text(encoding="utf-8")

    missing = [
        classification
        for classification in REQUIRED_CLASSIFICATIONS
        if classification not in text
    ]
    assert not missing, "\n".join(missing)


def test_documented_help_entrypoints_are_alive() -> None:
    failures: list[str] = []

    for command in HELP_COMMANDS:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            failures.append(f"{' '.join(command)} -> {result.returncode}")
            continue
        if "usage:" not in result.stdout:
            failures.append(f"{' '.join(command)} -> missing usage text")

    assert not failures, "\n".join(failures)
