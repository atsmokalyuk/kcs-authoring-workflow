# KCS-14 Slice 6 Batch 5 Draft Argument Selection Fields

Status: ready for staged-diff review.

## Objective

Start the `desktop_draft_workflow` refactor with a narrow
arguments-only batch. The target is the Desktop draft argument helper module.

Target:

```text
src/kcs_adapters/desktop_draft_arguments.py
```

## Boundary Questions

What complexity are we hiding?

- The set of Desktop draft arguments that belong to operator-selection state
  and must be stripped before normal authoring continues.

What should this module not know?

- Pending-selection storage internals, semantic-review packet internals, core
  KCS decision rules, reviewer bundle writing, or Desktop protocol envelope
  details.

What input is allowed?

- Already parsed Desktop draft argument mappings.

What input is forbidden?

- Raw ticket bodies outside approved clean-ticket flow, provider payload
  bodies, reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- Argument-normalization helpers return the same mappings as before.
- Public helper names and `__all__` remain stable.
- Desktop primary argument allow-list remains stable.

What failure mode must be explicit?

- Unexpected tool arguments, missing required arguments, invalid item objects,
  invalid item candidates, and unsafe candidate payloads keep existing
  `DraftArticleArgumentError` or `ContractValidationError` behavior.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py` targeted draft-argument paths.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` argument helpers and refactor-log/closeout
  metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status, or
  reviewer bundle behavior changes.
- Behavior drift check compares old `HEAD` helper outputs/exceptions with
  staged helper outputs/exceptions on representative argument mappings.
  Completed: old and new helper outputs/exceptions matched for representative
  draft argument mappings.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_draft_arguments.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
