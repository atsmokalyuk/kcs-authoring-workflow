# KCS-14 Refactor Log

Status: authoritative Slice 6 refactor rationale log.

Purpose: record why each behavior-preserving refactor batch exists, how it
serves the KCS-14 outcome contract, which Ousterhout design lens applies, and
what evidence shows runtime behavior stayed stable.

This file is not a replacement for closeouts, tests, or code review. Use it as
a compact human-readable rationale index.

## Entry Template

```text
Batch:
Affected graph node:
Changed code:
What changed:
Why under KCS-14 outcome contract:
Ousterhout lens:
Contracts preserved:
Behavior drift check:
Behavior drift mapping:
Review-only drift risks:
Verdict:
Evidence:
Open follow-up:
```

## 2026-07-05 - Slice 6 Batch 1 Smoke Log Tooling

Batch: KCS-14 Slice 6 Batch 1.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `src/kcs_adapters/smoke_accounting.py`

What changed:

- Moved repeated regex marker extraction out of
  `build_smoke_accounting_report()` into a private `_SmokeMarkers` value
  object.
- Kept `build_smoke_accounting_report()` as the public report-building
  entrypoint.
- Kept `SmokeAccountingReport.to_json_dict()` and CLI behavior unchanged.

Why under KCS-14 outcome contract:

- Supports "more reviewable codebase" by making the marker-extraction owner
  visible inside the module.
- Supports "safer refactor path" by keeping the public output contract stable
  and proving it with existing characterization tests.
- Reduces future agent ambiguity: a future change to marker counting now has a
  narrower internal place to inspect before report assembly.

Ousterhout lens:

- Information hiding: marker-counting details are grouped behind one internal
  value object instead of being spread through report construction.
- Module depth: the public module interface did not grow; the implementation
  absorbed internal complexity.
- Avoid classitis: `_SmokeMarkers` is private, owns a real derived data shape,
  and does not create a new caller-facing interface.
- Change amplification: future additions to marker extraction should touch the
  marker extraction block and report field mapping, not a long inline sequence
  in the public builder.

Contracts preserved:

- runtime behavior;
- smoke-accounting JSON output schema;
- CLI exit codes and value-safe error codes;
- packet schemas;
- Desktop/tool schema behavior;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed identical
  `SmokeAccountingReport.to_json_dict()` payloads across representative smoke
  transcript cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `tool_names` local variable | `_SmokeMarkers.tool_names` | Old-vs-new report JSON equivalence. |
| `failure_count` local variable | `_SmokeMarkers.failure_count` | Old-vs-new report JSON equivalence. |
| `fallback_count` local variable | `_SmokeMarkers.fallback_count` | Old-vs-new report JSON equivalence. |
| `success_count` local variable | `_SmokeMarkers.controlled_success_count` | Old-vs-new report JSON equivalence. |
| `draft_call_count` local variable | `_SmokeMarkers.draft_call_count` | Old-vs-new report JSON equivalence. |
| `draft_selected_count` local variable | `_SmokeMarkers.draft_selected_count` | Old-vs-new report JSON equivalence. |
| `draft_split_count` local variable | `_SmokeMarkers.draft_split_count` | Old-vs-new report JSON equivalence. |
| `draft_success_count` local variable | `_SmokeMarkers.draft_success_count` | Old-vs-new report JSON equivalence. |
| `upload_ticket_ref_count` local variable | `_SmokeMarkers.draft_upload_ticket_ref_count` -> `SmokeAccountingReport.kcs_draft_upload_ticket_ref_count` | Old-vs-new equivalence case for uploaded ticket ref. |
| `tool_result_invalid_count` local variable | `_SmokeMarkers.tool_result_invalid_count` | Old-vs-new equivalence case for tool-result-invalid. |
| `timeout_or_disconnect_count` local variable | `_SmokeMarkers.timeout_or_disconnect_count` | Old-vs-new equivalence case for timeout/disconnect marker. |
| `blocker_codes` local variable | `_SmokeMarkers.draft_blocker_codes` | Old-vs-new equivalence case for split blocker. |
| inline `deterministic_draft_passed` formula | `_SmokeMarkers.deterministic_draft_passed` | Old-vs-new equivalence case for split + selected draft success. |
| new `_SmokeMarkers` dataclass | old inline marker extraction local variables | Private implementation detail; no new public interface; old-vs-new equivalence passed. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current staged implementation produced
  identical `SmokeAccountingReport.to_json_dict()` payloads across six
  representative transcripts covering basic counts, deterministic draft,
  upload-ticket-ref detection, tool-result-invalid detection, manual fallback,
  empty input, and timeout/disconnect markers.
