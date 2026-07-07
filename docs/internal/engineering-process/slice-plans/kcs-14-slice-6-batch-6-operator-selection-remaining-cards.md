# KCS-14 Slice 6 Batch 6 Operator Selection Remaining Cards

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow
operator-selection batch. The target is the Desktop operator-selection helper
module.

Target:

```text
src/kcs_adapters/desktop_operator_selection.py
```

## Boundary Questions

What complexity are we hiding?

- The repeated rule for which operator-choice candidate cards remain available
  after selected candidates have already been drafted.

What should this module not know?

- Desktop MCP envelopes, result-shaping ownership, clean-ticket storage,
  semantic-review packet internals, core KCS decision rules, reviewer bundle
  writing, or Zendesk publication behavior.

What input is allowed?

- Existing in-memory `PendingDraftSelection` state that was already created
  from validated split-candidate payloads.

What input is forbidden?

- Raw ticket bodies outside approved clean-ticket flow, provider payload
  bodies, reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- Public helper names and `__all__` remain stable.
- Operator choice request, submit options, review summary, remaining status,
  and selected-candidate behavior remain stable.

What failure mode must be explicit?

- Already-used selections and invalid selections keep existing
  `ContractValidationError` behavior.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_operator_selection.py`.
- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` operator-selection helpers and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, or reviewer bundle behavior changes.
- Behavior drift check compares old `HEAD` helper outputs/exceptions with
  staged helper outputs/exceptions on representative pending-selection state.
  Completed: old and new helper outputs/exceptions matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_operator_selection.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
