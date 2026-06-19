# KCS Desktop Authoring Review Checkpoint - 2026-06-19

## PR Intent

Review the current Tool-Owned KCS Desktop Authoring Workflow slice against
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

This checkpoint covers the implemented parts of:

- `KCS-12a: Desktop schema diet + workflow service`;
- `KCS-12b: Local reviewer bundle boundary`;
- `KCS-12c: Semantic provider boundary`;
- `KCS-12d: Desktop smoke/install alignment`.

The target behavior is:

- Claude Desktop sees one thin primary tool: `kcs_draft_article`;
- Desktop-visible input schema contains only:
  - `approved_summary_text`;
  - `operator_selection_ref`;
  - `operator_selected_item_ref`;
  - `debug`;
- Python owns semantic provider calls, workflow state, validation, decisions,
  rendering, local reviewer bundles, and output boundary;
- no production local regex semantic extractor;
- no manual/freehand fallback;
- default output is compact status plus local refs/hashes, not full HTML.

## Review Status

Status: approved to move past `KCS-12a`.

Final ChatGPT Pro follow-up review found no remaining P0/P1 blockers. The
original blocking issue is fixed: Desktop `kcs_draft_article` now routes only
through the thin Desktop call shapes, and non-thin hidden runtime arguments
return controlled `draft_article_call_shape_invalid` results instead of
entering the old broad fallback pipeline.

`KCS-12a` is complete. The next implementation slice may start with the
deferred items below carried forward.

## Review Focus

Please review for:

- scope drift against the KCS Authoring MVP design;
- privacy/safety boundary;
- Claude/provider ownership;
- Python validation/decision ownership;
- MCP Desktop schema thinness;
- no full packets/HTML by default;
- no hidden publish/write behavior;
- test coverage gaps.

Do not bikeshed style unless it affects maintainability or contract clarity.

## Changed Files For Review

Primary implementation files:

- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/desktop_payload.py`
- `src/kcs_adapters/desktop_ticket_ref.py`
- `src/kcs_adapters/desktop_reviewer_bundle.py`
- `src/kcs_adapters/smoke_accounting.py`
- `src/kcs_adapters/zendesk_markup_quality.py`
- `src/kcs_core/semantic_extraction.py`
- `src/kcs_core/renderer.py`
- `src/kcs_core/safety.py`
- `src/kcs_core/sanitizer.py`

Desktop packaging, smoke, and contract files:

- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/manifest.json`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/README.md`
- `packaging/cowork/kcs-authoring/skills/kcs-authoring-control/SKILL.md`
- `packaging/cowork/kcs-authoring/skills/kcs-authoring-control/references/tool-surface.md`
- `scripts/smoke_kcs_mcpb_stdio.py`
- `scripts/check_claude_kcs_desktop_log.py`
- `scripts/install_kcs_mcpb.py`
- `scripts/smoke_claude_desktop_ui_prompt.py`

Tests:

- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/kcs_adapters/test_mcpb_package.py`
- `tests/kcs_adapters/test_desktop_workflow.py`
- `tests/kcs_adapters/test_desktop_payload.py`
- `tests/kcs_adapters/test_desktop_ticket_ref.py`
- `tests/kcs_adapters/test_smoke_accounting.py`
- `tests/kcs_core/test_semantic_extraction.py`
- `tests/kcs_core/test_safety.py`

Docs:

- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/kcs-core-pipeline-architecture-and-contracts.md`
- `docs/internal/kcs-core-pipeline-technical-design.md`
- `docs/internal/kcs-core-pipeline-review-notes.md`
- `README.md`

Other:

- `pyproject.toml`
- `src/kcs_adapters/__init__.py`

## Current Architecture State

`kcs_adapters.mcp_desktop` still owns MCP lifecycle, JSON-RPC transport, tool
descriptors, tool dispatch, and Desktop result wrapping.

Moved out of `mcp_desktop.py`:

- Desktop workflow state and pending operator selection:
  `kcs_adapters.desktop_workflow`;
- approved-summary pipeline sequencing through typed adapter hooks:
  `kcs_adapters.desktop_workflow`;
- split-required / selection-error result shaping:
  `kcs_adapters.desktop_workflow`;
- compact draft result shaping, draft-only reuse-missing status, quality-block
  handling, and final bundle result:
  `kcs_adapters.desktop_workflow`;
- approved-summary reviewer draft/HTML/preview shaping and quality gaps:
  `kcs_adapters.desktop_workflow`;
- approved-summary payload normalization and compatibility aliases:
  `kcs_adapters.desktop_payload`;
- repo-local approved ticket summary safe-ref loading:
  `kcs_adapters.desktop_ticket_ref`;
- local reviewer bundle file writing:
  `kcs_adapters.desktop_reviewer_bundle`.

## Desktop Contract Evidence

Current Desktop-visible schema is expected to expose only:

- `approved_summary_text`;
- `operator_selection_ref`;
- `operator_selected_item_ref`;
- `debug`.

The log checker currently verifies:

- old `item` schema absent;
- old `item_candidates` schema absent;
- old `reference_article_html` schema absent;
- thin argument visible;
- annotations are non-read-only and non-idempotent.

## Validation Evidence

Last local validation run:

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

Manual Claude Desktop GUI-submit smoke was not repeated in this checkpoint.
The current automated evidence covers stdio behavior, installed wrapper/cache
alignment, and Desktop log-visible schema.

## Review Findings Resolution

External review initially returned a blocking verdict for `KCS-12a` because
`kcs_draft_article` still accepted hidden broad runtime arguments even though
the visible Desktop schema was thin.

Resolved in this checkpoint:

- P1 fixed: `kcs_draft_article` runtime now accepts only the thin Desktop call
  shapes:
  - `approved_summary_text`, optional `debug`;
  - `operator_selection_ref` plus `operator_selected_item_ref`, optional
    `debug`.
- P1 fixed: hidden/broad arguments such as `item`, `item_candidates`,
  `ticket_ref`, `reference_article_html`, top-level article fields, reuse
  fields, and operator-choice compatibility flags now return controlled
  `draft_article_call_shape_invalid` results from the primary Desktop tool.
- P1 test contract updated: provider-driven split/selection remains covered;
  hidden `item_candidates` and `ticket_ref` calls are explicit negative tests.
- P2 fixed: MCPB manifest wording now distinguishes forbidden
  Claude Desktop-owned/raw provider calls from explicitly configured
  Python-owned approved semantic provider calls over bounded sanitized context.
- P2 fixed: local reviewer bundle writing now enforces the
  `local-data/reviewer-bundles` path boundary inside
  `kcs_adapters.desktop_reviewer_bundle`.
- Final follow-up review verdict: approved to move past `KCS-12a`; no P0/P1
  findings remain.

## Known Deferred Items

- Keep remaining MCP transport glue narrow in `kcs_adapters.mcp_desktop`.
- Do not add a production semantic extractor until an approved provider/runtime
  is configured.
- Continue shrinking `kcs_adapters.mcp_desktop`; it is improved but still
  broader than the final target.
- Clarify compact provider-call status fields before real approved provider
  rollout, for example value-safe `semantic_provider_mode`,
  `semantic_provider_called`, and `provider_call_owner=python`.
- Keep fixture provider smoke/test-only; later consider requiring a second
  explicit fixture-smoke env guard.
- Strengthen the Desktop log checker later to assert the exact tool schema
  property set, not only the current absence/presence checks.
- Future local RAG must be added only as a Search / reuse adapter between
  accepted `NormalizedTicketEvidencePacket` and `ReuseSearchResultsPacket`.
  It must not read raw tickets, call Claude, decide create/update/reuse,
  return full article bodies/snippets in Desktop output, perform Zendesk writes,
  or mark a draft KCS-ready unless `searched=true`.
- Do not expand Desktop-visible schema to include `item`, `item_candidates`,
  reference article bodies, provider internals, or broad aliases.
- Full `reviewer_only_html` remains debug/smoke compatibility only.
- Native choice popup rendering remains client-dependent; deterministic
  fallback is `operator_choice_request.options[*].submit_arguments`.
- Before further broad compatibility cleanup, use this checkpoint for external
  architecture/code review.

## Suggested Review Prompt

```text
Review this slice against the KCS Authoring MVP design.

Focus on:
- scope drift
- privacy/safety boundary
- Claude/provider ownership
- Python validation/decision ownership
- MCP Desktop schema thinness
- no full packets/HTML by default
- no hidden publish/write behavior
- test coverage gaps

Do not bikeshed style unless it affects maintainability or contract clarity.
```
