# KCS Desktop Authoring Review Checkpoint - KCS-12d - 2026-06-19

## PR Intent

Review `KCS-12d: Desktop smoke/install alignment` against
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

This checkpoint is focused on Desktop packaging, installed-wrapper smoke,
source-wrapper smoke, registry/cache checks, wrapper environment boundaries, and
GUI-log contract checks. `KCS-12a`, `KCS-12b`, and `KCS-12c` are complete and
approved to move forward.

Target behavior:

- installed MCPB and source wrapper expose the same thin
  `kcs_draft_article` contract;
- stdio smoke uses the fixture provider explicitly and only for deterministic
  smoke/test behavior;
- installed-wrapper smoke checks Claude registry/cache consistency;
- source-wrapper smoke skips installed registry/cache checks;
- GUI-log checker verifies the Desktop-visible thin schema and tool
  annotations;
- manifest wording matches the tool-owned Desktop workflow and does not promise
  native choice popups as guaranteed behavior;
- wrapper forwards only bounded, explicit environment fields and starts the
  repo-local server through `uv`;
- no broad Desktop schema, old item/item_candidates payloads, manual fallback,
  timeout/disconnect, or hidden publish/write contract is accepted as passing.

## Review Status

Status: ready for external ChatGPT Pro review.

`KCS-12d` implementation evidence is prepared, but `KCS-12d` is not complete
until external review is done and findings are fixed or recorded as explicit
deferrals.

## Review Focus

Please review for:

- manifest/schema wording alignment with the thin Desktop tool contract;
- MCP annotations for non-read-only, non-idempotent, non-destructive local
  reviewer bundle writes;
- installed-wrapper registry/cache validation;
- source-wrapper behavior and fixture-provider smoke setup;
- Node wrapper environment forwarding and repo-root validation;
- GUI-log checker coverage for old schema fields, annotations, and client
  capabilities;
- old native-popup-guaranteed wording not reappearing;
- no absolute paths, raw provider payloads, or hidden public-publish behavior in
  Desktop-visible contract;
- test coverage gaps around installed/source wrapper smoke, cache mismatch,
  stale popup wording, and log-check behavior.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

## Changed Files For Review

Primary packaging and smoke files:

- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/manifest.json`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/README.md`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
- `scripts/smoke_kcs_mcpb_stdio.py`
- `scripts/check_claude_kcs_desktop_log.py`
- `scripts/smoke_claude_desktop_ui_prompt.py`
- `scripts/install_kcs_mcpb.py`

Implementation context:

- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/desktop_reviewer_bundle.py`

Tests:

- `tests/kcs_adapters/test_mcpb_package.py`
- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/kcs_adapters/test_desktop_workflow.py`

Docs:

- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12b-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12c-2026-06-19.md`

## Current Architecture State

The MCPB manifest exposes one primary Desktop tool:

- `kcs_draft_article`;
- no generated prompts or tools;
- wording instructs Claude Desktop to pass only `approved_summary_text` or
  selected refs;
- wording states Python owns semantic extraction, workflow state, validation,
  decisions, rendering, local reviewer bundle output, and output safety;
- wording states native choice popup is preferred only when the client provides
  one, with deterministic fallback through
  `operator_choice_request.options[*].submit_arguments`;
- wording forbids raw Zendesk payloads, internal notes, attachments, Zendesk
  writes, Help Center publication, Claude Desktop-owned provider calls, raw
  provider payloads, and arbitrary file-writing tools.

The Node wrapper:

- validates `KCS_AUTHORING_MVP_REPO_ROOT`;
- rejects `KCS_AUTHORING_MVP_UV_COMMAND` values containing whitespace,
  arguments, newlines, tabs, or NUL;
- verifies the repo root contains the expected `pyproject.toml` and
  `src/kcs_adapters/mcp_desktop.py`;
- starts `uv --project <repo> run kcs-desktop-mcp --tool-name-style
  claude_desktop_aliases`;
- forwards only selected environment fields, including explicit semantic
  provider env fields, into the child process;
- preserves stdout line ordering for JSON-RPC responses.

The stdio smoke:

- explicitly sets `KCS_AUTHORING_SEMANTIC_PROVIDER=fixture`;
- initializes the wrapper, reads `tools/list`, validates the thin tool surface,
  validates controlled failure statuses, validates split-choice and selected
  continuation flow, validates non-debug output excludes full HTML, and
  validates installed registry/cache when using the installed wrapper;
- reports `registry_cache_checked=true` for installed wrapper and skips that
  check for source/custom wrapper.

The Desktop log checker:

- reads only the active KCS Authoring Claude Desktop log tail;
- finds the latest `tools/list` and `initialize` entries;
- checks `readOnlyHint=false`, `idempotentHint=false`, thin arguments visible,
  and old `item`, `item_candidates`, and `reference_article_html` absent;
- reports client capability hints such as MCP UI extension and elicitation
  declaration.

## Boundary Evidence

The implementation currently enforces:

- Desktop-visible schema remains thin in MCPB and Desktop log checks;
- installed wrapper registry/cache mismatch is detected by tests;
- old native-popup-guaranteed wording is rejected by registry/cache tests;
- source wrapper smoke does not require installed registry/cache;
- fixture provider use is explicit in stdio smoke env;
- non-debug smoke verifies full `reviewer_only_html` is not returned;
- GUI-log smoke verifies tool annotations and old schema field absence;
- wrapper env forwarding remains bounded and does not expose inline endpoint
  URLs, credentials, raw provider payloads, or arbitrary command arguments.

## Validation Evidence

Focused validation for this checkpoint:

```text
uv run pytest tests/kcs_adapters/test_mcpb_package.py \
  tests/kcs_adapters/test_mcp_desktop.py -q
174 passed, 2 skipped

uv run ruff check scripts/smoke_kcs_mcpb_stdio.py \
  scripts/check_claude_kcs_desktop_log.py \
  tests/kcs_adapters/test_mcpb_package.py \
  tests/kcs_adapters/test_mcp_desktop.py
All checks passed

/Users/alex.tsmokalyuk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  --check packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js
passed

git diff --check
passed

uv run python scripts/smoke_kcs_mcpb_stdio.py
ok=true, wrapper_kind=installed, registry_cache_checked=true

uv run python scripts/smoke_kcs_mcpb_stdio.py --wrapper packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js
ok=true, wrapper_kind=custom

uv run python scripts/check_claude_kcs_desktop_log.py
ok=true
```

One invalid validation command was attempted and superseded:

```text
uv run ruff check packaging/claude-desktop/.../server/index.js ...
failed because Ruff parsed the JavaScript wrapper as Python.
Superseded by Node syntax check above.
```

## Known Deferred Items

- Strengthen `scripts/check_claude_kcs_desktop_log.py` later to parse the latest
  `tools/list` JSON and assert the exact Desktop schema property set.
- GUI submit remains manual when macOS automation is unavailable, rate-limited,
  or not needed for the current checkpoint.
- Continue shrinking `kcs_adapters.mcp_desktop`; this checkpoint only reviews
  smoke/install alignment.
- Carry forward KCS-12c deferred semantic-provider status fields and
  provider-context pre-validation.
- Future local RAG must be added only as a Search/reuse adapter after accepted
  `NormalizedTicketEvidencePacket`.

## Suggested Review Prompt

```text
Review KCS-12d against the KCS Desktop Authoring Refactor Plan.

Focus on:
- manifest/schema wording and MCP annotations;
- installed-wrapper registry/cache validation;
- source-wrapper smoke behavior;
- explicit fixture-provider smoke setup;
- Node wrapper env forwarding and repo-root validation;
- GUI-log checker coverage;
- old native-popup-guaranteed wording not reappearing;
- no broad Desktop schema, manual fallback, hidden publish behavior, or raw
  provider payload exposure;
- test coverage gaps.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

Return findings ordered by severity P0/P1/P2/P3, with file/line, why it
matters, suggested fix, and whether it blocks KCS-12d completion.
```
