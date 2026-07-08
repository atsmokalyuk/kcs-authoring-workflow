# Test Suite Maintainability Aggregate Review: Batches 1-2

## Status

Aggregate review complete.

## Scope

Batches reviewed:

- Batch 1: Desktop tools/list contract
- Batch 2: Approved-summary reviewer-only draft

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Aggregate Findings

- Both batches followed reverse freeze: no `src/` files changed.
- Both batches extracted assertion groups into private test helpers.
- No assertion was intentionally removed or weakened.
- No runtime behavior, tool schema, packet schema, publication, reviewer-bundle,
  privacy, or fail-closed boundary changed.
- Full Desktop characterization file passed after each batch.

## Complexity Signals

Before Batch 1:

```text
max_cc: 56
cc_average: 8.04
high_complexity_functions: 88
```

After Batch 2:

```text
max_cc: 41
cc_average: 7.35
high_complexity_functions: 88
```

Interpretation:

- the top two hotspots were reduced materially;
- high-complexity count did not drop yet because the file still has many large
  characterization scenarios;
- the next max is `test_prepare_semantic_review_returns_bounded_selected_excerpts`.

## Triage

`map_error`:

- no

`process_error`:

- no

`architecture_error`:

- no

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- full `tests/kcs_adapters/test_mcp_desktop.py` passed;
- graph/freeze policy checks passed;
- Ruff passed for the touched test file.

Reviewed drift risks:

- helper extraction retained all expected terms as all-term assertions;
- forbidden terms remain explicit exclusions;
- no source code changed.

Review-only drift risks:

- reviewer should verify that helper extraction did not hide or reorder
  scenario-specific expectations in a way that reduces failure locality.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Promotion And Demotion Scan

Promotion candidates:

- none new.

Demotion candidates:

- none.

## Outcome

Continue with the next hotspot only if it has an obvious assertion-group split
that preserves behavior and improves reviewability.

Next candidate:

- `test_prepare_semantic_review_returns_bounded_selected_excerpts`
