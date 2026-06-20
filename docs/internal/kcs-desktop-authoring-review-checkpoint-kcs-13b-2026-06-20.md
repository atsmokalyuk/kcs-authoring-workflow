# KCS-13b Review Checkpoint: Semantic Review State and Bounded Prepare Packet

Date: 2026-06-20

## Verdict

Approved to commit locally and move to KCS-13c.

Two `gpt-5.3-codex-spark` review passes were run for this checkpoint.
The first pass found one P2 lifecycle issue: a pending `semantic_review_ref`
could survive a later `kcs_register_clean_ticket` call. The issue was fixed by
clearing pending semantic-review state during clean-ticket registration and by
adding regression coverage.

The follow-up pass found no P0, P1, or P2 blockers. It recorded one P3 deferred
item: the prepared packet already names `kcs_submit_semantic_review`, but that
tool is intentionally implemented in KCS-13c.

## Implemented Scope

- Added process-local pending semantic-review state with TTL.
- Added `kcs_prepare_semantic_review` as a Desktop-visible bounded follow-up
  tool.
- `kcs_draft_article(ticket_ref=...)` can return
  `workflow_state=semantic_review_required` for eligible low-confidence clean
  tickets.
- Prepared semantic-review packets return `selected_excerpts` only.
- Excerpts are capped by UTF-8 bytes:
  - max 10 excerpts;
  - max 8,000 bytes per excerpt;
  - max 64,000 total excerpt bytes.
- Generic MCP tool-result cap for this adapter is 128 KB.
- Prepared packets include compact audit metadata:
  `excerpt_count`, `excerpt_total_bytes`, and
  `semantic_review_packet_sha256`.
- Pending semantic-review state is one-shot:
  - successful prepare clears the pending ref;
  - expired prepare clears the pending ref;
  - new draft calls clear previous pending refs;
  - clean-ticket registration clears previous pending refs.
- Claude-visible docs and tool descriptors state that the packet is for
  semantic item identification only, not article drafting.
- Cowork plugin skill text and stdio-visible tool expectations were aligned
  with the new fourth operator tool.

## Preserved Boundaries

- No full ticket, raw Zendesk JSON, redaction map, reviewer packet, Zendesk
  HTML, local absolute path, article draft, KCS decision, publication flag, or
  provider payload is returned by `kcs_prepare_semantic_review`.
- `kcs_draft_article` remains the primary draft tool and does not accept
  semantic-review payloads.
- `kcs_prepare_semantic_review` accepts only `semantic_review_ref`.
- Manual/freehand drafting remains disallowed on blocked or review-required
  states.
- Python still owns state, validation, decision, rendering, readiness, and
  bundle writing.

## Validation Evidence

- Focused pytest:
  `uv run pytest tests/kcs_adapters/test_mcp_desktop.py tests/kcs_adapters/test_mcpb_package.py tests/kcs_adapters/test_desktop_ticket_ref.py tests/kcs_adapters/test_desktop_stdio_transport.py tests/kcs_adapters/test_cowork_plugin_package.py -q`
  passed: 222 passed, 2 skipped.
- Full pytest:
  `uv run pytest -q`
  passed: 970 passed, 2 skipped.
- Ruff:
  `uv run ruff check src scripts tests`
  passed.
- Whitespace:
  `git diff --check`
  passed.

## Deferred To KCS-13c

- Implement `kcs_submit_semantic_review` as the executable next action named
  by the prepare packet.
- Accept only strict `candidate_semantic_extraction_v1`.
- Reject article drafts, HTML, `recommended_action`, `item`,
  `item_candidates`, unknown `source_refs`, unsafe values, copied full ticket
  text, local paths, and publication flags.
- Continue through the existing Python-owned draft or split-required pipeline
  only after validation.

## Deferred Beyond KCS-13b

- Keep chunk browsing deferred.
- Continue Desktop log checker hardening in KCS-13d.
- Keep future local RAG strictly as a reuse-search adapter after accepted
  evidence.
