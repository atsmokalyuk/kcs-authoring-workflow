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

## 2026-07-07 - Slice 6 Batch 19 Stdio Smoke Tool Surface Specs

Batch: KCS-14 Slice 6 Batch 19.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `scripts/smoke_kcs_mcpb_stdio.py`

What changed:

- Moved the long inline Desktop tool-surface assertion in `_tool_surface_ok()`
  into a private `_EXPECTED_TOOL_SURFACES` table and
  `_tool_matches_surface_spec()` helper.
- Kept `_tool_surface_ok()` as the same private smoke check entrypoint.
- Kept the stdio smoke CLI, JSON-RPC requests, report keys, and tool contract
  expectations unchanged.

Why under KCS-14 outcome contract:

- Reduces review ambiguity in the remaining stdio smoke script hotspot without
  touching runtime adapter code or Desktop schema definitions.
- Makes expected tool-surface knowledge easier to inspect as one local table
  instead of a long boolean expression.
- Uses the complexity sensor on a known Slice 6 hotspot while preserving the
  existing smoke behavior.

Ousterhout lens:

- Information hiding: expected name/properties/annotation/description checks
  now live as one local tool-surface spec decision.
- Deep module: the script surface did not grow; internal validation knowledge
  moved behind a private helper.
- Avoid classitis: `_ExpectedToolSurface` is a private tuple-shaped value used
  only to group existing expected-surface facts.
- Change amplification: future expected-tool updates should touch one spec
  entry instead of multiple branches in a long `and` chain.

Contracts preserved:

- runtime behavior;
- stdio smoke CLI arguments and exit codes;
- `run_smoke()` report shape and check names;
- Desktop/tool schema behavior;
- MCPB manifest and wrapper files;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching
  `_tool_surface_ok()` booleans across representative accepted and rejected
  tool-surface cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| expected six-tool length check | unchanged `_tool_surface_ok()` guard | Old-vs-new tool-surface equivalence. |
| per-tool lookup by name | `_tool_by_name()` loop from `_tool_surface_ok()` | Old-vs-new tool-surface equivalence. |
| register tool properties, required fields, and annotations | `_EXPECTED_TOOL_SURFACES` register entry | Old-vs-new accepted/current and missing-required cases. |
| ticket-ref tool properties, required fields, annotations, and description substrings | `_EXPECTED_TOOL_SURFACES` ticket-ref entry | Old-vs-new accepted/current and wrong-annotation cases. |
| draft article properties, annotation checks, description includes/excludes, and debug description check | `_EXPECTED_TOOL_SURFACES` draft entry | Old-vs-new upload-reference, forbidden-description, and missing-debug-description cases. |
| semantic review prepare/submit tool checks | `_EXPECTED_TOOL_SURFACES` prepare/submit entries | Old-vs-new accepted/current and missing-tool cases. |
| behavior helper tool checks | `_EXPECTED_TOOL_SURFACES` behavior entry | Old-vs-new accepted/current case. |
| long inline boolean expression | `_tool_matches_surface_spec()` | Existing focused tests and old-vs-new equivalence. |

Review-only drift risks:

- The private spec table now carries the same order-sensitive `required` lists
  as the old inline checks; old-vs-new cases covered the existing order.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation returned matching
  `_tool_surface_ok()` booleans for current contract, upload-reference
  rejection, missing prepare tool, wrong ticket annotation, missing register
  required field, forbidden raw-comments description, and missing debug
  description.
- Focused MCPB stdio smoke tool-surface tests passed.
- Ruff passed for the touched script and related MCPB package tests.
- Complexity sensor showed script max CC dropping from 70 to 51; full-repo
  `max_cc` delta from baseline is now `-13`.

Open follow-up:

- `_registry_manifest_has_thin_contract()` remains the next stdio smoke
  hotspot (`cc=51`) if another explicit `smoke_log_tooling` batch is worth the
  review cost.
- Aggregate review is due after one more refactor batch or an earlier
  methodology trigger.

## 2026-07-07 - Slice 6 Batch 20 Stdio Registry Manifest Descriptions

Batch: KCS-14 Slice 6 Batch 20.

Affected graph node: `smoke_log_tooling`.

Changed code:

- `scripts/smoke_kcs_mcpb_stdio.py`

What changed:

- Moved the registry-manifest tool-description contract out of the long
  `_registry_manifest_has_thin_contract()` boolean expression into private
  `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` and
  `_registry_manifest_tools_have_expected_descriptions()`.
- Moved long-description include/exclude checks into private constants and
  reused `_text_has_expected_terms()`.
- Kept `_registry_manifest_has_thin_contract()` as the same private registry
  smoke predicate.

Why under KCS-14 outcome contract:

- Finishes the high-payoff stdio smoke contract cleanup identified by the
  complexity sensor after Batch 19.
- Reduces ambiguity around what the installed registry manifest must preserve:
  per-tool description terms and long-description terms now have explicit
  local owners.
