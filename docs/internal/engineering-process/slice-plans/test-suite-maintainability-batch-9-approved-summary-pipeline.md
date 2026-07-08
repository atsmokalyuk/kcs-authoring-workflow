# Test Suite Maintainability Batch 9: Approved Summary Pipeline

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the approved-summary compact-ready pipeline scenario be made easier to
inspect without weakening success-status, safety flag, or compact-output
assertions?

## Finding

After Batch 8, `test_run_approved_summary_pipeline_returns_compact_ready_status()`
was tied for the file max at `cc=20`. The test body mixed the workflow call,
structured success fields, safety flags, no-provider/no-write fields, and
compact-output exclusions.

## Decision

Keep the workflow call in the test body and extract the output contract into
`_assert_approved_summary_pipeline_compact_ready()`.

The helper uses a field/value table for the structured compact-ready status and
the existing text-exclusion helper for forbidden raw output terms.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused approved-summary compact-ready scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| approved-summary pipeline result kind | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| success and no-failure fields | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| input safety and evidence validity fields | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| reviewer and draft-request readiness fields | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| original recommendation and article type fields | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| no auto-publish/public-output/provider-calls/write flags | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |
| compact-output exclusions | `_assert_approved_summary_pipeline_compact_ready()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the field/value table preserves all old exact field
  values and boolean assertions.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 9:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 229
cc_average: 6.56
max_cc: 20
high_complexity_functions: 86
```

After Batch 9:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 230
cc_average: 6.47
max_cc: 20
high_complexity_functions: 85
```

The file max now sits on the ambiguous-ticket semantic-review scenario.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- compact output exclusions preserved;
- no-write/no-provider/no-publish flags preserved.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Continue only if the ambiguous-ticket semantic-review scenario can be split by
assertion ownership without hiding the register-then-draft workflow order.
