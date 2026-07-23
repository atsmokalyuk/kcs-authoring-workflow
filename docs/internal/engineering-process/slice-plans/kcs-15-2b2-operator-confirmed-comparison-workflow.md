# KCS-15.2b2 Operator-Confirmed Comparison Workflow

Status: parent outcome and target UX selected; Phase A Delivery and independent
review complete. Phase B Desktop/model/operator Delivery remains locked.

## Requested outcome

Avoid drafting a new article before the operator has enough ticket and public
article evidence to decide whether an existing article can be reused, should
be flagged for an update, is not a fit, or requires more investigation.

The operator approves or rejects the result of autonomous comparison research
and may steer it. The operator is not expected to diagnose which evidence the
system failed to collect.

## Operational baseline

- KCS-15.2a can validate the existing loopback public RAG runtime and retrieve
  bounded public candidate metadata.
- KCS-15.2b1 can retrieve and validate one to three public candidates with
  bounded cited excerpts through a provider-neutral core contract.
- The active `plesk_support` runtime exposes semantic `/api/snippets` search,
  but it has no exact public-article lookup or filter by canonical URL or
  `source_doc_id`.
- A successful semantic search for an explicitly referenced article would
  prove feasibility only. It would not guarantee that the exact article is
  returned.
- The active Desktop workflow does not call the comparison provider, expose
  comparison evidence, ask for a reuse confirmation, or retain pending reuse
  state.
- Existing compatibility behavior can treat a resolution-related public URL
  as a partial match without comparing article content. KCS-15.2b2 must not
  treat URL presence alone as article fit or update evidence.
- Desktop already has bounded in-memory semantic-review and operator-selection
  states with opaque references and a 15-minute TTL. These are proven patterns,
  not permission to overload their existing contracts.

## Confirmed target UX

Comparison happens after Python has accepted one atomic issue and after any
required operator scope selection, but before a draft or reviewer bundle is
created for that issue.

For one issue, runtime Claude should present one compact comparison step:

- the relevant accepted ticket facts, not the raw ticket;
- one to three public article links;
- bounded cited public excerpts;
- a concise evidence-based recommendation describing covered and missing
  knowledge;
- one operator question with allowed outcomes.

The operator outcomes are:

- `reuse`: the selected article is the same issue and already covers the
  required knowledge;
- `update`: the selected public article is the same issue but is incomplete,
  outdated, or missing relevant knowledge;
- `none_fit`: the displayed articles do not cover the issue and drafting a new
  candidate may continue;
- `need_more_evidence`: stop without drafting.

For a multi-issue selection, comparison is sequential. The operator sees one
issue and one comparison question at a time, with at most five already selected
items following the existing batch bound.

## Explicit article relation and priority

An article URL in a ticket is not sufficient to give that article priority or
to create a reuse match.

Priority is controlled by accepted ticket evidence:

| Ticket relation | Comparison treatment |
| --- | --- |
| `confirmed_helpful` | retrieve exact context and place the article before search-only candidates |
| `confirmed_partially_helpful` | retrieve exact context and place the article before search-only candidates |
| `confirmed_not_helpful` | do not promote it; retain it only as bounded negative evidence when useful |
| `unconfirmed` or merely mentioned | do not promote it or infer article fit |

`confirmed_helpful` includes evidence that the article resolved the issue.
`confirmed_partially_helpful` means the ticket states that it helped with only
part of the issue.

The relation must come from accepted, source-grounded ticket evidence. Claude
may summarize that relation but cannot upgrade an unconfirmed mention, infer
success from a URL, or assign final priority by itself. Absence of a reported
outcome remains `unconfirmed`.

The existing KCS-15.2b1 explicit-reference priority mechanism is valid only
when its caller has already established `confirmed_helpful` or
`confirmed_partially_helpful`. Other public article mentions must not be passed
as a priority-bearing explicit resolution reference.

## Ownership

Python owns:

- accepted ticket facts and article-relation validation;
- provider readiness, exact-reference request, and evidence acceptance;
- candidate bounds, origin, ordering, and opaque pending state;
- validation of the operator's selected action and candidate;
- construction of `ReuseSearchResultsPacket`;
- final KCS identity/action decision;
- fail-closed, expiry, retry, rendering, and write behavior.