- Keeps the change behavior-preserving and inside smoke tooling, without
  editing package manifests, Desktop schemas, or runtime adapter code.

Ousterhout lens:

- Information hiding: registry manifest description requirements are grouped
  as one local contract table.
- Change amplification: future manifest wording contract updates should touch
  one description spec entry instead of a long expression.
- Deep module: no public script entrypoint or report shape changed; internal
  contract knowledge moved downward.
- Avoid classitis: the new tuple-shaped spec is private data, not a new
  caller-facing abstraction.

Contracts preserved:

- runtime behavior;
- stdio smoke CLI arguments and exit codes;
- registry cache check return behavior;
- `run_smoke()` report shape and check names;
- Desktop/tool schema behavior;
- MCPB manifest and wrapper files;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching
  `_registry_manifest_has_thin_contract()` booleans across representative valid
  and invalid registry manifest cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| manifest object type and six-tool list guard | unchanged `_registry_manifest_has_thin_contract()` guard | Old-vs-new manifest equivalence. |
| register tool description includes `clean_ticket_text` and `next_arguments` | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` register entry | Old-vs-new valid manifest case. |
| ticket-ref tool description includes `/draft <ticket_ref>`, `only ticket_ref`, and attachment prohibition | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` ticket entry | Old-vs-new valid manifest case. |
| draft tool description includes approved-summary and draft-ticket routing terms | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` draft entry | Old-vs-new valid manifest case. |
| draft tool description excludes stale structured-item/raw-comments/internal-notes/popup wording | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` draft entry | Old-vs-new stale-description and old-popup cases. |
| semantic review prepare/submit description checks | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` prepare/submit entries | Old-vs-new missing-tool and valid cases. |
| behavior helper description checks | `_EXPECTED_REGISTRY_MANIFEST_TOOL_DESCRIPTIONS` behavior entry | Old-vs-new valid manifest case. |
| long-description include/exclude checks | `_EXPECTED_REGISTRY_LONG_DESCRIPTION_*` constants | Old-vs-new missing-long-description and forbidden-read-only cases. |
| repeated substring check mechanics | `_text_has_expected_terms()` | Existing tests and old-vs-new equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation returned matching
  `_registry_manifest_has_thin_contract()` booleans for valid manifest, missing
  prepare tool, stale draft description, old popup phrase, missing
  long-description phrase, forbidden old read-only phrase, non-dict input, and
  wrong tools type.
- Focused MCPB registry-cache smoke tests passed.
- Ruff passed for the touched script and related MCPB package tests.
- Complexity sensor showed script max CC dropping from 51 to 22; full-repo
  `high_complexity_functions` delta from baseline is now `-3`.

Open follow-up:

- Batch 20 completes the explicit stdio smoke tool-surface/registry-manifest
  cleanup pair.
- Aggregate review is now due before another refactor batch.

## 2026-07-07 - Slice 6 Batch 21 MCPB Manifest Test Terms

Batch: KCS-14 Slice 6 Batch 21.

Affected graph node: `packaging_and_install_tooling`.

Changed code:

- `tests/kcs_adapters/test_mcpb_package.py`

What changed:

- Moved repeated MCPB manifest long-description and per-tool description
  assertions into private test constants and small assertion helpers.
- Kept `test_mcpb_manifest_exposes_desktop_alias_tools_only()` as the
  behavior-facing characterization test.
- Preserved every existing manifest term assertion and forbidden draft-tool
  phrase assertion.

Why under KCS-14 outcome contract:

- Reduces ambiguity in the top remaining test complexity hotspot without
  changing runtime code, packaging files, or manifest contents.
- Makes the packaging manifest contract easier to review: expected
  long-description terms, per-tool description terms, and forbidden draft-tool
  terms now have explicit test owners.
- Extends Slice 6 refactor discipline to test code while preserving the
  characterization surface.

Ousterhout lens:

- Information hiding: manifest wording contract knowledge is grouped as test
  data instead of being spread across a long assertion sequence.
- Change amplification: a future intentional manifest wording change should
  update one expected-term table entry rather than a long test body.
- Deep module: the test still exposes one scenario; helper details are private
  to the test file.
- Avoid classitis: helpers only express repeated assertion mechanics and do not
  introduce a new test framework.

Contracts preserved:

- runtime behavior;
- MCPB manifest and wrapper files;
- packaging output behavior;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- No runtime source file was touched.
- Assertion-preservation review mapped every removed manifest term assertion to
  a new expected-term constant used by the same test.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| long-description required terms | `MCPB_MANIFEST_LONG_DESCRIPTION_INCLUDES` | Diff review and focused test pass. |
| register tool required description terms | `MCPB_MANIFEST_TOOL_DESCRIPTION_INCLUDES["kcs_register_clean_ticket"]` | Diff review and focused test pass. |
| draft-ticket tool required description terms | `MCPB_MANIFEST_TOOL_DESCRIPTION_INCLUDES["kcs_draft_ticket"]` | Diff review and focused test pass. |
| draft article required description terms | `MCPB_MANIFEST_TOOL_DESCRIPTION_INCLUDES["kcs_draft_article"]` | Diff review and focused test pass. |
| semantic review prepare/submit required terms | matching entries in `MCPB_MANIFEST_TOOL_DESCRIPTION_INCLUDES` | Diff review and focused test pass. |
| behavior helper required terms | `MCPB_MANIFEST_TOOL_DESCRIPTION_INCLUDES["support_get_behavior_instructions"]` | Diff review and focused test pass. |
| draft article forbidden wording terms | `MCPB_DRAFT_TOOL_DESCRIPTION_EXCLUDES` | Diff review and focused test pass. |
| repeated `term in text` assertion mechanics | `_assert_text_contains_all()` and `_assert_text_excludes_all()` | Focused test pass. |

Review-only drift risks:

- The refactor relies on diff review to confirm that no assertion term was
  dropped; focused test execution proves the current manifest still satisfies
  the preserved assertions.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Focused MCPB manifest characterization test passed.
- Ruff passed for `tests/kcs_adapters/test_mcpb_package.py`.
- Complexity sensor showed full-repo `max_cc` delta from baseline improving to
  `-14`; the previous top test function is no longer the max-complexity
  function.

Open follow-up:

- This batch starts a new aggregate window after batches 19-20.
- Do not continue test refactor by mining large tests; the next batch needs a
  new explicit test ownership question.

## 2026-07-07 - Slice 6 Batch 17 Strict JSON Scalar Boundary

Batch: KCS-14 Slice 6 Batch 17.

Affected graph node: `cli_ingest_readiness`.

Changed code:

- `src/kcs_core/json_payload.py`
- `tests/kcs_core/test_json_payload.py`

What changed:

- Moved strict JSON scalar acceptance out of `_ensure_strict_json_value()` into
  a private `_is_strict_json_scalar()` helper.
- Added focused characterization for already accepted strict scalar values:
  `None`, strings, booleans, integers, finite floats, and lists containing
  those values.

Why under KCS-14 outcome contract:

- Reduces ambiguity inside a shared JSON payload boundary without changing the
  public serialization helpers.
- Keeps strict JSON rejection behavior stable while making scalar acceptance a
  named local decision.
- Exercises the new complexity sensor on a small mid-risk node before any
  larger `cli_ingest_readiness` work.

Ousterhout lens:

- Information hiding: scalar acceptance is now a named predicate instead of
  being embedded in the recursive dispatcher.
- Deep module: public functions `dump_json_dict()`, `dumps_payload()`, and
  `require_json_object()` did not grow.
- Avoid classitis: the split is one private predicate with a clear decision,
  not a new public class or shallow wrapper chain.
- Change amplification: a future change to scalar acceptance has one local
  predicate to inspect.

Contracts preserved:

- strict JSON serialization behavior;
- public `kcs_core.json_payload` function names and return shapes;
- `ContractValidationError` failure mode;
- packet schemas;
- CLI, Desktop/tool schema, privacy, fail-closed, reviewer-bundle,
  publication, and customer-reply boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD:src/kcs_core/json_payload.py`
  produced identical outcomes for six representative valid and invalid payload
  cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `None`, string, bool, and int acceptance inside `_ensure_strict_json_value()` | `_is_strict_json_scalar()` | Old-vs-new equivalence and new scalar characterization test. |
