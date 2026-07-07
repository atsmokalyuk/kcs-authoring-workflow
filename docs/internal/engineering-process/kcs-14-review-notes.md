# KCS-14 Review Notes

Use this file for material KCS-14 process, documentation, code-map, refactor,
and review-tooling verdicts.

Core runtime review notes remain in
`docs/internal/kcs-core-pipeline-review-notes.md` unless a KCS-14 slice touches
core runtime boundaries.

Each entry should include:

- slice;
- reviewer or review route;
- changed files;
- unchanged contracts;
- validation evidence;
- findings;
- promotion candidates or explicit "none";
- deferred risks;
- closeout metadata, when material;
- final verdict.

## 2026-07-05 - Slice 0 Documentation Ownership Cleanup

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `.gitignore`
- `README.md`
- `docs/internal/kcs-authoring-mvp-feature-engineering.md`
- `docs/internal/kcs-authoring-mvp-jira-tracking.md`
- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/engineering-process/`
- `docs/internal/portability/portability-from-plesk-support.md`
- `engineering-playbook/`
- `tests/policy/test_kcs14_docs_policy.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py -q` passed.
- Active KCS-14/KCS-15 conflict grep is covered by
  `test_active_docs_do_not_define_kcs14_as_style_or_markup_parity`.
- Tracked path reference validation is covered by
  `test_tracked_policy_docs_reference_existing_repo_paths`.

Findings:

- `AGENTS.md` and `.gitignore` were previously ignored/untracked, which meant
  the policy kernel and ignore rules were not available from a fresh clone.
- Authoritative process docs under `local-docs/` were copied to tracked
  `docs/internal/engineering-process/` paths.
- `local-docs/` remains developer-local and ignored for personal notes,
  temporary drafts, and local-only observations.

Deferred risks:

- Slice 1 still needs to make the agent-operable workflow authoritative and
  run the unsupported-harness check over active docs.
- Slice 2 still needs the tracked `tool-entrypoints.md` artifact.
- Slice 4 still needs the file-based review packet format and validator.
- The local debug artifact under `local-data/debug/` remains untracked and was
  intentionally excluded.

Closeout metadata:

- slice id: KCS-14 Slice 0
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: numbering/history policy check; tracked path
  reference check
- findings promoted to future checks: unsupported-harness check in Slice 1;
  review packet shape/forbidden-content checks in Slice 4
- deferred risks: tool entrypoints, code-review graph baseline, review packet format, refactor
  freeze checks

Final verdict: Slice 0 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 1 Engineering Process Baseline

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `tests/policy/test_kcs14_docs_policy.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_docs_policy.py` passed.
- Agent workflow authoritative status is covered by
  `test_agent_workflow_is_tracked_authoritative_process`.
- Unsupported development harness wording is covered by
  `test_active_docs_do_not_list_claude_code_as_active_harness`.

Findings:

- `agent-operable-engineering-workflow.md` is now the authoritative tracked
  development-agent workflow below `AGENTS.md`.
- `AGENTS.md` references the workflow as an authoritative layer without
  duplicating the detailed procedure.
- The authority ladder no longer treats local workflow drafts as an
  authoritative layer.

Deferred risks:

- Slice 2 still needs the tracked `tool-entrypoints.md` artifact and command
  classification.
- Slice 4 still needs the file-based review packet format and validator.

Closeout metadata:

- slice id: KCS-14 Slice 1
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: unsupported-harness policy check; authoritative
  workflow check
- findings promoted to future checks: none
- deferred risks: tool entrypoints and review packet format

Final verdict: Slice 1 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 2 Local Tool Entrypoints

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `docs/internal/engineering-process/tool-entrypoints.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `tests/policy/test_tool_entrypoints.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py` passed.
- Tool command coverage is checked by
  `test_tool_entrypoints_doc_lists_supported_commands`.
- Deterministic/manual command classification is checked by
  `test_tool_entrypoints_doc_classifies_deterministic_and_manual_commands`.
- Help-only liveness is checked by
  `test_documented_help_entrypoints_are_alive`.

Findings:

- `tool-entrypoints.md` is now the authoritative tracked local command
  surface for KCS-14 engineering work.
- `AGENTS.md` keeps only a compact index and delegates command details to the
  tracked tool-entrypoints document.
- Deterministic checks, manual Desktop/UI steps, and local side-effect commands
  are separated so agents can choose the right validation surface without
  inventing ad hoc workflows.

Deferred risks:

- Slice 3 still needs functional-test-from-behavior templates and fixture
  provenance checks.
- Slice 4 still needs the file-based review packet format and validator.
- Slice 5 still needs the code-review graph baseline before codebase refactor work.

Closeout metadata:

- slice id: KCS-14 Slice 2
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: tool-entrypoint command coverage;
  deterministic/manual classification; help-only liveness checks
- findings promoted to future checks: fixture provenance in Slice 3; review
  packet shape in Slice 4; code-map staleness in Slice 5
- deferred risks: functional test templates, review packet format, code-review graph baseline

Final verdict: Slice 2 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 3 Functional Test From Behavior

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `docs/internal/engineering-process/functional-test-from-behavior.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/spec-first-engineering-playbook/05-test-plan.md`
- `tests/policy/test_functional_test_policy.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py` passed.
- Functional-test process coverage is checked by
  `test_functional_test_process_doc_defines_required_fixture_tiers`.
- Committed clean-ticket-derived fixture provenance is checked by
  `test_committed_clean_ticket_derived_fixtures_have_provenance`.
