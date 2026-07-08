# KCS-14 Slice 8 Review Node: Clean Ticket Storage

## Status

Review-only complete.

## Scope

Graph node:

- `clean_ticket_storage`

Reviewed files:

- `src/kcs_adapters/desktop_ticket_ref.py`
- `src/kcs_adapters/desktop_clean_ticket_metadata.py`
- `tests/kcs_adapters/test_desktop_ticket_ref.py`

Related frozen characterization coverage:

- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed.

## Ownership Assessment

The node owns the local clean-ticket path for `ticket_ref`:

- approved summary lookup and merge;
- clean ticket registration;
- safe local clean-ticket text reads and writes;
- clean-ticket metadata creation and validation;
- metadata binding for semantic-review eligibility.

The current split is acceptable:

- `desktop_ticket_ref.py` owns the operator-facing `ticket_ref` argument path,
  store paths, clean-ticket registration, read/merge behavior, and fail-closed
  adapter errors.
- `desktop_clean_ticket_metadata.py` owns the metadata schema, hash binding,
  cleanup-form compatibility normalization, and semantic-review metadata
  validation.

This is an ownership split by knowledge, not by execution order.

## Must Not Own

This node must not own:

- semantic extraction decisions;
- article rendering;
- reviewer bundle writing;
- provider credential or endpoint material.

The reviewed files respect these boundaries.

## Ousterhout Lens

- Information hiding: metadata schema and hash-binding rules live in
  `desktop_clean_ticket_metadata.py`; callers do not need to know cleanup-form
  normalization details.
- Deep modules: `desktop_ticket_ref.py` exposes a compact adapter-facing
  behavior around `ticket_ref` while hiding path and text-safety checks.
- Change amplification: moving small pieces out would likely create more
  interfaces around the safety path without reducing caller knowledge.
- Temporal decomposition: the node is not split into read/register/validate
  workflow stages; the storage rules remain grouped around clean-ticket
  ownership.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover clean-ticket load, registration, configured store root,
  generated refs, operator refs, semantic-review metadata binding, cleanup-form
  metadata compatibility, hash mismatch rejection, symlink rejection, tool
  artifact rejection, secret artifact rejection, and unsafe ref rejection

Reviewed drift risks:

- `ticket_ref` remains the primary local clean-ticket path.
- raw or incomplete ticket text remains rejected before use.
- path traversal, symlink escape, and private artifact exposure remain blocked
  by existing path/ref/text checks and related tests.
- clean-ticket metadata remains bound to exact text by SHA-256 before semantic
  review.

Review-only drift risks:

- future cleanup-form metadata changes must be reviewed against both native and
  cleanup-form metadata normalization; this is contract-dense enough that a
  broad helper split would be risky without behavior tests.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

A future refactor would need a narrower ownership question, such as:

- Should metadata compatibility be isolated further from native metadata
  writing?
- Should clean-ticket text safety checks become a separately tested value
  object?

Neither question is currently backed by repeated review friction, complexity
hotspot evidence, or failed validation.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Node

Review `reviewer_bundle_output`.
