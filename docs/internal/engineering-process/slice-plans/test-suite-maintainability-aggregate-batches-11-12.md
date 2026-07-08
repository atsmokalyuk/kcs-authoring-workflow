# Test Suite Maintainability Aggregate Review: Batches 11-12

## Status

Aggregate review complete.

## Scope

Batches reviewed:

- Batch 11: provider split-required scenario
- Batch 12: selected-candidate helper cleanup

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Aggregate Findings

- Both batches followed reverse freeze: no `src/` files changed.
- Batch 11 preserved provider setup and tool invocation in the scenario body.
- Batch 12 addressed a helper hotspot created by earlier extraction instead of
  mining a new scenario.
- Both batches used field/value tables only for stable scalar output contracts.
- Focused tests passed after each batch.
- No assertion was intentionally removed, broadened, or changed from exact
  field/value checks into softer presence checks.

## Complexity Signals

Before Batch 11:

```text
functions_total: 231
cc_average: 6.41
max_cc: 19
high_complexity_functions: 85
```

After Batch 12:

```text
functions_total: 233
cc_average: 6.31
max_cc: 16
high_complexity_functions: 85
```

Overall since this branch started:

```text
max_cc: 56 -> 16
cc_average: 8.04 -> 6.31
high_complexity_functions: 88 -> 85
```

Interpretation:

- the branch continues to reduce the worst hotspot and average complexity;
- high-complexity count is now the slower signal because many remaining broad
  tests sit near the configured threshold;
- helper cleanups are acceptable when the helper itself becomes a measured
  hotspot and the parent scenario remains behavior-preserving.

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

- focused Batch 11 and Batch 12 tests passed;
- full Desktop characterization file passed;
- graph/freeze policy checks passed;
- Ruff passed for the touched test file;
- `git diff --check` passed.

Reviewed drift risks:

- provider-call assertion remains exact;
- split-required operator-choice equality assertions remain exact;
- selected-candidate remaining-selection assertions remain explicit;
- selected-candidate reviewer-bundle path assertions remain explicit;
- no source code changed.

Review-only drift risks:

- reviewer should confirm field/value tables preserved all old exact expected
  values.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Promotion And Demotion Scan

Promotion candidates:

- none new; field/value contract tables remain an existing checklist-level
  pattern for stable structured outputs.

Demotion candidates:

- none.

## Outcome

Continue only where the next high-complexity scenario has a clear output
contract split or where a previously introduced helper is itself the measured
hotspot.
