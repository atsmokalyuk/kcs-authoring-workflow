# KCS-13d Review Checkpoint: MCPB, Smoke, and Desktop Contract Alignment

Date: 2026-06-20

## Verdict

Approved to commit locally and complete KCS-13.

Two `gpt-5.3-codex-spark` review passes covered this checkpoint. The first
pass found hardening issues in the Desktop log checker and stdio smoke
annotation checks. The follow-up pass approved the corrected log checker and
smoke changes. A final focused review also approved the increased semantic
review packet budget.

## Implemented Scope

- Rebuilt and reinstalled the MCPB package.
- Source-wrapper and installed-wrapper stdio smoke cover the full five-tool
  Desktop surface:
  - `kcs_register_clean_ticket`;
  - `kcs_draft_article`;
  - `kcs_prepare_semantic_review`;
  - `kcs_submit_semantic_review`;
  - `support_get_behavior_instructions`.
- Stdio smoke now validates the full annotation intent, including
  `openWorldHint=false`.
- Claude Desktop log checker now parses exact tool JSON when the tools/list log
  line is complete.
- For truncated Claude Desktop tool-surface logs, the log checker uses an
  explicit degraded check:
  - old broad schema fragments are absent in the visible log line;
  - a truncated tool-surface line is observed;
  - closed-world non-destructive non-idempotent annotations are visible.
- Truncated GUI-log mode does not claim exact schema or exact tool-name
  validation. Exact schema validation remains covered by source and installed
  stdio smoke.
- Semantic-review packet budget was raised for larger noisy tickets:
  - max 12 selected excerpts;
  - max 12,000 UTF-8 bytes per excerpt;
  - max 144,000 total selected-excerpt bytes;
  - max 256 KB generic MCP tool-result size.

The KCS-13d packet-budget values supersede older KCS-13b/KCS-13c checkpoint
values. The older dated checkpoint files remain historical records of the
limits at those review points.

## Preserved Boundaries

- Forbidden key/value fragments in MCP tool results remain enforced.
- Semantic-review packet keys remain compact and safe, including
  `selected_excerpts`; no `raw_ticket`, `local_path`, raw Zendesk payload,
  redaction map, reviewer packet, Zendesk HTML, or article draft is returned by
  the prepare packet.
- `kcs_draft_article` remains thin and does not accept semantic-review submit
  payloads.
- `kcs_submit_semantic_review` remains the only submit path for
  `candidate_semantic_extraction_v1`.
- Claude Desktop may propose semantic item identification only. Python still
  validates, decides, renders, writes reviewer bundles, and controls readiness.
- Full reviewer HTML remains excluded from default Desktop output.

## Review Findings Fixed

- Removed fake exact-schema success from truncated Desktop log checks.
- Removed a fragile support-helper anchor from truncated tool-surface log
  detection.
- Added `openWorldHint=false` checks to stdio smoke for all Desktop tools.
- Fixed synthetic test fixtures so read-only and mutating annotations match the
  active Desktop contract.
- Raised the semantic-review result cap without changing forbidden-key checks
  or allowing full-ticket packet output.

## Validation Evidence

- Focused semantic-review/tool-result pytest:
  `uv run pytest tests/kcs_adapters/test_mcp_desktop.py -k 'semantic_review or tool_result' -q`
  passed: 39 passed, 121 deselected.
- Focused MCPB/stdio pytest:
  `uv run pytest tests/kcs_adapters/test_mcpb_package.py tests/kcs_adapters/test_desktop_stdio_transport.py -q`
  passed: 49 passed, 2 skipped.
- Full pytest:
  `uv run pytest -q`
  passed: 982 passed, 2 skipped.
- Ruff:
  `uv run ruff check src scripts tests`
  passed.
- Source-wrapper stdio smoke:
  `uv run python scripts/smoke_kcs_mcpb_stdio.py --wrapper packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
  passed with `tool_count=5`, `semantic_review_submit_ok=true`, and
  `semantic_review_invalid_submit_ok=true`.
- Installed-wrapper stdio smoke:
  `uv run python scripts/smoke_kcs_mcpb_stdio.py`
  passed with `tool_count=5`, `registry_cache_checked=true`,
  `semantic_review_submit_ok=true`, and
  `semantic_review_invalid_submit_ok=true`.
- Claude Desktop log check:
  `uv run python scripts/check_claude_kcs_desktop_log.py`
  passed in truncated-log degraded mode.
- Whitespace:
  `git diff --check`
  passed.

## Deferred Items

- Manual GUI smoke remains operator-run when needed because Claude Desktop
  limits and macOS automation permissions make it unreliable as a hard local
  gate.
- Future GUI-log hardening can report degraded mode explicitly in a richer
  machine-readable field if needed.
- Local RAG reuse search remains deferred and must enter only as a Search/reuse
  adapter after accepted evidence.
