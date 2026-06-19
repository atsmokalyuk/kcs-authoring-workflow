# KCS Desktop Authoring Review Checkpoint - KCS-12b - 2026-06-19

## PR Intent

Review `KCS-12b: Local reviewer bundle boundary` against
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

This checkpoint is focused on local reviewer bundle output only. `KCS-12a` is
already complete and approved to move forward.

Target behavior:

- reviewer bundle writing is owned by `kcs_adapters.desktop_reviewer_bundle`;
- bundle writes are constrained to `local-data/reviewer-bundles/`;
- Claude-visible output returns compact refs, relative paths, status flags, and
  hashes;
- default output excludes full `reviewer_only_html`;
- full `reviewer_only_html` is debug/smoke compatibility only;
- no absolute paths, raw packet bodies, public-publish flags, or hidden Zendesk
  writes appear in default output.

## Review Status

Status: approved to move past `KCS-12b`.

External ChatGPT Pro review on 2026-06-19 found no P0/P1 blockers for the
local reviewer bundle boundary. `KCS-12b` is complete.

The next implementation slice may start from
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

## External Review Verdict

Verdict: approved to move past `KCS-12b`.

No blocking fixes are required before starting the next planned slice. The
review confirmed that bundle writing is owned by
`kcs_adapters.desktop_reviewer_bundle`, writes are constrained to
`local-data/reviewer-bundles`, default Desktop output is compact
refs/paths/hashes/status, and full `reviewer_only_html` remains debug/smoke
only.

Deferred findings from the review:

- defensively strip `reviewer_only_html` and `zendesk_source_html` from
  non-ready results in `finalize_author_result_with_bundle(...)` in a future
  hardening slice;
- keep the current suffix-based reviewer bundle root guard for `KCS-12b`; a
  future multi-workspace implementation may use a workspace-root-aware guard;
- continue shrinking `kcs_adapters.mcp_desktop`;
- keep exact Desktop schema parsing in the log checker deferred;
- clarify semantic provider status fields in `KCS-12c`;
- keep future local RAG strictly as a Search/reuse adapter after accepted
  evidence.

## Review Focus

Please review for:

- local write boundary enforcement;
- relative refs/paths/hashes only in default output;
- no full packets or full HTML by default;
- no absolute local paths in Claude-visible output;
- no hidden Zendesk write, publication, or public-output approval behavior;
- no unsafe interaction between bundle output and missing reuse search;
- test coverage gaps around bundle write success/failure and blocked outputs.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

## Changed Files For Review

Primary implementation files:

- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_adapters/zendesk_markup_quality.py`

Tests:

- `tests/kcs_adapters/test_desktop_workflow.py`
- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/kcs_adapters/test_mcpb_package.py`

Packaging and smoke evidence:

- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/manifest.json`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/README.md`
- `scripts/smoke_kcs_mcpb_stdio.py`
- `scripts/check_claude_kcs_desktop_log.py`

Docs:

- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-2026-06-19.md`

## Current Architecture State

`kcs_adapters.desktop_reviewer_bundle` owns local bundle file writing:

- `DEFAULT_REVIEWER_BUNDLE_ROOT = local-data/reviewer-bundles`;
- `write_desktop_reviewer_bundle(...)` writes `reviewer_only.html` and
  `manifest.json`;
- `_require_reviewer_bundle_root(...)` rejects roots that do not end with
  `local-data/reviewer-bundles`;
- returned manifest fields are compact and relative:
  - `bundle_ref`;
  - `manifest_path`;
  - `html_path`;
  - `html_sha256`;
  - status and policy flags.

`kcs_adapters.desktop_workflow` owns final Desktop result shaping:

- `finalize_author_result_with_bundle(...)` writes the bundle only when
  `reviewer_only_html` exists and the draft is not blocked;
- `compact_draft_result(...)` includes refs, paths, hashes, status flags, and
  policy flags;
- `reviewer_only_html` is included only when
  `include_reviewer_only_html=true`, which the Desktop adapter maps to
  `debug=true`;
- reuse-missing output is downgraded to `draft_only` with
  `kcs_ready=false`, `ready_for_reviewer=false`, and
  `debug_code=draft_only_reuse_search_missing`.

`kcs_adapters.mcp_desktop` still owns the MCP result envelope and chooses
whether debug output may include full `reviewer_only_html`.

## Boundary Evidence

The implementation currently enforces:

- local writes only under roots ending in `local-data/reviewer-bundles`;
- relative `html_path` and `manifest_path` beginning with
  `local-data/reviewer-bundles/`;
- `html_sha256` in compact output;
- `auto_publish_allowed=false`;
- `public_output_approved=false`;
- `writes_files=true` only for successful local reviewer bundle output;
- no default `reviewer_only_html` in non-debug Desktop results;
- no bundle write for blocked/invalid outputs.

## Validation Evidence

Last full validation before this checkpoint:

```text
uv run pytest -q
865 passed, 2 skipped

uv run ruff check src scripts tests
All checks passed

git diff --check
passed

uv run python scripts/smoke_kcs_mcpb_stdio.py
ok=true, wrapper_kind=installed, registry_cache_checked=true

uv run python scripts/smoke_kcs_mcpb_stdio.py --wrapper packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js
ok=true, wrapper_kind=custom

uv run python scripts/check_claude_kcs_desktop_log.py
ok=true
```

Focused validation for this checkpoint should include:

```text
uv run pytest tests/kcs_adapters/test_desktop_workflow.py \
  tests/kcs_adapters/test_mcp_desktop.py \
  tests/kcs_adapters/test_mcpb_package.py -q
189 passed, 2 skipped

uv run ruff check src/kcs_adapters/desktop_reviewer_bundle.py \
  src/kcs_adapters/desktop_workflow.py \
  src/kcs_adapters/mcp_desktop.py \
  tests/kcs_adapters/test_desktop_workflow.py \
  tests/kcs_adapters/test_mcp_desktop.py \
  tests/kcs_adapters/test_mcpb_package.py
All checks passed

git diff --check
passed
```

## Known Deferred Items

- Add defensive stripping of `reviewer_only_html` and `zendesk_source_html` for
  non-ready Desktop finalizer results.
- Continue shrinking `kcs_adapters.mcp_desktop`; this checkpoint only reviews
  the local bundle/output boundary.
- Full `reviewer_only_html` remains debug/smoke compatibility only.
- Native choice popup rendering remains client-dependent; deterministic
  fallback remains `operator_choice_request.options[*].submit_arguments`.
- Provider-call status fields are deferred to `KCS-12c`.
- Future local RAG must be added only as a Search/reuse adapter after accepted
  `NormalizedTicketEvidencePacket`.

## Suggested Review Prompt

```text
Review KCS-12b against the KCS Desktop Authoring Refactor Plan.

Focus on:
- local reviewer bundle write boundary;
- relative refs/paths/hashes only;
- no absolute paths;
- no full packets or full HTML by default;
- no hidden publish/Zendesk write behavior;
- no unsafe write behavior for blocked outputs;
- test coverage gaps.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

Return findings ordered by severity P0/P1/P2/P3, with file/line, why it
matters, suggested fix, and whether it blocks KCS-12b completion.
```
