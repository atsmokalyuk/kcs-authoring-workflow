# KCS-14 Slice 8 Review Node: Reviewer Bundle Output

## Status

Review-only complete.

## Scope

Graph node:

- `reviewer_bundle_output`

Reviewed files:

- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_core/reviewer_bundle.py`
- `src/kcs_adapters/desktop_reviewer_preview.py`
- `tests/kcs_core/test_reviewer_bundle.py`
- `tests/kcs_adapters/test_desktop_reviewer_preview.py`

Related frozen characterization coverage:

- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed.

## Ownership Assessment

The node owns local reviewer-only bundle output:

- Desktop local bundle writing and relative bundle references;
- core reviewer-bundle manifest and file payload assembly;
- reviewer-only preview text and quality-gap shaping used by the Desktop path.

The current split is acceptable:

- `kcs_core/reviewer_bundle.py` owns validated packet assembly, manifest shape,
  file list, safe JSON payloads, hash entries, consistency validation, and
  local write safety for the core bundle.
- `kcs_adapters/desktop_reviewer_bundle.py` owns Desktop-specific local bundle
  root conventions, relative path reporting, storage hint/ref environment
  values, and the small Desktop manifest used by the adapter workflow.
- `kcs_adapters/desktop_reviewer_preview.py` owns reviewer-only preview and
  quality-gap shaping for Desktop output.

This is a boundary between core bundle invariants, Desktop local paths, and
Desktop preview shaping. It should not be collapsed casually.

## Must Not Own

This node must not own:

- KCS decisions;
- Desktop tool schema;
- Zendesk publish/write behavior;
- provider output trust.

The reviewed files respect these boundaries.

## Ousterhout Lens

- Information hiding: bundle consistency, file hashing, safe payload checks,
  and write safety are hidden behind the core bundle object.
- Deep modules: the core bundle writer does substantial validation behind a
  small construction/write API.
- Change amplification: merging Desktop bundle path conventions with core
  bundle invariants would make future path/storage changes riskier.
- Shallow abstraction risk: `desktop_reviewer_bundle.py` is small, but it hides
  a real Desktop-specific storage boundary rather than acting as a generic
  pass-through.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover bundle manifest shape, reviewer-only flags, omitted
  optional Claude artifacts, case mismatch rejection, unsafe payload rejection
  without echo, stale evidence validation rejection, draft artifact handoff
  requirements, overwrite rejection, symlink rejection, traversal rejection,
  pre-existing temp-file preservation, root exports, preview section text,
  quality gaps, reuse-search status, existing-KB delegation blocker, and helper
  reexports

Reviewed drift risks:

- bundles remain local artifacts only.
- returned bundle paths remain relative/value-safe.
- `auto_publish_allowed` and `public_output_approved` remain false.
- bundle writing does not generate customer replies or publish content.
- packet consistency validation remains in the core bundle writer.

Review-only drift risks:

- `desktop_reviewer_preview.py` includes article-quality and style-adjacent
  checks, but this review did not open KCS-15 style/markup parity. Future
  formatting changes must be explicitly scoped outside this node review.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future refactor should require a narrower ownership question, such as:

- Should reviewer-only preview/quality-gap shaping be split from bundle-output
  ownership in the graph?
- Should Desktop bundle manifest writing be aligned more explicitly with the
  core bundle manifest without changing the Desktop result shape?

Neither question currently has repeated friction, behavior drift, or complexity
evidence strong enough to justify code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Nodes

Continue review-only coverage with:

- `semantic_review_fallback`
- `packet_validation_decision`
