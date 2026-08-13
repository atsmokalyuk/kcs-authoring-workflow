from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROCESS_ROOT = ROOT / "docs" / "internal" / "engineering-process"
CATALOG_PATH = ROOT / "engineering-playbook" / "ddd-universal-core.json"
REGISTRY_PATH = PROCESS_ROOT / "engineering-rule-portability.md"

CANONICAL_RULE_ID_RE = re.compile(r"ENG-PORT-(?:DISC|DES|DEL)-\d{3}\Z")

EXPECTED_EXTRACTED = {
    "ENG-PORT-DISC-001",
    "ENG-PORT-DISC-002",
    "ENG-PORT-DES-004",
    "ENG-PORT-DES-007",
    "ENG-PORT-DES-010",
    "ENG-PORT-DEL-008",
    "ENG-PORT-DEL-010",
    "ENG-PORT-DEL-011",
    "ENG-PORT-DEL-012",
}

EXPECTED_FIELD_ADVISORY = {
    "ENG-PORT-DES-001",
    "ENG-PORT-DEL-006",
}

EXPECTED_SHADOW = {
    "ENG-PORT-DISC-003",
    "ENG-PORT-DISC-006",
    "ENG-PORT-DES-002",
    "ENG-PORT-DES-003",
    "ENG-PORT-DES-006",
    "ENG-PORT-DES-008",
    "ENG-PORT-DES-011",
    "ENG-PORT-DES-012",
    "ENG-PORT-DEL-003",
    "ENG-PORT-DEL-004",
    "ENG-PORT-DEL-007",
    "ENG-PORT-DEL-009",
}

EXPECTED_REFERENCE = {
    "ENG-PORT-DISC-004",
    "ENG-PORT-DISC-005",
    "ENG-PORT-DES-009",
    "ENG-PORT-DEL-001",
    "ENG-PORT-DEL-002",
}

EXPECTED_EXCLUDED = {
    "ENG-PORT-DES-005",
    "ENG-PORT-DEL-005",
}

EXPECTED_SHADOW_OUTCOMES = {
    "ENG-PORT-DISC-003": (
        "Connect stakeholder context, requirements and constraints to measurable "
        "evaluation and correction."
    ),
    "ENG-PORT-DISC-006": (
        "Verify a material external capability in conditions relevant to the "
        "intended design."
    ),
    "ENG-PORT-DES-002": (
        "Identify, control and evaluate intended changes against the existing baseline."
    ),
    "ENG-PORT-DES-003": ("Demonstrate behavior preservation with traceable evidence."),
    "ENG-PORT-DES-006": (
        "Characterize compatibility-sensitive unchanged behavior and residual "
        "risk before change closure."
    ),
    "ENG-PORT-DES-008": (
        "Make a material human decision ready with context, options, consequences, "
        "uncertainty and residual risk."
    ),
    "ENG-PORT-DES-011": (
        "Ensure a claimed deterministic invariant is evaluatable and cannot be "
        "bypassed through supported entrypoints."
    ),
    "ENG-PORT-DES-012": (
        "Collect proportional human-centred evidence before committing to a "
        "material interaction design."
    ),
    "ENG-PORT-DEL-003": (
        "Use recurring root causes and findings to improve process or tooling."
    ),
    "ENG-PORT-DEL-004": (
        "Close a material change with validation, drift review and explicit "
        "residual risk."
    ),
    "ENG-PORT-DEL-007": (
        "Establish provenance and privacy suitability for sensitive, sanitized or "
        "derived fixtures."
    ),
    "ENG-PORT-DEL-009": (
        "Prove current source, build, and artifact identity before relying on an "
        "installed trial."
    ),
}

AUTHORITATIVE_SEMANTIC_FIELDS = {
    "trigger",
    "applicability",
    "invariant",
    "expected_outcome",
    "authority_boundary",
    "stop_or_narrow",
    "limitations",
    "non_goals",
}

PROJECT_SPECIFIC_MECHANISMS = (
    "kcs",
    "plesk",
    "understanding tool",
    "ai engineer",
    "etag",
    "idempotency key",
    "replay cache",
    "ttl",
    "launchctl",
    "mcpb",
    "zendesk",
    "claude",
    "docs/internal/",
    "tests/",
    "src/",
)


def _load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _rules_by_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {rule["rule_id"]: rule for rule in catalog["rules"]}


def _registry_statuses() -> dict[str, str]:
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    candidate_section = registry.split("## Candidate Registry", 1)[1].split(
        "## Registry Maintenance", 1
    )[0]
    rows = [
        [part.strip() for part in line.strip().strip("|").split("|")]
        for line in candidate_section.splitlines()
        if line.startswith("| ENG-PORT-")
    ]
    return {row[0]: row[4] for row in rows}


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    raise AssertionError(f"unexpected semantic value: {value!r}")


def test_catalog_has_exact_complete_disjoint_universal_core_membership() -> None:
    catalog = _load_catalog()
    rule_ids = [rule["rule_id"] for rule in catalog["rules"]]
    excluded_ids = {
        entry["rule_id"] for entry in catalog["excluded_project_local_rules"]
    }
    expected_core = (
        EXPECTED_EXTRACTED
        | EXPECTED_FIELD_ADVISORY
        | EXPECTED_SHADOW
        | EXPECTED_REFERENCE
    )

    assert catalog["schema_version"] == "engineering_ddd_catalog_v1"
    assert catalog["kcs17_execution"] == "locked"
    assert len(rule_ids) == 28
    assert len(set(rule_ids)) == len(rule_ids)
    assert all(CANONICAL_RULE_ID_RE.fullmatch(rule_id) for rule_id in rule_ids)
    assert set(rule_ids) == expected_core
    assert excluded_ids == EXPECTED_EXCLUDED
    assert excluded_ids.isdisjoint(rule_ids)
    assert len(expected_core | excluded_ids) == 30


