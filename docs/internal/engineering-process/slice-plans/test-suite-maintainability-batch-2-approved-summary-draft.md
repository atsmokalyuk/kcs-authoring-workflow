# Test Suite Maintainability Batch 2: Approved Summary Reviewer Draft

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the approved-summary reviewer-only draft characterization test be made
easier to review without weakening output, privacy, or no-publication
assertions?

## Finding

`test_author_approved_summary_returns_reviewer_only_draft()` was the current
file max after Batch 1 at `cc=46`. It asserted multiple contracts inline:

- approved-summary success flags;
- atomic item title;
- reviewer-only draft structure;
- preview text;
- quality gap marker;
- fenced HTML/JSON output shape;
- forbidden instruction copy;
- reviewer-only HTML sections;
- compact output privacy exclusions.

## Decision

Split contract groups into private helpers:

- `_assert_approved_summary_authoring_success()`;
- `_assert_monitoring_reviewer_only_preview_text()`;
- `_assert_monitoring_reviewer_only_draft()`;
- `_assert_reviewer_only_result_output()`;
- `_assert_monitoring_reviewer_only_html()`.

Keep the test as the owner of the overall approved-summary reviewer-only draft
scenario.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused approved-summary reviewer-only draft test passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| approved-summary success/status flags | `_assert_approved_summary_authoring_success()` | focused test passed |
| preview text terms | `_assert_monitoring_reviewer_only_preview_text()` | focused test passed |
| reviewer-only draft fields | `_assert_monitoring_reviewer_only_draft()` | focused test passed |
| fenced result output and forbidden instruction text | `_assert_reviewer_only_result_output()` | focused test passed |
| reviewer-only HTML section checks | `_assert_monitoring_reviewer_only_html()` | focused test passed |
| compact output privacy exclusions | `_assert_text_excludes()` | focused test passed |

Review-only drift risks:

- reviewer should confirm that forbidden-output checks remain all-terms
  exclusions and that the preview text remains excluded from result output.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 2:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 204
cc_average: 7.6
max_cc: 46
high_complexity_functions: 88
```

After Batch 2:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 209
cc_average: 7.35
max_cc: 41
high_complexity_functions: 88
```

The file max moved to the semantic-review excerpt characterization test.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- approved-summary reviewer-only draft behavior unchanged;
- reviewer-only HTML output assertions unchanged;
- privacy exclusions unchanged;
- publication/customer-reply behavior unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Review the next hotspot:

- `test_prepare_semantic_review_returns_bounded_selected_excerpts`