- Privacy-scan markers and private-value patterns are checked by
  `test_committed_clean_ticket_derived_fixtures_have_privacy_scan_marker` and
  `test_committed_clean_ticket_fixtures_do_not_contain_private_values`.
- Local clean-ticket refs are checked by
  `test_local_clean_ticket_ref_fixtures_are_skip_if_absent`.

Findings:

- `functional-test-from-behavior.md` is now the authoritative tracked process
  doc for turning accepted behavior into pytest scenarios.
- The spec-first test-plan template now points to the authoritative process
  doc and no longer embeds a project-specific reviewer-packet slice instance.
- Policy tests now protect the two-tier fixture model for future committed
  clean-ticket-derived fixtures and local-ref fixtures.

Deferred risks:

- Slice 4 still needs the file-based review packet format and validator.
- Slice 5 still needs the code-review graph baseline before codebase refactor work.
- Slice 6 still needs reviewed test inventory before behavior-preserving
  refactors.

Closeout metadata:

- slice id: KCS-14 Slice 3
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: functional-test process doc coverage; fixture
  provenance; fixture privacy-scan marker; private-value pattern scan for
  committed clean-ticket fixtures; local-ref skip-if-absent check
- findings promoted to future checks: review packet shape in Slice 4; code-map
  staleness in Slice 5; freeze-list checks in Slice 6
- deferred risks: review packet format, code-review graph baseline, refactor test inventory

Final verdict: Slice 3 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 4 Review Context Protocol

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/promotion-candidates.md`
- `docs/internal/engineering-process/review-context-protocol.md`
- `docs/internal/engineering-process/review-packets/kcs-14-slice-4-doc-only-review-packet.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-1-agent-operable-workflow-feature-note.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-2-local-tool-entrypoints-feature-note.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-3-functional-test-from-behavior-feature-note.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-4-review-context-protocol-feature-note.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-4-enforcement-ladder-feature-note.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-engineering-and-codebase-design-hardening.md`
- `tests/policy/test_review_context_policy.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py tests/policy/test_review_context_policy.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py tests/policy/test_review_context_policy.py` passed.
- Review packet required sections are checked by
  `test_review_context_protocol_defines_required_packet_sections` and
  `test_file_based_review_packets_have_required_sections`.
- Forbidden content and output budget rules are checked by
  `test_review_context_protocol_defines_forbidden_content_and_output_budget`
  and `test_file_based_review_packets_do_not_include_forbidden_content`.
- Promotion candidate fields and cadence are checked by
  `test_promotion_candidate_registry_defines_required_fields` and
  `test_promotion_protocol_keeps_automation_after_stability`.

Findings:

- `review-context-protocol.md` is now the authoritative tracked protocol for
  compact review packets, forbidden-content boundaries, output budget, review
  harness routing, and promotion-candidate workflow.
- `promotion-candidates.md` now records repeated findings that may move down
  the enforcement ladder.
- A dry-run doc-only review packet exists under `review-packets/` and is
  covered by packet-shape and forbidden-content checks.

Promotion candidates:

- none new. This slice created the registry and recorded already implemented
  promotions from Slices 0 through 3.

Deferred risks:

- Slice 5 still needs the code-review graph baseline before codebase refactor work.
- Slice 7 still needs to automate only promoted, stable, mechanically
  checkable rules.
- Reusable extraction remains deferred until after a later retrospective.

Closeout metadata:

- slice id: KCS-14 Slice 4
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: review packet required sections; file-based
  packet required sections; review protocol forbidden-content/output-budget
  anchors; file-based packet forbidden-content scan; promotion-candidate field
  coverage; promotion-cadence anchors
- findings promoted to future checks: code-map staleness in Slice 5;
  freeze-list checks in Slice 6; stable automation candidates in Slice 7
- deferred risks: code-review graph baseline, refactor freeze checks, review tooling automation

Final verdict: Slice 4 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 5 Code-Review Graph Baseline

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `AGENTS.md`
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/module-boundaries.md`
- `docs/internal/engineering-process/review-checkpoints.md`
- `docs/internal/engineering-process/review-context-protocol.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-engineering-and-codebase-design-hardening.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-5-code-review-graph-baseline-feature-note.md`
- `tests/policy/test_code_review_graph_policy.py`
- `tests/policy/test_review_context_policy.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py tests/policy/test_review_context_policy.py tests/policy/test_code_review_graph_policy.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py tests/policy/test_review_context_policy.py tests/policy/test_code_review_graph_policy.py` passed.
- `git diff --check` passed.
- Graph shape, repo-relative path references, file existence, contract-edge
  references, and file-hash staleness are checked by
  `tests/policy/test_code_review_graph_policy.py`.

Findings:

- `code-review-graph.json` now maps all current Python source files under
  `src/`, all Python test files under `tests/`, and refactor-relevant local
  tooling/package files under `scripts/` and `packaging/` before
  behavior-preserving refactor work.
- `module-boundaries.md` records human-readable ownership, must-not-own
  boundaries, and refactor risks for each mapped area.
- `review-checkpoints.md` defines how to use affected graph nodes before
  coding, during staged-diff review, and at closeout.
- Review packets should now include affected code-map nodes where practical.
- `kcs-14-slice-6-refactor-methodology.md` records the distilled Fable 5
  methodology review for Slice 6 target ordering and pre-refactor gates.

Promotion candidates:

- none new. This slice implemented the planned code-map staleness check from
  prior closeouts.

Deferred risks:

- Slice 6 still needs to select refactor targets from reviewed graph nodes and
  keep each refactor scoped to one ownership area.
