# KCS-14 Slice 6 Batch 12 Platform Match Flags

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow workflow fallback
batch. The target is platform match flag derivation used by semantic-review
fallback environment inference.

Target:

```text
src/kcs_adapters/desktop_workflow.py
```

## Boundary Questions

What complexity are we hiding?

- The Windows/Linux regex match tuple used to infer minimal fallback platform
  metadata.

What should this module not know?

- Candidate semantic extraction schema internals, renderer/style gates,
  reviewer bundle writing, Desktop MCP envelopes, or Zendesk publication
  behavior.

What input is allowed?

- Sanitized approved-summary text already inside the Desktop workflow.

What input is forbidden?

- Provider payload bodies, raw ticket bodies outside clean-ticket flow,
  reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- `_platform_type_from_text()` and `_minimal_environment_from_text()` return
  the same values for Linux, Windows, both-platform, and no-platform text.

What failure mode must be explicit?

- Ambiguous or missing platform evidence still returns no fallback environment.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` platform fallback inference and
  refactor-log/closeout metadata are affected.
- No semantic-review packet schema, candidate schema, Desktop tool schema, MCP
  envelope, workflow result shape, reviewer bundle, or publication behavior
  changes.
- Behavior drift check compares old `HEAD` platform and minimal-environment
  outputs with staged outputs for Linux, Windows, both-platform, and
  no-platform text. Completed: old and new outputs matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_workflow.py`.

## Not In Scope

- Candidate semantic extraction validation.
- Semantic-review packet schema changes.
- Result-shaping ownership movement.
- Desktop tool schema changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
