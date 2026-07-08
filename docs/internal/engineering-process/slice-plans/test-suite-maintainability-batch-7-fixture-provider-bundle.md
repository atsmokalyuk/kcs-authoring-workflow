# Test Suite Maintainability Batch 7: Fixture Provider Bundle

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the fixture-provider bundle-writing scenario be made easier to inspect
without weakening draft status, reviewer-bundle artifact, or operator guidance
assertions?

## Finding

After Batch 6, `test_draft_article_primary_fixture_provider_writes_bundle()`
was tied for the file max at `cc=21`. The test body mixed the workflow call,
structured draft result fields, reviewer-bundle file checks, generated HTML
checks, and final operator guidance text.

## Decision

Keep the workflow call in the test body and extract the two assertion owners:

- `_assert_fixture_provider_bundle_draft_result()`;
- `_assert_fixture_provider_bundle_artifacts()`.

The structured result helper uses a field/value table so exact assertions stay
visible without creating another high-complexity helper.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused bundle-writing scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| structured draft result fields | `_assert_fixture_provider_bundle_draft_result()` | focused test passed |
| reviewer-bundle path prefix assertion | `_assert_fixture_provider_bundle_draft_result()` | focused test passed |
| no inline reviewer HTML in structured result | `_assert_fixture_provider_bundle_draft_result()` | focused test passed |
| reviewer-only HTML file path construction and read | `_assert_fixture_provider_bundle_artifacts()` | focused test passed |
| generated HTML contains Resolution heading | `_assert_fixture_provider_bundle_artifacts()` | focused test passed |
| result output is not fenced HTML | `_assert_fixture_provider_bundle_artifacts()` | focused test passed |
| required operator guidance terms | `_assert_fixture_provider_bundle_artifacts()` | focused test passed |
| forbidden operator guidance terms | `_assert_fixture_provider_bundle_artifacts()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the field/value table preserves the old exact field
  values and boolean assertions;
- reviewer should confirm the text include/exclude helpers preserve all old
  operator guidance terms.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 7:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 225
cc_average: 6.77
max_cc: 21
high_complexity_functions: 88
```

After Batch 7:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 227
cc_average: 6.67
max_cc: 21
high_complexity_functions: 87
```

The file max remains `cc=21`, now held by the raw-ticket fixture-provider
scenario.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- reviewer-bundle artifact assertions preserved;
- operator guidance include/exclude assertions preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Continue only if the next raw-ticket fixture-provider hotspot has a concrete
scenario-level question and can preserve all domain-specific HTML assertions.