| finite float acceptance inside `_ensure_strict_json_value()` | `_is_strict_json_scalar()` | Old-vs-new equivalence and new scalar characterization test. |
| non-finite float rejection | `_is_strict_json_scalar()` returns false, caller raises same `ContractValidationError` | Old-vs-new equivalence for NaN and infinity cases. |
| arbitrary object rejection | unchanged caller error path after scalar predicate returns false | Old-vs-new equivalence for object value. |
| non-string mapping key rejection | unchanged `_ensure_strict_json_object()` path | Old-vs-new equivalence for non-string key. |
| new `_is_strict_json_scalar()` helper | old scalar branches in `_ensure_strict_json_value()` | Private helper only; no public interface change. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old-vs-new JSON payload equivalence passed for six representative cases.
- Touched subset complexity measurement reports `high_complexity_functions: 0`
  and `max_cc: 5`.
- Full repository complexity delta from baseline reports
  `high_complexity_functions: -1` and `functions_total: +2`; the private
  scalar helper and new characterization test account for the function-count
  increase.
- Focused JSON payload, graph policy, and freeze snapshot tests passed after
  the graph hash update.

Open follow-up:

- `src/kcs_core/readiness.py` still contains `_renderer_blockers()`, the other
  `cli_ingest_readiness` function above the advisory complexity threshold.
- Aggregate review is due after one more refactor batch or an earlier
  methodology trigger.

## 2026-07-07 - Slice 6 Batch 18 Renderer Report Blocker Extraction

Batch: KCS-14 Slice 6 Batch 18.

Affected graph node: `cli_ingest_readiness`.

Changed code:

- `src/kcs_core/readiness.py`

