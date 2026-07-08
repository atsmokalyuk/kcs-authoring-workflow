# KCS-14 Slice 8 Review Node: CLI, Ingest, And Readiness

## Status

Review-only complete.

## Scope

Graph node:

- `cli_ingest_readiness`

Reviewed files:

- `src/kcs_core/cli.py`
- `src/kcs_core/json_payload.py`
- `src/kcs_core/zendesk_ingest.py`
- `src/kcs_core/readiness.py`
- `src/kcs_core/errors.py`
- `tests/kcs_core/test_cli.py`
- `tests/kcs_core/test_readiness.py`

Related tests also listed by the graph:

- `tests/kcs_core/test_json_payload.py`
- `tests/kcs_core/test_zendesk_ingest.py`
- `tests/kcs_core/test_validation.py`
- `tests/kcs_core/test_safety.py`

No runtime code was changed.

## Ownership Assessment

The node owns local CLI and ingest readiness behavior:

- deterministic CLI command parsing and JSON output;
- strict JSON payload loading;
- read-only Zendesk ingest handoff for cleanup;
- readiness report state and value-safe error surfaces.

The current split is acceptable:

- `cli.py` owns the process entrypoint, safe JSON loading, command dispatch,
  value-safe CLI errors, and CLI result shape.
- `json_payload.py` owns strict JSON serialization helpers for packet contracts.
- `zendesk_ingest.py` owns read-only raw snapshot ingest and cleanup-handoff
  safety rules.
- `readiness.py` owns readiness report state, blocker summaries, renderer
  validation summaries, and false publication flags.
- `errors.py` is a tiny cross-cutting contract error type. Moving it is not
  worth a separate refactor without a broader exception-boundary question.

## Must Not Own

This node must not own:

- Desktop-specific state;
- provider trust decisions;
- renderer presentation policy;
- reviewer bundle writing.

The reviewed files respect those boundaries.

## Ousterhout Lens

- Information hiding: CLI callers get deterministic JSON and value-safe error
  codes, not raw parser traces, paths, or private values.
- Deep modules: `zendesk_ingest.py` and `readiness.py` hide meaningful safety
  and state logic behind compact construction/check functions.
- Change amplification: moving readiness or ingest checks without a concrete
  behavior question would force broad revalidation across packet validation,
  renderer status, and CLI fixtures.
- Shallow abstraction risk: `errors.py` is intentionally minimal and
  cross-cutting; extracting or relocating it now would add churn without
  reducing caller knowledge.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover CLI fixture scenarios, safe CLI errors, strict JSON
  boundaries, readiness states, blocked readiness, split readiness, renderer
  validation summaries, and false publication flags

Reviewed drift risks:

- CLI errors remain value-safe.
- input loading does not bypass packet validation.
- readiness checks do not become runtime publication approval.
- raw Zendesk ingest remains cleanup-only and requires explicit policy before
  writing handoff files.

Review-only drift risks:

- `readiness.py` is contract-dense and connected to renderer validation status;
  any future split must preserve blocker/status codes and renderer summary
  shape.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Future refactor should require a narrow ownership question, such as:

- Should CLI raw-private-value screening be factored from CLI command dispatch?
- Should readiness renderer-summary helpers become a deeper renderer-readiness
  module without changing output shape?
- Should `errors.py` remain a package-wide tiny boundary, or should a later
  exception taxonomy be introduced?

None of these questions currently has enough evidence for code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Node

Review `packaging_and_install_tooling`.