def test_catalog_authority_is_limited_to_independently_ready_rules() -> None:
    catalog = _load_catalog()
    rules = _rules_by_id(catalog)
    authoritative = {
        rule_id for rule_id, rule in rules.items() if rule["authoritative"] is True
    }

    assert authoritative == EXPECTED_EXTRACTED
    assert catalog["authority_contract"]["authoritative_treatment"] == (
        "authoritative-extracted-beta"
    )
    for rule_id in EXPECTED_EXTRACTED:
        rule = rules[rule_id]
        assert rule["catalog_lane"] == "field-evidence"
        assert rule["portability_status"] == "extracted-beta"
        assert rule["kit_treatment"] == "authoritative-extracted-beta"
        assert rule["source_revision"] == catalog["reviewed_source_revision"]
        assert rule["extraction_revision"] == catalog["catalog_revision"]
        assert rule["source_review_id"].startswith("SR-")
        assert len(rule["supporting_contexts"]) >= 2
        assert rule["limitations"]
        assert rule["extraction_review_decision"].startswith("approved-kcs-16")
        assert AUTHORITATIVE_SEMANTIC_FIELDS <= rule.keys()
        assert all(rule[field] for field in AUTHORITATIVE_SEMANTIC_FIELDS)


def test_catalog_advisory_lanes_cannot_be_consumed_as_authority() -> None:
    catalog = _load_catalog()
    rules = _rules_by_id(catalog)
    expected_treatments = {
        **{
            rule_id: "advisory-field-evidence-candidate"
            for rule_id in EXPECTED_FIELD_ADVISORY
        },
        **{rule_id: "advisory-standards-shadow" for rule_id in EXPECTED_SHADOW},
        **{rule_id: "advisory-reference-only" for rule_id in EXPECTED_REFERENCE},
    }

    assert set(catalog["authority_contract"]["advisory_treatments"]) == set(
        expected_treatments.values()
    )
    for rule_id, expected_treatment in expected_treatments.items():
        rule = rules[rule_id]
        assert rule["authoritative"] is False
        assert rule["kit_treatment"] == expected_treatment
        assert rule["missing_gate"]
        assert rule["extraction_review_decision"] == "not-approved-advisory-only"
        assert rule["portability_status"] != "extracted-beta"

    assert {
        rule_id
        for rule_id, rule in rules.items()
        if rule["kit_treatment"] == "advisory-field-evidence-candidate"
    } == EXPECTED_FIELD_ADVISORY
    assert all(
        rules[rule_id]["portability_status"] == "external-trial-active"
        for rule_id in EXPECTED_FIELD_ADVISORY
    )


def test_catalog_statuses_match_source_registry_treatment_independently() -> None:
    rules = _rules_by_id(_load_catalog())
    registry_statuses = _registry_statuses()

    assert set(rules) == set(registry_statuses) - EXPECTED_EXCLUDED
    for rule_id, rule in rules.items():
        assert rule["portability_status"] == registry_statuses[rule_id]


def test_shadow_support_is_exact_outcome_level_and_bounded() -> None:
    catalog = _load_catalog()
    rules = _rules_by_id(catalog)
    prohibited_outcome_claims = (
        "conform",
        "certif",
        "field usefulness",
        "implementation correctness",
        "runtime capability",
        "extraction readiness",
    )

    assert "does not establish" in catalog["authority_contract"]["standards_boundary"]
    for rule_id, expected_outcome in EXPECTED_SHADOW_OUTCOMES.items():
        rule = rules[rule_id]
        support = rule["standards_support"]
        assert rule["catalog_lane"] == "standards-backed-shadow"
        assert support["sources"]
        assert support["outcome"] == expected_outcome
        assert support["limitations"]
        outcome = support["outcome"].lower()
        assert not any(claim in outcome for claim in prohibited_outcome_claims)


def test_reference_entries_make_no_standards_or_field_authority_claim() -> None:
    rules = _rules_by_id(_load_catalog())

    for rule_id in EXPECTED_REFERENCE:
        rule = rules[rule_id]
        assert rule["catalog_lane"] == "reference-only"
        assert rule["standards_support"] is None
        limitations = rule["advisory_limitations"].lower()
        assert "reference" in limitations
        assert "authority" in limitations or "authoritative" in limitations
        assert "no claim" in limitations or re.search(
            r"(?:no|not) external validation", limitations
        )


def test_authoritative_semantics_exclude_project_specific_mechanisms() -> None:
    rules = _rules_by_id(_load_catalog())

    for rule_id in EXPECTED_EXTRACTED:
        rule = rules[rule_id]
        semantic_text = " ".join(
            _flatten_text(rule[field]) for field in AUTHORITATIVE_SEMANTIC_FIELDS
        ).lower()
        leaked = [
            mechanism
            for mechanism in PROJECT_SPECIFIC_MECHANISMS
            if mechanism in semantic_text
        ]
        assert not leaked, f"{rule_id} leaks project mechanism(s): {leaked}"


def test_kcs16_stabilized_wording_keeps_recorded_evidence_boundaries() -> None:
    rules = _rules_by_id(_load_catalog())

    assert (
        "does not grant decision authority" in rules["ENG-PORT-DISC-002"]["invariant"]
    )
    assert "it does not validate content" in rules["ENG-PORT-DES-004"]["invariant"]
    assert "mechanical leaf exception" in rules["ENG-PORT-DES-010"]["applicability"]
    assert (
        "target-appropriate mechanism"
        in rules["ENG-PORT-DEL-010"]["authority_boundary"]
    )
    assert (
        "it is not a default for every change" in rules["ENG-PORT-DEL-012"]["invariant"]
    )