- Slice 6 still needs freeze-list checks for public/runtime contracts before
  touching risky boundaries.
- Slice 7 may automate diff-to-contract review only after this manual graph
  usage proves stable.

Closeout metadata:

- slice id: KCS-14 Slice 5
- affected graph nodes: `desktop_tool_surface`, `clean_ticket_storage`,
  `desktop_protocol_transport`, `provider_handoff_boundary`,
  `semantic_review_fallback`, `desktop_draft_workflow`,
  `packet_validation_decision`, `cli_ingest_readiness`,
  `renderer_style_gates`, `reviewer_bundle_output`, `smoke_log_tooling`,
  `packaging_and_install_tooling`, `package_surface`,
  `engineering_policy_tests`
- graph hashes updated: initial snapshot for commit `a497d74`
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: code-review graph shape; full Python source,
  test, script, and packaging file coverage; repo-relative path and file
  existence; graph file-hash staleness; graph edge integrity; forbidden
  private/raw artifact markers; code-map feature note shape
- findings promoted to future checks: freeze-list checks in Slice 6; stable
  diff-to-contract tooling in Slice 7
- deferred risks: Slice 6 commit 0 freeze/snapshot checks; result-shaping
  ownership decision before related refactor targets; behavior-preserving
  refactor; review tooling automation

Final verdict: Slice 5 implementation checkpoint is ready for external review.

## 2026-07-05 - Slice 6 Commit 0 Freeze/Snapshot Checks

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-commit-0-freeze-snapshots.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-refactor-methodology.md`
- `docs/internal/engineering-process/tool-entrypoints.md`
- `tests/policy/test_kcs14_freeze_snapshots.py`
- `tests/policy/test_tool_entrypoints.py`

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_tool_entrypoints.py tests/policy/test_functional_test_policy.py tests/policy/test_review_context_policy.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check tests/policy/test_kcs14_freeze_snapshots.py tests/policy/test_tool_entrypoints.py` passed.
- `git diff --check` passed.

Findings:

- Slice 6 now has pre-refactor freeze/snapshot checks before code movement.
- The new checks snapshot Desktop tool names, Desktop aliases, input schema
  properties, required input fields, read/idempotency hints, tool output success
  keys, packet schema versions and dataclass field sets, MCP result envelope
  keys, compact Desktop result key sets, and high-risk frozen contract paths.
- Snapshot failures during Slice 6 must be treated as contract-drift evidence
  until explicitly reviewed.
- The code-review graph now covers the new freeze/snapshot policy test.

Promotion candidates:

- none new. This commit implemented the planned Slice 6 freeze/snapshot checks.

Deferred risks:

- First refactor batch still needs a behavior-preserving target frame for
  `smoke_log_tooling`.
- Result-shaping ownership decision still must be written before touching
  `desktop_draft_workflow` or `desktop_tool_surface` result-shaping files.
- Freeze/snapshot tests protect public shapes, but design judgment still
  requires staged review with the Ousterhout and module-boundary checklists.

Closeout metadata:

- slice id: KCS-14 Slice 6 commit 0
- affected graph nodes: `engineering_policy_tests`, `desktop_tool_surface`,
  `desktop_protocol_transport`, `desktop_draft_workflow`,
  `packet_validation_decision`, `semantic_review_fallback`,
  `reviewer_bundle_output`
- graph hashes updated: `tests/policy/test_tool_entrypoints.py` and
  `tests/policy/test_kcs14_freeze_snapshots.py`
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: Desktop tools/list snapshot; tool output key-set
  snapshot; packet schema/version/field-set snapshot; MCP envelope key-set
  snapshot; compact result key-set snapshot; frozen contract path diff gate
- findings promoted to future checks: none
- deferred risks: first refactor batch, result-shaping ownership gate,
  behavior-preserving refactor review

Final verdict: Slice 6 is ready for the first behavior-preserving refactor
batch after staged-diff review and commit of this pre-refactor safety layer.

## 2026-07-05 - Slice 6 Batch 1 Smoke Log Tooling

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-1-smoke-log-tooling.md`
- `src/kcs_adapters/smoke_accounting.py`

Unchanged contracts:

- runtime behavior unchanged;
- smoke-accounting JSON output contract unchanged;
- CLI exit codes and value-safe error codes unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across six representative
  transcripts, confirming matching report JSON payloads for old inline local
  variables and new `_SmokeMarkers` fields.
- `uv run pytest tests/kcs_adapters/test_smoke_accounting.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/smoke_accounting.py tests/kcs_adapters/test_smoke_accounting.py` passed.
- `uv run pytest tests/kcs_adapters/test_smoke_accounting.py tests/kcs_adapters/test_mcpb_package.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed with two existing skips.
- `git diff --check` passed.

Findings:

- `build_smoke_accounting_report` now delegates regex marker extraction to an
  internal `_SmokeMarkers` value object.
- The public `SmokeAccountingReport` schema and CLI behavior are covered by
  existing characterization tests.
- Freeze/snapshot checks stayed green, so no packet, Desktop, or compact result
  contract drift was detected.
- `kcs-14-refactor-log.md` records the human-readable rationale and maps the
  change to the KCS-14 outcome contract and Ousterhout review lens.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Desktop log checker and MCPB/UI smoke scripts remain untouched in this batch.
- Aggregate design review is not due until after the second refactor batch or
  an earlier event trigger.
