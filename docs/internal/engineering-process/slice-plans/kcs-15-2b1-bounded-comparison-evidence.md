# KCS-15.2b1 Bounded Public Comparison Evidence

Status: completed on 2026-07-22; KCS-15.2b2 Phase A was subsequently
authorized on 2026-07-23, while Phase B remains Delivery-locked.

## Requested outcome

Give the future reuse-confirmation workflow enough bounded public article
evidence to compare ticket facts with one to three reusable articles before
drafting, without coupling the KCS core to Claude Desktop or to where the RAG
runtime is hosted.

## Operational baseline

- KCS-15.2a can check the existing loopback public RAG runtime and retrieve
  public metadata-only candidates.
- Metadata and relevance scores do not let the operator judge whether an
  article already covers the ticket facts or needs an update.
- The `plesk_support` runtime already exposes `/api/snippets` over the approved
  public Plesk corpus.
- The active KCS Desktop workflow does not request, display, persist, or pass
  those excerpts to Claude.
- An article explicitly referenced as the ticket resolution has higher
  comparison priority than candidates discovered only by RAG.

## Parent target UX

Before drafting, runtime Claude should ask one intermediate reuse question. It
should present one to three public article links, the relevant ticket facts,
bounded cited article evidence, and a recommendation to reuse, update, reject,
or continue searching. The operator confirms or steers the choice; the
operator is not expected to diagnose missing system evidence.

KCS-15.2b1 does not implement that UX. It provides only the provider-neutral
evidence contract and one local provider adapter needed by the later workflow.

## Confirmed boundaries

- At most three public candidates are projected.
- At most two excerpts per article and six excerpts total are projected.
- The token budget is at most 1,200 whitespace-delimited tokens, matching the
  current runtime rule but recomputed by the core acceptance gate; each excerpt
  is at most 6,000 characters and total excerpt text is at most 24,000.
- Only approved public `support.plesk.com`, `kb.plesk.com`, and
  `docs.plesk.com` HTTPS URLs are accepted.
- Query input is bounded already sanitized symptom text and is sent with
  `query_source=final_clean_ticket`.
- A priority-bearing explicit article is moved ahead of RAG-ranked candidates
  when its public context is returned. The caller may supply that reference
  only after accepted ticket evidence establishes that the article helped,
  resolved, or partially helped. URL-only or unconfirmed mentions do not carry
  priority. If the requested context is absent, the result carries a blocker
  and must not silently substitute a search hit.
- Excerpts remain untrusted comparison evidence. They do not establish KCS
  identity, content status, recommended action, or article actuality.
- Runtime query tails, index paths, chunk IDs, runtime citations, rendered
  Markdown, vectors, and retrieval IDs are not projected.
- Every provider result passes the core-owned contract gate. Local-adapter
  parsing is not the only safety boundary.

## Exact-integration feasibility record

The first plan placed the operational check too late. Before substantial
adapter implementation, a bounded live smoke was run against the exact
`/api/snippets` path in the existing `plesk_support` runtime.

```text
Claim: the current loopback runtime can return bounded cited public snippets
  with the schema and safety properties required by KCS-15.2b1
Safe input: synthetic public query about Plesk HTTP 500 login failure
Bounds: hybrid, top_k=5, max_snippets=3, max_tokens=400,
  per_article_cap=1, timeout=30 seconds
Expected invariants: wrapped success result, knowledge-cited-snippets-v1,
  approved public URLs, bounded counts/text, no query or private-path output
Allowed side effect: standard value-safe local RAG observability event
Failure handling: stop Delivery and revise the adapter contract
Stop condition: one valid response or the first incompatible contract fact
```

Observed result:

- response completed in about seven seconds;
- schema and wrapper were compatible;
- five candidates produced three excerpts, 158 tokens total;
- all returned URLs were approved public Plesk URLs;
- no query field, raw-query tail, or private path was returned;
- the largest excerpt was 607 characters;
- the first attempted status CLI syntax and the assumed top-level response
  shape were corrected before adapter implementation.

This proves bounded exact-path feasibility only. It does not prove retrieval
quality, stability, operator usability, or production readiness.

After implementation, the exact adapter path was smoked again with its actual
request bounds (`top_k=5`, `max_snippets=6`, `max_tokens=1200`,
`per_article_cap=2`, `query_source=final_clean_ticket`). It returned three
provider-neutral candidates and three excerpts, 128 recomputed tokens total,
a 607-character largest excerpt, and no blocker in about eight seconds. This
second success confirms implemented compatibility, still not stability.

## In scope

- immutable provider-neutral comparison-evidence request/result contracts;
- explicit public-article reference and priority semantics;
- local loopback `/api/snippets` projection behind the existing RAG adapter;
- strict bounds, public-origin validation, fail-closed parsing, and value-safe
  failure statuses;
- core-owned request/result invariants applied to local and future providers;
- deterministic fixtures and negative tests;
- approved data-boundary, architecture, ownership-map, and tracking updates.

## Out of scope

- Desktop/MCP tools, schemas, state, prompts, or result text;
- Claude/model calls or recommendations;
- operator comparison cards or confirmation state;
- `ReuseSearchResultsPacket`, KCS action, identity, renderer, or drafting
  integration;
- persistence, logs containing query/excerpt content, article writes, or
  publication;
