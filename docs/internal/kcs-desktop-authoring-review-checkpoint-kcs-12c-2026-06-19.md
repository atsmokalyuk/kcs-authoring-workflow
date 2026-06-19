# KCS Desktop Authoring Review Checkpoint - KCS-12c - 2026-06-19

## PR Intent

Review `KCS-12c: Semantic provider boundary` against
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

This checkpoint is focused on provider ownership and semantic extraction
boundaries. `KCS-12a` and `KCS-12b` are already complete and approved to move
forward.

Target behavior:

- Claude Desktop remains a thin control surface and passes only
  `approved_summary_text` or operator selection refs;
- Python owns semantic extraction provider selection, state, validation,
  decision, rendering, and acceptance;
- production default is a controlled
  `semantic_extraction_provider_unavailable` result;
- approved provider calls are Python-owned, explicitly configured, and use
  sanitized bounded context;
- fixture extraction is explicit smoke/test-only behavior;
- no Gemma/local LLM semantic layer is added;
- no production Monitoring/DataDir regex semantic extractor is on the default
  path;
- untrusted provider output must validate as
  `candidate_semantic_extraction_v1` before the workflow continues.

## Review Status

Status: approved to move past `KCS-12c`.

External ChatGPT Pro review on 2026-06-19 found no P0/P1 blockers for the
semantic provider boundary. `KCS-12c` is complete.

The next implementation slice may start from
`docs/internal/kcs-desktop-authoring-refactor-plan.md`.

## External Review Verdict

Verdict: approved to move past `KCS-12c`.

No blocking fixes are required before starting `KCS-12d`. The review confirmed
that Claude Desktop remains a thin control surface, Python owns provider
selection/state/validation/decision/rendering/acceptance, the default provider
state is controlled unavailable, provider output is untrusted, and Desktop does
not own `item` / `item_candidates` payloads.

Deferred findings from the review:

- add explicit semantic-provider status fields, for example
  `semantic_provider_mode`, `semantic_provider_called`,
  `semantic_provider_owner=python`, and `provider_payload_exposed=false`;
- add workflow-level provider-context pre-validation before calling any
  injected provider;
- keep fixture provider smoke/test-only and consider requiring a second smoke
  guard later;
- continue shrinking `kcs_adapters.mcp_desktop`;
- keep future local RAG strictly as a Search/reuse adapter after accepted
  evidence.

Local `gpt-5.3-codex-spark` pre-review also found no P0/P1 blockers. Its
additional deferred findings are:

- clarify the non-operational `approved` env path when no approved provider
  client is injected;
- clear stale pending selection state after a non-split primary summary path;
- add tests for env-approved behavior and stale selection cleanup.

## Review Focus

Please review for:

- approved-provider ownership and safe configuration boundaries;
- fixture-only semantics staying visibly smoke/test-only;
- no production local regex semantic engine;
- no manual/freehand fallback when the provider is missing or invalid;
- validation of untrusted provider output before conversion to Desktop article
  candidates;
- value-safe errors that do not echo unsafe provider output;
- state-machine correctness for split-required and selected-item continuation;
- no Desktop-owned `item` or `item_candidates` extraction payloads;
- test coverage gaps around provider failure, invalid provider output, fixture
  use, and selection flow.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

## Changed Files For Review

Primary implementation files:

- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_core/semantic_extraction.py`

Tests:

- `tests/kcs_adapters/test_desktop_workflow.py`
- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/kcs_adapters/test_mcpb_package.py`
- `tests/kcs_core/test_semantic_extraction.py`

Packaging and smoke evidence:

- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/manifest.json`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/README.md`
- `packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js`
- `scripts/smoke_kcs_mcpb_stdio.py`
- `scripts/check_claude_kcs_desktop_log.py`

Docs:

- `docs/internal/kcs-desktop-authoring-refactor-plan.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12b-2026-06-19.md`

## Current Architecture State

`kcs_core.semantic_extraction` owns the bounded semantic contract:

- `SemanticExtractionProvider.propose_candidates(context)` is the provider
  boundary;
- `CandidateSemanticExtraction` and `CandidateKcsItem` define
  `candidate_semantic_extraction_v1`;
- `validate_candidate_semantic_extraction(...)` validates untrusted provider
  output without echoing provider values;
- accepted extraction can be normalized into evidence through the core semantic
  extraction contract.

`kcs_adapters.desktop_workflow` owns Desktop provider orchestration:

- `UnavailableSemanticExtractionProvider` is the production default when no
  explicit provider config is present;
