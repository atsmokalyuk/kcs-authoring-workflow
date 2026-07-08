# Test Suite Maintainability Batch 10: Ambiguous Semantic Review

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the registered ambiguous-ticket semantic-review scenario be made easier to
inspect without hiding the register-then-draft workflow order or weakening the
semantic-review-required blocker assertions?

## Finding

After Batch 9, `test_draft_article_registered_ambiguous_ticket_requires_semantic_review()`
held the file max at `cc=20`. The test body mixed fixture setup, clean-ticket
registration, draft-tool invocation, and semantic-review-required output
contract assertions.

## Decision

Keep environment setup, transcript registration, and draft-tool invocation in
the scenario body. Extract only the semantic-review-required payload contract
into `_assert_ambiguous_ticket_semantic_review_required()`.

The helper uses a field/value table for stable status fields and keeps bounded
excerpt, packet hash, reviewer HTML absence, and manual-draft blocker assertions
explicit.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused ambiguous-ticket semantic-review scenario passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| blocked semantic-review status fields | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| next tool and next arguments | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| excerpt count and byte bound | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| semantic-review packet hash type | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| no draft/no bundle/no manual draft fields | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| ticket ref preservation | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| no inline reviewer HTML | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |
| manual-draft blocker text | `_assert_ambiguous_ticket_semantic_review_required()` | focused test passed |

Review-only drift risks:

- reviewer should confirm the register-then-draft order remains visible in the
  main test body;
- reviewer should confirm the helper preserves every old semantic-review
  blocker assertion.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 10:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 230
cc_average: 6.47
max_cc: 20
high_complexity_functions: 85
```

After Batch 10:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 231
cc_average: 6.41
max_cc: 19
high_complexity_functions: 85
```

The file max now sits on the provider split-required primary summary scenario.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- Desktop tool surface unchanged;
- packet schemas unchanged;
- semantic-review-required blocker behavior preserved;
- manual/freehand drafting remains blocked.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this batch.
