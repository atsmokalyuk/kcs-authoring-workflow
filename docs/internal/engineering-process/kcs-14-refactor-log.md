# KCS-14 Refactor Log

Status: authoritative Slice 6 refactor rationale log.

Purpose: record why each behavior-preserving refactor batch exists, how it
serves the KCS-14 outcome contract, which Ousterhout design lens applies, and
what evidence shows runtime behavior stayed stable.

This file is not a replacement for closeouts, tests, or code review. Use it as
a compact human-readable rationale index.

## Analysis Use

This log is intentionally more detailed during Slice 6 because refactor-heavy
work needs practical evidence for later aggregate review, Fable review, and
future feature-slice planning.

Useful entries should let a reviewer compare theory to practice:

- declared outcome-contract reason vs actual diff;
- Ousterhout lens used vs concrete code movement;
- old behavior element -> new location -> evidence;
- preserved contracts vs validation evidence;
- recurring ownership or drift risks that may become promotion candidates;
- reusable implementation patterns that should influence later feature work.

Keep entries evidence-oriented. Do not paste full command output, raw/private
artifacts, long logs, repeated boilerplate, or general quality commentary. If a
future slice does not need detailed refactor analysis, use a shorter entry with
the same essential fields.

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

## 2026-07-06 - Slice 6 Batch 3 Desktop UI Smoke Observations

Batch: KCS-14 Slice 6 Batch 3.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `scripts/smoke_claude_desktop_ui_prompt.py`

What changed:

- Moved repeated derived UI smoke log observations out of
  `_report_from_log()` into a private `_UiLogObservations` value object.
- Kept `_report_from_log()` as the report-shaping entrypoint.
- Kept CLI arguments, exit codes, report keys, check names, failure-stage
  behavior, debug-code lists, and value-safe file-name metadata unchanged.

Why under KCS-14 outcome contract:

- Supports "more reviewable codebase" by making log-derived observations a
  named internal owner before report/check assembly.
- Reduces future agent ambiguity: future UI smoke changes can inspect one
  observation-building function before changing report shaping.
- Preserves proven smoke behavior while reducing local cognitive load inside a
  high-branch report function.

Ousterhout lens:

- Information hiding: regex-derived observations are grouped behind a private
  value object instead of being spread through `_report_from_log()`.
- Change amplification: future observation changes should touch
  `_ui_log_observations()` and the report field mapping, not a long sequence of
  local variables.
- Avoid classitis: `_UiLogObservations` is private, owns a real derived data
  shape, and adds no public interface.
- Deep module: the external script/report contract did not grow; internal
  complexity moved downward.

Contracts preserved:

- runtime behavior;
- UI smoke CLI arguments and exit codes;
- `_report_from_log()` output shape, check names, failure stages, attention,
  next steps, debug-code fields, and value-safe log-file metadata;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed identical
  `_report_from_log()` report dictionaries across representative synthetic log
  cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `client_call_text` local variable | `_UiLogObservations.client_call_text` | Old-vs-new report equivalence. |
| `tool_result_summary` local variable | `_UiLogObservations.tool_result_summary` | Old-vs-new report equivalence for debug-code and no-candidate cases. |
| `web_diagnostics` local variable | `_UiLogObservations.web_diagnostics` | Old-vs-new report equivalence for report and failure-stage paths. |
| `timeout_or_disconnect_observed` local variable | `_UiLogObservations.timeout_or_disconnect_observed` | Old-vs-new disconnect cases. |
| `draft_result_observed` local variable | `_UiLogObservations.draft_result_observed` | Old-vs-new single draft and split continuation cases. |
| `provider_unavailable_result_observed` local variable | `_UiLogObservations.provider_unavailable_result_observed` | Old-vs-new provider-unavailable case. |
| inline `terminal_result_observed` formula | `_UiLogObservations.terminal_result_observed` | Old-vs-new single and provider-unavailable cases. |
| `post_success_disconnect_observed` local variable | `_UiLogObservations.post_success_disconnect_observed` | Existing UI smoke tests and old-vs-new disconnect cases. |
| `manual_fallback_text` local variable plus regex | `_UiLogObservations.manual_fallback_observed` | Old-vs-new manual fallback case. |
| inline `_TOOL_RESULT_RE.search(text)` check | `_UiLogObservations.tool_result_observed` | Old-vs-new success and failure cases. |
| new `_UiLogObservations` tuple | old inline observation local variables | Private implementation detail; no new public interface; old-vs-new equivalence passed. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced identical
  `_report_from_log()` dictionaries across seven representative cases:
  single draft success, provider unavailable, manual fallback after blocker,
  disconnect after call, split selected continuation, old-argument rejection,
  and dry-run not-success.