- `tests/kcs_adapters/test_smoke_accounting.py` passed.
- `tests/kcs_adapters/test_mcpb_package.py` passed with existing skips.
- `tests/policy/test_code_review_graph_policy.py` passed.
- `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.
- Staged-diff review found no blockers and no material warnings.

Open follow-up:

- Remaining smoke/log scripts are not refactored in this batch.
- Aggregate design review is due after the second Slice 6 refactor batch or an
  earlier methodology trigger.

## 2026-07-06 - Slice 6 Batch 2 Desktop Log Checker

Batch: KCS-14 Slice 6 Batch 2.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `scripts/check_claude_kcs_desktop_log.py`

What changed:

- Consolidated expected Desktop tool-surface knowledge into one private
  `_EXPECTED_TOOLS` table.
- Replaced separate tool-name, mutating-tool, read-only-tool, and repeated
  per-tool property definitions with `_ExpectedTool` entries.
- Kept `check_log()`, CLI arguments, exit codes, report keys, and `checks`
  keys unchanged.

Why under KCS-14 outcome contract:

- Supports "more reviewable codebase" by giving the active Desktop
  tools/list expectation a single local owner inside the checker.
- Reduces future agent ambiguity: a future tool-surface change has one compact
  internal table to inspect instead of several parallel sets and inline schema
  literals.
- Keeps the proven runtime workflow stable; this batch only changes internal
  log-checker organization.

Ousterhout lens:

- Information hiding: tool properties and read/idempotency expectations now
  live together as one design decision.
- Change amplification: adding or changing a checked Desktop tool no longer
  requires synchronizing separate name, annotation, and property structures.
- Avoid classitis: `_ExpectedTool` is a private tuple-shaped value with no
  public caller-facing interface.
- Deep module: the checker's external interface stayed the same while internal
  knowledge became easier to inspect.

Contracts preserved:

- runtime behavior;
- Desktop log-check CLI arguments and exit codes;
- `check_log()` report shape, `schema_version`, `error_code`, and `checks`
  keys;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed identical `check_log()`
  report dictionaries across representative synthetic log cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `_EXPECTED_TOOL_NAMES` | `set(_EXPECTED_TOOLS)` | Old-vs-new `check_log()` report equivalence. |
| `_MUTATING_TOOLS` | `_EXPECTED_TOOLS[*].read_only is False` | Old-vs-new report equivalence for full current and stale tool surfaces. |
| `_READ_ONLY_TOOLS` | `_EXPECTED_TOOLS[*].read_only is True` | Old-vs-new report equivalence for full current tool surface. |
| inline draft tool property set | `_EXPECTED_TOOLS["kcs_draft_article"].properties` | Old-vs-new report equivalence for full current and stale tool surfaces. |
| inline prepare/register/submit property sets | matching `_EXPECTED_TOOLS[...] .properties` entries | Old-vs-new report equivalence for full current tool surface. |
| `_tool_annotations_exact()` mutating/read-only loops | one `_EXPECTED_TOOLS.items()` loop | Old-vs-new report equivalence for accepted and rejected surfaces. |
| new `_ExpectedTool` tuple | old parallel expected-name/property/annotation data | Private implementation detail; no new public interface; existing tests and old-vs-new equivalence passed. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced identical
  `check_log()` report dictionaries for latest thin tool surface, stale tool
  surface, truncated tool surface, `--since` filtering, and missing log path.
- Desktop log checker tests in `tests/kcs_adapters/test_mcpb_package.py`
  passed.
- Tool-entrypoint and freeze/snapshot policy tests passed for the touched
  checker surface.
- Ruff passed for the touched script and related MCPB package tests.

Open follow-up:

- `scripts/smoke_kcs_mcpb_stdio.py` and
  `scripts/smoke_claude_desktop_ui_prompt.py` remain untouched.
- Aggregate design review is now due before starting Slice 6 Batch 3.