Claude may:

- compare only the bounded ticket facts and accepted public excerpts;
- explain likely coverage and missing knowledge;
- recommend one allowed operator outcome;
- ask the one bounded comparison question.

The operator owns:

- confirmation that an article fits the issue;
- confirmation that it is complete or needs an update;
- rejection of displayed candidates;
- the decision to stop for more evidence.

Claude does not own KCS identity or action. The operator's bounded confirmation
becomes validated input; Python maps it into the existing decision contract.

## Architecture

```text
accepted atomic ticket issue
        |
        v
validated article relation
        |
        +--> exact public context when confirmed helpful/partially helpful
        |
        +--> bounded semantic search candidates
        |
        v
core-owned comparison evidence acceptance
        |
        v
opaque in-memory pending comparison state
        |
        v
Claude presents evidence and recommendation
        |
        v
operator confirms one allowed outcome
        |
        v
Python validates ref + candidate + outcome
        |
        v
ReuseSearchResultsPacket -> existing KCS decision pipeline
        |
        v
reuse / flag existing / create candidate / blocked
```

For a public article, `update` maps to the existing reviewer-controlled
`flag_existing` action. It does not authorize automatic article modification.

## Delivery phases

### Design-process correction applied before Phase A

Status: Delivery complete in committed documentation/policy batch `40d10b2`;
acceptance and review gates passed.

During KCS-15.2b2 Design, the detailed plan would have remained in chat until
the operator explicitly requested a tracked artifact. The operator then
requested a durable rule for future, more autonomous agentic engineering and a
review linkage that prevents Delivery from relying on chat memory.

This process-correction sub-scope is part of the current planning batch:

- make a tracked `slice-plans/` artifact mandatory before Delivery for every
  material feature/slice;
- record selected and authorized phases when approval arrives before the file;
- require material review packets and the default PR template to name the
  Active Slice Plan, authorized phase, locked phases, and plan/diff verdict;
- make a missing plan, locked-phase touch, or material plan/diff mismatch a
  review blocker;
- anchor the rule in existing AGENTS/playbook/review surfaces and policy tests;
- register the generic rule as portability candidate `ENG-PORT-DES-010`;
- do not create a Designer role, orchestration layer, state service, or
  semantic auto-approval mechanism.

Acceptance gates:

| Criterion | Gate |
| --- | --- |
| Material Design is persisted before Delivery and later corrections update it. | deterministic policy anchors across AGENTS and existing playbooks |
| The default material review handoff resolves the Active Slice Plan and exact authorized/locked phases. | deterministic PR-template/protocol shape test plus named reviewer plan/diff verdict |
| Policy automation checks shape without claiming semantic design judgment. | policy-test review and explicit human-review ownership |
| Product runtime, data, Desktop, RAG, packet, persistence, and publication behavior do not change. | diff scope review and full policy suite |
| The rule remains a candidate for future export rather than premature kit/orchestration implementation. | portability registry status review |

Unchanged contracts for this sub-scope:

- all KCS runtime and packet schemas;
- all Desktop tools, prompts, states, and outputs;
- RAG endpoints and adapters;
- data handling, persistence, reviewer bundles, and publication behavior.

### Phase A: exact public article context

Status: Delivery and independent review complete.

Requested outcome:

Provide a deterministic, bounded way for a provider adapter to request public
comparison excerpts for one exact canonical article URL or `source_doc_id`.
This removes probabilistic semantic search from the highest-priority
confirmed-helpful path.

In scope:

- inspect the authoritative `plesk_support` runtime contracts and choose the
  smallest exact-reference read capability consistent with that repository;
- add or extend a read-only local-runtime capability that accepts only an
  allowlisted public Plesk article identity;
- return bounded cited excerpts using the existing public corpus;
- project the exact result through the existing provider-neutral KCS
  comparison contract;
- require URL and `source_doc_id` to identify the same article when both are
  supplied;
- fail closed for absent, stale, deleted, conflicting, unsafe, malformed, or
  oversized context;
- run an exact endpoint/mode/response smoke before substantial integration
  implementation;
