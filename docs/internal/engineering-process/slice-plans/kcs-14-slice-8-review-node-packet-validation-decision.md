# KCS-14 Slice 8 Review Node: Packet Validation And KCS Decisions

## Status

Review-only complete.

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

## Ownership Assessment

The node owns deterministic packet and decision behavior:

- KCS packet model contracts and schema versions;
- evidence safety validation;
- evidence readiness validation;
- deterministic action recommendation and blocker codes;
- approved sanitized evidence packet construction;
- sanitizer/value-safety helpers used by packet boundaries.

The current split is acceptable:

- `models.py` owns packet dataclasses, schema parsing, field validation, and
  serialization contracts.
- `safety.py` owns fail-closed evidence safety checks.
- `validation.py` owns readiness blockers and warnings for accepted evidence.
- `decision.py` owns deterministic KCS action recommendations.
- `evidence_builder.py` owns construction from approved sanitized exports.
- `sanitizer.py` owns shared value-safety normalization and checks.

This is a stable high-invariant core boundary.

## Must Not Own

This node must not own:

- Desktop transport;
- provider calls;
- renderer presentation details;
- local reviewer-bundle paths.

The reviewed files preserve those boundaries.

## Ousterhout Lens

- Information hiding: packet invariants, blocker codes, and value-safety checks
  are owned by core modules rather than leaking into Desktop adapters.
- Deep modules: `decision.py`, `safety.py`, and `validation.py` expose compact
  functions over dense decision and blocker logic.
- Change amplification: refactoring this node has high blast radius because
  many downstream modules depend on exact schema, blocker, and decision
  behavior.
- Shallow abstraction risk: extracting small validators without a concrete
  behavior question would add interfaces around stable contract code.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover packet model parsing/serialization, validation blockers,
  safety blockers, deterministic decisions, approved evidence construction,
  fixture contracts, and CLI validation behavior

Reviewed drift risks:

- `auto_publish_allowed` remains false in packet and decision outputs.
- privacy and evidence boundaries remain fail-closed.
- manual/freehand drafting remains blocked by higher workflow layers and is not
  introduced in the core decision layer.
- provider output cannot decide, render, publish, or write artifacts from this
  node.
- decision/blocker codes remain deterministic and value-safe.

Review-only drift risks:

- `models.py` is broad because it owns several packet families. Any future
  split must preserve schema-version parsing and public imports, and should be
  staged behind snapshot/freeze checks.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future refactor should require a narrow ownership question, such as:

- Should packet model families be split while preserving root imports and
  schema snapshots?
- Should sanitizer/value-safety helpers move only if repeated callers expose a
  clearer deep module boundary?

Neither question is currently supported by repeated drift, review friction, or
sensor evidence.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Nodes

Continue review-only coverage with lower-risk or deferred nodes only after an
aggregate review.
