from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
FUNCTIONAL_TEST_DOC = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "functional-test-from-behavior.md"
)

COMMITTED_JSON_FIXTURES = sorted((ROOT / "tests").rglob("*.json"))
REAL_TICKET_FIXTURE_CLASSES = {"approved_sanitized_fixture"}
REQUIRED_PROVENANCE_FIELDS = {
    "source_type",
    "approval_ref",
    "approved_on",
    "sanitized_by",
    "privacy_scan",
}
LOCAL_REF_KEYS = {
    "clean_ticket_ref",
    "local_clean_ticket_ref",
}
LOCAL_REF_MODES = {
    "local_ref_skip_if_absent",
    "skip_if_absent",
}

PRIVATE_VALUE_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"/Users/[^/\\\s]+"),
    re.compile(r"C:\\Users\\[^\\\s]+"),
    re.compile(r"\b(?:password|passwd|token|secret|api[_-]?key)\s*[:=]", re.I),
)


def _walk_objects(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_objects(child)


def _walk_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def test_functional_test_process_doc_defines_required_fixture_tiers() -> None:
    text = FUNCTIONAL_TEST_DOC.read_text(encoding="utf-8")

    required = (
        "BDD-shaped pytest",
        "Given = state, fixture, or precondition",
        "approved_sanitized_fixture",
        "fixture_provenance",
        "Local-ref fixtures",
        "skip-if-absent",
        "Agent Reminder Gate",
        "Behavior-To-Code Workflow",
        "Behavior definition",
        "Functional test spec",
        "Test-first skeleton",
        "Persistent Slice Specs",
        "behavior.md",
        "functional-tests.md",
        "expected tool calls",
        "files written or not written",
        "affected code-map nodes",
        "xfail",
        "Review",
        "Before coding",
        "Forbidden-Path Tests",
        "Refactor Safety",
        "docs/internal/kcs-authoring-mvp-data-handling-baseline.md",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_committed_clean_ticket_derived_fixtures_have_provenance() -> None:
    violations: list[str] = []

    for path in COMMITTED_JSON_FIXTURES:
        payload = _load_json(path)
        for obj in _walk_objects(payload):
            if obj.get("input_class") not in REAL_TICKET_FIXTURE_CLASSES:
                continue
            provenance = obj.get("fixture_provenance")
            missing = (
                REQUIRED_PROVENANCE_FIELDS - set(provenance)
                if isinstance(provenance, dict)
                else REQUIRED_PROVENANCE_FIELDS
            )
            if missing:
                rel_path = path.relative_to(ROOT)
                violations.append(f"{rel_path}: missing {sorted(missing)}")

    assert not violations, "\n".join(violations)


def test_committed_clean_ticket_derived_fixtures_have_privacy_scan_marker() -> None:
    violations: list[str] = []

    for path in COMMITTED_JSON_FIXTURES:
        payload = _load_json(path)
        for obj in _walk_objects(payload):
            if obj.get("input_class") not in REAL_TICKET_FIXTURE_CLASSES:
                continue
            provenance = obj.get("fixture_provenance")
            if (
                not isinstance(provenance, dict)
                or provenance.get("privacy_scan") != "passed"
            ):
                rel_path = path.relative_to(ROOT)
                violations.append(f"{rel_path}: privacy_scan must be passed")

    assert not violations, "\n".join(violations)


def test_committed_clean_ticket_fixtures_do_not_contain_private_values() -> None:
    violations: list[str] = []

    for path in COMMITTED_JSON_FIXTURES:
        payload = _load_json(path)
        for obj in _walk_objects(payload):
            if obj.get("input_class") not in REAL_TICKET_FIXTURE_CLASSES:
                continue
            for value in _walk_strings(obj):
                for pattern in PRIVATE_VALUE_PATTERNS:
                    if pattern.search(value):
                        rel_path = path.relative_to(ROOT)
                        violations.append(
                            f"{rel_path}: forbidden private value pattern"
                        )

    assert not violations, "\n".join(violations)


def test_local_clean_ticket_ref_fixtures_are_skip_if_absent() -> None:
    violations: list[str] = []

    for path in COMMITTED_JSON_FIXTURES:
        payload = _load_json(path)
        for obj in _walk_objects(payload):
            has_local_ref = any(key in obj for key in LOCAL_REF_KEYS)
            if not has_local_ref:
                continue
            mode = obj.get("fixture_mode")
            if mode not in LOCAL_REF_MODES:
                rel_path = path.relative_to(ROOT)
                violations.append(f"{rel_path}: local refs must be skip-if-absent")

    assert not violations, "\n".join(violations)
