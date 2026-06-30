# KCS Desktop Authoring Refactor Plan

Status note, 2026-06-20: this plan describes the current KCS Authoring
Workflow, not only the original MVP milestone. Enterprise/PAUX rollout is
postponed. Some package names still contain `mvp` for compatibility, but the
implemented product is now a production-shaped local workflow with clean-ticket
registration, `ticket_ref` drafting, compact default output, and local reviewer
bundles. Claude Desktop MCPB is the current local operator adapter, not a core
product dependency.

## Summary

The Desktop drafting workflow must be tool-owned, not Claude-owned.
Claude Desktop is a thin control surface: it can register a complete sanitized
ticket transcript as a repo-local clean ticket file, then pass either the
opaque `ticket_ref`, complete approved sanitized ticket context as
`approved_summary_text` for short pasted text, or the exact selection refs
returned by the previous tool call.

Python owns:

- the semantic extraction contract;
- workflow state and pending selections;
- validation, safety, decision, rendering, readiness, and acceptance;
- local reviewer bundle output.

The production Desktop semantic source is a bundled local approved-summary
provider called from Python. It extracts only explicit facts from
`approved_summary_text` and does not require Claude CLI/Code, an API key, or a
manually configured semantic provider. Any future external approved provider
must remain Python-owned, explicit, bounded, and untrusted until it validates as
`candidate_semantic_extraction_v1`.

## Desktop Tool Surface

Keep the Desktop-visible MCP surface narrow:

- one registration tool: `kcs_register_clean_ticket`;
- one ticket-ref authoring tool for `/draft <ticket_ref>`:
  `kcs_draft_ticket`;
- one short-text/selection authoring tool: `kcs_draft_article`;
- two bounded semantic-review tools:
  `kcs_prepare_semantic_review` and `kcs_submit_semantic_review`;
- `kcs_register_clean_ticket` input args only:
  - `clean_ticket_text`;
  - `ticket_ref`;
  - `debug`;
- `kcs_draft_article` input args only:
  - `approved_summary_text`;
  - `operator_selection_ref`;
  - `operator_selected_item_ref`;
  - `debug`;
- `kcs_draft_ticket` input args only:
  - `ticket_ref`;
  - `debug`;
- no `item`, `item_candidates`, `reference_article_html`, broad aliases,
  provider internals, schema internals, or Desktop-owned extraction payloads.

`support_get_behavior_instructions` is an internal legacy compatibility helper
only. It is not part of the Claude Desktop operator-visible tool surface and
must not be advertised as an authoring route.

Valid call shapes:

- optional clean-ticket registration call: `clean_ticket_text`, optionally
  `ticket_ref` and `debug`;
- first ticket-ref call: `kcs_draft_ticket` with `ticket_ref`, optionally
  `debug`;
- first call fallback for short pasted text: `approved_summary_text`,
  optionally `debug`;
- second call: `operator_selection_ref` and `operator_selected_item_ref`,
  optionally `debug`.

Invalid call shapes return controlled tool results, not generic MCP failures.
`ticket_ref` is an opaque ref, not a path. The canonical source-independent
clean ticket file layout is:

```text
local-data/approved-summaries/<ticket_ref>/clean.ticket.txt
```

Zendesk cleanup, Claude attachment preparation, and web GUI cleanup should all
write the same clean ticket file shape. Python reads that file and feeds the
complete cleaned transcript through the same semantic extraction, validation,
decision, renderer, and bundle pipeline.

When Claude Desktop receives a sanitized attachment but no `ticket_ref`, it
should automatically first call `kcs_register_clean_ticket` with the complete
visible sanitized transcript in `clean_ticket_text`; the operator should not
need to ask for registration explicitly. The registration result returns
`next_arguments`, and Claude must call `kcs_draft_article` with those arguments
exactly.

## Architecture Rule

Python owns the semantic extraction contract, state, validation, and
acceptance. Claude Desktop does not map a wide schema and does not choose item
structure.

Allowed provider roles:

- `ApprovedSummarySemanticExtractionProvider`: production default; bundled with
  the MCPB; extracts explicit approved-summary facts locally and returns no
  candidates when the summary lacks required semantic facts.
- `UnavailableSemanticExtractionProvider`: controlled failure mode for explicit
  unsupported provider configuration; returns
  `semantic_extraction_provider_unavailable`.
