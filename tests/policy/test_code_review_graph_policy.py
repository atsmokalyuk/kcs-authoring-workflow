from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = (
    ROOT / "docs" / "internal" / "engineering-process" / "code-review-graph.json"
)
MODULE_BOUNDARIES = (
    ROOT / "docs" / "internal" / "engineering-process" / "module-boundaries.md"
)
REVIEW_CHECKPOINTS = (
    ROOT / "docs" / "internal" / "engineering-process" / "review-checkpoints.md"
)
FEATURE_NOTE = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-5-code-review-graph-baseline-feature-note.md"
)
SLICE_6_METHODOLOGY = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-slice-6-refactor-methodology.md"
)
OUTCOME_CONTRACT = (
    ROOT
    / "docs"
    / "internal"
    / "engineering-process"
    / "slice-plans"
    / "kcs-14-outcome-contract.md"
)

FORBIDDEN_GRAPH_PATTERNS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"/Users/[^/\\\s]+"),
    re.compile(r"C:\\Users\\[^\\\s]+"),
    re.compile(r"\b(?:password|passwd|token|secret|api[_-]?key)\s*[:=]", re.I),
    re.compile(r"\braw_ticket\b", re.I),
    re.compile(r"\bprovider_payload\b", re.I),
    re.compile(r"BEGIN REVIEWER BUNDLE", re.I),
)


def _load_graph() -> dict[str, Any]:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def _repo_path(path_text: str) -> Path:
    assert not path_text.startswith("/"), path_text
    assert ".." not in Path(path_text).parts, path_text
    return ROOT / path_text


def test_code_review_graph_defines_required_shape() -> None:
    graph = _load_graph()

    assert graph["schema_version"] == "kcs_code_review_graph_v1"
    assert graph["status"] == "advisory_orientation_snapshot"
    assert graph["generated_for_commit"]
    assert graph["path_root"] == "repository-relative"
    assert "not a replacement for reading touched files" in graph["purpose"]

    nodes = graph["nodes"]
    assert len(nodes) >= 6
    assert len({node["id"] for node in nodes}) == len(nodes)

    required_fields = {
        "id",
        "label",
        "risk",
        "owns",
        "must_not_own",
        "must_preserve",
        "contract_edges",
        "risk_areas",
        "files",
        "related_tests",
    }
    failures: list[str] = []
    for node in nodes:
        missing = sorted(required_fields - set(node))
        if missing:
            failures.append(f"{node.get('id', '<missing id>')}: missing {missing}")
        if node.get("risk") not in {"low", "medium", "high"}:
            failures.append(f"{node.get('id', '<missing id>')}: invalid risk")

    assert not failures, "\n".join(failures)


def test_code_review_graph_references_existing_repo_paths() -> None:
    graph = _load_graph()
    failures: list[str] = []

    for node in graph["nodes"]:
        for file_entry in node["files"]:
            path = _repo_path(file_entry["path"])
            if not path.exists():
                failures.append(f"{node['id']}: missing file {file_entry['path']}")
        for test_path in node["related_tests"]:
            path = _repo_path(test_path)
            if not path.exists():
                failures.append(f"{node['id']}: missing test {test_path}")

    assert not failures, "\n".join(failures)


def test_code_review_graph_maps_every_source_file() -> None:
    """Recount dynamically so refactor deletions do not punish success."""
    graph = _load_graph()
    mapped = {
        file_entry["path"]
        for node in graph["nodes"]
        for file_entry in node["files"]
        if file_entry["path"].startswith("src/")
    }
    source_files = {
        str(path.relative_to(ROOT)) for path in (ROOT / "src").rglob("*.py")
    }

    missing = sorted(source_files - mapped)

    assert not missing, "\n".join(missing)


def test_code_review_graph_maps_every_test_file() -> None:
    """Recount dynamically so test movement changes the required denominator."""
    graph = _load_graph()
    mapped = {
        file_entry["path"]
        for node in graph["nodes"]
        for file_entry in node["files"]
        if file_entry["path"].startswith("tests/")
    }
    mapped.update(
        test_path
        for node in graph["nodes"]
        for test_path in node["related_tests"]
        if test_path.startswith("tests/")
    )
    test_files = {
        str(path.relative_to(ROOT)) for path in (ROOT / "tests").rglob("*.py")
    }

    missing = sorted(test_files - mapped)

    assert not missing, "\n".join(missing)


