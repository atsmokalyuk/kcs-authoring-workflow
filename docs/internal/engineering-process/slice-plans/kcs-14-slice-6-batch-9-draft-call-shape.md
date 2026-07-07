# KCS-14 Slice 6 Batch 9 Draft Call Shape

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow Desktop draft
tool batch. The target is primary `kcs_draft_article` call-shape routing.

Target:

```text
src/kcs_adapters/desktop_draft_tool.py
```

## Boundary Questions

What complexity are we hiding?

- The derived booleans that classify a primary Desktop draft call as summary,
  ticket-ref, operator-selection, invalid, or outside the primary surface.

What should this module not know?

- Core KCS decision rules, semantic-review packet internals, reviewer bundle
  path details, renderer/style rules, or Zendesk publication behavior.

What input is allowed?

- Already parsed Desktop draft tool arguments.

What input is forbidden?

- Raw ticket bodies outside approved clean-ticket flow, provider payload
  bodies, reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- `_draft_article_primary_surface_result()` routes the same argument shapes to
  summary, ticket-ref, operator-selection, invalid-call-shape, or non-primary
  behavior.
- Public helper names and `__all__` remain stable.

What failure mode must be explicit?

- Invalid primary call shapes keep existing `draft_article_call_shape_invalid`
  behavior, and unknown primary-surface arguments still return `None` to the
  outer failure path.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` draft call-shape routing and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, or publication behavior changes.
- Behavior drift check compares old `HEAD` primary-surface routing and
  semantic-review clear behavior with staged behavior for summary, ticket-ref,
  operator-selection, invalid mixed, empty, and unknown-argument cases.
  Completed: old and new routes matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_draft_tool.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