- Result-shaping ownership decision still must be written before touching
  `desktop_draft_workflow` or `desktop_tool_surface` result-shaping files.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 1
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/smoke_accounting.py`
- batches since aggregate review: 1
- net module/file count change by node: `smoke_log_tooling` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `build_smoke_accounting_report` remains the entrypoint
- complexity distribution: not measured by a tool; local extraction complexity
  moved behind `_SmokeMarkers`
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: remaining smoke/log scripts, aggregate design review after
  batch 2, result-shaping ownership gate

Final verdict: Slice 6 batch 1 is ready for staged-diff review.

## 2026-07-06 - Slice 6 Batch 2 Desktop Log Checker

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-process-gap-audit.md`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-2-desktop-log-checker.md`
- `scripts/check_claude_kcs_desktop_log.py`

Unchanged contracts:

- runtime behavior unchanged;
- Desktop log-check CLI arguments and exit codes unchanged;
- `check_log()` report shape, `schema_version`, `error_code`, and `checks`
  keys unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across five representative
  synthetic log cases, confirming matching `check_log()` report dictionaries
  for old parallel expected-tool data and new `_EXPECTED_TOOLS` entries.
- `uv run pytest tests/kcs_adapters/test_mcpb_package.py::test_claude_desktop_log_check_accepts_latest_thin_tool_surface tests/kcs_adapters/test_mcpb_package.py::test_claude_desktop_log_check_rejects_stale_tool_surface tests/kcs_adapters/test_mcpb_package.py::test_claude_desktop_log_check_accepts_truncated_latest_tool_surface tests/kcs_adapters/test_mcpb_package.py::test_claude_desktop_log_check_honors_since_timestamp tests/policy/test_tool_entrypoints.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run pytest tests/kcs_adapters/test_mcpb_package.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py tests/policy/test_tool_entrypoints.py -q` passed with two existing skips.
- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_review_context_policy.py tests/policy/test_functional_test_policy.py -q` passed.
- `uv run ruff check scripts/check_claude_kcs_desktop_log.py tests/kcs_adapters/test_mcpb_package.py` passed.
- `git diff --cached --check` passed.

Findings:

- Desktop tool-surface expectations now have one private owner in
  `_EXPECTED_TOOLS`.
- The first attempted implementation used `@dataclass`, but existing tests
  caught an import-loader incompatibility. The implementation now uses a
  private `NamedTuple`, preserving the intended internal shape without changing
  behavior.
- No graph ownership definitions changed; only the touched script hash changed.
- Freeze/snapshot checks stayed green, so no packet, Desktop, or compact result
  contract drift was detected by the listed checks.

Promotion candidates:

- none new. The import-loader failure was fixed inside the batch and did not
  recur across closeouts.

Deferred risks:

- `scripts/smoke_kcs_mcpb_stdio.py` and
  `scripts/smoke_claude_desktop_ui_prompt.py` remain untouched.
- Aggregate design review is now due before starting Slice 6 Batch 3.
- Result-shaping ownership decision still must be written before touching
  `desktop_draft_workflow` or `desktop_tool_surface` result-shaping files.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 2
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- graph hashes updated: `scripts/check_claude_kcs_desktop_log.py`
- batches since aggregate review: 2
- net module/file count change by node: `smoke_log_tooling` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `check_log()` remains the entrypoint
- complexity distribution: not measured by a tool; expected-tool knowledge
  moved into one private table
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: remaining smoke/log scripts, aggregate design review before
  batch 3, result-shaping ownership gate

Final verdict: Slice 6 batch 2 is ready for commit. Do not start Slice 6 batch
3 until aggregate design review is complete.

## 2026-07-06 - Slice 6 Aggregate Review After Batches 1-2

Reviewer or review route: local Codex aggregate design checkpoint.

Review artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-aggregate-review-batches-1-2.md`

Scope:

- Batch 1 `smoke_log_tooling`: `src/kcs_adapters/smoke_accounting.py`
- Batch 2 `smoke_log_tooling`:
  `scripts/check_claude_kcs_desktop_log.py`

Aggregate findings:

- Both batches stayed inside the declared `smoke_log_tooling` node plus graph
  and closeout metadata.
- Net file/module count change was 0.
- Public interface/export count change was 0.
- Caller-facing entrypoints stayed unchanged.
- Graph ownership definitions did not change.
- Freeze/snapshot false positives: none.
- Test assertion edits or justified exceptions: none.
- Review blockers: none.
- `must_not_own` near-misses: none.
- Promotion candidates: none.
- Demotion candidates: none.

Triage:

- `map_error`: no.
- `process_error`: no.
- `architecture_error`: no.

Outcome:

- Continue current node-by-node refactor.
- Architecture Patterns with Python is not activated by these batches.
- No higher-level design note is required.
- No promotion or demotion action is required.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- safety floor remains intact by freeze/snapshot evidence and related tests.

Closeout metadata:

- slice id: KCS-14 Slice 6 aggregate review batches 1-2
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- aggregate review trigger: two completed refactor batches
- aggregate review outcome: continue node-by-node refactor
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none
- next aggregate review due: after two more refactor batches or an earlier
  methodology trigger

Final verdict: Aggregate review gate is complete. Slice 6 may continue with the
next scoped refactor batch after the normal context window check and process
gap audit.

## 2026-07-07 - Slice 6 Result-Shaping Ownership Decision

Reviewer or review route: local Codex design checkpoint.

Decision artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-result-shaping-ownership-decision.md`

Scope:

- `src/kcs_adapters/desktop_tool_results.py`
- `src/kcs_adapters/desktop_mcp_results.py`
- `src/kcs_adapters/desktop_draft_output.py`
- `src/kcs_adapters/desktop_workflow_results.py`
- `src/kcs_adapters/desktop_workflow_status.py`

