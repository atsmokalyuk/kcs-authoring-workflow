# KCS-14 Slice 9 Target 1: Packet Validation And KCS Decisions Audit

Status: design audit complete; no source refactor opened.

## Scope

Graph node:

- `packet_validation_decision`

Reviewed files:

- `src/kcs_core/models.py`
- `src/kcs_core/validation.py`
- `src/kcs_core/safety.py`
- `src/kcs_core/decision.py`
- `src/kcs_core/evidence_builder.py`
- `src/kcs_core/sanitizer.py`

Related tests:

- `tests/kcs_core/test_models.py`
- `tests/kcs_core/test_validation.py`
- `tests/kcs_core/test_safety.py`
- `tests/kcs_core/test_decision.py`
- `tests/kcs_core/test_evidence_builder.py`
- `tests/kcs_core/test_fixture_contracts.py`
- `tests/kcs_core/test_cli.py`

No runtime code was changed.

## Entry Question

Is validation, safety, and decision knowledge duplicated or leaking across
these files in a way that increases change amplification for KCS-15?

## Complexity Sensor

Command:

```bash
uv run python scripts/measure_complexity.py --paths src/kcs_core
```

Runtime core summary:

```text
files_scanned: 17
functions_total: 600
cc_average: 3.08
max_cc: 12
high_complexity_functions: 18
mi_average: 27.56
import_edges: 66
public_defs: 111
all_exports: 80
```

Relevant hotspots inside this node:

```text
src/kcs_core/models.py:_validate_validation_report_codes: cc=9
src/kcs_core/sanitizer.py:normalize_string_list: cc=9
src/kcs_core/safety.py:_strings_from: cc=8
src/kcs_core/safety.py:_contains_unsafe_identifier: cc=8
src/kcs_core/decision.py:_candidate_string_list: cc=8
```

Interpretation:

- this node is contract-dense but not a top runtime complexity hotspot;
- complexity is moderate and concentrated in validation/normalization helpers;
- cyclomatic complexity alone does not justify source movement.

## Ownership Assessment

Current ownership is coherent:

- `models.py` owns schema-versioned packet shapes, enum value contracts, packet
  serialization, and validation-report subdocument shape checks.
- `validation.py` owns evidence readiness blockers and warnings after safety
  validation.
- `safety.py` owns normalized evidence safety gates, visibility class checks,
  source-ref safety, and unsafe text detection.
- `decision.py` owns deterministic KCS action recommendation, split-item
  decision cards, reuse-match selection, override eligibility, and value-safe
  decision metadata.
- `evidence_builder.py` owns approved export-to-evidence packet construction.
- `sanitizer.py` owns strict JSON normalization and raw/private value
  screening before packet construction.

Import direction is simple:

- `sanitizer.py` is a low-level input normalizer.
- `safety.py` depends on packet shape and validates normalized evidence.
- `validation.py` depends on safety and adds readiness blockers.
- `decision.py` depends on models and validation.
- `evidence_builder.py` depends on sanitizer and safety to construct accepted
  evidence.
- `models.py` depends only on generic JSON helpers and contract errors.

## Ousterhout Assessment

### Deep Modules

`decision.py`, `safety.py`, and `models.py` are large relative to simple
helpers, but they hide meaningful contract logic behind stable public entry
points:

- `decide_kcs_action()`;
- `validate_evidence_safety()` / `ensure_evidence_safe()`;
- packet `from_json_dict()` / `to_json_dict()` methods.

Size alone is not a sufficient reason to split them.

### Information Hiding

The current split hides the right kinds of knowledge:

- callers do not need to know how safety scans nested evidence text;
- callers do not need to know how decision identity matching compares
  technical vs how-to articles;
- callers do not need to know nested validation-report subdocument rules;
- unsafe values are turned into value-free blocker/error codes.

### Duplication / Leakage

Potential duplication exists between `sanitizer.py` and `safety.py` because
both reject private-looking values.

This is currently acceptable because the modules operate at different
boundaries:

- `sanitizer.py` rejects unsafe raw JSON before evidence packet construction;
- `safety.py` rejects unsafe normalized evidence after packet construction.

Merging them would reduce some regex duplication but blur two safety gates and
increase risk.

### Temporal Decomposition

The files are not primarily split by execution order. They are split by
knowledge ownership:

- input normalization;
- evidence safety;
- evidence readiness;
- packet shape;
- action decision;
- evidence building.

That is the desired direction.

### Shallow Abstraction / Classitis Risk

Extracting small helper modules such as `decision_identity.py`,
`decision_split_items.py`, `validation_report_codes.py`, or
`safety_regexes.py` would add interfaces around already-private details unless
a concrete repeated-edit problem appears.

That would likely increase caller and maintainer navigation cost.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed;
- related tests already cover packet shape, auto-publish false enforcement,
  evidence readiness, safety/private-value rejection, decision outcomes,
  split-required behavior, builder safety, fixture contracts, and CLI boundary
  errors;
- complexity sensor was advisory only.

Reviewed drift risks:

- packet schemas must remain unchanged;
- `auto_publish_allowed=false` must remain enforced;
- decision blocker/status/recommended-action behavior must not drift;
- unsafe/private values must not be echoed in errors or serialized outputs;
- split-item decision behavior must remain deterministic;
- sanitizer and safety gates must remain separate fail-closed boundaries.

Review-only drift risks:

- refactoring decision identity matching could silently change reuse/update/
  flag/create behavior;
- refactoring sanitizer/safety regexes could change privacy false positives or
  false negatives;
- moving validation-report subdocument rules out of `models.py` could create a
  pass-through contract module unless the new owner hides real complexity.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Decision

Do not refactor `packet_validation_decision` in this pass.

Reason:

- current module boundaries are mostly ownership-based;
- measured complexity is moderate;
- tests are dense around the important runtime behavior;
- likely extraction targets would create shallow modules or blur fail-closed
  safety gates;
- KCS-15 is more likely to stress renderer/output behavior and semantic review
  boundaries than this node.

## Parked Follow-Ups

Only reopen this node if one of these triggers appears:

- KCS-15 requires repeated changes to validation-report subdocument fields;
- decision identity matching changes in multiple feature slices;
- sanitizer/safety false-positive or false-negative issues recur;
- packet schema evolution is explicitly approved;
- aggregate review records repeated `packet_validation_decision` ownership
  conflicts.

Possible future narrow questions:

- Should validation-report subdocument rules remain inside `models.py` or move
  to a deeper report-contract owner?
- Should decision identity key lists become local named tables if KCS-15
  changes matching behavior?
- Should sanitizer and safety share a small private pattern list, without
  merging their gate responsibilities?

None of these is currently strong enough for code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Target

Proceed to `semantic_review_fallback`.

That target has higher KCS-15 risk because it spans Desktop workflow,
provider output, source-ref validation, and candidate semantic extraction.