- keep semantic search behavior backward compatible;
- update tracked provider/readiness documentation and tests.

Out of scope:

- Desktop tools, schemas, prompts, result text, or workflow state;
- Claude calls, recommendations, or operator confirmation;
- KCS identity, content-status, or action assignment;
- article writes, publication, Zendesk access, corpus ingestion, or indexing;
- credentials, non-loopback transport, hosted RAG, or private/internal
  sources;
- treating an article mention as helpful without accepted ticket evidence.

The exact `plesk_support` endpoint shape is intentionally not prescribed here.
It must be selected after reading that repository's current policy and runtime
contracts. The required capability and safety behavior are fixed; the
provider-specific API shape remains local to its adapter.

Resolved provider design on 2026-07-23:

- `plesk_support` owns a dedicated loopback
  `POST /api/article-snippets` endpoint with
  `knowledge-exact-article-snippets-v1`;
- exact selection is structural rather than semantic:
  `Symptoms`/`Question`, `Cause`, `Resolution`/`Answer`, contiguous solution
  detail, then remaining document order;
- when an approved explicit article is present, the KCS adapter requests at
  most six exact chunks/600 tokens and four semantic chunks/600 tokens;
- the explicit-path semantic request uses one excerpt per article so repeated
  chunks cannot consume the alternative-candidate budget;
- the adapter projects exact chunks into at most two provider-neutral excerpts:
  issue/cause context and resolution/step context;
- the existing core maximums remain unchanged: three candidates, six excerpts
  total, two excerpts per article, and 1200 tokens total;
- without an explicit article, the KCS-15.2b1 semantic request remains six
  excerpts/1200 tokens with its existing per-article cap;
- an exact lookup failure cannot be replaced silently by a semantic hit;
  successful exact evidence remains usable when optional semantic candidates
  are unavailable.

Known safe operational limitation:

- the current adapter maps both an unavailable exact endpoint and an unavailable
  exact article to `explicit_article_context_missing` when semantic search still
  succeeds;
- both cases fail closed and cannot authorize reuse, but Phase B diagnostics may
  later distinguish capability deployment from corpus/article absence without
  changing the Phase A core evidence contract.

Live Phase A feasibility on 2026-07-23:

- the corrected exact endpoint returned six structural chunks/137 tokens for
  one real active public article under the final 600-token exact bound;
- the KCS adapter collapsed them into two provider-neutral excerpts and added
  two distinct one-excerpt semantic candidates;
- the final evidence contained three candidates, four excerpts, and 172 tokens;
- exact article identity, first position, public origins, and the existing
  3-candidate/6-excerpt/1200-token core bounds all passed;
- this is `N=1` feasibility evidence only, not Phase B model/operator stability.

### Phase B: Desktop/operator comparison state

Status: Delivery locked.

Phase B may start only after Phase A closeout and a separate operator approval
of its final Desktop contract.

The current recommended design is:

- the existing draft entrypoints return `reuse_comparison_required` before any
  draft is generated;
- the result contains accepted ticket facts, one to three comparison candidates,
  an opaque `comparison_ref`, and exact allowed outcomes;
- a dedicated narrow submit tool, provisionally named
  `kcs_confirm_reuse_comparison`, accepts the opaque ref, operator outcome, and
  candidate ref when required;
- evidence bodies are retained only in bounded in-memory state and are not
  copied into the submit arguments;
- an expired, mismatched, replayed, or tampered ref requires a controlled
  restart;
- existing batch selections proceed one item at a time and cannot bypass the
  comparison gate.

The dedicated submit tool is provisional until the Phase B design gate. Phase A
does not change the Desktop tool count or approve this name/schema.

### KCS-15.2b3: repeated comparison trial

Status: locked.

One successful Phase B Desktop smoke may prove feasibility only. Recommendation
quality, retrieval stability, operator comfort, correction overhead, and false
positives require a separately approved repeated trial contract.

## Phase A exact-integration smoke contract

Before substantial integration implementation:

```text
Claim: the existing public corpus can return bounded context for one exact
  allowlisted public article identity without relying on semantic rank.
Safe input: one synthetic or known-public Plesk canonical URL/source ID.
Exact condition: selected runtime endpoint, request mode, response schema,
  warmed local runtime, and actual adapter bounds.
Invariants: exact identity match; bounded excerpts; approved public citations;
  no query tail, private path, runtime artifact ID, credential, or unrelated
  article context.
Allowed side effect: existing value-safe local runtime observability only.
Threshold: one compatible response for feasibility.
Failure handling: stop Phase A implementation and revise the provider contract.
Stop condition: first incompatible contract fact or one valid exact response.
```

This smoke does not prove stability, freshness, retrieval quality, or operator
usability.

## Preliminary Phase B model feasibility smoke

This contract is recorded now so model-mediated behavior is not added without
an explicit gate. It must be rechecked immediately before Phase B Delivery.

```text
Fixtures and provenance: one synthetic sanitized atomic issue with a
  confirmed-helpful public article and one search-only candidate.
Trial count: N=1.
Fixed conditions: record the actual Desktop extension build, client version,
  selected Claude model, tool schemas, and local provider state.
Behavioral invariants: explicit helpful article first; bounded evidence only;
  concise coverage/missing-knowledge recommendation; exactly one operator
  question; no draft before confirmation; only an allowed submit action;
  Python action matches the confirmed outcome.
Acceptable variance: wording and concise ordering only.
Threshold: 1/1 with zero critical invariant violations.
Permitted corrections: none inside the run; revise the contract and restart.
Operator overhead: one comparison question, one answer, one submit action.
False positives: zero unsupported article-fit or action claims.
Stop condition: first invariant breach or one successful feasibility run.
```

## Acceptance-to-gate mapping

### Phase A

| Acceptance criterion | Gate |
| --- | --- |
| Exact context is selected by canonical public URL/source ID rather than semantic rank. | deterministic provider tests plus exact live smoke |
| URL and source ID must identify the same article when both are supplied. | deterministic conflict test |
| Only allowlisted public Plesk article context and bounded cited excerpts are returned. | deterministic positive, bounds, and origin tests |
| Missing, deleted, stale, unsafe, conflicting, malformed, or oversized context fails closed. | deterministic negative matrix |
| Existing semantic search and KCS-15.2b1 contracts remain backward compatible. | focused and full regression suites plus behavior-drift review |
| Phase A introduces no Desktop/model/operator or KCS-action behavior. | tool-surface snapshots, policy tests, and architecture/privacy review |
| Provider-specific complexity remains behind the adapter. | compact Ousterhout closeout and architecture review |

### Phase B, not yet authorized

| Acceptance criterion | Gate |
| --- | --- |
| A draft or bundle cannot be created before comparison confirmation. | deterministic workflow tests |
| A URL alone never creates priority, identity, or a partial match. | deterministic positive/negative relation tests |
| Confirmed helpful or partially helpful resolution evidence puts the exact article first. | deterministic priority tests |
| Confirmed not-helpful and unconfirmed mentions are not promoted. | deterministic negative-priority tests |
| Pending evidence, candidate, issue, and operator action remain bound to one opaque ref. | deterministic TTL, replay, mismatch, and tampering tests |
| The four operator outcomes map to existing KCS decisions without giving Claude action ownership. | deterministic decision tests |
| Claude presents bounded comparison evidence and asks one question before continuation. | the predeclared Phase B feasibility smoke |
| Recommendation stability and operator comfort meet an approved threshold. | KCS-15.2b3 bounded repeated trial |

## Unchanged contracts during Phase A

- KCS core remains independent of Claude Desktop and local/remote RAG hosting.
- KCS-15.2a metadata search and KCS-15.2b1 semantic comparison behavior remain
  compatible.
- Desktop-visible tool count, tool arguments, results, instructions, and
  pending workflow states remain unchanged.
- Existing packet and schema versions remain unchanged.
- Claude, operator-selection, KCS action, renderer, reviewer bundle, and
  readiness behavior remain unchanged.
- No raw ticket, query, excerpt, private path, credential, vector, or internal
  runtime artifact is persisted in the KCS repository.
- Reviewer-only, no-customer-reply, no-write, no-publication, and
  `auto_publish_allowed=false` boundaries remain unchanged.

## Resolved Phase A design facts