Decision summary:

- `desktop_mcp_results.py` owns MCP envelope shape:
  `content`, `isError`, `structuredContent`, `McpToolResult`, and envelope
  validation against descriptor output schemas.
- `desktop_tool_results.py` owns Desktop-visible tool-result text,
  `structuredContent` filtering, output-size limits, forbidden payload gates,
  and reviewer-only HTML presentation boundaries.
- `desktop_workflow_results.py`, `desktop_workflow_status.py`, and
  `desktop_draft_output.py` own workflow status semantics, compact draft result
  semantics, blockers, `debug_code`, `failure_stage`, `recommended_action`,
  split/operator-selection results, semantic-review breakpoint results, and
  quality-blocked draft output.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- no Architecture Patterns activation.

Validation evidence:

- Docs-only ownership decision; no runtime code changed.
- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_review_context_policy.py tests/policy/test_code_review_graph_policy.py -q` passed.
- `git diff --check` passed.

Promotion candidates:

- none new. This implements the planned Slice 6 result-shaping ownership gate.

Deferred risks:

- Future result-shaping refactor batches must state which owner they simplify
  before editing code.
- Moving logic across these ownership groups must be the declared scope of a
  future batch, not an incidental side effect.

Closeout metadata:

- slice id: KCS-14 Slice 6 result-shaping ownership decision
- affected graph nodes: `desktop_tool_surface`, `desktop_protocol_transport`,
  `desktop_draft_workflow`
- graph hashes updated: none; docs-only decision
- aggregate review trigger: none
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none

Final verdict: Result-shaping ownership gate is complete. Slice 6 may start a
scoped `desktop_draft_workflow` or `desktop_tool_surface` refactor batch after
the normal context window check and process-gap audit.

## 2026-07-07 - Slice 6 Batch 5 Draft Argument Selection Fields

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-5-draft-argument-selection-fields.md`
- `src/kcs_adapters/desktop_draft_arguments.py`

Unchanged contracts:

- runtime behavior unchanged;
- Desktop draft argument allow-lists unchanged;
- public helper names and `__all__` unchanged;
- `DraftArticleArgumentError` and `ContractValidationError` behavior
  unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across representative helper
  outputs/exceptions for draft argument mappings.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_workflow_results.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_workflow_results.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_review_context_policy.py tests/policy/test_functional_test_policy.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_draft_arguments.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py` passed.
- `git diff --check` passed.

Findings:

- Operator-selection draft argument fields now have one private owner in
  `_DRAFT_ARTICLE_OPERATOR_SELECTION_FIELDS`.
- No public helper, allow-list, exception, workflow status, result-shaping, or
  Desktop protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Next aggregate design review is due after one more refactor batch or an
  earlier methodology trigger.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 5
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_draft_arguments.py`
- batches since aggregate review: 1
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  draft argument helpers remain the entrypoints
- complexity distribution: not measured by a tool; repeated operator-selection
  argument field knowledge moved into one private set
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: one more batch before aggregate review, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 5 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Batch 6 Operator Selection Remaining Cards

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-6-operator-selection-remaining-cards.md`
- `src/kcs_adapters/desktop_operator_selection.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- operator choice request, submit options, review summary, and remaining status
  payload shapes unchanged;
- `ContractValidationError` behavior for already-used and invalid selections
  unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across representative
  pending-selection helper outputs/exceptions.
- `uv run pytest tests/kcs_adapters/test_desktop_operator_selection.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_operator_selection.py tests/kcs_adapters/test_desktop_operator_selection.py` passed.
- `git diff --check` passed.

Findings:

- Remaining operator-selection candidate-card filtering now has one private
  owner in `_remaining_candidate_cards()`.
- No public helper, payload key, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Aggregate design review is now due before starting another refactor batch.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 6
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_operator_selection.py`
- batches since aggregate review: 2
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  operator-selection helpers remain the entrypoints
- complexity distribution: not measured by a tool; repeated remaining-card
  filtering moved into one private helper
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: aggregate review before next refactor batch, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 6 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Aggregate Review After Batches 5-6

Reviewer or review route: local Codex aggregate design checkpoint.

Review artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-aggregate-review-batches-5-6.md`

Scope:

- Batch 5 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_draft_arguments.py`
- Batch 6 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_operator_selection.py`

Aggregate findings:

- Both batches stayed inside the declared `desktop_draft_workflow` node plus
  graph and closeout metadata.
- Net file/module count change was 0.
- Public interface/export count change was 0.
- Caller-facing entrypoints stayed unchanged.
- Graph ownership definitions did not change.
- Freeze/snapshot false positives: none.
- Test assertion edits or justified exceptions: none.
- Review blockers: none.
- `must_not_own` near-misses: none.
- Promotion candidates: none.
- Demotion candidates: none.

Triage:

- `map_error`: no.
- `process_error`: no.
- `architecture_error`: no.

Outcome:

- Continue current node-by-node refactor.
- Architecture Patterns with Python is not activated by these batches.
- No higher-level design note is required.
- No promotion or demotion action is required.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- safety floor remains intact by freeze/snapshot evidence and related tests.

Closeout metadata:

- slice id: KCS-14 Slice 6 aggregate review batches 5-6
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- aggregate review trigger: two completed refactor batches
- aggregate review outcome: continue node-by-node refactor
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none
- next aggregate review due: after two more refactor batches or an earlier
  methodology trigger

Final verdict: Aggregate review gate is complete. Slice 6 may continue with the
next scoped refactor batch after the normal context window check and process
gap audit.