- Focused Claude Desktop UI prompt smoke tests passed.
- Ruff passed for the touched script and related MCPB package tests.

Open follow-up:

- `scripts/smoke_kcs_mcpb_stdio.py` remains untouched.
- Next aggregate review is due after one more refactor batch or an earlier
  methodology trigger.

## 2026-07-06 - Slice 6 Batch 4 Stdio Smoke Environment

Batch: KCS-14 Slice 6 Batch 4.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `scripts/smoke_kcs_mcpb_stdio.py`

What changed:

- Moved repeated wrapper process environment construction into private
  `_wrapper_env()`.
- Kept `run_smoke()` as the public smoke entrypoint.
- Kept JSON-RPC message order, CLI arguments, exit codes, report keys, check
  names, and `SmokeError` codes unchanged.

Why under KCS-14 outcome contract:

- Supports "more reviewable codebase" by giving the wrapper execution
  environment one local owner.
- Reduces future agent ambiguity: future changes to fixture-provider or
  repo-root override behavior have one private function to inspect.
- Preserves proven stdio smoke behavior while reducing repeated setup logic
  across multiple smoke sessions.

Ousterhout lens:

- Information hiding: the smoke wrapper environment policy is grouped behind
  `_wrapper_env()` instead of being repeated in each session runner.
- Change amplification: changing the uv command or semantic provider handling
  should touch one helper instead of four environment blocks.
- Avoid classitis: `_wrapper_env()` is a private helper with real policy value;
  it does not add a public layer or pass-through abstraction.
- Deep module: the external CLI/report contract did not grow; internal setup
  knowledge moved downward.

Contracts preserved:

- runtime behavior;
- stdio smoke CLI arguments and exit codes;
- `run_smoke()` report shape, check names, debug-code fields, wrapper kind,
  registry-cache metadata, and value-safe error codes;
- JSON-RPC request order and smoke scenarios;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct comparison showed `_wrapper_env()` matches the old inline formulas for
  fixture-provider and inherited-provider paths under a controlled environment.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `_run_jsonrpc_session()` inline fixture env | `_wrapper_env(semantic_provider="fixture")` | Old formula vs new helper equivalence. |
| `_run_split_choice_smoke()` inline fixture env | `_wrapper_env(semantic_provider="fixture")` | Old formula vs new helper equivalence; focused stdio tests passed. |
| `_run_register_then_draft_smoke()` inline fixture env | `_wrapper_env(semantic_provider="fixture")` | Old formula vs new helper equivalence; focused stdio tests passed. |
| `_run_semantic_review_smoke()` inline inherited-provider env | `_wrapper_env(semantic_provider=None)` | Old formula vs new helper equivalence; focused stdio tests passed. |
| removal of `KCS_AUTHORING_MVP_REPO_ROOT` | `_wrapper_env()` | Old formula vs new helper equivalence. |
| removal of `KCS_AUTHORING_SEMANTIC_PROVIDER` for semantic-review smoke | `_wrapper_env(semantic_provider=None)` | Old formula vs new helper equivalence. |
| setting `KCS_AUTHORING_MVP_UV_COMMAND` | `_wrapper_env()` | Old formula vs new helper equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- `_wrapper_env()` matched old inline env formulas for fixture and
  inherited-provider paths under controlled `os.environ` values.
- Focused MCPB stdio smoke tests passed.
- Ruff passed for the touched script and related MCPB package tests.

Open follow-up:

- `smoke_log_tooling` has now had four low-blast-radius batches; aggregate
  design review is due before starting another refactor batch.

## 2026-07-07 - Slice 6 Batch 5 Draft Argument Selection Fields