What changed:

- Moved renderer validation-report list invalidity checks out of
  `_renderer_blockers()` into private `_renderer_report_blockers()`.
- Kept `_renderer_blockers()` responsible for decision-specific blocker
  filtering and no-article reason handling.

Why under KCS-14 outcome contract:

- Reduces ambiguity in a readiness boundary that protects reviewer handoff
  safety.
- Keeps failure codes and report outcomes stable while separating generic
  renderer-report shape validation from decision-specific blocker handling.
- Uses the complexity sensor on the exact hotspot left by Batch 17.

Ousterhout lens:

- Information hiding: validation-report shape invalidity is now one named
  internal decision.
- Deep module: no public readiness API changed.
- Avoid classitis: one private helper owns a real local rule and returns the
  same data the caller already used.
- Change amplification: future changes to renderer report list validation
  should touch `_renderer_report_blockers()` instead of decision-specific
  blocker filtering.

Contracts preserved:

- `build_validation_report()` behavior;
- `ensure_ready_for_reviewer()` behavior;
- readiness blocker codes, including `renderer_validation_report_invalid`;
- packet schemas;
- CLI, Desktop/tool schema, privacy, fail-closed, reviewer-bundle,
  publication, and customer-reply boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD:src/kcs_core/readiness.py`
  produced identical `_renderer_blockers()` outputs for five representative
  renderer-report cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| read `blockers` list and invalid flag | `_renderer_report_blockers()` | Old-vs-new blocker equivalence. |
| read `checks` invalid flag | `_renderer_report_blockers()` | Old-vs-new invalid-checks equivalence. |
| read `warnings` invalid flag | `_renderer_report_blockers()` | Old-vs-new invalid-report equivalence. |
| append `renderer_validation_report_invalid` on any invalid renderer list | unchanged `_renderer_blockers()` branch using new report-invalid boolean | Old-vs-new invalid-report equivalence. |
| no-article safe-blocker filtering | unchanged `_renderer_blockers()` decision-specific branch | Old-vs-new no-article equivalence. |
| new `_renderer_report_blockers()` helper | old first three `_renderer_report_codes()` calls and invalidity expression | Private helper only; no public interface change. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old-vs-new renderer blocker equivalence passed for five representative
  cases.
- Touched subset complexity measurement reports source
  `high_complexity_functions: 0`, source `max_cc: 6`; before the batch,
  `readiness.py::_renderer_blockers` was `cc=8`.
- Focused readiness, graph policy, and freeze snapshot tests passed after the
  graph hash update.

Open follow-up:

- Aggregate review is now due before another refactor batch.

## 2026-07-07 - Slice 6 Batch 10 Draft Tool Alias

Batch: KCS-14 Slice 6 Batch 10.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_draft_tool.py`

What changed:

- Moved repeated `claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE)` calls into
  private `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS`.
- Kept operator-choice payload values, public tool surface, result contracts,
  and `__all__` unchanged.

Why under KCS-14 outcome contract:

- Keeps repeated Desktop alias knowledge in one local owner inside the draft
  tool orchestration module.
- Reduces future agent ambiguity around the submit tool used for operator
  choice follow-up payloads.
- Preserves runtime behavior while making alias usage easier to inspect.

Ousterhout lens:

- Information hiding: the draft tool alias is named once as internal module
  knowledge.
- Change amplification: future local alias-use changes should touch one private
  constant instead of three call sites.
- Avoid classitis: no class/file/public helper was introduced.
- Deep module: public tool behavior stayed stable while internal repeated
  knowledge moved downward.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- operator-choice `submit_tool` and `next_tool` values;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed the private alias constant
  matches the old call-site value.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| first `attach_pending_selection(... submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE))` | `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS` | Old-vs-new alias value equivalence. |
| second `attach_pending_selection(... submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE))` | `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS` | Old-vs-new alias value equivalence. |
| `remaining_operator_choice_status(... submit_tool=claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE))` | `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS` | Old-vs-new alias value equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` call-site alias and current private alias constant matched.
- `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.

## 2026-07-07 - Slice 6 Batch 11 Semantic Review Pending Ref

