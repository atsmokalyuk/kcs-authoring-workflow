# KCS Desktop Authoring Refactor Plan

## Summary

The Desktop drafting workflow must be tool-owned, not Claude-owned.
Claude Desktop is a thin control surface: it passes either complete approved
sanitized ticket context as `approved_summary_text`, or the exact selection
refs returned by the previous tool call.

Python owns:

- the semantic extraction contract;
- workflow state and pending selections;
- validation, safety, decision, rendering, readiness, and acceptance;
- local reviewer bundle output.

The approved semantic source is an approved provider called from Python. The
provider output is untrusted and accepted only when it validates as
`candidate_semantic_extraction_v1`.

## Desktop Tool Surface

Keep the Desktop-visible MCP surface narrow:

- one primary tool: `kcs_draft_article`;
- input args only:
  - `approved_summary_text`;
  - `operator_selection_ref`;
  - `operator_selected_item_ref`;
  - `debug`;
- no `item`, `item_candidates`, `reference_article_html`, broad aliases,
  provider internals, schema internals, or Desktop-owned extraction payloads.

Valid call shapes:

- first call: `approved_summary_text`, optionally `debug`;
- second call: `operator_selection_ref` and `operator_selected_item_ref`,
  optionally `debug`.

Invalid call shapes return controlled tool results, not generic MCP failures.

## Architecture Rule

Python owns the semantic extraction contract, state, validation, and
acceptance. Claude Desktop does not map a wide schema and does not choose item
structure.

Allowed provider roles:

- `UnavailableSemanticExtractionProvider`: production default when no approved
  provider runtime config is present; returns a controlled
  `semantic_extraction_provider_unavailable` workflow result.
- `ApprovedSemanticExtractionProvider`: calls the approved provider/API/internal
  service using safe refs and bounded payloads; accepts only
  `candidate_semantic_extraction_v1`.
- `FixtureSemanticExtractionProvider`: smoke/test only, enabled explicitly by
  injection or smoke env; it is visibly fixture-only and must not become a
  product-specific production regex engine.

No local Gemma/local LLM semantic implementation is in scope. No production
Monitoring/DataDir or other product-specific regex semantic engine is allowed.

## Local RAG Reuse Search Boundary

Future local RAG belongs in the pipeline only as a Search / reuse adapter, not
as semantic extraction, Claude prompting, or decision logic.

Target position:

```text
NormalizedTicketEvidencePacket
  -> KCS-2 safety/evidence gates
  -> local RAG reuse search
  -> ReuseSearchResultsPacket
  -> KCS-3 decision engine
```

Target module shape:

```text
src/kcs_adapters/reuse_search_local_rag.py
  input: NormalizedTicketEvidencePacket
  output: ReuseSearchResultsPacket
```

The local RAG adapter may only:

- consume accepted sanitized evidence;
- search existing KB/articles;
- return structured reuse matches.

It must not:

- read raw tickets;
- call Claude;
- decide create/update/reuse;
- return full snippets or full article bodies in Desktop output;
- perform Zendesk writes;
- make a draft KCS-ready unless reuse search actually ran with
  `searched=true`.

`ReuseSearchResultsPacket` should expose safe metadata only:

- `searched=true`;
- `search_source=local_public_rag`;
- `search_run_ref`;
- matches with `article_ref` or `source_doc_id`, `title`, `canonical_url`,
  `score`, `match_kind`, and optional safe `reason_codes`;
- `blockers=[]` when search succeeds.

`kcs_core.decision` remains the only owner of the create/update/reuse decision:

- strong same-issue match -> reuse existing;
- close but incomplete match -> update existing;
- no good match -> create candidate;
- search unavailable or skipped -> reviewer-only `draft_only`, not KCS-ready.

Current MVP behavior remains valid until this adapter exists:

```text
reuse_search_status=skipped
draft_generated=true
kcs_ready=false
debug_code=draft_only_reuse_search_missing
```

## Module Boundaries

`kcs_adapters.mcp_desktop` should keep only:

- MCP lifecycle and JSON-RPC transport;
- tool descriptors;
- dispatch;
- compact MCP result wrapping.

`kcs_adapters.desktop_workflow` should own:

- first-call vs second-call workflow;
- pending selection state, opaque refs, TTL, selected candidate lookup;
- provider calls through `kcs_core.semantic_extraction.SemanticExtractionProvider`;
- provider output validation with
  `CandidateSemanticExtraction` / `validate_candidate_semantic_extraction`;
- conversion into the existing article pipeline input;
- safety, validation, decision, renderer, readiness orchestration.

`kcs_adapters.desktop_reviewer_bundle` should own:

- writing reviewer bundles only under `local-data/reviewer-bundles/`;
- returning `bundle_ref`, relative `manifest_path`, relative `html_path`, and
  `html_sha256`;
- excluding absolute paths, raw packet bodies, and full HTML by default.

## Delivery Slices

Implement this as small reviewable slices, not as one large commit:

