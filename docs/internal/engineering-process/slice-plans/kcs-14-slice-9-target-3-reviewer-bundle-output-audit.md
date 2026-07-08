# KCS-14 Slice 9 Target 3: Reviewer Bundle Output Audit

Status: design audit complete; narrow Desktop manifest extraction implemented.

## Scope

Graph node:

- `reviewer_bundle_output`

Reviewed files:

- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_core/reviewer_bundle.py`
- `src/kcs_adapters/desktop_reviewer_preview.py`

Related tests:

- `tests/kcs_core/test_reviewer_bundle.py`
- `tests/kcs_adapters/test_desktop_reviewer_preview.py`
- `tests/kcs_adapters/test_desktop_draft_output.py`
- `tests/kcs_adapters/test_mcp_desktop.py`

## Entry Question

Are bundle pathing, manifest, preview, and hash rules owned in one clear
boundary, or do callers need to understand too much of the output internals?

## Complexity Sensor

Command:

```bash
uv run python scripts/measure_complexity.py --paths src/kcs_adapters/desktop_reviewer_bundle.py src/kcs_core/reviewer_bundle.py src/kcs_adapters/desktop_reviewer_preview.py
```

Before source movement:

```text
files_scanned: 3
functions_total: 47
cc_average: 3.15
max_cc: 10
high_complexity_functions: 4
mi_average: 30.69
import_edges: 0
public_defs: 30
all_exports: 17
```

After source movement:

```text
files_scanned: 3
functions_total: 48
cc_average: 3.1
max_cc: 10
high_complexity_functions: 4
mi_average: 30.51
import_edges: 0
public_defs: 30
all_exports: 17
```

`desktop_reviewer_bundle.py` after source movement:

```text
functions_total: 8
cc_average: 2.12
max_cc: 6
high_complexity_functions: 0
```

Interpretation:

- the full node's complexity remains dominated by core reviewer-bundle path and
  consistency checks;
- the Desktop writer itself is small, but separating manifest shape from file
  writing reduces local review cost;
- cyclomatic complexity is not the main driver for this target.

## Ownership Assessment

Current ownership is mostly coherent:

- `src/kcs_core/reviewer_bundle.py` owns schema-versioned packet-bundle
  assembly, manifest file entries, packet consistency, hash calculation,
  symlink/overwrite/traversal protections, and fixed local JSON writes.
- `src/kcs_adapters/desktop_reviewer_bundle.py` owns the Desktop authoring
  bundle surface: local reviewer-only HTML artifact, compact manifest values,
  relative path refs, storage hints, and draft-only readiness mapping.
- `src/kcs_adapters/desktop_reviewer_preview.py` owns reviewer-only preview
  fields, preview text, reference coverage warnings, and local HTML quality
  gap aggregation.

The main design risk is not raw file size. It is boundary confusion between:

- core validated packet bundles; and
- Desktop reviewer-only HTML bundles.

Those are related but different artifact families. Merging them now would blur
contract boundaries and risk local path/output drift.

## Ousterhout Assessment

### Deep Modules

`reviewer_bundle.py` is a deep module: callers provide already-validated packet
objects and receive a manifest path. Internally, it owns packet consistency,
manifest entries, hashes, file permissions, symlink rejection, overwrite
protection, cleanup, and safe JSON writing.

It should not be split during Slice 9 without a concrete path or consistency
bug. Its high-complexity functions protect important local-output contracts.

### Information Hiding

The Desktop bundle writer now has a clearer internal split:

- `write_desktop_reviewer_bundle()` owns local directory/file creation and
  reviewer-only HTML writing;
- `_desktop_reviewer_bundle_manifest()` owns compact manifest shape and
  readiness/debug-code mapping.

Callers still know only the existing `write_desktop_reviewer_bundle()` API.

### Temporal Decomposition

The split is not by workflow phase. It separates two kinds of knowledge inside
the Desktop bundle owner:

- filesystem write sequence;
- manifest contract shape.

### Shallow Abstraction / Classitis Risk

No new class or public module was introduced. A single private helper is enough
for the current debt. Extracting a generic manifest builder or unifying core
and Desktop bundles would be premature.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- focused reviewer bundle, preview, and compact draft output tests passed;
- graph policy passed after hash update;
- Ruff passed for the touched source file;
- `git diff --check` passed.

Reviewed drift risks:

- relative `local-data/reviewer-bundles/...` paths must remain stable;
- `reviewer_only_html` must stay out of compact output by default;
- `auto_publish_allowed` and `public_output_approved` must remain false;
- draft-only reuse-skipped behavior must remain unchanged;
- HTML SHA-256 must continue to match written HTML content;
- bundle writing must not become Zendesk publish/customer-reply behavior.

Review-only drift risks:

- the two bundle concepts can still confuse future maintainers if later work
  tries to consolidate them without a design note;
- core writer path/symlink behavior is intentionally left untouched because it
  is contract-dense.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Decision

Keep the core reviewer-bundle writer unchanged in this target.

Reason:

- it already owns a coherent deep contract;
- tests cover manifest shape, file permissions, hashes, overwrite rejection,
  symlink rejection, traversal rejection, stale validation rejection, unsafe
  payload rejection, and optional artifact omission;
- moving path or consistency checks would risk weakening local artifact safety.

Apply one narrow Desktop writer refactor:

- extract `_desktop_reviewer_bundle_manifest()` inside
  `desktop_reviewer_bundle.py`;
- keep `write_desktop_reviewer_bundle()` as the only public call point;
- preserve compact manifest keys and path strings.

## Behavior Drift Mapping

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| bundle directory, item directory, and HTML file creation | `write_desktop_reviewer_bundle()` | Focused Desktop draft-output tests passed. |
| relative bundle/html/manifest path strings | unchanged `write_desktop_reviewer_bundle()` inputs to manifest helper | MCP Desktop bundle path tests remain applicable. |
| HTML SHA-256 calculation | unchanged `write_desktop_reviewer_bundle()` | Focused draft-output tests passed. |
| draft-only reuse-skipped readiness/debug-code mapping | `_desktop_reviewer_bundle_manifest()` | Focused draft-output tests passed. |
| `auto_publish_allowed=false` and `public_output_approved=false` | `_desktop_reviewer_bundle_manifest()` | Focused draft-output tests passed. |
| optional storage hint/ref fields | `_desktop_reviewer_bundle_manifest()` | Existing behavior preserved; no source of values changed. |
| manifest JSON write with sorted keys and newline | unchanged `write_desktop_reviewer_bundle()` | Focused tests passed. |

New behavior:

- none.

## Required Tests

Actual validation:

```text
uv run ruff check src/kcs_adapters/desktop_reviewer_bundle.py
uv run pytest tests/kcs_core/test_reviewer_bundle.py tests/kcs_adapters/test_desktop_reviewer_preview.py tests/kcs_adapters/test_desktop_draft_output.py -q
uv run pytest tests/policy/test_code_review_graph_policy.py -q
git diff --check
```

Before commit, staged review should also consider whether a focused
`tests/kcs_adapters/test_mcp_desktop.py` run is needed because many Desktop
bundle assertions live there.

## Parked Follow-Ups

Only reopen broader bundle design if one of these triggers appears:

- KCS-15 or later work needs the core packet-bundle writer and Desktop
  reviewer-only HTML bundle to share a manifest contract;
- local path leakage or storage hint/ref confusion recurs;
- review finds repeated confusion between reviewer-only HTML bundle and core
  packet bundle;
- Desktop bundle writer needs symlink/path hardening beyond the existing root
  suffix check, which would be behavior hardening rather than refactor-only
  work.

Possible future narrow questions:

- Should Desktop reviewer-only HTML bundles get a dedicated contract test file
  outside the large MCP Desktop characterization suite?
- Should the two bundle artifact families be named more explicitly in docs and
  graph labels?

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Decision

Run staged-diff review for this target. If clean, commit the Target 3
checkpoint and proceed to the Slice 9 aggregate review for Targets 2-3 before
opening renderer/provider targets.