Batch: KCS-14 Slice 6 Batch 11.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_workflow.py`

What changed:

- Moved shared pending semantic-review ref/type/expiry validation into private
  `_pending_semantic_review_for_ref()`.
- Kept prepare-specific `packet_prepared` and submit-specific
  `not packet_prepared` rules at their original call sites.

Why under KCS-14 outcome contract:

- Reduces duplication in a sensitive workflow-state boundary without changing
  semantic-review packet or candidate validation contracts.
- Makes the pending-ref invariant easier to inspect before future
  semantic-review changes.
- Preserves runtime behavior while keeping Python ownership of workflow state
  explicit.

Ousterhout lens:

- Information hiding: ref/type/expiry validation for pending semantic review
  has one private owner.
- Change amplification: future ref/expiry behavior changes should touch one
  helper instead of prepare and submit paths separately.
- Avoid classitis: no new class/file/public helper was introduced.
- Deep module: public workflow behavior stayed stable while common state
  validation moved downward.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- semantic-review packet schema;
- candidate semantic extraction schema;
- prepare/submit controlled error behavior;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching prepare/submit
  outcomes for valid prepare, invalid ref, invalid type, double prepare, submit
  before prepare, and expired prepare.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| prepare path pending missing check | `_pending_semantic_review_for_ref()` | Old-vs-new exception equivalence. |
| prepare path ref type check | `_pending_semantic_review_for_ref()` | Old-vs-new exception equivalence. |
| prepare path ref mismatch check | `_pending_semantic_review_for_ref()` | Old-vs-new exception equivalence. |
| prepare path expiry check and state clear | `_pending_semantic_review_for_ref()` | Old-vs-new exception/state equivalence. |
| submit path pending missing check | `_pending_semantic_review_for_ref()` | Old-vs-new exception equivalence. |
| submit path ref type/mismatch checks | `_pending_semantic_review_for_ref()` | Old-vs-new exception equivalence. |
| submit path expiry check and state clear | `_pending_semantic_review_for_ref()` | Old-vs-new exception/state equivalence. |
| prepare one-shot `packet_prepared` guard | unchanged prepare call site | Old-vs-new double-prepare equivalence. |
| submit requires prepared packet | unchanged submit call site | Old-vs-new submit-before-prepare equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  prepare/submit outcomes and pending-state clearing behavior.
- `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Next aggregate review is due after one more refactor batch or an earlier
  methodology trigger.

## 2026-07-07 - Slice 6 Batch 12 Platform Match Flags

Batch: KCS-14 Slice 6 Batch 12.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_workflow.py`

What changed:

- Moved Windows/Linux regex match tuple construction into private
  `_platform_match_flags()`.
- Kept `_platform_type_from_text()` and `_minimal_environment_from_text()`
  behavior unchanged.

Why under KCS-14 outcome contract:

- Makes semantic-review fallback environment inference easier to inspect
  without changing semantic-review packet or candidate validation behavior.
- Gives platform match tuple knowledge one private owner.
- Preserves runtime behavior while removing an inline boolean tuple from the
  platform lookup expression.

Ousterhout lens:

- Information hiding: platform match flags are named as one internal rule.
- Cognitive load: platform type lookup now reads as mapping lookup from named
  flags.
- Avoid classitis: no class/file/public helper was introduced.
- Change amplification: future platform flag changes should touch one helper.

Contracts preserved:

- runtime behavior;
- minimal fallback environment output;
- semantic-review packet schema;
- candidate semantic extraction schema;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching platform and
  minimal-environment outputs for Linux, Windows, both-platform, and
  no-platform text.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| inline Windows regex bool in `_platform_type_from_text()` | `_platform_match_flags()` | Old-vs-new platform/env equivalence. |
| inline Linux regex bool in `_platform_type_from_text()` | `_platform_match_flags()` | Old-vs-new platform/env equivalence. |
| platform lookup tuple | `_platform_match_flags()` return value | Old-vs-new platform/env equivalence. |
| no fallback for ambiguous both-platform text | unchanged mapping behavior | Old-vs-new both-platform equivalence. |
| no fallback for missing platform text | unchanged mapping behavior | Old-vs-new no-platform equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  platform and minimal-environment outputs.
- `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.

## 2026-07-07 - Slice 6 Batch 13 Split Required Selection Result

Batch: KCS-14 Slice 6 Batch 13.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_draft_tool.py`

What changed:

- Moved repeated split-required result creation, pending-selection creation,
  and operator-choice submit-tool attachment into private
  `_split_required_selection_result()`.
- Kept primary-summary and semantic-review-submit path-specific fields at
  their original call sites.

Why under KCS-14 outcome contract:

- Reduces duplicated orchestration knowledge inside the Desktop draft workflow
  without changing Desktop result contracts.
- Makes the split-required operator-selection handoff easier to inspect before
  future multi-item workflow changes.
- Preserves runtime behavior while keeping result/status consolidation out of
  scope.

Ousterhout lens:

- Information hiding: split-required selection attachment has one private
  owner inside the draft tool.
- Change amplification: future changes to pending-selection attachment should
  touch one helper rather than the primary-summary and semantic-review-submit
  branches separately.
- Avoid classitis: no new class/file/public helper was introduced.
- Ownership over temporal order: the helper owns one decision boundary
  (split-required selection handoff), not a new workflow phase.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- Desktop `split_required` result shape;
- operator-selection ref/request attachment;
- semantic-review-submit extra fields:
  `approved_summary_source`, `reviewer_bundle_written`,
  `semantic_item_outcomes`, review-summary semantic outcomes, and
  `ticket_ref`;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Focused split-required tests passed for primary-summary multi-candidate,
  semantic-review submit multi-candidate, operator-selection payloads, and
  freeze snapshots.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| primary-summary branch builds `split_required` result | `_split_required_selection_result()` | Focused Desktop draft tests and freeze snapshots passed. |
| primary-summary branch starts pending selection | `_split_required_selection_result()` | Operator-selection and MCP Desktop split tests passed. |
| primary-summary branch attaches `kcs_draft_article` submit tool | `_split_required_selection_result()` | Operator-selection and MCP Desktop split tests passed. |
| semantic-review submit branch builds `split_required` result | `_split_required_selection_result()` | MCP Desktop and freeze snapshot tests passed. |
| semantic-review submit branch starts pending selection with outcomes | `_split_required_selection_result()` | MCP Desktop semantic-review tests passed. |
| semantic-review-specific result fields | unchanged semantic-review submit call site | MCP Desktop and freeze snapshot tests passed. |
| defensive invalid-result failure debug code | `_split_required_selection_result()` parameter | Code review mapping; branch remains defensive-only. |

Review-only drift risks:

- The defensive `result is None` branch remains review-only because normal
  helper output is expected to be stable and existing tests cover public result
  shapes, not forced monkeypatching of the defensive path.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- `tests/kcs_adapters/test_mcp_desktop.py`,
  `tests/kcs_adapters/test_desktop_workflow_results.py`,
  `tests/kcs_adapters/test_desktop_operator_selection.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- One more refactor batch may proceed before the next aggregate review if it
  remains inside a declared ownership node and avoids result/status/output
  consolidation.