## 2026-07-07 - Slice 6 Batch 7 Approved Summary Reuse Source

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-7-approved-summary-reuse-source.md`
- `src/kcs_adapters/desktop_authoring_pipeline.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- `ReuseSearchResultsPacket` values unchanged for explicit article references,
  checked reuse search, and skipped reuse search;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across explicit article
  reference, checked reuse, and skipped reuse cases.
- `uv run pytest tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_authoring_pipeline.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py` passed.
- `git diff --check` passed.

Findings:

- Approved-summary reuse search-source selection now has one private owner in
  `_approved_summary_reuse_search_source()`.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Next aggregate design review is due after one more refactor batch or an
  earlier methodology trigger.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 7
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_authoring_pipeline.py`
- batches since aggregate review: 1
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  approved-summary authoring helpers remain the entrypoints
- complexity distribution: not measured by a tool; nested reuse-source
  decision moved into one private helper
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: one more batch before aggregate review, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 7 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Batch 8 Existing Article Text Fields

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-8-existing-article-text-fields.md`
- `src/kcs_adapters/desktop_authoring_pipeline.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- explicit existing-article text, match, and reuse-results outputs unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across string-field, list-field,
  and mixed non-string item cases.
- `uv run pytest tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_authoring_pipeline.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py` passed.
- `git diff --check` passed.

Findings:

- Explicit existing-article detection field groups now have private named
  owners.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Aggregate design review is now due before starting another refactor batch.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 8
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_authoring_pipeline.py`
- batches since aggregate review: 2
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  approved-summary authoring helpers remain the entrypoints
- complexity distribution: not measured by a tool; inline explicit-article
  field groups moved into named private tuples
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: aggregate review before next refactor batch, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 8 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Aggregate Review After Batches 7-8

Reviewer or review route: local Codex aggregate design checkpoint.

Review artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-aggregate-review-batches-7-8.md`

Scope:

- Batch 7 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_authoring_pipeline.py`
- Batch 8 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_authoring_pipeline.py`

Aggregate findings:

- Both batches stayed inside the declared `desktop_draft_workflow` node plus
  graph and closeout metadata.
- Net file/module count change was 0.
- Public interface/export count change was 0.
- Caller-facing entrypoints stayed unchanged.
- Graph ownership definitions did not change.
- Freeze/snapshot false positives: none.
- Test assertion edits or justified exceptions: none.
- Review blockers: none.
- `must_not_own` near-misses: none.
- Promotion candidates: none.
- Demotion candidates: none.

Triage:

- `map_error`: no.
- `process_error`: no.
- `architecture_error`: no.

Outcome:

- Continue current node-by-node refactor.
- Architecture Patterns with Python is not activated by these batches.
- No higher-level design note is required.
- No promotion or demotion action is required.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- safety floor remains intact by freeze/snapshot evidence and related tests.

Closeout metadata:

- slice id: KCS-14 Slice 6 aggregate review batches 7-8
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- aggregate review trigger: two completed refactor batches
- aggregate review outcome: continue node-by-node refactor
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none
- next aggregate review due: after two more refactor batches or an earlier
  methodology trigger

Final verdict: Aggregate review gate is complete. Slice 6 may continue with the
next scoped refactor batch after the normal context window check and process
gap audit.

## 2026-07-07 - Slice 6 Batch 9 Draft Call Shape

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-9-draft-call-shape.md`
- `src/kcs_adapters/desktop_draft_tool.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- primary draft-call route behavior unchanged;
- invalid call-shape failure behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across summary, ticket-ref,
  operator-selection, invalid mixed, empty, and unknown-argument cases.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_draft_tool.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py` passed.
- `git diff --check` passed.

Findings:

- Primary Desktop draft call-shape classification now has one private owner in
  `_DraftArticlePrimaryCallShape`.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Next aggregate design review is due after one more refactor batch or an
  earlier methodology trigger.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 9
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_draft_tool.py`
- batches since aggregate review: 1
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `DesktopDraftArticleTool.draft_article()` remains the entrypoint
- complexity distribution: not measured by a tool; repeated call-shape booleans
  moved into one private value object
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: one more batch before aggregate review, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 9 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Batch 10 Draft Tool Alias

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-10-draft-tool-alias.md`
- `src/kcs_adapters/desktop_draft_tool.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- operator-choice `submit_tool` and `next_tool` values unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new alias equivalence check passed.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_draft_tool.py tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py` passed.
- `git diff --check` passed.

Findings:

- Draft article Desktop alias usage now has one private owner in
  `_DRAFT_ARTICLE_DESKTOP_TOOL_ALIAS`.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Aggregate design review is now due before starting another refactor batch.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 10
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_draft_tool.py`
- batches since aggregate review: 2
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `DesktopDraftArticleTool.draft_article()` remains the entrypoint
- complexity distribution: not measured by a tool; repeated draft tool alias
  lookup moved into one private constant
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: aggregate review before next refactor batch

Final verdict: Slice 6 batch 10 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Aggregate Review After Batches 9-10

Reviewer or review route: local Codex aggregate design checkpoint.

Review artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-aggregate-review-batches-9-10.md`

Scope:

