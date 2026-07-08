# Test Suite Maintainability Aggregate Review: Batches 9-10

## Status

Aggregate review complete.

## Scope

Batches reviewed:

- Batch 9: approved-summary compact-ready pipeline
- Batch 10: ambiguous-ticket semantic-review requirement

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Aggregate Findings

- Both batches followed reverse freeze: no `src/` files changed.
- Both batches kept workflow calls in the scenario body.
- Batch 9 extracted compact-ready pipeline status fields into a field/value
  helper.
- Batch 10 extracted semantic-review-required blocker fields into a field/value
  helper while keeping register-then-draft ordering visible.
- Focused scenario tests passed after each batch.
- No assertion was intentionally removed, broadened, or changed from exact
  field/value checks into softer presence checks.

## Complexity Signals

Before Batch 9:

```text
functions_total: 229
cc_average: 6.56
max_cc: 20
high_complexity_functions: 86
```

After Batch 10:

```text
functions_total: 231
cc_average: 6.41
max_cc: 19
high_complexity_functions: 85
```

Overall since this branch started:

```text
max_cc: 56 -> 19
cc_average: 8.04 -> 6.41
high_complexity_functions: 88 -> 85
```

Interpretation:

- the branch continues to reduce the worst hotspot and the high-complexity
  count;
- field/value tables are useful when a scenario owns a stable structured output
  contract;
- the pattern should remain scoped to contract-like assertions, not general
  test rewriting.

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

- focused Batch 9 and Batch 10 scenario tests passed;
- full Desktop characterization file passed;
- graph/freeze policy checks passed;
- Ruff passed for the touched test file;
- `git diff --check` passed.

Reviewed drift risks:

- approved-summary compact status fields remain exact;
- compact output exclusions remain explicit;
- ambiguous-ticket register-then-draft workflow order remains visible;
- semantic-review-required blocker fields remain exact;
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
contract split and focused assertions can be preserved exactly.