- corpus ingestion, indexing, installation, hosted/internal RAG, credentials,
  or non-loopback transport;
- retrieval-quality or operator-usability claims.

## Acceptance-to-gate mapping

| Acceptance criterion | Gate |
| --- | --- |
| The contract is independent of Claude/Desktop and local/remote RAG hosting. | deterministic contract tests and architecture review |
| The local adapter sends the exact bounded `/api/snippets` request using `final_clean_ticket` query provenance. | deterministic transport fixture plus exact-path operational smoke |
| Only one to three allowlisted public articles and bounded cited excerpts are projected. | deterministic positive, bounds, and forbidden-field tests |
| Provider-declared token counts match independently recomputed whitespace-token counts. | deterministic under-reporting and aggregate-bound tests |
| An accepted helpful/partially-helpful priority reference outranks RAG-only candidates; absent explicit context blocks silent substitution. | deterministic priority and missing-context tests plus caller-prerequisite review |
| When explicit URL and source ID are both present, both identify the same returned article. | deterministic conflicting-identifier test |
| Cold, stale, unavailable, malformed, unsafe, or oversized responses fail closed with value-safe statuses. | deterministic negative matrix |
| Existing search, packet, Desktop, decision, rendering, persistence, and publication behavior does not change. | focused/full regression suite and behavior-drift review |
| The new provider boundary hides runtime-specific complexity without absorbing KCS decisions. | compact Ousterhout closeout and independent architecture/privacy review |

No model trial is appropriate for KCS-15.2b1. Retrieval relevance and the
operator-facing recommendation become measurable only in KCS-15.2b2/b3 after
their fixtures and trial protocol are approved.

## Unchanged contracts

- existing KCS-15.2a readiness and metadata-search inputs and outputs;
- core packet and schema versions, including `reuse_search_results_packet_v1`;
- KCS action, identity, article type, and content-status decisions;
- Desktop/MCP tool count, arguments, results, prompts, and workflow states;
- semantic-review/provider ownership retained from KCS-14.5;
- renderer and reviewer bundle output;
- local persistence and runtime artifact locations;
- reviewer-only, no-write, no-publish, and no-customer-reply boundaries.

## Approval ledger

```text
Parent requested outcome: agreed
Parent target UX: selected
Controlled bounded-public-excerpt boundary: approved
KCS-15.2b1 Delivery: authorized
KCS-15.2b1 closeout: completed
KCS-15.2b2 Phase A exact public context Delivery: authorized 2026-07-23
KCS-15.2b2 Phase B Desktop/operator workflow Delivery: locked
KCS-15.2b3 repeated model/operator trial: locked
```

## Stop condition

Stop and return to Design if this slice requires a Desktop change, a model
call, article/KCS identity inference, persistence of excerpt or query text, a
non-public source, credentials, a non-loopback provider, or any change to the
existing decision/drafting pipeline.

## Review corrections

The first independent architecture/privacy review requested changes before
closeout:

- move request/result invariants into a core-owned gate so a future provider
  cannot bypass local-adapter checks;
- independently recompute the runtime's whitespace-token count;
- reject known authorization/credential forms in excerpt output;
- require both URL and source ID to match when an explicit reference supplies
  both identifiers.

All four were corrected and received deterministic regression tests. The
repeat review found no remaining issue and approved KCS-15.2b1. A final citation
shape check also ensures a provider cannot append arbitrary text to the
generated title/section/public-URL citation.

## Compact Ousterhout closeout

```text
Ousterhout gate: reviewed
Trigger: new runtime-independent contract, external API adapter projection,
  and approved public-excerpt boundary
Complexity hidden: runtime wrapper/schema checks, exact request bounds,
  public-origin projection, grouping, explicit-reference priority, common
  provider-output acceptance, token verification, and value-safe failures
Owner and what it must not know: the core comparison contract owns common
  evidence invariants and LocalPublicRagAdapter owns loopback API translation;
  neither owns Desktop state, prompts, operator decisions, KCS identity,
  drafting, persistence, rendering, or publication
Interface depth and caller cognitive load: a caller supplies bounded symptoms
  and an optional public reference and receives one typed accepted evidence
  result; it does not handle local runtime wrappers, snippets schema, grouping,
  safety patterns, bounds, or transport errors
Information leakage and change amplification: query tails, local paths, runtime
  IDs/citations/Markdown, chunk IDs, vectors, and invalid provider fields stay
  behind the boundary; local API changes remain localized to one adapter while
  common provider changes retain one core acceptance gate
Complexity removed, moved, or added: necessary public-evidence invariants were
  centralized in the core contract and runtime-specific variation moved into
  the adapter; no Desktop/model/orchestration layer or KCS decision logic was
  added
Residual design risk: an explicit article absent from retrieval remains blocked
  rather than directly fetched; retrieval quality, recommendation quality,
  operator comfort, workflow state, and repeated stability remain for
  separately approved KCS-15.2b2/b3
Verdict: pass after review corrections
```

Closeout gates:

- 73 focused core/adapter tests passed;
- exact live adapter smoke returned three candidates, three excerpts, 128
  independently verified tokens, and `contract_ok=true`;
- production-code complexity stayed at or below CC 7;
- independent architecture/privacy review approved the corrected boundary;
- 33 focused process/policy/graph checks passed;
- the full repository suite passed 1,504 tests with one expected skip.
