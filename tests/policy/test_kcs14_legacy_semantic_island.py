from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LEGACY_SEMANTIC_TOKENS = (
    "CandidateSemanticExtraction",
    "CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION",
    "candidate_semantic_extraction_v1",
    "validate_candidate_semantic_extraction",
)

ALLOWED_LEGACY_SEMANTIC_SOURCE_PATHS = {
    "src/kcs_adapters/approved_summary_semantic.py",
    "src/kcs_adapters/desktop_semantic_candidates.py",
    "src/kcs_adapters/desktop_semantic_providers.py",
    "src/kcs_core/__init__.py",
    "src/kcs_core/semantic_extraction.py",
}

EXPLICIT_REFERENCE_VALIDATION_EXEMPTION_CALL_PATHS = {
    "src/kcs_adapters/desktop_authoring_pipeline.py",
    "src/kcs_adapters/desktop_payload.py",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def _uses_explicit_reference_validation_exemption(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return any(
        isinstance(node, ast.Call)
        and any(
            keyword.arg == "explicit_existing_article_match"
            for keyword in node.keywords
        )
        for node in ast.walk(tree)
    )


def test_legacy_semantic_extraction_source_island_does_not_expand() -> None:
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if any(
            token in path.read_text(encoding="utf-8")
            for token in LEGACY_SEMANTIC_TOKENS
        )
    }

    unexpected_paths = actual_paths - ALLOWED_LEGACY_SEMANTIC_SOURCE_PATHS

    assert not unexpected_paths, sorted(unexpected_paths)


def test_core_package_does_not_import_adapter_package() -> None:
    violations = {
        path.relative_to(ROOT).as_posix(): sorted(
            module
            for module in _imported_modules(path)
            if module == "kcs_adapters" or module.startswith("kcs_adapters.")
        )
        for path in (ROOT / "src" / "kcs_core").rglob("*.py")
    }
    violations = {
        path: modules for path, modules in violations.items() if modules
    }

    assert not violations, violations


def test_explicit_reference_validation_exemption_call_island_does_not_expand() -> None:
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if _uses_explicit_reference_validation_exemption(path)
    }

    assert actual_paths == EXPLICIT_REFERENCE_VALIDATION_EXEMPTION_CALL_PATHS
