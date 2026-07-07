# KCS-14 Slice 6 Batch 13 Split Required Selection Result

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow Desktop draft tool
batch. The target is repeated split-required result creation and pending
operator-selection attachment inside `DesktopDraftArticleTool`.

Target:

```text
src/kcs_adapters/desktop_draft_tool.py
```

## Boundary Questions

What complexity are we hiding?

- The repeated local sequence: build `split_required` result, start pending
  selection, and attach the Desktop draft submit tool.

What should this module not know?

- Desktop tool schema internals, MCP envelope serialization, result/status
  consolidation policy, semantic-review schema internals, packet schemas, or
  Zendesk publication behavior.

What input is allowed?

- Existing validated item candidates and already-derived approved summary
  context for the primary-summary and semantic-review-submit paths.

What input is forbidden?

- Raw ticket bodies, provider payload bodies, unvalidated candidate extraction
  payloads, new tool aliases, Desktop schema changes, and publication/write
  intents.

What output contract is stable?

- `split_required` result shape remains stable.
- Operator-selection refs, choice request, submit tool, and next arguments
  remain stable.
- Semantic-review-submit extra fields remain owned by the submit path.

What failure mode must be explicit?

- The defensive invalid split-required result branch keeps the existing
  caller-specific debug code.

What test proves the boundary?

- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/kcs_adapters/test_desktop_workflow_results.py`.
- `tests/kcs_adapters/test_desktop_operator_selection.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` split-required selection handoff logic and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  reviewer bundle, publication, or customer-reply behavior changes.
- No result/status/output consolidation is introduced.
- Behavior drift check accounts for both primary-summary and semantic-review
  submit multi-candidate paths.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_draft_tool.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review validation behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
