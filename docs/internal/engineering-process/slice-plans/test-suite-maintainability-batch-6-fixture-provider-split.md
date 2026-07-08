# Test Suite Maintainability Batch 6: Fixture Provider Split

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the fixture-provider split scenario be made easier to inspect without
weakening split-required, operator-choice, selected-candidate, or generated HTML
assertions?

## Finding

After Batch 5, `test_draft_article_primary_fixture_provider_splits_items()`
held the file max at `cc=23`. The test body mixed the split-required payload
contract with the selected-candidate draft and HTML assertions.

## Decision

Keep the workflow order in the test body and extract assertion clusters into
private helpers:

- `_assert_fixture_provider_split_required()`;
- `_assert_fixture_provider_selected_candidate_draft()`.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused fixture-provider split scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| split-required debug/recommended-action/prompt-style assertions | `_assert_fixture_provider_split_required()` | focused test passed |
| operator choice request safety flags | `_assert_fixture_provider_split_required()` | focused test passed |
| first candidate submit arguments | `_assert_fixture_provider_split_required()` | focused test passed |
| submit-options and all-submit-arguments equality | `_assert_fixture_provider_split_required()` | focused test passed |
| exact two item candidates | `_assert_fixture_provider_split_required()` | focused test passed |
| no inline reviewer HTML in split result | `_assert_fixture_provider_split_required()` | focused test passed |
| selected second candidate draft fields | `_assert_fixture_provider_selected_candidate_draft()` | focused test passed |
| selected second candidate generated HTML contains expected title | `_assert_fixture_provider_selected_candidate_draft()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the helper keeps all operator safety flags as exact
  boolean assertions;
- reviewer should confirm the helper extraction did not hide the split-then-
  select workflow order.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 6:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 223
cc_average: 6.82
max_cc: 23
high_complexity_functions: 88
```

After Batch 6:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 225
cc_average: 6.77
max_cc: 21
high_complexity_functions: 88
```

The file max now sits on two fixture-provider scenarios at `cc=21`.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- operator-choice safety flags preserved;
- selected-candidate generated HTML assertion preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this batch.