def test_code_review_graph_maps_every_script_and_packaging_file() -> None:
    """Recount dynamically; no hardcoded current file counts."""
    graph = _load_graph()
    mapped = {
        file_entry["path"]
        for node in graph["nodes"]
        for file_entry in node["files"]
    }
    required_files = {
        str(path.relative_to(ROOT))
        for base in (ROOT / "scripts", ROOT / "packaging")
        for path in base.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    }

    missing = sorted(required_files - mapped)

    assert not missing, "\n".join(missing)


def test_code_review_graph_hashes_match_current_files() -> None:
    graph = _load_graph()
    failures: list[str] = []

    for node in graph["nodes"]:
        for file_entry in node["files"]:
            path = _repo_path(file_entry["path"])
            expected = file_entry["file_hash"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected:
                failures.append(f"{node['id']}: stale hash for {file_entry['path']}")
            if file_entry.get("valid_until_changed") is not True:
                file_path = file_entry["path"]
                failures.append(
                    f"{node['id']}: valid_until_changed missing for {file_path}"
                )

    assert not failures, "\n".join(failures)


def test_code_review_graph_edges_point_to_known_nodes() -> None:
    graph = _load_graph()
    node_ids = {node["id"] for node in graph["nodes"]}
    failures: list[str] = []

    for node in graph["nodes"]:
        for edge in node["contract_edges"]:
            if edge not in node_ids:
                failures.append(f"{node['id']}: unknown edge {edge}")

    assert not failures, "\n".join(failures)


def test_code_review_graph_excludes_private_or_raw_artifact_markers() -> None:
    texts = {
        "code-review-graph.json": GRAPH_PATH.read_text(encoding="utf-8"),
        "module-boundaries.md": MODULE_BOUNDARIES.read_text(encoding="utf-8"),
        "review-checkpoints.md": REVIEW_CHECKPOINTS.read_text(encoding="utf-8"),
    }

    failures: list[str] = []
    for name, text in texts.items():
        for pattern in FORBIDDEN_GRAPH_PATTERNS:
            if pattern.search(text):
                failures.append(f"{name}: matched {pattern.pattern}")

    assert not failures, "\n".join(failures)


def test_code_map_docs_define_orientation_not_source_replacement() -> None:
    boundary_text = MODULE_BOUNDARIES.read_text(encoding="utf-8")
    checkpoint_text = REVIEW_CHECKPOINTS.read_text(encoding="utf-8")

    required = (
        "runtime contract",
        "not a replacement for reading source code",
        "Split by ownership of knowledge",
        "Map every staged source file to one or more graph nodes.",
        "Do not turn deep-module, classitis, or",
        "ownership-quality questions into blocking regex checks",
        "blocking regex checks",
        "graph entry is stale until reviewed",
    )
    combined = f"{boundary_text}\n{checkpoint_text}"
    missing = [phrase for phrase in required if phrase not in combined]

    assert not missing, "\n".join(missing)


def test_code_review_graph_baseline_feature_note_has_required_shape() -> None:
    text = FEATURE_NOTE.read_text(encoding="utf-8")

    required = (
        "Feature Note: Code-Review Graph Baseline",
        "## Problem",
        "## Decision",
        "## Workflow",
        "## Agent Stop Condition",
        "## Implemented In Slice",
        "## Not In Scope",
        "## Later Use",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)


def test_slice_6_refactor_methodology_defines_pre_refactor_gates() -> None:
    text = (
        SLICE_6_METHODOLOGY.read_text(encoding="utf-8")
        + "\n"
        + OUTCOME_CONTRACT.read_text(encoding="utf-8")
    )

    required = (
        "Pre-Refactor Commit 0",
        "Desktop `tools/list` snapshot",
        "packet schema/version/field-set snapshot",
        "compact-result key-set snapshot",
        "freeze-list or diff gate",
        "ready for planning only",
        "not ready for code movement",
        "First Refactor Target",
        "`smoke_log_tooling`",
        "Result-Shaping Ownership Gate",
        "target 2 starts",
        "Cross-Package Movement Rule",
        "keep graph ownership-definition edits separate",
        "demonstrated by green snapshots",
        "Aggregate Design Review Gate",
        "after every two completed refactor batches",
        "batches since aggregate review",
        "promotion candidates by node",
        "continue current node-by-node refactor",
        "pause and write a higher-level design proposal",
        "demote or retire noisy checks",
        "separately scoped slice",
        "MVP safety floor",
        "KCS-14 Success Signals",
        "Ousterhout Review Lens",
        "Information hiding",
        "Deep modules",
        "Classitis",
        "Temporal decomposition",
        "Pass-through layers",
    )
    missing = [phrase for phrase in required if phrase not in text]

    assert not missing, "\n".join(missing)