- Future external approved provider adapters: call an approved provider/API or
  internal service only when explicitly configured, using safe refs and bounded
  payloads; accept only `candidate_semantic_extraction_v1`.
- `FixtureSemanticExtractionProvider`: smoke/test only, enabled explicitly by
  injection or smoke env; it is visibly fixture-only and must not become a
  product-specific production regex engine.

No local Gemma/local LLM semantic implementation is in scope. No production
Monitoring/DataDir or other product-specific regex semantic engine is allowed.
The local approved-summary provider may parse generic labeled or narrative
support-summary structure, but it must not become a product-specific ticket
solver.

## Controlled Semantic Review Fallback

`KCS-13` adds a fallback for free Claude Desktop environments where no Claude
API/CLI/Code provider and no local LLM are available. This fallback must not
reopen the Desktop-owned schema problem. Claude Desktop may identify candidate
KCS items from bounded selected excerpts only. Python still validates, decides,
renders, and writes any reviewer bundle.

Primary invariant:

```text
Claude may identify candidate KCS items from bounded selected excerpts.
Claude must not draft, decide, render, or publish.
Python validates everything before any reviewer bundle is written.
```

The fallback is a new explicit Claude-visible data-egress lane:

```text
approved clean ticket
  -> semantic-review eligible metadata
  -> bounded selected excerpts
  -> candidate_semantic_extraction_v1 proposal
  -> Python validation / decision / rendering
```

Clean-ticket metadata must live next to `clean.ticket.txt`:

```text
local-data/approved-summaries/<ticket_ref>/clean.ticket.meta.json
```

Metadata schema:

```json
{
  "schema_version": "kcs_clean_ticket_metadata_v1",
  "ticket_ref": "...",
  "clean_ticket_sha256": "...",
  "semantic_review_allowed": true,
  "source_kind": "cleanup_form|claude_visible_registration"
}
```

Before returning `semantic_review_required`, before preparing excerpts, and
before accepting a submitted semantic extraction, Python must verify:

- metadata exists;
- `schema_version` is valid;
- `ticket_ref` matches;
- `sha256(clean.ticket.txt)` matches `clean_ticket_sha256`;
- `semantic_review_allowed=true`.

Missing metadata, false eligibility, or hash mismatch is a hard blocker. It
must not expose excerpts.

`semantic_review_required` is a workflow state, not a KCS action. The result
contract is:

```json
{
  "recommended_action": "blocked",
  "workflow_state": "semantic_review_required",
  "failure_stage": "semantic_extraction",
  "debug_code": "semantic_identification_low_confidence",
  "semantic_review_ref": "semantic-review-...",
  "next_tool": "kcs_prepare_semantic_review",
  "next_arguments": {
    "semantic_review_ref": "semantic-review-..."
  },
  "manual_draft_allowed": false,
  "draft_generated": false,
  "reviewer_bundle_written": false,
  "auto_publish_allowed": false,
  "public_output_approved": false
}
```

New Desktop-visible tools:

- `kcs_prepare_semantic_review`;
- `kcs_submit_semantic_review`.

`kcs_draft_article` must not accept semantic-review payloads. Its schema stays:

- `approved_summary_text`;
- `operator_selection_ref`;
- `operator_selected_item_ref`;
- `debug`.

Ticket-ref drafting stays on `kcs_draft_ticket`:

- `ticket_ref`;
- `debug`.

`kcs_prepare_semantic_review` returns only precomputed bounded selected
excerpts. Do not use "chunks" in Desktop-facing docs, manifest wording, or tool
descriptions.

Resolution evidence rule:

- If the clean ticket gives the resolution outcome or a high-level resolution
  description but does not include the exact executable procedure needed to
  apply and verify it, `approved_summary_resolution_steps_incomplete` is a
  valid blocker.
- Claude and Python must not infer the missing implementation details.
- The operator may resolve this blocker by adding explicit
  operator-confirmed resolution detail as approved evidence, then rerunning the
  workflow. This is not manual/freehand drafting; the added detail becomes
  validated input to the same KCS pipeline.
- If no operator-confirmed detail is available, the candidate remains blocked
  or is flagged for review instead of producing a speculative article.

MVP packet caps:

- max 12 excerpts;
- max 12,000 UTF-8 bytes per excerpt;
- max 144,000 total excerpt UTF-8 bytes;
- max 5 candidate items.

The generic MCP tool-result cap for this adapter is 256 KB. Semantic review
packets must stay comfortably below that cap after JSON overhead.