## 2026-07-07 - Slice 6 Batch 14 Draft Tool Alias Completion

Batch: KCS-14 Slice 6 Batch 14.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_draft_tool.py`

What changed:

- Replaced the remaining local `claude_desktop_tool_alias(TOOL_DRAFT_ARTICLE)`
  call in the operator-selection invalid path with the existing private
  `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS` constant.

Why under KCS-14 outcome contract:

- Completes local ownership of the Desktop draft tool alias inside
  `desktop_draft_tool.py`.
- Reduces future agent ambiguity about which alias value should be used in
  operator-choice payloads.
- Preserves behavior while avoiding new helper/class/file churn.

Ousterhout lens:

- Information hiding: the canonical Desktop draft alias remains one private
  module constant.
- Change amplification: future alias changes touch one constant.
- Avoid classitis: no new abstraction was introduced.

Contracts preserved:

- runtime behavior;
- Desktop draft alias value;
- operator-selection invalid result shape;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Focused Desktop draft/operator-selection/freeze tests passed.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| selection-error submit tool alias lookup | `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS` | Focused Desktop draft/operator-selection/freeze tests passed. |

Review-only drift risks:

- none identified beyond staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- `tests/kcs_adapters/test_mcp_desktop.py`,
  `tests/kcs_adapters/test_desktop_operator_selection.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.

## 2026-07-07 - Slice 6 Batch 15 Stdio Transport Protocol Constants

Batch: KCS-14 Slice 6 Batch 15.

Affected graph node: `desktop_protocol_transport`.

Changed code:

- `src/kcs_adapters/desktop_stdio_transport.py`

What changed:

- Moved supported tool-name styles, pre-initialize ready methods, and tool-call
  parameter keys into private module constants.
- Kept the JSON-RPC transport request flow, tool dispatch, error messages, and
  MCP response envelopes unchanged.

Why under KCS-14 outcome contract:

- Switches from `desktop_draft_workflow` to the declared
  `desktop_protocol_transport` node after the aggregate gate stopped same-node
  draft workflow momentum.
- Reduces protocol-surface ambiguity by naming small transport rule sets that
  were previously inline literals.
- Preserves runtime behavior while keeping protocol transport separate from KCS
  workflow decisions and tool schema business rules.

Ousterhout lens:

- Information hiding: transport method/key rule sets are named once near the
  transport sentinel.
- Change amplification: future protocol key changes should touch one constant.
- Avoid classitis: no class/file/public helper was introduced.
- Deep module: public transport behavior stayed stable while internal rule
  names became explicit.

Contracts preserved:

- runtime behavior;
- JSON-RPC error behavior and messages;
- initialize/ping readiness behavior;
- tool-call parameter validation;
- Desktop tool schema behavior;
- MCP response envelope shape;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Focused stdio transport, MCP Desktop, and freeze snapshot tests passed.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| supported tool-name style inline set | `_SUPPORTED_TOOL_NAME_STYLES` | Focused stdio/MCP/freeze tests passed. |
| pre-initialize allowed methods `initialize` and `ping` | `_READY_BEFORE_INITIALIZED_METHODS` | Focused stdio/MCP/freeze tests passed. |
| tool-call allowed parameter keys `arguments` and `name` | `_TOOL_CALL_PARAM_KEYS` | Focused stdio/MCP/freeze tests passed. |

Review-only drift risks:

- none identified beyond staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- `tests/kcs_adapters/test_desktop_stdio_transport.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- One more `desktop_protocol_transport` batch may proceed before aggregate
  review if it remains inside protocol ownership and avoids Desktop schema or
  result-shaping changes.

## 2026-07-07 - Slice 6 Batch 16 Approved Summary Alias Table

Batch: KCS-14 Slice 6 Batch 16.

Affected graph node: `desktop_protocol_transport`.

Changed code:

- `src/kcs_adapters/desktop_payload.py`

What changed:

- Moved the ordered approved-summary item alias mapping into private
  `_APPROVED_SUMMARY_ITEM_ALIASES`.
- Replaced the repeated `move_item_alias()` call chain with a loop over the
  ordered alias table.

Why under KCS-14 outcome contract:

- Keeps approved-summary payload normalization behavior stable while making
  alias ownership explicit and reviewable.
- Reduces change amplification for future alias updates.
- Preserves alias priority by keeping the table order identical to the previous
  call order.

Ousterhout lens:

- Information hiding: alias-to-canonical field knowledge has one named private
  owner.
- Change amplification: alias changes now touch data, not a long procedural
  call chain.
- Avoid temporal decomposition: the module still owns payload normalization;
  only the alias decision table moved.
- Avoid classitis: no new class/file/public helper was introduced.

Contracts preserved:

- runtime behavior;
- approved-summary payload alias priority;
- approved-summary payload fields;
- Desktop/tool schema behavior;
- MCP/JSON-RPC transport behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Focused payload, MCP Desktop, and freeze snapshot tests passed.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| sequential alias priority in `normalize_approved_summary_item()` | `_APPROVED_SUMMARY_ITEM_ALIASES` order | Focused payload/MCP/freeze tests passed. |
| alias movement behavior | unchanged `move_item_alias()` | Focused payload/MCP/freeze tests passed. |

Review-only drift risks:

- Alias priority remains review-sensitive because order matters when multiple
  aliases target the same canonical field. The staged diff preserves the old
  order exactly.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- `tests/kcs_adapters/test_desktop_payload.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.

## 2026-07-07 - Slice 6 Batch 8 Existing Article Text Fields

Batch: KCS-14 Slice 6 Batch 8.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_authoring_pipeline.py`

What changed:

- Moved explicit existing-article text field groups into private
  `_EXPLICIT_EXISTING_ARTICLE_TEXT_FIELDS` and
  `_EXPLICIT_EXISTING_ARTICLE_LIST_FIELDS`.
- Kept `_explicit_existing_article_text()`,
  `_explicit_existing_article_match()`, `_approved_summary_reuse_results()`,
  public helper names, and `__all__` unchanged.

Why under KCS-14 outcome contract:

- Keeps the approved-summary refactor inside one ownership module.
- Reduces future agent ambiguity by naming which item fields are part of
  existing-article detection.
- Preserves runtime behavior while making the field ownership easier to review
  and less likely to drift through inline tuple edits.

Ousterhout lens:

- Information hiding: explicit article detection field groups are named as
  private module knowledge.
- Change amplification: future changes to detection fields should touch one
  field group instead of inline loop literals.
- Avoid classitis: no class/file/public helper was introduced.
- Deep module: public authoring pipeline helpers stayed stable while internal
  field knowledge became easier to inspect.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- explicit existing-article text, match, and reuse-results outputs;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching text, match, and
  reuse-results outputs for string-field, list-field, and mixed non-string
  item cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| inline string fields in `_explicit_existing_article_text()` | `_EXPLICIT_EXISTING_ARTICLE_TEXT_FIELDS` | Old-vs-new text/match/reuse-results equivalence. |
| inline list fields in `_explicit_existing_article_text()` | `_EXPLICIT_EXISTING_ARTICLE_LIST_FIELDS` | Old-vs-new text/match/reuse-results equivalence. |
| ignore non-string scalar values | unchanged loop using named field group | Old-vs-new mixed non-string equivalence. |
| include only string list items | unchanged loop using named field group | Old-vs-new mixed non-string equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  explicit existing-article text, match, and reuse-results outputs.
- `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Remaining `desktop_draft_workflow` files are not refactored in this batch.
- Aggregate review is due before starting another refactor batch unless an
  earlier methodology trigger has already stopped the sequence.

## 2026-07-07 - Slice 6 Batch 9 Draft Call Shape