Batch: KCS-14 Slice 6 Batch 5.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_draft_arguments.py`

What changed:

- Moved the repeated operator-selection draft argument field set into private
  `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS`.
- Kept all public helper names, `__all__`, allow-lists, exception types, and
  argument-normalization behavior unchanged.

Why under KCS-14 outcome contract:

- Starts the higher-risk `desktop_draft_workflow` refactor with an
  arguments-only batch.
- Reduces future agent ambiguity by giving operator-selection argument-field
  knowledge one local owner.
- Preserves runtime behavior while reducing repeated field-list knowledge in a
  workflow boundary module.

Ousterhout lens:

- Information hiding: the operator-selection field group is now named as one
  internal design decision.
- Change amplification: future changes to fields stripped before authoring
  should touch one private set instead of inline literals.
- Avoid classitis: no new class/file/public helper was introduced.
- Deep module: the public argument-helper interface stayed stable while
  internal knowledge became easier to inspect.

Contracts preserved:

- runtime behavior;
- Desktop draft argument allow-lists;
- public helper names and `__all__`;
- `DraftArticleArgumentError` and `ContractValidationError` behavior;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching helper outputs
  and exception shapes for representative argument mappings.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| inline `operator_choice_confirmed` removal | `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS` | Old-vs-new helper output equivalence. |
| inline `operator_selected_item_ref` removal | `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS` | Old-vs-new helper output equivalence. |
| inline `operator_selection_ref` removal | `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS` | Old-vs-new helper output equivalence. |
| inline `item_candidates` removal | `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS` | Old-vs-new helper output equivalence. |
| `draft_article_without_operator_selection_fields()` behavior | same public helper using private field set | Old-vs-new helper output equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  outputs/exceptions for operator-selection stripping, uploaded-ticket-ref
  stripping, confirmed-selection predicate, item normalization, approved-summary
  input predicates, and invalid item-candidate failure.
- `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_desktop_workflow_results.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Remaining `desktop_draft_workflow` files are not refactored in this batch.
- Next aggregate review is due after one more refactor batch or an earlier
  methodology trigger.

## 2026-07-07 - Slice 6 Batch 6 Operator Selection Remaining Cards

Batch: KCS-14 Slice 6 Batch 6.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_operator_selection.py`

What changed:

- Moved the repeated remaining-candidate-card filter into private
  `_remaining_candidate_cards()`.
- Kept all public helper names, `__all__`, request/status payload keys, and
  selection failure behavior unchanged.

Why under KCS-14 outcome contract:

- Continues the `desktop_draft_workflow` refactor with an operator-selection
  batch that stays inside one ownership module.
- Reduces future agent ambiguity by giving the "which candidate cards remain"
  rule one private owner.
- Preserves runtime behavior while reducing duplicated selection-state
  filtering knowledge.

Ousterhout lens:

- Information hiding: remaining-candidate-card filtering is named as one
  internal rule.
- Change amplification: future changes to selected-candidate filtering should
  touch one private helper instead of two payload builders.
- Avoid classitis: no new class/file/public helper was introduced.
- Deep module: the public operator-selection interface stayed stable while
  implementation knowledge moved downward.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- operator choice request, submit options, review summary, and remaining status
  payload shapes;
- `ContractValidationError` behavior for already-used and invalid selections;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching helper outputs
  and exception strings for representative pending-selection state.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| inline selected-candidate filter in `operator_choice_submit_options()` | `_remaining_candidate_cards()` | Old-vs-new submit-options equivalence. |
| inline selected-candidate filter in `remaining_operator_choice_status()` | `_remaining_candidate_cards()` | Old-vs-new remaining-status equivalence. |
| option payload construction | same public helper using private remaining-card helper | Old-vs-new choice-request and submit-options equivalence. |
| remaining `next_arguments` condition for one candidate | same public helper using private remaining-card helper | Old-vs-new remaining-status equivalence. |
| already-used and invalid selection failures | unchanged `selected_pending_candidate()` branches | Old-vs-new exception string equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  outputs/exceptions for submit options, choice request, review summary,
  remaining status, selected-candidate lookup, and pending-selection update.
- `tests/kcs_adapters/test_desktop_operator_selection.py`,
  `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Remaining `desktop_draft_workflow` files are not refactored in this batch.
- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.
