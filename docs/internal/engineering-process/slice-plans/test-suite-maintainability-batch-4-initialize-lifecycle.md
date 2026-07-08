# Test Suite Maintainability Batch 4: Initialize Lifecycle

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the initialize lifecycle characterization test be made easier to maintain
without weakening capability or instruction-safety assertions?

## Finding

`test_initialize_lifecycle_and_capabilities_are_narrow()` was tied for the file
max at `cc=32` after Batch 3. It mixed lifecycle assertions, capabilities
shape, instruction required terms, and instruction forbidden terms in one test
body.

## Decision

Split capability and instruction assertions into private helpers:

- `_assert_narrow_initialize_capabilities()`;
- `_assert_desktop_initialize_instructions()`.

Keep the main test responsible for lifecycle ordering and initialized state.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused initialize lifecycle test passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| exact initialize capabilities shape | `_assert_narrow_initialize_capabilities()` | focused test passed |
| required instruction terms | `_assert_desktop_initialize_instructions()` | focused test passed |
| forbidden instruction terms | `_assert_desktop_initialize_instructions()` | focused test passed |
| before/after initialization lifecycle behavior | unchanged main test | focused test passed |
| logging capability absence | unchanged main test | focused test passed |

Review-only drift risks:

- reviewer should confirm instruction checks remain all-term inclusions and
  exclusions.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 4:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 217
cc_average: 7.08
max_cc: 32
high_complexity_functions: 88
```

After Batch 4:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 219
cc_average: 6.93
max_cc: 32
high_complexity_functions: 88
```

The file max remains `cc=32`, now held by one remaining Desktop primary
selection scenario.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- initialize lifecycle behavior unchanged;
- capabilities shape unchanged;
- instruction guidance and forbidden terms unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this batch.