- Batch 9 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_draft_tool.py`
- Batch 10 `desktop_draft_workflow`:
  `src/kcs_adapters/desktop_draft_tool.py`

Aggregate findings:

- Both batches stayed inside the declared `desktop_draft_workflow` node plus
  graph and closeout metadata.
- Net file/module count change was 0.
- Public interface/export count change was 0.
- Caller-facing entrypoints stayed unchanged.
- Graph ownership definitions did not change.
- Freeze/snapshot false positives: none.
- Test assertion edits or justified exceptions: none.
- Review blockers: none.
- `must_not_own` near-misses: none.
- Promotion candidates: none.
- Demotion candidates: none.

Triage:

- `map_error`: no.
- `process_error`: no.
- `architecture_error`: no.

Outcome:

- Continue current node-by-node refactor.
- Architecture Patterns with Python is not activated by these batches.
- No higher-level design note is required.
- No promotion or demotion action is required.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- safety floor remains intact by freeze/snapshot evidence and related tests.

Closeout metadata:

- slice id: KCS-14 Slice 6 aggregate review batches 9-10
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- aggregate review trigger: two completed refactor batches
- aggregate review outcome: continue node-by-node refactor
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none
- next aggregate review due: after two more refactor batches or an earlier
  methodology trigger

Final verdict: Aggregate review gate is complete. Slice 6 may continue with the
next scoped refactor batch after the normal context window check and process
gap audit.

## 2026-07-07 - Slice 6 Batch 11 Semantic Review Pending Ref

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-11-semantic-review-pending-ref.md`
- `src/kcs_adapters/desktop_workflow.py`

Unchanged contracts:

- runtime behavior unchanged;
- public helper names and `__all__` unchanged;
- semantic-review packet schema unchanged;
- candidate semantic extraction schema unchanged;
- prepare/submit controlled error behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across valid prepare, invalid ref,
  invalid type, double prepare, submit before prepare, and expired prepare.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_workflow.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py` passed.
- `git diff --check` passed.

Findings:

- Pending semantic-review ref/type/expiry validation now has one private owner
  in `_pending_semantic_review_for_ref()`.
- Prepare one-shot and submit-ready rules remained at their original call
  sites.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Remaining `desktop_draft_workflow` files are untouched.
- Next aggregate design review is due after one more refactor batch or an
  earlier methodology trigger.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 11
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_workflow.py`
- batches since aggregate review: 1
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `DesktopDraftWorkflow` remains the workflow-state owner
- complexity distribution: not measured by a tool; repeated semantic-review
  ref validation moved into one private helper
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: one more batch before aggregate review, remaining
  `desktop_draft_workflow` files

Final verdict: Slice 6 batch 11 is ready for staged-diff review.

## 2026-07-07 - Slice 6 Batch 12 Platform Match Flags

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-12-platform-match-flags.md`
- `src/kcs_adapters/desktop_workflow.py`

Unchanged contracts:

- runtime behavior unchanged;
- minimal fallback environment output unchanged;
- semantic-review packet schema unchanged;
- candidate semantic extraction schema unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across Linux, Windows,
  both-platform, and no-platform text cases.
- `uv run pytest tests/kcs_adapters/test_desktop_draft_tool.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_mcp_desktop.py tests/policy/test_kcs14_freeze_snapshots.py -q` passed.
- `uv run ruff check src/kcs_adapters/desktop_workflow.py tests/kcs_adapters/test_desktop_workflow.py tests/kcs_adapters/test_desktop_draft_tool.py` passed.
- `git diff --check` passed.

Findings:

- Platform fallback match flags now have one private owner in
  `_platform_match_flags()`.
- No public helper, payload schema, workflow status, result-shaping, or Desktop
  protocol behavior changed.
- No graph ownership definitions changed; only the touched source hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Aggregate design review is now due before starting another refactor batch.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 12
- affected graph nodes: `desktop_draft_workflow`, `engineering_policy_tests`
- graph hashes updated: `src/kcs_adapters/desktop_workflow.py`
- batches since aggregate review: 2
- net module/file count change by node: `desktop_draft_workflow` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `DesktopDraftWorkflow` remains the workflow-state owner
- complexity distribution: not measured by a tool; inline platform match tuple
  moved into one private helper
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: aggregate review before next refactor batch

Final verdict: Slice 6 batch 12 is ready for staged-diff review.

## 2026-07-06 - Slice 6 Batch 3 Desktop UI Smoke Observations

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-3-desktop-ui-smoke-observations.md`
- `scripts/smoke_claude_desktop_ui_prompt.py`

Unchanged contracts:

- runtime behavior unchanged;
- UI smoke CLI arguments and exit codes unchanged;
- `_report_from_log()` report shape, check names, failure stages, attention,
  next steps, debug-code fields, and value-safe log-file metadata unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct old-vs-new equivalence check passed across seven representative
  synthetic log cases, confirming matching `_report_from_log()` dictionaries
  for old inline observation variables and new `_UiLogObservations` fields.