Batch: KCS-14 Slice 6 Batch 9.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_draft_tool.py`

What changed:

- Moved primary draft-call booleans into private
  `_DraftArticlePrimaryCallShape`.
- Kept `_draft_article_primary_surface_result()` routing behavior, public tool
  surface, result contracts, and `__all__` unchanged.

Why under KCS-14 outcome contract:

- Makes the Desktop draft call-shape decision explicit before any broader
  workflow refactor.
- Reduces future agent ambiguity around which combinations are accepted by the
  primary tool surface.
- Preserves runtime behavior while grouping route-classification knowledge
  behind one private value object.

Ousterhout lens:

- Information hiding: the derived call-shape booleans are grouped behind one
  internal value object.
- Cognitive load: routing reads as named cases instead of repeated negative
  boolean conjunctions.
- Avoid classitis: the dataclass is private and owns a real derived decision
  shape; it does not add a public interface.
- Change amplification: future primary-surface route changes should touch the
  call-shape owner and route dispatch together.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- primary draft-call route behavior;
- invalid call-shape failure behavior;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching
  `_draft_article_primary_surface_result()` routes and semantic-review clear
  counts for summary, ticket-ref, operator-selection, invalid mixed, empty, and
  unknown-argument cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| `has_summary` local bool | `_DraftArticlePrimaryCallShape.has_summary` | Old-vs-new route equivalence. |
| `has_selection_ref` local bool | `_DraftArticlePrimaryCallShape.has_selection_ref` | Old-vs-new route equivalence. |
| `has_selected_item_ref` local bool | `_DraftArticlePrimaryCallShape.has_selected_item_ref` | Old-vs-new route equivalence. |
| `has_ticket_ref` local bool | `_DraftArticlePrimaryCallShape.has_ticket_ref` | Old-vs-new route equivalence. |
| summary-only route condition | `_DraftArticlePrimaryCallShape.is_summary_authoring` | Old-vs-new route and clear-count equivalence. |
| ticket-ref-only route condition | `_DraftArticlePrimaryCallShape.is_ticket_ref_authoring` | Old-vs-new route and clear-count equivalence. |
| operator-selection route condition | `_DraftArticlePrimaryCallShape.is_operator_selection_authoring` | Old-vs-new route and clear-count equivalence. |
| invalid mixed/empty route behavior | unchanged fallback after call-shape checks | Old-vs-new failure result equivalence. |
| unknown primary-surface argument behavior | unchanged primary-arg subset guard | Old-vs-new `None` route equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  primary-surface routes and semantic-review clear counts.
- `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
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

## 2026-07-07 - Slice 6 Batch 7 Approved Summary Reuse Source

Batch: KCS-14 Slice 6 Batch 7.

Affected graph node: `desktop_draft_workflow`.

Changed code:

- `src/kcs_adapters/desktop_authoring_pipeline.py`

What changed:

- Moved the nested `ReuseSearchResultsPacket.search_source` selection rule into
  private `_approved_summary_reuse_search_source()`.
- Kept `_approved_summary_reuse_results()` output, public helper names, and
  `__all__` unchanged.

Why under KCS-14 outcome contract:

- Continues the `desktop_draft_workflow` refactor with a small internal
  cognitive-load reduction.
- Reduces future agent ambiguity by naming the reuse-source decision instead of
  embedding it in a nested conditional expression.
- Preserves runtime behavior while making the existing decision easier to
  review against reuse-search cases.

Ousterhout lens:

- Information hiding: the search-source mapping is now one named internal rule.
- Cognitive load: `_approved_summary_reuse_results()` now assembles the packet
  while the source-selection decision lives in a focused helper.
- Avoid classitis: no new class/file/public helper was introduced.
- Change amplification: future source-label changes should touch one helper
  rather than packet construction shape.

Contracts preserved:

- runtime behavior;
- public helper names and `__all__`;
- `ReuseSearchResultsPacket` values for explicit article references, checked
  reuse search, and skipped reuse search;
- Desktop/tool schema behavior;
- packet schemas;
- privacy, fail-closed, reviewer-bundle, publication, and customer-reply
  boundaries.

Behavior drift check:

- Direct old-vs-new comparison against `HEAD` showed matching
  `_approved_summary_reuse_results()` outputs for explicit article reference,
  checked reuse, and skipped reuse cases.

Behavior drift mapping:

| Old behavior element | New location | Evidence |
| --- | --- | --- |
| explicit article reference -> `operator_explicit_existing_article_reference` | `_approved_summary_reuse_search_source()` | Old-vs-new reuse-results equivalence. |
| reuse checked -> `operator_approved_summary` | `_approved_summary_reuse_search_source()` | Old-vs-new reuse-results equivalence. |
| reuse skipped -> `operator_approved_summary_reuse_skipped` | `_approved_summary_reuse_search_source()` | Old-vs-new reuse-results equivalence. |
| `matches` selection for explicit article references | unchanged `_approved_summary_reuse_results()` | Old-vs-new reuse-results equivalence. |

Review-only drift risks:

- none identified beyond mechanical equivalence and staged-diff review.

Verdict:

- no drift found by listed checks; residual risks listed above.

Evidence:

- Old `HEAD` implementation and current implementation produced matching
  `ReuseSearchResultsPacket` values for explicit article reference, checked
  reuse, and skipped reuse cases.
- `tests/kcs_adapters/test_desktop_workflow.py`,
  `tests/kcs_adapters/test_desktop_draft_tool.py`,
  `tests/kcs_adapters/test_mcp_desktop.py`, and
  `tests/policy/test_kcs14_freeze_snapshots.py` passed.
- Ruff passed for the touched source/test paths.

Open follow-up:

- Remaining `desktop_draft_workflow` files are not refactored in this batch.
- Next aggregate review is due after one more refactor batch or an earlier
  methodology trigger.
