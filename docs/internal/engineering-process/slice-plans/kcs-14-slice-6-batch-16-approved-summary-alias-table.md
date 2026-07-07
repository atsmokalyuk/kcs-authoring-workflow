# KCS-14 Slice 6 Batch 16 Approved Summary Alias Table

Status: ready for staged-diff review.

## Objective

Continue the `desktop_protocol_transport` pass with a payload-normalization
cleanup: make approved-summary item aliases an ordered private table instead
of a long procedural call chain.

Target:

```text
src/kcs_adapters/desktop_payload.py
```

## Boundary Questions

What complexity are we hiding?

- The ordered mapping from accepted approved-summary aliases to canonical item
  fields.

What should this module not know?

- KCS workflow decisions, semantic-review validation, provider behavior, MCP
  response envelopes, reviewer bundle writing, or Zendesk publication behavior.

What input is allowed?

- Existing approved-summary item fields and top-level item alias fields already
  accepted by the Desktop payload surface.

What input is forbidden?

- New accepted aliases, raw ticket bodies, provider payload bodies, credentials,
  schema changes, and publication/write intents.

What output contract is stable?

- Alias priority and canonical field output remain stable.
- `approved_summary_pipeline_payload()` remains the payload-normalization
  entrypoint.

What failure mode must be explicit?

- No new failure mode is introduced; invalid payload fields and unsafe payloads
  still fail through the existing validation paths.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_payload.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_protocol_transport` approved-summary alias normalization and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, publication, or customer-reply behavior
  changes.
- The ordered alias table preserves the old call order exactly.
- Behavior drift check verifies focused payload, MCP Desktop, and freeze
  snapshot tests pass.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_payload.py`.

## Not In Scope

- Adding or removing aliases.
- Desktop tool schema changes.
- MCP response envelope changes.
- KCS workflow decisions.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
