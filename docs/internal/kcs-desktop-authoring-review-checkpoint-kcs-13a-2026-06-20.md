# KCS Desktop Authoring Review Checkpoint - KCS-13a - 2026-06-20

## Scope

Review `KCS-13a: Semantic review policy, metadata, and result contract`
against `docs/internal/kcs-desktop-authoring-refactor-plan.md`.

This checkpoint is intentionally limited to the metadata/result contract for a
future controlled semantic-review fallback. It does not return ticket excerpts
and does not add `kcs_prepare_semantic_review` or
`kcs_submit_semantic_review`.

## Status

Status: approved to move past `KCS-13a`.

The local code-review subagent found one blocking P1 issue in the initial
checkpoint: metadata writes did not reject broken symlinks at
`clean.ticket.meta.json`. The issue was fixed by rejecting `path.is_symlink()`
before writing metadata and adding regression coverage.

Follow-up review found no remaining P0/P1 blockers.

## Implemented Boundary

- Clean-ticket registration writes `clean.ticket.meta.json` next to
  `clean.ticket.txt`.
- Metadata uses schema `kcs_clean_ticket_metadata_v1` and binds the clean ticket
  by SHA-256.
- Metadata records `semantic_review_allowed` and `source_kind`.
- Semantic-review fallback validates metadata before returning
  `workflow_state=semantic_review_required`.
- Missing, disabled, stale, or mismatched metadata returns a controlled
  `workflow_state=semantic_review_metadata_blocked` result.
- KCS action vocabulary is preserved: semantic review uses
  `recommended_action=blocked`, not a new KCS action.
- No ticket excerpts, full ticket text, article draft, reviewer HTML, or bundle
  output is returned by this checkpoint.

## Validation Evidence

Focused validation passed:

```text
uv run pytest tests/kcs_adapters/test_desktop_ticket_ref.py \
  tests/kcs_adapters/test_mcp_desktop.py \
  tests/kcs_adapters/test_mcpb_package.py -q

uv run ruff check src/kcs_adapters/desktop_clean_ticket_metadata.py \
  src/kcs_adapters/desktop_ticket_ref.py \
  src/kcs_adapters/desktop_draft_tool.py \
  src/kcs_adapters/desktop_tool_results.py \
  src/kcs_adapters/desktop_workflow_results.py \
  tests/kcs_adapters/test_desktop_ticket_ref.py \
  tests/kcs_adapters/test_mcp_desktop.py

git diff --check
```

## Deferred Items

- `KCS-13b` must add process-local semantic-review state and make
  `semantic_review_ref` resumable before the prepare tool can be used.
- `KCS-13b` must add the bounded selected-excerpt prepare packet and keep all
  excerpts within the approved Claude-visible semantic-review lane.
- The `likely_kcs_material` gate is intentionally conservative MVP logic and
  may need refinement after more ticket samples.
- The pre-release `next_tool=kcs_prepare_semantic_review` field is acceptable
  for this checkpoint, but `KCS-13b` must close the UX/API gap.