Prepare output may include safe audit metadata only:

- `semantic_review_packet_sha256`;
- `excerpt_count`;
- `excerpt_total_bytes`.

Prepare output must exclude raw Zendesk JSON, attachments, redaction maps, full
ticket dumps, local absolute paths, reviewer packets, Zendesk HTML, article
drafts, KCS decisions, publication flags, and provider payloads.

`kcs_submit_semantic_review` accepts only:

```json
{
  "semantic_review_ref": "...",
  "candidate_semantic_extraction": {
    "schema_version": "candidate_semantic_extraction_v1",
    "case_ref": "...",
    "extraction_source_ref": "...",
    "source_refs": ["excerpt-001"],
    "items": []
  }
}
```

It must reject article drafts, Markdown or HTML, `reviewer_only_html`,
`recommended_action`, `item`, `item_candidates`, publication flags, local paths,
copied full ticket text, broad aliases, unknown source refs, unsafe values, and
raw provider payloads. Valid output is still untrusted until the existing core
`CandidateSemanticExtraction` validation and semantic-review-specific source-ref
checks pass.

Trigger rules:

- keep `semantic_extraction_no_candidates` for no usable KCS item,
  incomplete/unresolved tickets, unsafe input, missing eligibility metadata, or
  no final evidence;
- return `workflow_state=semantic_review_required` only when Python sees likely
  KCS material, deterministic extraction is low-confidence, metadata/hash
  validation passes, and bounded selected excerpts can be prepared;
- hard block unsafe, raw, unresolved, too-large, or non-eligible tickets.

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
  - replace local semantic hacks with the core semantic extraction contract and
    the bundled local approved-summary provider;
  - keep future external approved providers behind explicit safe configuration
    boundaries;
  - keep fixture extraction opt-in for tests and smoke only;
  - do not add Gemma/local LLM semantics;
  - do not keep Monitoring/DataDir regex extraction as production semantics.
- `KCS-12d: Desktop smoke/install alignment`
  - make stdio and installed-wrapper smoke explicit about fixture provider use;
  - keep GUI-log smoke focused on observed Desktop behavior;
  - verify the installed MCPB exposes the same thin schema and wording.
- `KCS-13a: Semantic review policy, metadata, and result contract`
  - document the explicit Claude-visible excerpt lane;
  - add clean-ticket metadata and hash validation;
  - add `workflow_state=semantic_review_required` without exposing excerpts.
- `KCS-13b: Semantic review state and bounded prepare packet`
  - add process-local semantic-review state with TTL;
  - precompute bounded selected excerpts before returning
    `semantic_review_required`;
  - add `kcs_prepare_semantic_review`.
- `KCS-13c: Submit semantic extraction and continue existing pipeline`
  - add `kcs_submit_semantic_review`;
  - accept only `candidate_semantic_extraction_v1`;
  - validate source refs and forbidden payloads before continuing to draft or
    split selection.
- `KCS-13d: MCPB, docs, smoke, and Desktop contract alignment`
  - update tool names, descriptors, manifest, README, stdio smoke, installed
    wrapper smoke, and Desktop log checks;
  - keep bounded selected excerpts only and defer browsing/chunk tools.
- `KCS-14: KCS style and markup parity`
  - bring renderer, Zendesk HTML quality gates, and style checks closer to the
    mature `plesk_support` KCS article workflow;
  - enforce source-document-backed KCS content standards for titles, symptoms,
    cause, resolution, language style, and Zendesk markup;
  - keep enforcement deterministic where possible and treat any optional style
    judge as reviewer-assist feedback, not publication approval.

## Review Breakpoints

Do not wait for the full refactor to complete before external review. Use
review checkpoints after each meaningful PR/slice:

Current review checkpoint artifact:

- `docs/internal/kcs-desktop-authoring-review-checkpoint-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12b-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12c-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12d-2026-06-19.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-13a-2026-06-20.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-13b-2026-06-20.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-13c-2026-06-20.md`
- `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-13d-2026-06-20.md`

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
  - status: complete after ChatGPT Pro review;
  - review required after provider-state-machine tests and smoke pass;
  - findings must be fixed or explicitly recorded as deferred in the checkpoint
    artifact before `KCS-12c` is considered complete;
  - focus on approved-provider ownership, fixture-only semantics, no production
    regex semantic engine, no manual fallback, and validation of untrusted
    provider output.
