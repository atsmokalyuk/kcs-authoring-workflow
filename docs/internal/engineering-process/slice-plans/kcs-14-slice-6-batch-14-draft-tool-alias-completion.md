# KCS-14 Slice 6 Batch 14 Draft Tool Alias Completion

Status: ready for staged-diff review.

## Objective

Complete local ownership of the Desktop draft tool alias inside
`desktop_draft_tool.py` by using the existing private alias constant at the
remaining operator-selection invalid call site.

Target:

```text
src/kcs_adapters/desktop_draft_tool.py
```

## Boundary Questions

What complexity are we hiding?

- The mapping from canonical `TOOL_DRAFT_ARTICLE` to the Desktop-visible draft
  tool alias.

What should this module not know?

- The full Desktop tool-name registry, MCP envelope serialization, packet
  schemas, or Zendesk publication behavior.

What input is allowed?

- Existing internal call sites that need the Desktop alias for the draft tool.

What input is forbidden?

- New tool aliases, Desktop schema changes, raw ticket bodies, provider payload
  bodies, credentials, and publication/write intents.

What output contract is stable?

- The operator-selection invalid result keeps the same submit-tool alias.

What failure mode must be explicit?

- No new failure mode is introduced; alias lookup remains resolved by the
  private module constant.

What test proves the boundary?

- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/kcs_adapters/test_desktop_operator_selection.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` draft alias use and refactor-log/closeout
  metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, publication, or customer-reply behavior
  changes.
- Behavior drift check verifies focused Desktop draft/operator-selection/freeze
  tests pass.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_draft_tool.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
