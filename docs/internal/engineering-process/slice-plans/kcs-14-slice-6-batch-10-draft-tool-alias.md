# KCS-14 Slice 6 Batch 10 Draft Tool Alias

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow Desktop draft tool
batch. The target is repeated use of the Claude Desktop alias for
`kcs.draft_article` inside operator-choice payload construction.

Target:

```text
src/kcs_adapters/desktop_draft_tool.py
```

## Boundary Questions

What complexity are we hiding?

- The repeated mapping from canonical `TOOL_DRAFT_ARTICLE` to the Desktop tool
  alias used in operator-choice submit payloads.

What should this module not know?

- The full Desktop tool-name registry, MCP envelope serialization,
  result-shaping ownership, packet schemas, or Zendesk publication behavior.

What input is allowed?

- Existing internal call sites that need the Desktop alias for the draft tool.

What input is forbidden?

- New tool aliases, Desktop schema changes, raw ticket bodies, provider payload
  bodies, credentials, and publication/write intents.

What output contract is stable?

- Operator-choice payloads keep the same `submit_tool` and `next_tool` values.
- Public helper names and `__all__` remain stable.

What failure mode must be explicit?

- Existing alias lookup failure behavior remains outside this batch; no new
  alias validation path is added.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` draft tool alias call sites and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, or publication behavior changes.
- Behavior drift check compares the old call-site alias with the staged private
  alias constant. Completed: values matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_draft_tool.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
