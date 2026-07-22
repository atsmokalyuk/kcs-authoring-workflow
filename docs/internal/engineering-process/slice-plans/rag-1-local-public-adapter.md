# RAG-1 Local Public Search Adapter

Status: approved for implementation on 2026-07-22.

## Requested outcome

Provide a small, replaceable adapter that can verify the existing local public
RAG runtime and run a bounded metadata-only search from already validated,
public-safe symptom text.

## Operational baseline

- `ReuseSearchResultsPacket` already defines the core search boundary.
- The active Desktop workflow does not call local RAG and reports reuse search
  as skipped.
- The local `plesk_support` runtime exposes loopback JSON status and hybrid
  search endpoints over an operator-managed public Plesk corpus.
- RAG results contain ranked public article/chunk metadata. They do not prove
  cause-resolution or question-answer identity.
- A live warmed-runtime search can take about 14 seconds on the current local
  corpus, so the adapter uses a bounded 30-second default timeout.

## Target behavior

- The adapter accepts only a validated bounded symptom list.
- It calls only an explicit loopback HTTP endpoint.
- Readiness fails closed when the runtime is unavailable, stale, cold,
  incompatible, or not ready for both keyword and vector search.
- Search returns at most five projected candidates containing public metadata
  and relevance signals only.
- Raw query text, snippets, chunk bodies, vectors, local paths, and runtime
  payload tails are not returned or persisted by this repository.
- A search candidate remains an unclassified candidate. The adapter does not
  assign KCS article type, content status, or article identity.

## In scope

- stdlib loopback HTTP transport with redirects disabled;
- explicit adapter configuration and bounds;
- value-safe readiness result;
- symptom-oriented query validation;
- strict projection of allowlisted public result metadata;
- deterministic transport, safety, readiness, and response-contract tests;
- ownership-map and review-graph registration.

## Out of scope

- Desktop/MCP integration or schema changes;
- automatic invocation from the authoring pipeline;
- `ReuseSearchResultsPacket` construction;
- reuse/update/create decisions;
- operator confirmation UX;
- snippets, full article bodies, chunk text, or Claude context;
- corpus ingestion, indexing, maintenance, or runtime installation;
- hosted/internal RAG, credentials, non-loopback endpoints, writes, or publish;
- changes to KCS-14.5 semantic/provider/evaluation/control-surface behavior.

## Acceptance-to-gate mapping

| Acceptance criterion | Gate |
| --- | --- |
| Non-loopback, credential-bearing, redirected, or malformed endpoints are rejected. | deterministic unit tests |
| Cold, stale, unavailable, or non-hybrid-ready runtime reports a value-safe not-ready result. | deterministic unit tests |
| Safe bounded symptoms produce one bounded hybrid-search request. | deterministic unit test |
| Results contain only allowlisted public metadata and no snippet/chunk/query payload. | deterministic projection and forbidden-field tests |
| Unsupported schemas, oversized responses, unsafe URLs, or malformed candidates fail closed. | deterministic negative tests |
| Current local runtime readiness is reported accurately without changing it. | read-only local readiness smoke |
| Existing packet, Desktop, persistence, privacy, reviewer, and publish behavior remains unchanged. | deterministic diff review and full regression suite |

No model trial is appropriate because this slice validates an adapter boundary,
not retrieval quality or semantic identity.

## Unchanged contracts

- core packet and schema versions;
- KCS action and article-identity decisions;
- Desktop/MCP tools, arguments, results, and workflow states;
- renderer and reviewer bundle output;
- persistence and runtime artifact locations;
- reviewer-only, no-write, no-publish, and no-customer-reply boundaries;
- KCS-14.5 semantic ownership and provider/evaluation behavior.

## Stop condition

Stop and return to design if implementation requires Desktop changes, article
identity inference, snippets/chunks, a non-loopback endpoint, credentials,
runtime artifact writes, or changes to the retained KCS-14.5 control surface.
