# KCS-15.2a Local Public RAG Adapter

Status: completed on 2026-07-22 at commits `0e14e95` and `2fabe43`.

The historical filename is retained for Git traceability. Canonical tracking
is KCS-15.2a under the KCS-15.2 RAG-assisted reuse umbrella.

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

## Closeout And Parent Boundary

This enabling slice proves that the repository can validate a ready loopback
public RAG runtime and retrieve bounded metadata-only candidates through a
fail-closed adapter. It does not prove retrieval quality, article fit,
cause-resolution or question-answer identity, operator usability, or workflow
integration stability.

Parent KCS-15.2 state:

```text
Outcome agreement: agreed
Design selection: open
Delivery authorization: locked
```

The agreed outcome is to surface reusable public knowledge at the right moment
and avoid drafting in vain. KCS-15.2b must still establish a decision-ready
operator experience that presents relevant ticket context together with enough
candidate/article information to judge reuse, update, or create. Adapter
completion does not select that UX or authorize Desktop/pipeline integration.

Combined post-integration validation passed 91 focused adapter and policy
checks. Ruff on the adapter, its tests, and the KCS-15 policy test also passed.
The full repository suite passed 1,465 tests with one expected skip.

### Compact Ousterhout review

```text
Ousterhout gate: reviewed
Trigger: new adapter, loopback HTTP, readiness,
  response-projection, and privacy boundaries
Complexity hidden: endpoint validation, redirect suppression, bounded
  transport, readiness/schema parsing, and metadata allowlisting
Owner and what it must not know: LocalPublicRagAdapter owns the local-public
  search boundary; it must not know KCS identity, drafting, Desktop,
  persistence, publication, or reviewer decisions
Interface depth and caller cognitive load: callers provide bounded symptoms
  and configuration and receive typed readiness/search results; callers do not
  handle runtime payload variants, snippets, chunks, or transport failures
Information leakage and change amplification: query text, snippets, chunks,
  vectors, local paths, and payload tails remain behind the adapter; runtime
  API variation is localized to one adapter and its tests
Complexity removed, moved, or added: necessary external-API variability is
  pulled down into the adapter; article-identity complexity was not moved into it
Residual design risk: retrieval quality, sufficient article evidence,
  operator UX, and Desktop/pipeline integration remain unproved in KCS-15.2b
Verdict: pass
```

This verdict applies only to the KCS-15.2a adapter boundary. It does not approve
the parent design or authorize integration.

## KCS-15.2b Decision-Readiness Gate

The current metadata-only adapter cannot by itself make an article-fit decision
ready. Before asking the operator to select a UX, autonomous Design work must
determine:

- which relevant ticket facts and missing knowledge the operator needs to see;
- what article evidence is sufficient to judge reuse, update, or create;
- whether that evidence comes from a public page, an existing approved article
  context, or another separately reviewed read path;
- how to align the ticket and article evidence without showing two long raw
  documents or increasing cognitive load;
- how absent, stale, ambiguous, or conflicting evidence fails safely;
- which existing privacy, packet, Desktop, persistence, and identity contracts
  remain unchanged.

Record safe process evidence for the next material decision:

```text
uncertainty trigger
repository/research/feasibility/operator ownership classification
autonomous resolutions
operator-only questions
visible evidence and sufficiency limits
alternatives and consequences
early versus late corrections
false-positive protocol activation
approval ledger and authorization state
```

If model- or RAG-mediated quality becomes part of acceptance, the KCS-15.2b
plan must predeclare fixtures, `N`, fixed conditions, invariants, threshold,
permitted corrections, operator overhead, false positives, and stop conditions.
A successful adapter call remains feasibility evidence, not stability evidence.
