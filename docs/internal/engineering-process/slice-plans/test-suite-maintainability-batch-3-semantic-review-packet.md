# Test Suite Maintainability Batch 3: Semantic Review Packet

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Changed test file:

- `tests/kcs_adapters/test_mcp_desktop.py`

Runtime source files:

- none

## Entry Question

Can the semantic-review packet characterization test be made easier to review
without weakening excerpt bounds, submit-shape, or safety assertions?

## Finding

`test_prepare_semantic_review_returns_bounded_selected_excerpts()` was the file
max after Batch 2 at `cc=41`. The test mixed setup, packet header checks,
excerpt bounds, source-ref rules, submit-shape assertions, candidate metadata,
prompt text, and safety exclusions in one block.

## Decision

Split the scenario into private test helpers:

- `_ambiguous_semantic_review_ticket_text()`;
- `_prepared_semantic_review_response()`;
- `_assert_semantic_review_packet_header()`;
- `_assert_semantic_review_packet_bounds()`;
- `_assert_semantic_review_required_submit_shape()`;
- `_assert_semantic_review_candidate_field_metadata()`;
- `_assert_semantic_review_prompt_text()`;
- `_assert_semantic_review_packet_safety()`.

Keep the public test as the owner of the bounded selected-excerpt scenario.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused semantic-review packet test passed;
- Ruff passed for the touched test file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| noisy transcript setup | `_ambiguous_semantic_review_ticket_text()` | focused test passed |
| register/draft/prepare sequence | `_prepared_semantic_review_response()` | focused test passed |
| packet header/schema/ref/tool fields | `_assert_semantic_review_packet_header()` | focused test passed |
| excerpt count, byte limit, selected excerpt refs | `_assert_semantic_review_packet_bounds()` | focused test passed |
| required submit shape and item field types | `_assert_semantic_review_required_submit_shape()` | focused test passed |
| candidate field metadata and count policy | `_assert_semantic_review_candidate_field_metadata()` | focused test passed |
| human prompt guidance text | `_assert_semantic_review_prompt_text()` | focused test passed |
| no draft/manual/local-path/full-ticket safety checks | `_assert_semantic_review_packet_safety()` | focused test passed |

Review-only drift risks:

- reviewer should confirm that prompt guidance checks remain all-terms
  inclusions and that sentinel exclusion remains checked against the full
  packet text.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before Batch 3:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 209
cc_average: 7.35
max_cc: 41
high_complexity_functions: 88
```

After Batch 3:

```text
tests/kcs_adapters/test_mcp_desktop.py
functions_total: 217
cc_average: 7.08
max_cc: 32
high_complexity_functions: 88
```

The file max moved to two remaining Desktop characterization tests at `cc=32`.

## Contracts Preserved

- runtime behavior unchanged;
- no `src/` files changed;
- semantic-review packet behavior unchanged;
- selected excerpt bounds unchanged;
- submit shape and source-ref assertions unchanged;
- safety exclusions unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Next Recommended Target

Aggregate review is due after this material test-maintainability batch.
