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
- deferred risks: tool entrypoints, code map, review packet format, refactor
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
- Slice 5 still needs the minimal code map before codebase refactor work.

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
- deferred risks: functional test templates, review packet format, code map

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
- Slice 5 still needs the minimal code map before codebase refactor work.
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
- deferred risks: review packet format, code map, refactor test inventory

Final verdict: Slice 3 implementation checkpoint is ready for external review.
