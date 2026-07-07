# KCS-14 Slice 6 Batch 11 Semantic Review Pending Ref

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow workflow-state
batch. The target is shared pending semantic-review ref/type/expiry validation
inside `DesktopDraftWorkflow`.

Target:

```text
src/kcs_adapters/desktop_workflow.py
```

## Boundary Questions

What complexity are we hiding?

- The repeated rules for retrieving current pending semantic-review state,
  validating the submitted ref type/value, and expiring stale state.

What should this module not know?

- Candidate semantic extraction schema internals, renderer/style gates,
  reviewer bundle writing, Desktop MCP envelopes, or Zendesk publication
  behavior.

What input is allowed?

- A pending semantic-review ref supplied to prepare or submit paths.

What input is forbidden?

- Provider payload bodies, raw ticket bodies outside clean-ticket flow,
  reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- Prepare and submit paths raise the same controlled errors for unavailable,
  invalid, expired, already-prepared, and not-yet-prepared states.
- Public helper names and `__all__` remain stable.

What failure mode must be explicit?

- Expired pending semantic-review state still clears local pending state and
  raises `SemanticReviewExpiredError`.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` semantic-review pending ref validation and
  refactor-log/closeout metadata are affected.
- No semantic-review packet schema, candidate schema, Desktop tool schema, MCP
  envelope, workflow result shape, reviewer bundle, or publication behavior
  changes.
- Behavior drift check compares old `HEAD` prepare/submit outcomes with staged
  outcomes for valid prepare, invalid ref, invalid type, double prepare, submit
  before prepare, and expired prepare. Completed: old and new outcomes matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_workflow.py`.

## Not In Scope

- Candidate semantic extraction validation.
- Semantic-review packet schema changes.
- Result-shaping ownership movement.
- Desktop tool schema changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
