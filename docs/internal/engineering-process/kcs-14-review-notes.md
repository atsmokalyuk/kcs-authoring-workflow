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