- The provider uses dedicated `POST /api/article-snippets`, not a search filter.
- Exact identity is derived from the allowlisted canonical URL/source ID and
  remains stable across support-article slug changes.
- Exact chunks are structurally selected and projected into the unchanged core
  comparison bounds.
- The final provider and adapter live smoke passed `N=1`.

## Phase A Delivery closeout

Status: Delivery and independent review complete.

Changed behavior:

- the `plesk_support` provider exposes one strict, loopback-only exact public
  article endpoint;
- the KCS local-public-RAG adapter combines approved exact evidence with bounded
  semantic alternatives while keeping the explicit article first;
- explicit exact-context absence fails closed and cannot be replaced silently
  by a semantic hit.

Validation:

- provider focused endpoint/snippet suite: 90 passed, 5 subtests passed;
- provider local-knowledge regression suite: 482 passed, 1 skipped, 91
  subtests passed;
- KCS adapter suite: 70 passed;
- full KCS suite: 1516 passed, 1 skipped;
- KCS Ruff, configured C901, code-review-graph policy, graph hash, and
  `git diff --check`: passed;
- measured adapter complexity: maximum CC 7, zero functions above the
  configured threshold;
- real-corpus exact provider plus KCS projection smoke: passed at `N=1`
  feasibility only.

Behavior drift verdict:

- intended additive provider endpoint and explicit-reference adapter path;
- semantic-only KCS-15.2b1 requests and provider semantic endpoints remain
  backward compatible;
- no Desktop, Claude, operator state, KCS action, persistence, renderer,
  reviewer-bundle, publication, or observability behavior changed.

Ousterhout closeout:

- Trigger: new provider API plus a cross-repository adapter path for a material
  public-evidence boundary.
- exact identity, structural selection, validation, and provider schema remain
  hidden behind the adapter boundary;
- the provider endpoint and adapter calls are narrow and use existing runtime
  and core contracts;
- complexity was reduced to the repository threshold without adding a new
  framework, hierarchy, service, persistence layer, or observability layer;
- Phase B can consume provider-neutral comparison evidence without learning
  whether RAG is local or later hosted behind another adapter.
- Residual design risk: exact endpoint unavailability and exact article absence
  share one fail-closed KCS status, and provider normalization may leave a
  bounded footer tail after a solution section. Both are documented and
  deferred because neither can authorize reuse or expose private data.
- Verdict: `pass`; no redesign or decomposition is required before Phase A
  closeout.

Review:

- first independent review returned five blockers: request-field allowlisting,
  internal ID exposure, split-solution ordering, old-slug regression coverage,
  and adapter complexity;
- all five corrections are implemented and deterministically covered;
- final independent re-review verdict: `confirmed`; no blockers remain.

## Remaining unknown inventory

- Final Phase B submit tool name and schema.
- Exact Phase B pending-state composition with existing semantic and batch
  state.
- Whether the installed Desktop client reliably presents the comparison as one
  question under the final tool schema.
- Retrieval and recommendation stability across representative tickets.
- Operator comfort and correction overhead during repeated use.

These unknowns are retained for the Phase B/b3 gates and must not expand
Phase A.

## Approval ledger

```text
Parent requested outcome: agreed
Parent target UX: selected
Bounded public excerpt visibility: approved
Helpful/partially-helpful priority rule: confirmed
URL-only priority or partial match: rejected
KCS-15.2b1 Delivery and closeout: complete
Tracked material Design gate correction: Delivery authorized 2026-07-23
Active Slice Plan review linkage: Delivery authorized 2026-07-23
KCS-15.2b2 Phase A exact public context Delivery: complete; independent review confirmed
KCS-15.2b2 Phase B Desktop/model/operator Delivery: locked
KCS-15.2b3 repeated trial: locked
```

## Stop conditions

Stop Phase A and return to Design if it requires:

- raw or private ticket input;
- private/internal article sources;
- credentials or non-loopback transport;
- Desktop, Claude, operator-state, KCS-decision, renderer, or publication
  changes;
- a provider response that cannot guarantee the exact requested article;
- semantic rank being treated as an exact-reference guarantee;
- a new persistence or observability layer beyond existing value-safe runtime
  events.
