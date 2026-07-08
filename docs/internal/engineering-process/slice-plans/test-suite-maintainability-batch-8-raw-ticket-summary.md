# Test Suite Maintainability Batch 8: Raw Ticket Summary

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the raw-ticket fixture-provider scenario be made easier to inspect without
weakening draft result, blocker-gap, domain HTML, or placeholder-exclusion
assertions?

## Finding

After Batch 7, `test_draft_article_primary_fixture_provider_supports_raw_ticket_summary()`
held the file max at `cc=21`. The test body mixed the workflow call, structured
draft result assertions, blocker-gap filtering, domain-specific rendered HTML
terms, command/config markup, and placeholder exclusions.

## Decision

Keep the workflow call in the test body and extract the assertion owners:

- `_assert_raw_ticket_fixture_provider_draft_result()`;
- `_assert_raw_ticket_fixture_provider_html()`.

The rendered HTML helper uses include/exclude term tables to preserve exact
domain terms without spreading a long assertion chain across the scenario body.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused raw-ticket fixture-provider scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| structured draft result fields | `_assert_raw_ticket_fixture_provider_draft_result()` | focused test passed |
| no blocker quality gaps | `_assert_raw_ticket_fixture_provider_draft_result()` | focused test passed |
| Linux platform and Cause heading | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| collectd configuration cause wording | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| placeholder exclusions | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| SSH reference link | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| backup command markup | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| disable config command markup | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |
| restart command term | `_assert_raw_ticket_fixture_provider_html()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the include/exclude tables preserve all old raw-ticket
  HTML terms exactly;
- reviewer should confirm no placeholder exclusion was dropped.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 8:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 227
cc_average: 6.67
max_cc: 21
high_complexity_functions: 87
```

After Batch 8:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 229
cc_average: 6.56
max_cc: 20
high_complexity_functions: 86
```

The file max now sits outside the fixture-provider block.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- raw-ticket HTML domain assertions preserved;
- placeholder exclusions preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this batch.