- `KCS-12d: Desktop smoke/install alignment`
  - status: complete after ChatGPT Pro review;
  - lighter review after install/cache/log checks pass;
  - findings must be fixed or explicitly recorded as deferred in the checkpoint
    artifact before `KCS-12d` is considered complete;
  - focus on manifest/schema wording, MCP annotations, runtime wrapper env,
    installed cache behavior, and GUI-observable Desktop contract.
- `KCS-13a: Semantic review policy, metadata, and result contract`
  - review required before implementing excerpt return;
  - focus on data-egress lane, metadata/hash binding, and result vocabulary.
- `KCS-13b: Semantic review state and bounded prepare packet`
  - external review required before moving on;
  - focus on Claude-visible excerpt caps, no full-ticket exposure, no logs/raw
    echoes, and ref/TTL state boundaries.
- `KCS-13c: Submit semantic extraction and continue existing pipeline`
  - status: complete after `gpt-5.3-codex-spark` review;
  - external review required before moving on;
  - focus on preventing a broad Desktop-owned extraction backdoor and ensuring
    Python-owned validation/decision/rendering.
- `KCS-13d: MCPB, docs, smoke, and Desktop contract alignment`
  - status: complete after `gpt-5.3-codex-spark` review;
  - lighter review after source/installed smoke and log checks pass;
  - focus on Desktop-visible schema wording and no manual fallback.
- `KCS-14: KCS style and markup parity`
  - external/code review required before marking complete;
  - focus on parity with source KCS Style Guide, Article Quality criteria, KCS
    practices, and portable `plesk_support` rules;
  - review must check title/symptom/cause/resolution semantics, Zendesk trigger
    markup, command/config formatting, language style, blocker/warning
    taxonomy, and no subject-matter hardcoding.

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
  - production default is the bundled local
    `ApprovedSummarySemanticExtractionProvider`;
  - explicit unsupported provider configuration still returns controlled
    `semantic_extraction_provider_unavailable`;
  - future approved-provider adapters must stay behind safe refs;
  - fixture provider is explicit and used by smoke/tests;
  - production local Monitoring/DataDir regex semantics are not on the default
    path;
  - ChatGPT Pro review on 2026-06-19 approved moving past `KCS-12c` with no
    P0/P1 blockers;
  - deferred hardening is recorded in
    `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12c-2026-06-19.md`.
- `KCS-12d` smoke/install alignment is implemented for stdio and log checks:
  - stdio smoke uses the fixture provider explicitly;
  - installed-wrapper smoke checks registry/cache behavior;
  - Claude Desktop log check verifies the thin visible schema and tool
    annotations;
  - ChatGPT Pro review on 2026-06-19 approved moving past `KCS-12d` with no
    P0/P1 blockers;
  - deferred hardening is recorded in
    `docs/internal/kcs-desktop-authoring-review-checkpoint-kcs-12d-2026-06-19.md`.
- `KCS-13` controlled semantic review fallback is implemented locally:
  - design direction is conditionally approved after external review;
  - `KCS-13a` policy/metadata/result contract is implemented and approved to
    move forward after code-review checkpoint;
  - `KCS-13b` process-local semantic-review state and bounded prepare packet
    are implemented and approved to commit after code-review checkpoint;
  - `KCS-13b` adds `kcs_prepare_semantic_review` and bounded
    `selected_excerpts`;
  - `KCS-13c` strict `kcs_submit_semantic_review` validation and continuation
    through the existing draft/split pipeline are implemented and approved to
    commit after code-review checkpoint;
  - `KCS-13d` aligns MCPB packaging, installed/source smoke, docs, and Desktop
    log checks for the full KCS-13 tool set;
  - KCS-13d raises the bounded semantic-review budget to 144,000 total
    selected-excerpt bytes and the generic MCP tool-result cap to 256 KB while
    keeping forbidden-key checks and no-full-ticket output.
- `KCS-14` is the next hardening slice for KCS article style and markup parity:
  - use the attached/source-of-truth KCS Style Guide, Article Quality criteria,
    KCS practices, and approved article examples as requirements;
  - target result-level parity with mature `plesk_support` KCS behavior, not
    code-level parity or wholesale feature copying;
  - port only applicable, boundary-safe checks from `plesk_support`;
  - prefer the cleaner `kcs-authoring-workflow` architecture whenever an
    equivalent rule can be expressed as a deterministic renderer, quality, or
    style contract;
  - do not port old chat-flow behavior, subject-specific heuristics,
    duplicated abstractions, or adapter code that would weaken the current
    tool-owned workflow;
  - strengthen deterministic gates before reviewer bundle write;
  - keep style/markup blockers separate from safety/readiness blockers;
  - do not hardcode ticket subject matter, product incidents, commands, or
    Plesk component-specific solutions.

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