- `KCS-12a: Desktop schema diet + workflow service`
  - keep the Desktop-visible schema thin;
  - move first-call / second-call orchestration and pending selection state out
    of `mcp_desktop.py`;
  - make invalid call shapes controlled workflow results;
  - keep Claude Desktop from owning `item` or `item_candidates`.
- `KCS-12b: Local reviewer bundle boundary`
  - move local bundle writing out of `mcp_desktop.py`;
  - write only under `local-data/reviewer-bundles/`;
  - return only safe relative refs, paths, and hashes by default.
- `KCS-12c: Semantic provider boundary`
  - replace local semantic hacks with the approved provider/core semantic
    extraction contract;
  - keep fixture extraction opt-in for tests and smoke only;
  - do not add Gemma/local LLM semantics;
  - do not keep Monitoring/DataDir regex extraction as production semantics.
- `KCS-12d: Desktop smoke/install alignment`
  - make stdio and installed-wrapper smoke explicit about fixture provider use;
  - keep GUI-log smoke focused on observed Desktop behavior;
  - verify the installed MCPB exposes the same thin schema and wording.

## Review Breakpoints

Do not wait for the full refactor to complete before external review. Use
review checkpoints after each meaningful PR/slice:

Current review checkpoint artifact:

- `docs/internal/kcs-desktop-authoring-review-checkpoint-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12b-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12c-2026-06-19.md`

- `KCS-12a: Desktop schema diet + workflow service`
  - status: complete after final ChatGPT Pro follow-up review;
  - review required after local tests, Ruff, stdio smoke, and Desktop log check
    pass;
  - exit criterion: prepare the external review bundle and run ChatGPT Pro
    architecture/code review before starting the next implementation slice;
  - findings must be fixed or explicitly recorded as deferred in the checkpoint
    artifact before `KCS-12a` is considered complete;
  - focus on Desktop schema thinness, Claude/provider ownership, Python-owned
    validation/decision workflow, state boundaries, and scope drift.
- `KCS-12b: Local reviewer bundle boundary`
  - status: complete after ChatGPT Pro review;
  - review required after bundle writer/finalizer tests and smoke pass;
  - findings must be fixed or explicitly recorded as deferred in the checkpoint
    artifact before `KCS-12b` is considered complete;
  - focus on local write boundaries, relative refs/paths/hashes, no absolute
    paths, no full packets/HTML by default, and no hidden publish behavior.
- `KCS-12c: Semantic provider boundary`
  - status: ready for external ChatGPT Pro review;
  - review required after provider-state-machine tests and smoke pass;
  - findings must be fixed or explicitly recorded as deferred in the checkpoint
    artifact before `KCS-12c` is considered complete;
  - focus on approved-provider ownership, fixture-only semantics, no production
    regex semantic engine, no manual fallback, and validation of untrusted
    provider output.
- `KCS-12d: Desktop smoke/install alignment`
  - lighter review after install/cache/log checks pass;
  - focus on manifest/schema wording, MCP annotations, runtime wrapper env,
    installed cache behavior, and GUI-observable Desktop contract.

Review bundle should include:

- changed files;
- related tests;
- this plan and any touched design docs;
- MCPB manifest / Desktop-visible schema when touched;
- `pytest`, Ruff, `git diff --check`, stdio smoke, and log-check output;
- short PR intent;
- known deferred items.

Suggested review prompt:

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

## Implementation Checkpoint

Current branch status:

- `KCS-12a` is complete:
  - Desktop-visible schema is thin;
  - Desktop `kcs_draft_article` runtime accepts only the thin call shapes and
    rejects hidden broad arguments with controlled
    `draft_article_call_shape_invalid`;
  - first-call / second-call provider flow and pending selection state live in
    `kcs_adapters.desktop_workflow`;
  - split-required and operator-selection result shaping is delegated to
    `kcs_adapters.desktop_workflow`;
  - approved-summary pipeline sequencing
    (`payload -> evidence -> safety -> validation -> decision -> renderer ->
    readiness -> handoff/draft readiness`) lives in
    `kcs_adapters.desktop_workflow` through typed adapter hooks;
  - approved-summary status and authoring-failure shaping are delegated to
    `kcs_adapters.desktop_workflow`;
  - reviewer-only draft/HTML/preview shaping, quality-gap assembly, and reuse
    status helpers are delegated to `kcs_adapters.desktop_workflow`;
  - approved-summary payload normalization and argument compatibility handling
    live in `kcs_adapters.desktop_payload`;
  - repo-local approved ticket summary ref loading lives in
    `kcs_adapters.desktop_ticket_ref`;
  - remaining MCP transport glue stays in `kcs_adapters.mcp_desktop`.
- `KCS-12b` is complete:
  - local reviewer bundle writing lives in
    `kcs_adapters.desktop_reviewer_bundle`;
  - Desktop draft finalization and bundle-result shaping live in
    `kcs_adapters.desktop_workflow`;
  - default output returns compact refs, relative paths, and hashes;
  - ChatGPT Pro review on 2026-06-19 approved moving past `KCS-12b` with no
    P0/P1 blockers;
  - deferred hardening is recorded in
    `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12b-2026-06-19.md`.
