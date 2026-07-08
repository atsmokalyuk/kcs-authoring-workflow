# KCS-14 Slice 8 Review Node: engineering_policy_tests

Status: review-only complete.

## Scope

Graph node:

- `engineering_policy_tests`

Node owns:

- KCS-14 deterministic policy checks;
- documentation and process guardrail tests;
- code-review graph coverage checks;
- advisory complexity measurement entrypoint.

Node must not own:

- runtime KCS behavior;
- Desktop behavior;
- packet schemas;
- provider behavior.

Files reviewed:

- `scripts/measure_complexity.py`
- `tests/policy/test_code_review_graph_policy.py`
- `tests/policy/test_complexity_measurement.py`
- `tests/policy/test_functional_test_policy.py`
- `tests/policy/test_kcs14_docs_policy.py`
- `tests/policy/test_kcs14_freeze_snapshots.py`
- `tests/policy/test_review_context_policy.py`
- `tests/policy/test_tool_entrypoints.py`

## Review Question

Does this node need refactor now, or is it stable enough as the deterministic
guardrail layer for KCS-14?

## Findings

Policy tests are doing the intended job:

- graph coverage and hash checks are dynamic rather than hardcoded to a fixed
  file count;
- review-context tests anchor promotion cadence, forbidden packet content,
  behavior-drift mapping, and complexity closeout fields;
- tool-entrypoint tests keep official commands visible and help-liveness
  checked;
- freeze/snapshot tests protect runtime contracts before refactor;
- fixture/provenance tests keep functional-test rules from becoming chat-only
  advice;
- the complexity sensor remains advisory and does not block on metric values.

Potential brittleness:

- several tests intentionally check exact process phrases. This is acceptable
  while they protect authoritative policy wording, but future wording-only doc
  edits must update tests intentionally rather than weakening them.
- policy tests are not runtime behavior tests. They should remain in the
  engineering-policy layer and should not be used as proof that KCS runtime
  behavior is correct.

## Ousterhout Lens

The node is intentionally shallow at the individual test level but deep enough
as a module boundary: callers need to know "run policy tests" rather than every
individual grep or doc anchor.

The current design hides useful complexity:

- graph staleness and path coverage;
- forbidden review-packet content;
- active process source-of-truth drift;
- command-surface drift;
- fixture provenance and privacy markers.

No classitis or helper sprawl issue is visible in this node that justifies a
refactor now. The cost of splitting policy tests further would likely increase
the number of files a future agent must inspect.

## Behavior Drift Check

Behavior change intended:

- no.

Mechanical checks:

- policy tests pass as a suite;
- graph hash checks cover policy files that are graph-owned;
- complexity measurement remains advisory.

Reviewed drift risks:

- no runtime/source behavior touched;
- no policy test converted a judgment-only design question into a blocking
  regex;
- no private/local artifact requirement introduced.

Review-only drift risks:

- exact phrase anchors can become stale if process docs are reorganized. This
  is acceptable when the test protects an authoritative rule, but should be
  reviewed during doc rewrites.

Verdict:

- no code refactor needed for this node now.

## Decision

Status for this node:

- `review-only-complete`.

Recommended action:

- keep current structure;
- do not split policy tests only to reduce file size;
- revisit only if a policy test becomes noisy, blocks legitimate doc movement,
  or duplicates another authoritative check.

Promotion candidates:

- none. Existing Slice 7 promotions already cover the active policy-review
  backlog.

Demotion candidates:

- none. No false-positive evidence from the current review.

## Next Node

Recommended next review-only node:

- `desktop_tool_surface`

Reason:

- high-value boundary;
- protected by freeze/snapshot checks;
- result-shaping ownership decision already exists;
- review can classify whether more source refactor is justified before opening
  high-risk files.
