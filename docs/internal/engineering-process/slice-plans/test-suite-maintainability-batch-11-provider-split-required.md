# Test Suite Maintainability Batch 11: Provider Split Required

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the primary-summary provider split-required scenario be made easier to
inspect without weakening provider-call, split-required, operator-choice, or
candidate assertions?

## Finding

After Batch 10, `test_draft_article_primary_summary_uses_provider_for_split_required()`
held the file max at `cc=19`. The test body mixed provider setup, provider-call
verification, split-required status fields, operator-choice wiring, and exact
candidate assertions.

## Decision

Keep provider setup, transport setup, and tool invocation in the scenario body.
Extract output assertions into:

- `_assert_provider_called_once_for_split_required()`;
- `_assert_primary_provider_split_required()`.

The split-required helper uses a field/value table for stable status fields and
keeps operator-choice and candidate assertions explicit.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused provider split-required scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| provider called once with approved summary text | `_assert_provider_called_once_for_split_required()` | focused test passed |
| split-required status fields | `_assert_primary_provider_split_required()` | focused test passed |
| operator selection ref prefix | `_assert_primary_provider_split_required()` | focused test passed |
| choice options mirror request options | `_assert_primary_provider_split_required()` | focused test passed |
| choice request mode and submit tool | `_assert_primary_provider_split_required()` | focused test passed |
| second candidate submit arguments | `_assert_primary_provider_split_required()` | focused test passed |
| submit-options and all-submit-arguments equality | `_assert_primary_provider_split_required()` | focused test passed |
| exact item candidates | `_assert_primary_provider_split_required()` | focused test passed |
| no inline reviewer HTML | `_assert_primary_provider_split_required()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the provider call expected text is unchanged;
- reviewer should confirm the split-required helper preserves all operator-
  choice equality assertions.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 11:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 231
cc_average: 6.41
max_cc: 19
high_complexity_functions: 85
```

After Batch 11:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 233
cc_average: 6.35
max_cc: 17
high_complexity_functions: 85
```

The current file max is a helper introduced by earlier extraction:
`_assert_first_selected_provider_candidate_draft`.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- provider-call assertion preserved;
- operator-choice and candidate assertions preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Continue only if the next target is a real scenario-level issue. The current max
is a helper, so it should be reviewed for possible table conversion before
opening another scenario.
