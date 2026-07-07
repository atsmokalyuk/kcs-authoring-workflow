# KCS-14 Slice 6 Batch 8 Existing Article Text Fields

Status: ready for staged-diff review.

## Objective

Continue the `desktop_draft_workflow` refactor with a narrow approved-summary
pipeline batch. The target is the explicit existing-article text collection
rule inside the Desktop authoring pipeline helper module.

Target:

```text
src/kcs_adapters/desktop_authoring_pipeline.py
```

## Boundary Questions

What complexity are we hiding?

- The exact item fields that contribute to explicit existing-article
  detection text.

What should this module not know?

- Desktop MCP envelopes, compact result filtering, reviewer-bundle path
  writing, clean-ticket storage internals, semantic-review packet internals, or
  Zendesk publication behavior.

What input is allowed?

- Already parsed Desktop approved-summary item mappings.

What input is forbidden?

- Raw ticket bodies outside approved clean-ticket flow, provider payload
  bodies, reviewer bundle bodies, credentials, and publication/write intents.

What output contract is stable?

- `_explicit_existing_article_text()`,
  `_explicit_existing_article_match()`, and `_approved_summary_reuse_results()`
  return the same values for string-field, list-field, and mixed non-string
  cases.
- Public helper names and `__all__` remain stable.

What failure mode must be explicit?

- Existing explicit-article parsing and safe string validation behavior remain
  unchanged.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_workflow.py`.
- `tests/kcs_adapters/test_desktop_draft_tool.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_draft_workflow` explicit existing-article text field grouping
  and refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, or publication behavior changes.
- Behavior drift check compares old `HEAD` outputs with staged outputs for
  string-field, list-field, and mixed non-string cases. Completed: old and new
  outputs matched.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_authoring_pipeline.py`.

## Not In Scope

- Result-shaping ownership movement.
- Desktop tool schema changes.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
