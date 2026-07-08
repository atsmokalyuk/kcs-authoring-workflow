# Test Suite Maintainability Batch 5: Primary Selection

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the pending provider candidate selection scenario be made easier to inspect
without weakening split, draft, remaining-selection, or reviewer-bundle
assertions?

## Finding

After Batch 4, `test_draft_article_primary_selection_uses_pending_provider_candidate()`
held the file max at `cc=32`. The test mixed provider setup, first selected
candidate assertions, first bundle artifact assertions, second selected
candidate assertions, and second bundle artifact assertions in one scenario
body.

## Decision

Keep the scenario flow in the test body, but extract repeated assertion groups
into private helpers:

- `_two_item_monitoring_provider()`;
- `_assert_first_selected_provider_candidate_draft()`;
- `_assert_first_selected_provider_candidate_bundle()`;
- `_assert_second_selected_provider_candidate_bundle()`.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused primary-selection scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| two-item provider candidate setup | `_two_item_monitoring_provider()` | focused test passed |
| first selected candidate structured result fields | `_assert_first_selected_provider_candidate_draft()` | focused test passed |
| remaining-selection payload and next arguments | `_assert_first_selected_provider_candidate_draft()` | focused test passed |
| first selected candidate reviewer-bundle HTML and hash assertions | `_assert_first_selected_provider_candidate_bundle()` | focused test passed |
| second selected candidate draft fields and no remaining selection | `_assert_second_selected_provider_candidate_bundle()` | focused test passed |
| second selected candidate reviewer-bundle HTML assertion | `_assert_second_selected_provider_candidate_bundle()` | focused test passed |

Review-only drift risks:

- reviewer should confirm all old assertions moved into the helpers without
  changing exact expected field values;
- reviewer should confirm helper extraction did not hide workflow ordering in
  the main scenario body.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 5:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 219
cc_average: 6.93
max_cc: 32
high_complexity_functions: 88
```

After Batch 5:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 223
cc_average: 6.82
max_cc: 23
high_complexity_functions: 88
```

The file max moved from the primary-selection scenario to
`test_draft_article_primary_fixture_provider_splits_items`.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- reviewer-bundle assertions preserved;
- remaining-selection and next-arguments assertions preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Continue only if the next hotspot has a clear scenario-level question:

- `test_draft_article_primary_fixture_provider_splits_items`