Missing reuse/search may generate a reviewer-only draft in the current local
workflow, but it must not be reported as KCS-ready:

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
7. Add the bundled local approved-summary provider path and keep any future
   external approved provider behind safe configuration boundaries.
8. Implement `KCS-12d`: keep stdio and installed-wrapper smoke explicit about
   fixture usage.
9. Keep GUI-log smoke focused on observable Desktop behavior:
   tool call observed, `approved_summary_text` used, old structured args
   absent, manual fallback absent, timeout/disconnect absent.
10. Implement `KCS-13a`: semantic-review data policy, clean-ticket metadata,
    hash validation, and `workflow_state=semantic_review_required`.
11. Implement `KCS-13b`: process-local semantic-review state and bounded
    selected-excerpt prepare packet.
12. Implement `KCS-13c`: strict semantic extraction submit tool and continuation
    through the existing draft/split pipeline.
13. Implement `KCS-13d`: MCPB manifest, docs, stdio smoke, installed smoke, and
    Desktop log checker alignment for the new tools.
14. Implement `KCS-14`: style and markup parity hardening:
    title, symptoms, cause, resolution completeness, language style,
    command/config formatting, Zendesk trigger markup, and blocker/warning
    taxonomy.

## Test Plan

Unit and regression coverage must verify:

- Desktop schema exposes only thin args;
- `mcp_desktop.py` delegates workflow instead of owning extraction/bundle state;
- default production provider extracts explicit approved-summary facts locally;
- summaries without enough semantic facts return
  `semantic_extraction_no_candidates`;
- explicit unsupported provider configuration returns
  `semantic_extraction_provider_unavailable`;
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
- clean-ticket metadata is written by registration and validated before
  semantic review;
- missing/false/hash-mismatched metadata blocks semantic review without
  exposing excerpts;
- eligible low-confidence tickets return
  `workflow_state=semantic_review_required`, `recommended_action=blocked`, and
  `manual_draft_allowed=false`;
- `kcs_prepare_semantic_review` returns bounded selected excerpts only, with
  packet hash/count/size metadata and exact submit arguments;
- prepare output excludes full tickets, Zendesk HTML, absolute paths, reviewer
  packets, redaction maps, raw payloads, and article drafts;
- `kcs_submit_semantic_review` rejects invalid schema, unknown source refs,
  unsafe values, too many items, copied full text, article drafts, HTML,
  `recommended_action`, `item`, and `item_candidates` without raw echo;
- valid semantic-review submissions either continue to normal draft output or
  return the existing split-required operator-selection flow;
- simple deterministic tickets bypass semantic review and still draft normally.
- KCS-14 renderer/style tests verify:
  - titles describe the customer-visible issue and, when available, append the
    error/cause clue after a colon instead of including solution wording;
  - Symptoms start with the customer's observable issue and include only
    narrowing facts needed to identify the cause;
  - Cause is analysis, not procedure;
  - Resolution steps are executable from the article when the ticket contains
    the operational details;
  - when the ticket does not contain exact executable resolution detail, the pipeline
    blocks with `approved_summary_resolution_steps_incomplete` and may proceed
    only after operator-confirmed resolution detail is added as evidence;
  - commands and config blocks are nested inside the relevant numbered action
    step, not numbered as independent steps;
  - concrete Plesk panel navigation paths are written from the home page, for
    example `Plesk > Domains > example.com > Hosting Settings`, and rendered in
    bold in Zendesk HTML;
  - `CONFIG_TEXT`, `PLESK_ERROR`, `SVM_ERROR`, `MYSQL_LIN`, `MYSQL_WIN`,
    shell commands, paths, and errors follow Zendesk/KCS trigger formatting;
  - language is impersonal, concise, and free of source-ticket first-person
    wording or product-diminishing phrasing;
  - risky or custom actions preserve ticket-supported steps and add reviewer
    warnings when needed, without inventing commands or online-sourced
    remediation;
  - style/markup gates do not produce KCS-ready or publish-approved status.

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
