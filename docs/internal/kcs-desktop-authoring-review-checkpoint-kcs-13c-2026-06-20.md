# KCS-13c Review Checkpoint: Semantic Review Submit

Date: 2026-06-20

## Verdict

Approved to commit locally and move to KCS-13d.

Three `gpt-5.3-codex-spark` review passes were run for this checkpoint. The
first pass found submit-boundary gaps around `max_candidates`, local path
payloads, HTML/article payload detection, and total submit payload size. The
second pass confirmed those fixes but found a remaining local-path gap for
single-segment absolute Unix paths such as `/tmp`. The final pass approved the
slice after that gap was fixed and covered by regression tests.

## Implemented Scope

- Added Desktop-visible `kcs_submit_semantic_review`.
- Submit accepts only:
  - `semantic_review_ref`;
  - strict `candidate_semantic_extraction_v1`.
- Submit rejects broad Desktop-owned authoring payloads:
  - `item`;
  - `item_candidates`;
  - `recommended_action`;
  - article drafts;
  - Markdown/HTML article bodies;
  - reviewer HTML;
  - local paths;
  - publication flags.
- Submit validates:
  - live prepared `semantic_review_ref`;
  - `case_ref` match;
  - top-level and per-item `source_refs` grounded in prepared
    `selected_excerpts`;
  - max candidate count;
  - per-string and total submit payload caps;
  - existing `CandidateSemanticExtraction` schema and enum contract.
- Valid single-candidate submit continues through the existing draft pipeline.
- Valid multi-candidate submit continues through the existing split-required
  operator-selection pipeline.
- Invalid submit returns a controlled `semantic_review_submit_blocked` result
  with no bundle, no draft, and `manual_draft_allowed=false`.
- Semantic-review packet caps were raised for noisy tickets while staying
  bounded:
  - max 12 selected excerpts;
  - max 12,000 UTF-8 bytes per excerpt;
  - max 96,000 total selected-excerpt bytes;
  - max 192 KB generic MCP tool-result size.
- Stdio smoke now covers:
  - semantic review required;
  - prepare packet;
  - valid submit continuing to draft;
  - invalid submit blocked without manual fallback.

## Preserved Boundaries

- `kcs_draft_article` remains thin and does not accept semantic-review
  extraction payloads.
- Claude Desktop proposes only semantic item identification through
  `kcs_submit_semantic_review`; Python still validates, decides, renders, and
  writes reviewer bundles.
- No full ticket, raw Zendesk JSON, redaction map, reviewer packet, Zendesk
  HTML, local absolute path, article draft, KCS decision, publication flag, or
  provider payload is accepted as a submit payload.
- Default successful draft output remains compact and excludes full
  `reviewer_only_html`.
- Missing reuse search still produces `draft_only`, not KCS-ready output.

## Review Findings Fixed

- Enforced `SEMANTIC_REVIEW_MAX_CANDIDATES` on submit.
- Added total submit payload cap in addition to per-string cap.
- Broadened article/HTML/Markdown detection for submit strings.
- Rejected local path keys and local/absolute path values, including:
  - `file://`;
  - `~/...`;
  - Windows drive paths;
  - UNC paths;
  - absolute Unix paths such as `/tmp`, `/etc/...`, and `/usr/...`.
- Added regression coverage for unknown source refs, too many candidates,
  local paths, single-segment absolute Unix paths, HTML article tags, oversized
  payloads, broad `item` payloads, and article-draft content.

## Validation Evidence

- Focused pytest:
  `uv run pytest tests/kcs_adapters/test_mcp_desktop.py tests/kcs_adapters/test_mcpb_package.py tests/kcs_adapters/test_desktop_stdio_transport.py tests/kcs_adapters/test_cowork_plugin_package.py -q`
  passed: 212 passed, 2 skipped.
- Full pytest:
  `uv run pytest -q`
  passed: 979 passed, 2 skipped.
- Ruff:
  `uv run ruff check src scripts tests`
  passed.
- Source-wrapper stdio smoke:
  `uv run python scripts/smoke_kcs_mcpb_stdio.py --wrapper packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
  passed with `semantic_review_submit_ok=true` and
  `semantic_review_invalid_submit_ok=true`.
- Whitespace:
  `git diff --check`
  passed.

## Deferred To KCS-13d

- Rebuild/reinstall MCPB package and verify installed-wrapper smoke.
- Update any remaining Desktop log checker expectations for the fifth operator
  tool.
- Run GUI-observable Claude Desktop smoke after reinstall/reload.
- Keep full reviewer HTML debug/smoke-only.
- Continue carrying local RAG reuse search as a future Search/reuse adapter
  only after accepted evidence.
