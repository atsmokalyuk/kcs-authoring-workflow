# Test Suite Maintainability Aggregate Review: Batches 7-8

## Status

Aggregate review complete.

## Scope

Batches reviewed:

- Batch 7: fixture-provider bundle writing
- Batch 8: raw-ticket fixture-provider summary

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Aggregate Findings

- Both batches followed reverse freeze: no `src/` files changed.
- Both batches kept workflow calls in the scenario body and moved only
  assertion groups into private helpers.
- Both batches used term or field tables where the old assertion chain was
  long and contract-like.
- Focused scenario tests passed after each batch.
- No assertions were intentionally removed, broadened, or changed from exact
  field/value checks into softer presence checks.

## Complexity Signals

Before Batch 7:

```text
functions_total: 225
cc_average: 6.77
max_cc: 21
high_complexity_functions: 88
```

After Batch 8:

```text
functions_total: 229
cc_average: 6.56
max_cc: 20
high_complexity_functions: 86
```

Overall since this branch started:

```text
max_cc: 56 -> 20
cc_average: 8.04 -> 6.56
high_complexity_functions: 88 -> 86
```

Interpretation:

- the fixture-provider hotspot group is no longer the file maximum;
- the branch has started reducing high-complexity count, not only max function
  complexity;
- helper count increased, but the added helpers own concrete assertion groups
  and did not expand public/runtime surface.

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

- focused Batch 7 and Batch 8 scenario tests passed;
- full Desktop characterization file passed;
- graph/freeze policy checks passed;
- Ruff passed for the touched test file;
- `git diff --check` passed.

Reviewed drift risks:

- bundle-writing draft status fields stayed exact field/value assertions;
- operator guidance include/exclude terms stayed explicit;
- raw-ticket placeholder exclusions stayed explicit;
- raw-ticket command/config HTML terms stayed explicit;
- no source code changed.

Review-only drift risks:

- reviewer should confirm term tables did not drop old wording while making the
  scenarios easier to inspect.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Promotion And Demotion Scan

Promotion candidates:

- none new; term-table guidance is already an established checklist-level
  pattern from KCS-14 and this branch continues to use it with scenario-level
  justification.

Demotion candidates:

- none.

## Outcome

Continue only where the next high-complexity scenario has an explicit
maintainability question and focused assertions can be preserved exactly.