- `ApprovedSemanticExtractionProvider` accepts a safe `provider_ref`, validates
  sanitized provider context, and requires an injected approved client to make
  calls;
- `FixtureSemanticExtractionProvider` is documented as fixture-only and used
  explicitly by tests and smoke;
- `DesktopDraftWorkflow.item_candidates_from_summary(...)` calls the provider
  with approved sanitized summary context and converts only validated semantic
  extraction into Desktop candidates;
- invalid provider output raises a controlled semantic extraction failure in
  the MCP adapter path;
- multiple semantic items create pending operator selection state and require a
  second call with exact refs.

`kcs_adapters.mcp_desktop` keeps the Desktop runtime surface thin:

- visible and accepted `kcs_draft_article` call shapes remain
  `approved_summary_text` plus optional `debug`, or
  `operator_selection_ref` plus `operator_selected_item_ref` plus optional
  `debug`;
- hidden `item`, `item_candidates`, `ticket_ref`, reference article bodies,
  reuse fields, and broad article fields are rejected in Desktop alias mode
  with controlled `draft_article_call_shape_invalid`;
- missing provider, no candidates, invalid provider output, and invalid
  operator selection return controlled tool results rather than manual fallback.

## Boundary Evidence

The implementation currently enforces:

- no provider configured -> `semantic_extraction_provider_unavailable`;
- explicit fixture provider for deterministic tests and stdio smoke;
- approved provider mode requires safe refs and does not expose inline
  endpoint URLs or credentials in the Desktop schema;
- provider output validation through `CandidateSemanticExtraction`;
- invalid provider output -> `semantic_extraction_output_invalid` without
  echoing unsafe provider values;
- multiple candidates -> `split_required` and `operator_selection_ref`;
- selected-item continuation uses stored pending candidates, not Desktop-passed
  `item_candidates`;
- manual drafting/fallback is not advertised or returned by the tool result.

## Validation Evidence

Focused validation for this checkpoint:

```text
uv run pytest tests/kcs_adapters/test_desktop_workflow.py \
  tests/kcs_adapters/test_mcp_desktop.py \
  tests/kcs_adapters/test_mcpb_package.py \
  tests/kcs_core/test_semantic_extraction.py -q
223 passed, 2 skipped

uv run ruff check src/kcs_adapters/desktop_workflow.py \
  src/kcs_adapters/mcp_desktop.py \
  src/kcs_core/semantic_extraction.py \
  tests/kcs_adapters/test_desktop_workflow.py \
  tests/kcs_adapters/test_mcp_desktop.py \
  tests/kcs_core/test_semantic_extraction.py \
  scripts/smoke_kcs_mcpb_stdio.py
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

## Known Deferred Items

- Clarify compact provider-call status fields before real approved provider
  rollout, for example `semantic_provider_mode`,
  `semantic_provider_called`, and `provider_call_owner=python`.
- Add workflow-level provider-context pre-validation before calling injected
  providers.
- Clarify the env-selected `approved` provider behavior when no approved
  provider client is configured.
- Clear stale pending selection state after a non-split primary summary path.
- Add tests for env-approved provider behavior and stale selection cleanup.
- Consider requiring an additional explicit smoke marker before
  `FixtureSemanticExtractionProvider` can be selected from environment.
- Continue shrinking `kcs_adapters.mcp_desktop`; this checkpoint only reviews
  the semantic provider boundary.
- Add exact Desktop schema parsing to
  `scripts/check_claude_kcs_desktop_log.py`.
- Add defensive stripping of `reviewer_only_html` and `zendesk_source_html` for
  non-ready Desktop finalizer results, carried forward from `KCS-12b`.
- Future local RAG must be added only as a Search/reuse adapter after accepted
  `NormalizedTicketEvidencePacket`.

## Suggested Review Prompt

```text
Review KCS-12c against the KCS Desktop Authoring Refactor Plan.

Focus on:
- approved-provider ownership and safe configuration;
- fixture-only semantics;
- no production regex semantic engine;
- no manual/freehand fallback;
- validation of untrusted provider output;
- value-safe failures with no unsafe echo;
- Desktop schema thinness and no Desktop-owned item/item_candidates payloads;
- split-required and selected-ref state-machine correctness;
- privacy/safety boundary and architecture drift;
- test coverage gaps.

Do not bikeshed style unless it affects maintainability, safety, privacy, or
the runtime contract.

Return findings ordered by severity P0/P1/P2/P3, with file/line, why it
matters, suggested fix, and whether it blocks KCS-12c completion.
```
