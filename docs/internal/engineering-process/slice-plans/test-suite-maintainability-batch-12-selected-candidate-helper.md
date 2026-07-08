# Test Suite Maintainability Batch 12: Selected Candidate Helper

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the helper introduced for the first selected provider candidate be made
less complex without weakening remaining-selection, next-arguments, or reviewer-
bundle assertions?

## Finding

After Batch 11, the file max was `_assert_first_selected_provider_candidate_draft()`
at `cc=17`. This helper had become the current hotspot because it kept a long
chain of scalar field assertions after earlier scenario extraction.

## Decision

Convert repeated scalar draft-result assertions into a field/value table while
keeping path-prefix, remaining-selection, remaining-candidate, and next-argument
assertions explicit.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused parent primary-selection scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| scalar draft-result fields | field/value table inside `_assert_first_selected_provider_candidate_draft()` | focused parent test passed |
| reviewer-bundle path prefixes | unchanged explicit assertions | focused parent test passed |
| remaining selection ref | unchanged explicit assertion | focused parent test passed |
| remaining item candidate | unchanged explicit assertion | focused parent test passed |
| next tool and next arguments | unchanged explicit assertions | focused parent test passed |

Review-only drift risks:

- reviewer should confirm the field/value table preserves all old exact values.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 12:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 233
cc_average: 6.35
max_cc: 17
high_complexity_functions: 85
```

After Batch 12:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 233
cc_average: 6.31
max_cc: 16
high_complexity_functions: 85
```

The current file max is `test_draft_article_primary_fixture_provider_supports_narrative_summary`.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- remaining-selection behavior preserved;
- reviewer-bundle path assertions preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this batch.