- Focused Claude Desktop UI prompt smoke tests passed.
- `uv run pytest tests/kcs_adapters/test_mcpb_package.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py tests/policy/test_tool_entrypoints.py -q` passed with two existing skips.
- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_review_context_policy.py tests/policy/test_functional_test_policy.py -q` passed.
- Ruff passed for `scripts/smoke_claude_desktop_ui_prompt.py` and related MCPB
  package tests.
- `git diff --check` passed.

Findings:

- UI smoke log-derived observations now have one private owner in
  `_UiLogObservations` and `_ui_log_observations()`.
- No report keys, check names, failure stages, CLI arguments, or exit codes
  changed.
- No graph ownership definitions changed; only the touched script hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- `scripts/smoke_kcs_mcpb_stdio.py` remains untouched.
- Next aggregate design review is due after one more refactor batch or an
  earlier methodology trigger.
- Result-shaping ownership decision still must be written before touching
  `desktop_draft_workflow` or `desktop_tool_surface` result-shaping files.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 3
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- graph hashes updated: `scripts/smoke_claude_desktop_ui_prompt.py`
- batches since aggregate review: 1
- net module/file count change by node: `smoke_log_tooling` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `_report_from_log()` remains the report-shaping entrypoint
- complexity distribution: not measured by a tool; log-derived observations
  moved into one private value object and builder function
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: remaining stdio smoke script, aggregate review after one
  more batch, result-shaping ownership gate

Final verdict: Slice 6 batch 3 is ready for staged-diff review.

## 2026-07-06 - Slice 6 Batch 4 Stdio Smoke Environment

Reviewer or review route: local Codex implementation checkpoint.

Changed files:

- `docs/internal/engineering-process/code-review-graph.json`
- `docs/internal/engineering-process/kcs-14-refactor-log.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-batch-4-stdio-smoke-environment.md`
- `scripts/smoke_kcs_mcpb_stdio.py`

Unchanged contracts:

- runtime behavior unchanged;
- stdio smoke CLI arguments and exit codes unchanged;
- `run_smoke()` report shape, check names, debug-code fields, wrapper kind,
  registry-cache metadata, and value-safe error codes unchanged;
- JSON-RPC request order and smoke scenarios unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- local reviewer-bundle behavior unchanged;
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  remain out of scope.

Validation evidence:

- Direct env-construction equivalence check passed for fixture-provider and
  inherited-provider paths under controlled `os.environ` values.
- Focused MCPB stdio smoke tests passed.
- `uv run pytest tests/kcs_adapters/test_mcpb_package.py tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py tests/policy/test_tool_entrypoints.py -q` passed with two existing skips.
- `uv run pytest tests/policy/test_kcs14_docs_policy.py tests/policy/test_review_context_policy.py tests/policy/test_functional_test_policy.py -q` passed.
- Ruff passed for `scripts/smoke_kcs_mcpb_stdio.py` and related MCPB package
  tests.
- `git diff --check` passed.

Findings:

- Wrapper process environment construction now has one private owner in
  `_wrapper_env()`.
- No JSON-RPC requests, report keys, check names, CLI arguments, or error codes
  changed.
- No graph ownership definitions changed; only the touched script hash changed.

Promotion candidates:

- none new. No repeated, stable, or mechanically checkable review finding was
  introduced by this batch.

Deferred risks:

- Aggregate design review is now due before starting another refactor batch.
- Result-shaping ownership decision still must be written before touching
  `desktop_draft_workflow` or `desktop_tool_surface` result-shaping files.

Closeout metadata:

- slice id: KCS-14 Slice 6 batch 4
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- graph hashes updated: `scripts/smoke_kcs_mcpb_stdio.py`
- batches since aggregate review: 2
- net module/file count change by node: `smoke_log_tooling` 0
- public interface/export count change: 0
- files a caller must read to use node: unchanged for public API;
  `run_smoke()` remains the report entrypoint
- complexity distribution: not measured by a tool; repeated wrapper env setup
  moved into one private helper
- review blockers by stable code: none
- `must_not_own` near-misses caught in review: none
- promotion candidates by node: none
- graph ownership edits by node: none
- freeze/snapshot false positives: none
- test assertion edits or justified exceptions by node: none
- review route: local Codex checkpoint
- validation result: passed
- retry count bucket: 0-1
- recurring blocker codes: none
- review blocker count: 0
- deterministic checks added: none
- findings promoted to future checks: none
- deferred risks: aggregate review before next batch, result-shaping ownership
  gate

Final verdict: Slice 6 batch 4 is ready for staged-diff review.

## 2026-07-06 - Slice 6 Aggregate Review After Batches 3-4

Reviewer or review route: local Codex aggregate design checkpoint.

Review artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-6-aggregate-review-batches-3-4.md`

Scope:

- Batch 3 `smoke_log_tooling`:
  `scripts/smoke_claude_desktop_ui_prompt.py`
- Batch 4 `smoke_log_tooling`: `scripts/smoke_kcs_mcpb_stdio.py`

Aggregate findings:

- Both batches stayed inside the declared `smoke_log_tooling` node plus graph
  and closeout metadata.
- Net file/module count change was 0.
- Public interface/export count change was 0.
- Caller-facing entrypoints stayed unchanged.
- Graph ownership definitions did not change.
- Freeze/snapshot false positives: none.
- Test assertion edits or justified exceptions: none.
- Review blockers: none.
- `must_not_own` near-misses: none.
- Promotion candidates: none.
- Demotion candidates: none.

Triage:

- `map_error`: no.
- `process_error`: no.
- `architecture_error`: no.

Outcome:

- Continue current node-by-node refactor.
- Architecture Patterns with Python is not activated by these batches.
- No higher-level design note is required.
- No promotion or demotion action is required.

Unchanged contracts:

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schema behavior unchanged;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle/publication/customer-reply boundaries unchanged;
- safety floor remains intact by freeze/snapshot evidence and related tests.

Closeout metadata:

- slice id: KCS-14 Slice 6 aggregate review batches 3-4
- affected graph nodes: `smoke_log_tooling`, `engineering_policy_tests`
- aggregate review trigger: two completed refactor batches
- aggregate review outcome: continue node-by-node refactor
- architecture decision: no `architecture_error`; no Architecture Patterns
  activation
- promotion candidates by node: none
- demotion candidates by node: none
- recurring blocker codes: none
- next aggregate review due: after two more refactor batches or an earlier
  methodology trigger

Final verdict: Aggregate review gate is complete. Slice 6 may continue with the
next scoped refactor batch after the normal context window check and process
gap audit.
