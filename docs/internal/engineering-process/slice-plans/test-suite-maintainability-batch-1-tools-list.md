# Test Suite Maintainability Batch 1: Desktop Tools List Contract

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the highest-complexity Desktop characterization test be made easier to
maintain without weakening assertions or changing runtime behavior?

## Finding

`test_tools_list_desktop_mode_exposes_aliases_only_with_safe_annotations()` was
the top measured repo complexity point at `cc=56`. The complexity came from a
large branch chain inside one test, not from runtime code.

The test asserted several independent contracts:

- exposed Desktop aliases;
- excluded internal validation tools;
- tool ordering and count;
- common Desktop tool annotations;
- per-tool schema properties;
- per-tool description terms;
- forbidden hidden aliases.

## Decision

Split the assertions into private test helpers:

- `_tools_by_name()`;
- `_assert_desktop_tool_contract()`;
- `_assert_schema_shape()`;
- `_assert_tool_annotations()`;
- `_assert_text_includes()`;
- `_assert_text_excludes()`;
- `_assert_register_clean_ticket_tool()`;
- `_assert_draft_article_tool()`;
- `_assert_prepare_semantic_review_tool()`.

Keep the main test as the owner of the overall tools/list contract and exact
tool set.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused tools/list test passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| exact Desktop tool set and excluded internal tools | unchanged main test | focused test passed |
| first three Desktop tools order | unchanged main test | focused test passed |
| common Desktop annotation/input/output contract | `_assert_desktop_tool_contract()` | focused test passed |
| register clean ticket terms/schema/annotations | `_assert_register_clean_ticket_tool()` | focused test passed |
| draft article terms/schema/forbidden aliases/annotations | `_assert_draft_article_tool()` | focused test passed |
| prepare semantic review terms/schema/annotations | `_assert_prepare_semantic_review_tool()` | focused test passed |
| submit semantic review and draft ticket assertions | existing helpers unchanged | focused test passed |

Review-only drift risks:

- reviewer should confirm that helper extraction did not turn an all-terms check
  into an any-term check.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 195
cc_average: 8.04
max_cc: 56
high_complexity_functions: 88
```

After:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 204
cc_average: 7.6
max_cc: 46
high_complexity_functions: 88
```

The repo max complexity moved from the tools/list contract test to the next
Desktop characterization test.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tools/list behavior unchanged;
- tool schemas unchanged;
- tool annotations unchanged;
- packet schemas unchanged;
- privacy/fail-closed/reviewer-bundle/publication/customer-reply boundaries
  unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Review the next hotspot:

- `test_author_approved_summary_returns_reviewer_only_draft`
