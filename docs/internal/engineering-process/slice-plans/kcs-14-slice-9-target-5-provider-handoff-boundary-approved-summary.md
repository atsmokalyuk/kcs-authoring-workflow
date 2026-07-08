# KCS-14 Slice 9 Target 5: Provider Handoff Boundary Approved Summary

## Status

Implementation complete; staged-diff review required before commit.

## Scope

Graph node:

- `provider_handoff_boundary`

Changed file:

- `src/kcs_adapters/approved_summary_semantic.py`

Graph metadata:

- `docs/internal/engineering-process/code-review-graph.json`

Related focused tests:

- `tests/kcs_adapters/test_approved_summary_semantic.py`

## Entry Question

Is there a narrow provider-boundary design-debt fix that improves ownership
without changing domain extraction behavior or provider trust boundaries?

## Finding

`approved_summary_semantic.py` contained the top measured runtime hotspot in
the provider target:

- `_config_file_resolution_steps()` with `cc=25`

The function mixed the step assembly flow with condition details for package
ownership checks, config review, backup/disable evidence, graph recovery, and
historical-data caveats.

## Decision

Extract the condition checks into private predicates:

- `_mentions_unowned_package_check()`
- `_mentions_config_content_review()`
- `_mentions_config_backup_or_disable()`
- `_mentions_graphs_displaying_data()`
- `_mentions_repopulate_context()`

Keep `_config_file_resolution_steps()` as the owner of resolution-step order
and wording.

## Ousterhout Lens

- Information hiding: detailed trigger detection is named separately from the
  resolution-step assembly flow.
- Deep module: the approved-summary semantic extraction adapter remains one
  private module; no new public API or file boundary was introduced.
- Change amplification: future edits to a trigger family should touch one
  predicate while preserving the step assembly order.
- Avoid classitis: no new class, public helper, or module was introduced.
- Behavior discipline: the exact semantic-extraction output remains protected
  by the existing focused fixture.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused approved-summary semantic extraction tests passed;
- exact resolution-step fixture for the final monitoring fix passed;
- Ruff passed for the touched source file;
- complexity sensor recorded before/after shape.

Old-to-new mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| unowned package / `rpm -qf` trigger | `_mentions_unowned_package_check()` | Exact `resolution_steps` fixture passed. |
| DataDir or `cat <config_path>` trigger | `_mentions_config_content_review()` | Exact `resolution_steps` fixture passed. |
| backup/disable trigger family | `_mentions_config_backup_or_disable()` | Exact `resolution_steps` fixture passed. |
| graph data recovery trigger | `_mentions_graphs_displaying_data()` | Exact `resolution_steps` fixture passed. |
| historical/repopulate caveat trigger | `_mentions_repopulate_context()` plus existing `or steps` behavior | Exact `resolution_steps` fixture passed. |
| resolution-step order and wording | unchanged `_config_file_resolution_steps()` | Exact `resolution_steps` fixture passed. |

Review-only drift risks:

- The focused fixture proves the current known monitoring case. Other
  approved-summary text variants remain covered by existing broad semantic
  extraction tests and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Complexity Evidence

Before this target, the provider target measured:

```text
functions_total: 239
max_cc: 25
high_complexity_functions: 11
import_edges: 3
public_defs: 50
```

After this target, the provider target measures:

```text
functions_total: 244
max_cc: 19
high_complexity_functions: 11
import_edges: 3
public_defs: 50
```

For `approved_summary_semantic.py` itself:

```text
functions_total: 34
max_cc: 14
high_complexity_functions: 6
import_edges: 0
public_defs: 1
```

The main effect is reducing the top extraction hotspot while keeping import
coupling and public surface stable.

## Contracts Preserved

- provider output remains untrusted;
- Python validators still own packet acceptance;
- no provider/runtime endpoint or credential material enters serializable
  packets;
- approved-summary extraction schema and candidate output shape unchanged;
- publication and customer-reply behavior remain absent;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy and fail-closed boundaries unchanged.

## Promotion And Demotion Candidates

- Promotion candidates: none new.
- Demotion candidates: none.

## Deferred Risks

- `DirectHttpRuntimeConfig.__post_init__()` is now the provider target max
  complexity point at `cc=19`; any refactor there must preserve runtime-only
  credential/endpoint boundaries.
- `_semantic_item_from_approved_summary_section()` remains domain behavior and
  should not be split unless a behavior-preserving ownership question is
  explicit.

## Next Recommended Action

Run full provider-boundary focused tests and the graph/freeze policy checks,
then commit if staged-diff review is clean.