- `KCS-12c` provider boundary is implemented for the Desktop draft path:
  - production default is controlled
    `semantic_extraction_provider_unavailable`;
  - approved-provider adapter exists behind safe refs;
  - fixture provider is explicit and used by smoke/tests;
  - production local Monitoring/DataDir regex semantics are not on the default
    path;
  - external review checkpoint is ready in
    `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12c-2026-06-19.md`;
  - do not mark `KCS-12c` complete or start `KCS-12d` until external review
    findings are fixed or recorded as explicit deferrals.
- `KCS-12d` smoke/install alignment is implemented for stdio and log checks:
  - stdio smoke uses the fixture provider explicitly;
  - installed-wrapper smoke checks registry/cache behavior;
  - Claude Desktop log check verifies the thin visible schema and tool
    annotations.

## Output Boundary

Anything returned by an MCP tool may be visible to Claude Desktop. Therefore
default output must be compact status plus refs/hashes.

Default successful draft output:

- `draft_generated=true`;
- `bundle_ref`, relative `manifest_path`, relative `html_path`, `html_sha256`;
- compact status and blocker/warning codes;
- no full `reviewer_only_html`.

Full `reviewer_only_html` is allowed only with `debug=true` or explicit smoke
compatibility.

Missing reuse/search may generate a reviewer-only draft for MVP, but it must
not be reported as KCS-ready:

- `kcs_ready=false`;
- `ready_for_reviewer=false`;
- `recommended_action=draft_only`;
- `debug_code=draft_only_reuse_search_missing`;
- `auto_publish_allowed=false`;
- `public_output_approved=false`.

## Operator Choice Contract

Native choice popup support is client-dependent. The contract remains:

- use native choice UI when available;
- otherwise call `kcs_draft_article` again with the exact
  `operator_choice_request.options[*].submit_arguments` object.

The tool must not continue drafting randomly when multiple semantic KCS items
are detected.

## Implementation Order

1. Write this plan artifact and link nearby docs to it instead of duplicating
   details.
2. Implement `KCS-12a`: remove the wide Desktop call surface from the visible
   schema and move workflow orchestration from `mcp_desktop.py` into
   `kcs_adapters.desktop_workflow`.
3. Implement `KCS-12b`: extract bundle writer into
   `kcs_adapters.desktop_reviewer_bundle`.
4. Implement `KCS-12c`: replace the old Desktop extraction provider interface
   with `SemanticExtractionProvider.propose_candidates(context)`.
5. Remove the local label/raw Monitoring extractor from the production default
   path.
6. Add an explicit fixture provider path for deterministic tests and smoke.
7. Add the approved provider path with safe configuration boundaries.
8. Implement `KCS-12d`: keep stdio and installed-wrapper smoke explicit about
   fixture usage.
9. Keep GUI-log smoke focused on observable Desktop behavior:
   tool call observed, `approved_summary_text` used, old structured args
   absent, manual fallback absent, timeout/disconnect absent.

## Test Plan

Unit and regression coverage must verify:

- Desktop schema exposes only thin args;
- `mcp_desktop.py` delegates workflow instead of owning extraction/bundle state;
- missing approved provider returns `semantic_extraction_provider_unavailable`;
- fixture provider output is validated and invalid/unsafe extraction blocks
  without raw echo;
- multiple candidates return `split_required`, compact cards,
  `operator_selection_ref`, and no HTML;
- second call uses only `operator_selection_ref` plus
  `operator_selected_item_ref`;
- invalid/expired selection refs return controlled failures;
- default output excludes `reviewer_only_html`;
- debug output may include bounded reviewer-only HTML;
- missing reuse search produces draft-only, not KCS-ready;
- bundle writer writes only relative safe paths under
  `local-data/reviewer-bundles/`;
- no production test depends on raw Monitoring/DataDir regex extraction;
- fixture provider is opt-in and visibly fixture-only;
- MCPB manifest/cache rejects the old wide schema and old native-popup
  guaranteed wording;
- article types are limited to `technical_scr` and `howto_qa`;
- Linux first resolution step uses the SSH link;
- Windows first resolution step uses the RDP link;
- Applicable To remains `Plesk for Linux` / `Plesk for Windows`.

Validation commands:

```bash
uv run pytest -q
uv run ruff check src scripts tests
git diff --check
uv run python scripts/smoke_kcs_mcpb_stdio.py
uv run python scripts/smoke_kcs_mcpb_stdio.py --wrapper packaging/claude-desktop/kcs-authoring-mvp-validator-control/server/index.js
uv run python scripts/check_claude_kcs_desktop_log.py
```

GUI-log smoke still requires a Claude Desktop restart/reload and a manual GUI
submit if macOS automation is unavailable or rate-limited.
