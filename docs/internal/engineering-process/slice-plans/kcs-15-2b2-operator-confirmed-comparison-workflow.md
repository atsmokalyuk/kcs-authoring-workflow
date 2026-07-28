# KCS-15.2b2 Operator-Confirmed Comparison Workflow

Status: parent outcome and target UX selected; Phase A Delivery is complete and
the accepted Phase B deterministic implementation is committed in `dbb1b8e`.
Operational closeout remains open. The approved sanitized super-noisy KCS-14.5
canary now accepts five native items and has exercised three installed
comparison decisions. A current-source replay completes the comparison
transition ledger for all five items, but the new boundary correction is not
yet committed, rebuilt, installed, or rechecked in Desktop. Drafting of the
remaining `none_fit` items also reaches existing content-quality gates, so the
parent real-ticket authoring outcome remains open. The generic-chat
entrypoint claim is rejected after installed Sonnet 5 trials bypassed either
the operator decision or the complete KCS tool workflow. Phase C in-chat UI is
host-blocked and deferred because the current Claude Desktop contract exposes
no operator-controlled launcher for the first transition. Details:
`docs/internal/engineering-process/slice-plans/kcs-15-2b2-phase-c-controlled-operator-surface.md`.
The installed Phase C overlay is not accepted as a production path; recovery
returns the production connector to the last proven text-based workflow while
retaining the completed comparison backend and deterministic controller.
KCS-15.2b3 and KCS-15.3 Delivery remain locked until that recovery passes a
fresh end-to-end smoke.

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
- one to three reusable public KCS/KB article links;
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

Entrypoint correction:

- confirmed: once a KCS tool enters the Python workflow, the downstream
  comparison gate can block drafting;
- rejected: an installed MCP tool or tool description can force a generic
  Claude chat response to enter that workflow;
- confirmed: generic Claude chat may bypass the connector entirely through
  host-provided file create/read actions and produce a draft artifact without
  any KCS state, comparison, or operator outcome;
- confirmed: a direct local controller can invoke the Python workflow without
  model-owned tool routing and can collect the operator outcome through its own
  menu before submitting the opaque comparison reference;
- provisional: the local controller is an enforcement skeleton, not the final
  comfortable Desktop UX;
- unknown: which final Desktop-integrated operator surface can retain the same
  direct invocation and human-choice provenance without routing the invariant
  through the model;
- rejected: an MCP prompt, plugin command, slash-like chat text, tool
  description, or one successful model run as proof of deterministic entry.

The generic “draft from this ticket text” chat prompt is not an approved
entrypoint. MCP tools and alternative host tools are model-controlled, so a
zero-KCS-tool answer or direct file artifact occurs outside the Python
enforcement boundary.

### Controlled-entrypoint skeleton

Status: selected and Delivery authorized by the operator on 2026-07-23 after
the enforcement-reachability correction.

Requested outcome:

Prove the complete no-draft-before-comparison route without asking a model to
decide whether to enter the route or to invent an operator confirmation.

Boundary:

- add one small interactive local controller over the existing
  `KcsDesktopMcpAdapter`;
- accept only an existing approved `ticket_ref`; ticket ingestion and raw text
  handling do not change;
- create the production adapter with the existing local public RAG provider and
  call a comparison-only ticket path directly in the same process; this path
  shares extraction/comparison logic but cannot call authoring or bundle
  writers;
- accept only `reuse_comparison_required` or a fail-closed
  `reuse_comparison_blocked` as the first terminal state;
- display only the returned bounded accepted facts, eligible public article
  cards, and cited excerpts;
- collect the closed-enum outcome through the controller's interactive menu,
  collect a displayed candidate only for `reuse` or `update`, and submit both
  directly in the same process;
- refuse any unexpected first result, including a draft or reviewer-bundle
  result, as an invariant violation;
- require interactive stdin/stdout before constructing the production adapter;
  piped or redirected outcome input is rejected;
- bind confirm to the controller's own single-use comparison ref and displayed
  candidate refs, consume that local session on every submit attempt, and
  reject submit-failure or mismatched result packets;
- use a fixture provider first, then the live local RAG preflight; model
  recommendations and final Desktop integration remain outside this batch.

The controller does not create a second authoring workflow or duplicate KCS
decisions. It is a direct owner of entry and operator input around the existing
adapter/state machine. The existing downstream implementation remains the
single owner of evidence validation, TTL/ref checks, action mapping, and draft
continuation after `none_fit`.

Changed contracts:

- one additive local console entrypoint and its bounded text/menu rendering;
- one explicit controller-level invariant for allowed first results;
- one write-incapable comparison-only adapter port and one interactive-terminal
  requirement;
- tracked tool-entrypoint documentation and deterministic controller tests.

Unchanged contracts:

- existing MCP tool names, schemas, result packets, and stdio behavior;
- core reuse-evidence schema and candidate bounds;
- ticket registration/storage, semantic extraction, provider, renderer,
  reviewer bundle, publication, and Zendesk behavior;
- generic Claude chat remains best-effort and outside the deterministic claim;
- KCS-15.2b3 model/recommendation trial remains locked.

Acceptance-to-gate mapping:

| Acceptance criterion | Gate |
| --- | --- |
| The supported controller calls the draft gate directly; no model transition precedes it. | deterministic controller call-order test |
| The first controller path has no author/bundle writer transition and cannot return a draft or reviewer bundle. | comparison-only port tests, deterministic negative invariant test, and fixture integration test |
| `reuse`/`update` require an operator-selected displayed candidate; other outcomes do not. | deterministic interactive input matrix |
| The same controller process retains and consumes its own opaque comparison state once. | fixture integration, invalid-candidate, no-begin, and replay tests |
| Production confirmation cannot be pre-seeded through a pipe. | deterministic non-TTY rejection before adapter construction |
| Blocked, invalid, expired, or unexpected states fail closed without a manual draft fallback. | deterministic negative matrix |
| Existing MCP/Desktop/core contracts do not drift. | focused regression suite, full suite, and behavior-drift review |
| The controller remains a thin composition boundary. | Ousterhout closeout and architecture review |

Only `support.plesk.com` article URLs and legacy `kb.plesk.com` article URLs
are eligible for the operator's `reuse` or `update` comparison cards.
`docs.plesk.com` manuals, release notes, and changelogs may remain public
supporting evidence in the broader RAG corpus, but they are not reusable KCS
articles and must not appear as comparison candidates. The workflow may return
fewer than three candidates when no additional eligible article exists; it
must not fill the list with a documentation page.

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
- deterministic mapping of a validated operator outcome into the existing
  action vocabulary;
- re-entry into the existing decision/drafting pipeline only when the operator
  confirms that none of the candidates fit;
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
        +--> reuse -> reuse_existing, no draft
        |
        +--> update -> flag_existing, no draft
        |
        +--> none_fit -> mark bounded reuse search checked
        |                -> existing decision/drafting pipeline
        |
        +--> need_more_evidence -> blocked, no draft
```

For a public article, `update` maps to the existing reviewer-controlled
`flag_existing` action. It does not authorize automatic article modification.
Phase B does not synthesize a `ReuseSearchResultsPacket`: the provider-neutral
comparison evidence plus the validated operator confirmation are sufficient for
the terminal `reuse`, `update`, and `need_more_evidence` outcomes. Only
`none_fit` re-enters the existing pipeline, carrying the bounded search-run
reference so that the pipeline does not degrade the result to “reuse search
skipped”.

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

Status: downstream Python contract selected and implemented. The earlier
generic-chat entrypoint claim is rejected, so Phase B closeout and its
Desktop/model feasibility gate are blocked behind the controlled-entrypoint
skeleton and a later explicit final-UX selection.

Phase B may start only after Phase A closeout and a separate operator approval
of its final Desktop contract.

The current recommended design is:

- the existing draft entrypoints return `reuse_comparison_required` before any
  draft is generated;
- the result contains accepted ticket facts, one to three comparison candidates,
  an opaque `comparison_ref`, and exact allowed outcomes;
- a dedicated narrow submit tool
  `kcs_confirm_reuse_comparison`, accepts the opaque ref, operator outcome, and
  candidate ref when required;
- evidence bodies are retained only in bounded in-memory state and are not
  copied into the submit arguments;
- an expired, mismatched, replayed, or tampered ref requires a controlled
  restart;
- existing batch selections proceed one item at a time and cannot bypass the
  comparison gate.

Resolved Phase B contract:

- canonical tool name: `kcs.confirm_reuse_comparison`; Claude Desktop alias:
  `kcs_confirm_reuse_comparison`;
- submit arguments are exactly `comparison_ref`, `outcome`, and optional
  `candidate_ref`; `reuse` and `update` require one displayed opaque candidate
  ref. `none_fit` and `need_more_evidence` do not use candidate identity; the
  preferred call omits `candidate_ref`, while a redundant ref is tolerated only
  when it names one of the currently displayed candidates and is then ignored;
- allowed outcomes map deterministically to `reuse_existing`, `flag_existing`,
  normal draft continuation, and `blocked`, respectively;
- the initial result contains bounded accepted issue facts, one to three
  reusable public KCS/KB candidate cards with cited excerpts, one opaque ref,
  the four allowed
  outcomes, and instructions to present one concise coverage/gap recommendation
  and one operator question;
- the submit call never accepts ticket facts, excerpts, URLs, recommendations,
  drafts, HTML, or free-form operator text;
- `PendingReuseComparison` is in-memory only, uses the existing 15-minute TTL,
  and binds the opaque ref to one issue candidate, bounded comparison evidence,
  and any selected batch queue;
- valid submit consumes state once; expired, replayed, mismatched, unknown, or
  tampered input fails closed and requires restarting comparison;
- a comparison bound to an operator selection validates the same live
  `selection_ref`, current item, and selection TTL before any selection state
  is consumed or mutated;
- a multi-item selection stores at most five already operator-selected item
  refs and advances one comparison at a time;
- exact-first priority requires an allowlisted public URL plus explicit
  positive or partially-positive outcome in accepted issue evidence. The
  relation-bearing statement must be present verbatim in the approved source
  text and match a direct article-outcome grammar; semantic candidate prose
  cannot introduce or paraphrase the relation. Neutral mentions, referrals,
  unrelated later fixes, other-scope outcomes, negated/failed outcomes, and
  ambiguous wording do not receive priority;
- only Plesk Support/KB article URLs are eligible for exact-first priority or
  operator reuse/update candidates. `docs.plesk.com` pages remain supporting
  public sources outside this candidate contract;
- `none_fit` is authoritative for the displayed candidates: legacy URL
  inference is suppressed and contradictory public-article delegation steps
  are removed before normal draft continuation;
- provider not-ready, unavailable, invalid, empty, or missing approved-exact
  context blocks drafting instead of treating absence as permission;
- the production Desktop stdio entrypoint owns the initial local provider
  binding; the workflow depends only on `ReuseComparisonEvidenceProvider`.

The operator confirmation on 2026-07-23 approved this downstream contract and
Phase B Delivery. The later instruction to continue under the corrected
enforcement rules authorizes only the controlled-entrypoint skeleton above. It
does not approve a final Desktop UX, the b3 repeated trial, or a hosted
provider.

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

This contract is recorded so model-mediated behavior is not added without an
explicit gate. It was rechecked at Phase B authorization. The deterministic
tool/state contract is implemented first; the installed Desktop/model `N=1`
smoke remains a blocking closeout gate rather than being simulated by fixtures.

```text
Fixtures and provenance: one synthetic sanitized atomic issue with a
  confirmed-helpful public article and one search-only candidate.
Trial count: N=1.
Fixed conditions: record the actual Desktop extension build, client version,
  selected Claude model, tool schemas, and local provider state.
Behavioral invariants: explicit helpful article first; bounded evidence only;
  only reusable Plesk Support/KB articles appear as candidates;
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

### Phase B

| Acceptance criterion | Gate |
| --- | --- |
| Once the Python workflow is entered, a draft or bundle cannot be created before comparison confirmation. | deterministic workflow tests |
| Every supported deterministic entrypoint reaches that Python gate before any draft-capable transition. | controlled-entrypoint call-order and prohibited-first-result tests |
| A URL alone never creates priority, identity, or a partial match. | deterministic positive/negative relation tests |
| Confirmed helpful or partially helpful resolution evidence puts the exact article first. | deterministic priority tests |
| Confirmed not-helpful and unconfirmed mentions are not promoted. | deterministic negative-priority tests |
| Manuals, release notes, changelogs, and other `docs.plesk.com` pages never appear as `reuse`/`update` candidates. | deterministic core rejection, adapter-filter, and explicit-priority tests plus the repeated `N=1` smoke |
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

## Unchanged contracts during Phase B

- KCS core remains independent of Claude Desktop and local/remote RAG hosting.
- The provider-neutral `reuse_comparison_evidence_v1` bounds and validation
  remain unchanged.
- Existing semantic issue-selection and reviewer-only authoring schemas remain
  unchanged except for the additive pre-draft comparison state/tool surface.
- Claude cannot choose KCS actions; it presents bounded evidence and submits
  only the operator-selected closed-enum outcome.
- No ticket, excerpt, recommendation, prompt, or pending-state body is persisted
  or logged.
- No article write, Zendesk write, publication, auto-publish, customer reply,
  or hosted/private source behavior is added.

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

## Phase B downstream Delivery checkpoint

Status: downstream deterministic implementation and independent correction
re-review are complete. End-to-end closeout is not complete: generic Claude
chat bypassed the pre-tool boundary, and the controlled-entrypoint skeleton is
the next authorized batch.

Changed behavior:

- every implemented Python-owned Desktop draft tool path stops at bounded
  public-article comparison before drafting when the production provider is
  bound;
- a narrow single-use submit tool accepts only the opaque ref, closed-enum
  outcome, and candidate ref when required;
- `reuse`, `update`, and `need_more_evidence` are no-draft terminal outcomes;
  `none_fit` suppresses legacy URL inference and returns to normal drafting with
  reuse search marked checked;
- batch selections advance one live, ref-bound comparison at a time;
- public RAG unavailable, not-ready, invalid, or contract-incompatible states
  fail closed.

Deterministic validation:

- full repository suite excluding the two intentionally dirty-worktree
  frozen-path guards: 1566 passed, 1 skipped, 1 deselected;
- final focused core/adapter/Desktop reuse-comparison matrix: 127 passed;
- source MCPB stdio/RAG smoke: all 18 checks passed, including bounded
  comparison, `none_fit` continuation, sequential batch gate, and fail-closed
  provider response;
- Ruff, configured C901, code-review-graph policy/hash, package build,
  `git diff --check`, and independent deep review: passed.

Behavior drift verdict:

- intended additive Desktop tool/state and pre-draft comparison behavior;
- KCS action ownership remains in Python and operator confirmation remains the
  only authority for article fit;
- core evidence bounds, provider-neutral interface, semantic issue selection,
  renderer, reviewer-only output, publication, Zendesk, and persistence
  boundaries remain unchanged;
- comparison eligibility now excludes `docs.plesk.com` supporting pages while
  generic public RAG search still accepts them; legacy KB `/ID` and
  `/locale/ID` URLs share the correct article identity without collapsing
  distinct IDs;
- KCS-15.2b3 repeated recommendation/stability trials remain locked.

Ousterhout closeout:

- Trigger: new pending state, operator tool, provider boundary, and
  cross-entrypoint pre-draft gate.
- the local/hosted provider distinction, public evidence validation, opaque
  refs, TTL, batch sequencing, and action mapping are hidden behind the
  provider/workflow adapters;
- callers see one comparison result and one narrow submit contract; they do not
  learn provider schemas or mutate KCS decisions;
- review found and removed three complexity leaks: legacy URL inference after
  `none_fit`, prose-derived priority without source grounding, and parallel
  selection state mutation without identity validation;
- no new service, persistence layer, framework, or observability layer was
  added; startup/readiness remains owned by the existing loopback public RAG
  runtime;
- Downstream architecture verdict: `pass`; the eligibility rule remains
  centralized in the provider-neutral core and the local adapter reuses the
  core identity key.
- End-to-end entrypoint verdict: `revise`; model-owned routing cannot enforce
  the no-draft invariant or prove human provenance for the submitted outcome.
- Operational feasibility gate: blocked until the controller skeleton passes
  fixture and live-provider gates and a final Desktop UX is separately
  selected.

Independent review:

- initial verdict `revise` identified the three blockers above;
- source-grounded relation and scope/contrast regressions, production
  `none_fit` action regression, and selection interleaving regression were
  added;
- final targeted re-review verdict: `confirmed`; no blocking finding remains.
- the candidate-eligibility correction review then found two blockers:
  localized legacy KB identity was initially mishandled, and the authoritative
  data-handling baseline still admitted docs pages into the comparison lane;
- both were corrected by one core-owned article identity, deterministic
  collision/filter tests, and the aligned data-handling contract;
- the correction re-review found no remaining technical blocker and requested
  this explicit separation between the passing architecture verdict and the
  still-pending operational smoke.

Installed-runtime correction:

- the first manual Desktop attempt on 2026-07-23 is rejected as Phase B
  feasibility evidence because Claude called only built-in `create_file` and
  `present_files`; no KCS Authoring tool was called;
- source and installed manifests proved that Desktop still had the July 21
  six-tool extension while Phase B source had the July 23 seven-tool contract;
- this is classified as `installed_artifact_identity_stale`, not model behavior
  or RAG feasibility evidence;
- `ENG-PORT-DEL-009` and the UI-smoke preflight now report static
  source/package/installed-file/registry identity separately from live runtime
  proof. Prompt handoff additionally requires a post-install Desktop server
  start and a bounded exact-article request against the active RAG instance;
  RAG revision provenance remains provisional when the service cannot
  self-report it;
- the corrected production-like `/draft <ticket_ref>` run selected the fresh
  seven-tool KCS Authoring extension and correctly refused manual drafting, but
  stopped with `explicit_article_context_missing`;
- the same exact public URL returned HTTP 404 from the live
  `POST /api/article-snippets` path: the endpoint exists in committed
  `plesk_support` worktree revision `0fd28fe9`, while the running process came
  from the older `/Users/alex.tsmokalyuk/plesk_support` checkout without that
  route;
- generic RAG status, search, and `/api/snippets` health therefore did not
  establish the exact dependency capability or running revision required by
  Phase B. `ENG-PORT-DEL-009` now includes cross-repository process provenance
  and same-instance exact-capability evidence;
- after the exact-context worktree served the same local public index, the
  same-instance endpoint probe returned four bounded excerpts and the repeated
  `/draft` run presented the explicit partially-helpful article first, three
  comparison candidates, a grounded `none_fit` recommendation, exactly one
  allowed-outcome question, and no draft;
- the run also exposed one target-UX violation: Claude rendered candidate
  titles without clickable public links. The result proves the main control
  flow feasible but does not satisfy the `1/1` zero-critical-violation
  threshold;
- the existing comparison presentation contract now explicitly requires every
  title to be a clickable Markdown `public_url` link with visible
  `candidate_ref`;
- after rebuild/reinstall, the fresh `/draft` run displayed three clickable
  public article titles with their visible candidate refs, kept the
  confirmed-partially-helpful exact article first, explained the coverage gap,
  recommended `none_fit`, and asked exactly one question using only the four
  allowed outcomes. No draft was created;
- this final presentation sub-gate passes;
- after the operator selected `none_fit`, the same live Desktop server received
  two submit calls three seconds apart without a process restart or TTL expiry.
  The second call returned `reuse_comparison_unavailable`, which proves that the
  first call consumed the pending state. The value-safe Desktop logs do not
  retain submit arguments, so whether the first call carried a redundant
  candidate ref remains provisional;
- deterministic behavior shows that the likely first-call shape would be
  rejected and consume state even though the extra value is one of the bounded
  displayed refs and cannot affect a candidate-free outcome. The contract is
  corrected to tolerate and ignore only such a known redundant ref; unknown
  refs and every behavior-bearing mismatch remain fail-closed;
- after rebuild/reinstall, the restarted comparison presented the same bounded
  three-candidate decision, accepted the operator's `none_fit`, and generated
  reviewer-only bundle `run-20260723T151344-DbrmKoSy`;
- the final result reported `none_fit` confirmed, a new candidate ready for
  reviewer sign-off, `public_output_approved=false`, and no publication. The
  tool surfaced one informational missing-reference gap and one unbolded-GUI-path
  warning for later reviewer work rather than bypassing quality review;
- the operator then identified that one displayed item was a
  `docs.plesk.com` changelog rather than a reusable KCS article. That run proves
  the control flow feasible but does not satisfy the final `1/1` threshold;
- the candidate contract is corrected to exclude `docs.plesk.com` pages while
  leaving them available to the broader public RAG corpus as supporting
  evidence. A corrected installed Desktop/model run is required before Phase B
  closeout;
- a subsequent free-form raw-ticket prompt is rejected as feasibility
  evidence: the refreshed KCS Authoring server had initialized and listed its
  tools, but Sonnet 5 returned a manual article without any KCS tool call. This
  bypassed the entire comparison workflow and is a critical invariant
  violation, not a RAG/filter result;
- a later installed-client run confirmed a second bypass route: Claude used
  host-provided file create/read actions, generated one combined Markdown
  article for two distinct issues, and never established KCS item-selection or
  comparison state. The visible text then referred to a selection widget that
  did not exist. The fail-closed KCS tool result prevented a KCS-owned
  confirmation, but extension code could not prevent the separate host file
  action;
- the corrected closeout run must use the direct
  `kcs-controlled-draft <ticket_ref>` entrypoint. A text `/draft` command and a
  generic “draft from this text” chat prompt remain model-mediated unless a
  later host-level design can bind them directly to KCS Authoring;
- the safe handling of a redundant displayed candidate ref for `none_fit` and
  `need_more_evidence` is a delegated technical implementation choice: ignore
  the known displayed ref, but continue to reject an unknown ref.

## Controlled-entrypoint skeleton checkpoint

Status: implementation and fixture-first validation complete. One live
controller-begin feasibility check passed. Final Desktop UX and KCS-15.2b3
remain locked.

Changed behavior:

- `kcs-controlled-draft <ticket_ref>` creates one production adapter process
  with the approved local public RAG provider and directly calls a
  comparison-only ticket path that cannot invoke authoring or bundle writers;
- the controller refuses to call the tool when comparison is disabled and
  rejects any first result that reports a draft, reviewer bundle, file write,
  or a result other than comparison-required/comparison-blocked;
- the CLI displays bounded accepted facts and reusable public article cards
  before reading an outcome; there is no `--outcome` argument;
- production confirmation requires interactive stdin/stdout before the adapter
  is constructed; piped or redirected choices fail closed;
- `reuse` and `update` require a displayed article selection;
  `none_fit` and `need_more_evidence` submit no candidate identity;
- the controller binds confirmation to the ref and candidate refs retained by
  its own `begin`, consumes them on every submit attempt, validates the shared
  authoritative outcome enum and tool-result schema, and rejects expired,
  replayed, failed, mismatched, or unexpected result packets;
- non-`none_fit` outcomes are checked for zero draft, bundle, and file writes;
  `none_fit` requires the expected authoring result, no-publication flags, and
  a matching comparison outcome ledger;
- terminal display adds a separate 600-character, single-line fact/excerpt
  projection bound without changing retained core/provider evidence.

Deterministic validation:

- new controller/CLI suite after enforcement corrections: 28 passed;
- controller plus touched authoring/comparison regression matrix: 72 passed;
- focused comparison/provider/core matrix: 145 passed;
- Desktop transport/MCP/package matrix: 249 passed;
- engineering-process and code-review-graph policy: 20 passed;
- package/policy correction matrix after withdrawing the generic-chat claim:
  73 passed;
- full repository suite: 1590 passed, 1 skipped, 1 intentionally deselected
  frozen-path dirty-worktree guard;
- full Ruff, touched-file Ruff, `git diff --check`, console help, and graph
  hashes: passed;
- production source complexity for the controller/CLI: maximum CC 6, zero
  functions above the configured threshold.

Live feasibility:

- input: existing approved local
  `ticket_ref=kcs15-phase-b-smoke-20260723`;
- entry: direct `kcs-controlled-draft --preflight`, no Claude prompt or model
  routing;
- active local RAG returned three eligible Plesk Support article candidates;
- the first post-review preflight exposed one adapter/runtime mismatch: the
  live RAG assigns `candidate_rank` per retrieved chunk, so two excerpts from
  one article may have different ranks. The adapter had incorrectly required
  one shared rank per article and failed closed with
  `comparison_provider_invalid_response`;
- the grouping contract now orders an article by its earliest returned chunk
  rank while still requiring matching source ID, URL, title, status, and
  updated metadata across that article's excerpts. A deterministic regression
  fixture reproduces the live response shape;
- the same live preflight then passed with three reusable Plesk Support
  candidates; the `docs.plesk.com` changelog returned by RAG was excluded;
- the first result displayed comparison evidence and the four closed-enum
  choices with no draft or reviewer bundle;
- preflight returned success after the comparison-only path; it has no outcome
  input and made no confirm or authoring call;
- the first output exposed overly long public snippets; the controller display
  projection was bounded and the same live begin check was repeated;
- this is `N=1` entry/comparison feasibility only. It does not prove final UX,
  recommendation quality, repeated retrieval stability, or operator comfort.

Behavior drift verdict:

- intended additive local controller and console entrypoint;
- existing MCP tools, schemas, aliases, stdio transport, comparison state,
  action mapping, ticket store, reviewer bundle, renderer, publication, and
  Zendesk behavior remain unchanged;
- the package documentation no longer claims that generic chat or text
  `/draft` deterministically enters KCS tools;
- the controller does not ingest pasted/raw tickets and does not add a model,
  provider schema, state store, service, framework, or observability layer.

Ousterhout closeout:

- Trigger: new operator-facing composition boundary around a material
  no-draft invariant.
- the controller exposes two operations, `begin` and `confirm`, and delegates
  semantic extraction, evidence collection, pending state, ref/TTL validation,
  KCS action mapping, and authoring to the existing adapter;
- the CLI owns only bounded rendering and the local operator menu;
- the comparison-only port is a mode of the existing draft orchestrator and
  reuses its extraction/comparison code; it does not expose a second engine;
- there is one production provider composition root and no duplicate workflow
  engine or persistence;
- source complexity remains below the repository threshold;
- residual risks: final Desktop integration is unknown, the current adapter
  has one pending comparison slot, and bounded accepted-fact quality still
  needs later UX evidence;
- Verdict: `pass` for the controller skeleton. This does not close Phase B or
  authorize final Desktop/model integration.

## Closeout separation boundary

The post-`0233214` worktree contains multiple independently gated batches.
Closeout and review must preserve this separation.

Accepted KCS-15.2b2 controller/correction batch:

- centralized reusable KCS article eligibility and legacy KB identity;
- exclusion of `docs.plesk.com` pages from reuse/update candidates;
- safe handling of a redundant displayed candidate ref for candidate-free
  outcomes while unknown refs still fail closed;
- comparison-only first transition in `DesktopDraftArticleTool` and
  `DesktopAuthoringTools`;
- `KcsDesktopMcpAdapter.reuse_comparison_enabled` and
  `begin_operator_reuse_comparison`, without MCP App registration;
- the direct `OperatorAuthoringController`, interactive CLI, console
  entrypoint, focused tests, and their bounded operator documentation.

Separate process/documentation batch:

- Design uncertainty, enforcement reachability, operational feasibility,
  runtime identity, Ousterhout, and portability rule changes;
- their policy tests and cross-document status alignment.

Deferred Phase C batch:

- MCP App resources, app-only tools, production operator-surface controller,
  UI source/build output, package-data inclusion, and App-specific tests;
- `resources/list`/`resources/read` transport behavior, App request `_meta`,
  App capability negotiation, App-only model-selection rejection, and
  App-linked tool metadata;
- production prompt/descriptor routing changes, MCPB/App build packaging, and
  installed Desktop UI-smoke automation.

Mixed files must be reviewed or staged by hunk. In particular:

- `src/kcs_adapters/desktop_mcp_adapter.py`: retain only the direct-controller
  property/begin method in the accepted batch;
- `pyproject.toml`: retain only the `kcs-controlled-draft` console entrypoint;
- `README.md`, `docs/internal/engineering-process/tool-entrypoints.md`, and
  this plan: retain controller/status evidence while leaving Phase C build and
  active-UX claims out of the accepted runtime batch;
- package, stdio transport, protocol, resource, and UI changes remain deferred
  unless a later host capability reopens Phase C.

Do not use a whole-worktree test result as proof of the separated accepted
batch. Before commit, review the staged diff against this boundary and run the
focused controller/core/provider tests plus the unchanged Desktop regression
surface from a state that does not require deferred App files.

## Production text-recovery smoke checkpoint

Status on 2026-07-24: the recovery package without the deferred Phase C App
surface completed the core two-item workflow in Claude Desktop. The workflow
result is accepted as live feasibility evidence; one deterministic handoff
defect and one candidate-eligibility follow-up remain open.

Observed path:

- exact entrypoint: `/draft ticket-2a5274b2bdcd`;
- Python returned two independent KCS items before drafting;
- the operator selected both items through the text contract;
- each selected item reached its own bounded reuse comparison;
- the operator confirmed `none_fit` for both items;
- two reviewer-ready, non-public drafts were written:
  - `issue-001`:
    `local-data/reviewer-bundles/run-20260724T002415-lN5r-oXo/manifest.json`;
  - `issue-002`:
    `local-data/reviewer-bundles/run-20260724T002505-uCzHJmhd/manifest.json`;
- both manifests and their reviewer HTML hashes were verified against the
  local files under `~/Documents/KCS Authoring`;
- `auto_publish_allowed=false` and `public_output_approved=false` remained
  unchanged.

Detected handoff defect:

- the final Claude response named only the second manifest even though Python
  retained both ordered `comparison_sequence_outcomes`;
- root cause: model-visible tool-result text projected only the current
  comparison/current authoring result and omitted the completed sequence;
- bounded correction: every sequence ledger entry now carries its
  `bundle_ref`, `manifest_path`, and `html_path`; the next comparison text must
  show already completed item results, and final authoring text must show the
  complete ordered sequence;
- deterministic regression gate: intermediate and final projections must
  include all artifact refs in item order for both normal and inline-HTML tool
  results;
- focused validation after the correction: 240 tests passed, Ruff passed, and
  `git diff --check` passed;
- installed-client repetition of this exact handoff projection passed on
  2026-07-25: the final Claude response listed both ordered bundle refs and
  reviewer HTML paths.

Separate retrieval-quality follow-up:

- one comparison included a public Plesk Support article whose title is marked
  `[Incident]`;
- it was not selected and did not affect either `none_fit` decision;
- operator decision: incident notices are not reusable KCS articles and must
  not appear as `reuse`/`update` comparison candidates;
- requested outcome: the operator sees only reusable article choices, without
  spending attention rejecting transient incident notices;
- selected boundary: a bounded, case-insensitive leading `[Incident]` title
  marker is ineligible at the provider-neutral candidate contract and is
  filtered before local-adapter ranking/reindexing;
- unchanged contracts: the public RAG corpus and generic search remain
  unchanged; remaining candidate order, three-candidate bound, URL eligibility,
  explicit confirmed-helpful priority, operator outcomes, drafting,
  reviewer-only output, and publication safety remain unchanged;
- deterministic acceptance gates:
  - core construction rejects an incident-marked reuse candidate;
  - the local adapter removes incident-marked search results and reindexes the
    remaining reusable articles;
  - an all-incident search result becomes `comparison_no_evidence`, not a
    provider failure;
  - the repeated live ticket smoke no longer shows the observed incident page;
- validation before package rebuild:
  - active relevant matrix: 402 tests passed;
  - isolated package matrix: 380 tests passed;
  - Ruff and `git diff --check` passed in both snapshots;
  - a write-incapable live RAG query for the observed monitoring symptom
    returned three reindexed support articles and no incident-marked page;
- recovery package:
  `/private/tmp/kcs-authoring-recovery-incident-filter.mcpb`;
- package SHA-256:
  `750faba5879ab29816d666493c69d83f7aab4f50ed28759c3cdb09cfa5f6caa5`;
- packaged and installed-path stdio smokes each passed all 17 checks with the
  seven-tool production surface; installed files matched a fresh archive
  extraction and the prior connector process was stopped;
- the installed package then repeated the write-incapable live RAG query and
  returned the same three reindexed non-incident support articles;
- the 2026-07-25 installed Desktop repetition selected both ticket items and
  showed no incident-marked candidate. Issue one used three non-incident
  support articles, item two remained sequenced correctly, and two ordered
  reviewer bundles were written:
  - `run-20260725T174718-tV6zkAi-` for `issue-001`;
  - `run-20260725T174747-B9XDHbh7` for `issue-002`;
- both new manifests and reviewer HTML hashes were verified; both remain
  reviewer-only with `auto_publish_allowed=false` and
  `public_output_approved=false`;
- Ousterhout gate: `not triggered`; this is a leaf policy extension inside the
  existing centralized candidate-eligibility owner and adds no interface,
  state, dependency, service, persistence, or cross-module abstraction;
- deferred boundary: if a future accepted ticket explicitly says an incident
  notice resolved the issue, its supporting-evidence treatment requires a
  separate design decision; this correction does not turn it into a reusable
  article.

Duplicate-submit operational defect:

- in the next installed-client run, Sonnet 5 submitted the first
  operator-confirmed `none_fit` twice, about three seconds apart, before the
  first tool result returned;
- the first call succeeded and wrote
  `run-20260724T015108-Ll5COMAu` for
  `issue-1-monitoring-no-data`;
- the first call also advanced Python to the second pending comparison, but the
  queued duplicate retained the old comparison ref. The old ref was treated as
  invalid and consumed the newer pending state, so Claude displayed a false
  batch-stop result even though the first bundle existed;
- bounded correction: retain one ephemeral, TTL-bound successful comparison
  result. An equivalent duplicate replays that result without another author
  call or bundle write; a changed outcome/candidate remains invalid; a stale
  prior ref cannot clear the newer pending comparison;
- deterministic regression reproduces `none_fit -> next comparison -> duplicate
  old none_fit`, checks one author call, stable replay, conflicting replay
  rejection, preserved next ref, and successful continuation to the second
  item;
- this evidence produced portable candidate `ENG-PORT-DEL-010`;
- installed-client repetition passed on 2026-07-25. Claude submitted the first
  `none_fit` twice at `17:33:23` and `17:33:26`; the duplicate replay did not
  write another bundle or consume item two. The second item remained active,
  accepted its own `none_fit` at `17:34:10`, and the batch completed.

Recovery artifact evidence:

- active-worktree focused gate: 308 tests passed; Ruff and
  `git diff --check` passed;
- isolated seven-tool package snapshot: 286 tests passed; Ruff and
  `git diff --check` passed;
- recovery package:
  `/private/tmp/kcs-authoring-recovery-duplicate-replay.mcpb`;
- package SHA-256:
  `73842304cde8dc60b3a92403d667ac5b1d4871737c7461910a39362761b6115d`;
- the manifest exposes exactly seven production tools and contains no Phase C
  App/UI resources;
- the first packaged stdio smoke stopped at
  `comparison_provider_unavailable` because no process was listening on the
  required loopback RAG port. The package was not installed from that state;
- the authoritative `plesk_support` runtime entrypoint then started the
  current 6,150-article/35,695-chunk service with current keyword/vector cache
  and `ready_for_runtime_lookup=true`;
- the same unpacked package passed all 17 stdio checks against that live
  dependency;
- installed files were byte-for-byte identical to a fresh package extraction,
  and the prior connector process was stopped so the next Desktop invocation
  must load the installed artifact;
- the installed-path stdio smoke then passed the same 17 checks with
  `tool_count=7` and registry-cache verification enabled;
- the live run wrote exactly two ordered reviewer bundles:
  - `run-20260725T173324-g_56bSxo` for `issue-001`;
  - `run-20260725T173411-skSHbxuY` for `issue-002`;
- both manifests report `recommended_action=create_candidate`,
  `reuse_search_status=checked`, `ready_for_reviewer=true`,
  `auto_publish_allowed=false`, and `public_output_approved=false`; both
  reviewer HTML hashes match their manifests;
- this readiness interruption is additional local evidence for
  `ENG-PORT-DEL-009`: source/package tests did not authorize installation until
  the exact dependency service was live on the instance used by the package
  smoke.

Ousterhout closeout for the duplicate-submit correction:

- Trigger: the correction adds ephemeral state to a side-effecting continuation
  boundary.
- Complexity hidden: callers do not need to detect host retries, serialize
  equivalent submits, or know whether the first submit already advanced the
  workflow.
- Owner: `DesktopDraftArticleTool` owns one TTL-bound replay record; core
  comparison logic, RAG, rendering, and reviewer bundles remain unaware of it.
- Interface depth: the existing comparison ref, outcome, and candidate-ref
  contract is unchanged, while equivalent duplicates receive the same
  successful result without another author call or artifact write.
- Leakage and change amplification: no persistence, service, schema, or
  cross-module retry protocol was added. Only the last completed comparison is
  replayable, and a process restart still fails closed.
- Complexity verdict: the host race is absorbed at its narrow state owner
  instead of being moved into prompts or downstream workflow components.
- Residual risk: replay is process-local and intentionally bounded; durable
  multi-process idempotency remains outside this slice.
- Verdict: `pass`.

## Delivery Process Failure Audit

Status: recorded on 2026-07-25; both findings keep KCS-15.2b2 closeout open.

### Premature repository closeout

Confirmed evidence:

- the plan's closeout separation boundary requires hunk-level isolation,
  staged review, focused validation from the accepted boundary, and a commit;
- at the time of the finding, the accepted runtime and process changes were
  still mixed with deferred Phase C files and remained uncommitted;
- package and installed-client smokes were useful pre-commit implementation
  evidence, but were described as if the repository slice were complete.

Verdict: agent deviation from the existing plan and Git/Delivery discipline.
The plan already contained the required boundary. The missing higher-level
guard was an explicit rule that pre-commit or mixed-worktree operational
success remains provisional and cannot authorize the next material slice.
That gap is now tracked as `ENG-PORT-DEL-011`.

### Parent operational outcome not exercised

Confirmed evidence:

- the recorded Phase B smoke contract names one synthetic sanitized atomic
  issue and correctly limits `N=1` to feasibility;
- KCS-14.5 records that fixed synthetic stages do not prove routine
  real-ticket semantic stability or yield;
- the installed KCS-15.2b2 runs used constructed two-item ticket data;
- the approved sanitized super-noisy KCS-14.5 case was not run through the
  recovered `/draft <ticket_ref>` workflow.

Verdict: both a plan defect and an agent deviation. The tracked KCS-15.2b2
acceptance mapping failed to carry the parent super-noisy canary forward as a
named closeout gate. The agent then failed to reconcile the narrow synthetic
plan with the parent requested outcome and overstated completion instead of
narrowing the claim. This gap is now tracked as `ENG-PORT-DEL-012`.

Corrected evidence claims:

- confirmed: deterministic contracts, two-item sequencing, comparison
  decisions, duplicate replay, incident filtering, reviewer-only output, and
  no-publish behavior passed the recorded synthetic/installed gates;
- confirmed: the accepted runtime boundary was isolated without Phase C,
  passed 360 focused tests and 1,601 pre-commit tests, and was committed as
  `dbb1b8e`;
- provisional: the committed diagnostic correction can be packaged and
  installed without artifact or runtime identity drift;
- unknown: the exact second semantic validation cause for the approved
  sanitized super-noisy KCS-14.5 case under the committed diagnostic build;
- rejected: KCS-15.2b2 is complete, or the KCS-14.5 real-ticket problem is
  resolved, based only on the current synthetic runs.

Required closeout gates:

1. passed: isolate and review the accepted KCS-15.2b2 diff without deferred
   Phase C;
2. passed: focused and unchanged-contract gates from that isolated content;
3. passed for source: commit `dbb1b8e`; still required for runtime: rebuild and
   map the installed artifact to that commit;
4. after the committed diagnostic build is installed, run the approved
   sanitized super-noisy KCS-14.5 canary through the supported
   `/draft <ticket_ref>` entrypoint with the existing reviewer-only,
   no-publish, fail-closed, and bounded operator-decision invariants;
5. record `passed`, a specific bounded blocker, or a narrowed residual claim.

### Super-noisy representative canary result

Status on 2026-07-25: failed before native item selection and before the
KCS-15.2 reuse-comparison workflow.

Observed value-safe result:

- supported entrypoint: `/draft ticket-94893302`;
- the semantic proposal identified five issue identities, matching the approved
  ticket-level canary scope recorded by KCS-14.5;
- the first semantic submission failed an observation-shape contract and
  consumed the single bounded correction;
- the corrected second submission failed validation and terminated as
  `semantic_issue_submission_invalid` with no next action;
- no item selection, public-article comparison, draft, reviewer bundle, or
  publication action followed.

Interpretation:

- this is a valid failed representative-case gate, not a transient result and
  not permission for an unchanged retry;
- the KCS-15.2 comparison workflow cannot improve this ticket while the
  upstream semantic proposal does not pass submission validation;
- the five-identity result does not itself indicate over-splitting: KCS-14.5
  records five as the approved ticket-level canary scope;
- the current result does not expose the exact second validation cause because
  the correction-budget terminal path replaces a second bounded validator code
  with the generic terminal code.

Bounded diagnostic correction:

- preserve the existing primary `semantic_issue_submission_invalid` code,
  single-correction budget, terminal state clear, no-retry instruction, and
  fail-closed behavior;
- add only `terminal_cause_debug_code`, selected from existing bounded
  validator codes, to the structured result, review summary, output schema,
  and compact tool text;
- unknown/uncontrolled exception causes remain
  `semantic_review_submission_invalid`;
- do not expose submitted values, source refs, evidence text, ticket content,
  model prose, paths, or raw exceptions;
- deterministic regression: one correctable coverage error followed by a
  different top-level source-ref error ends with the unchanged generic primary
  code, no correction or next action, and the exact bounded terminal cause;
- focused validation: 239 Desktop/semantic contract tests passed.

Ousterhout gate: `not triggered`.
Reason: this is an additive value-safe diagnostic field on the existing
semantic-submit failure owner. It adds no state, retry, semantic decision,
workflow transition, dependency, persistence, or service boundary.

The diagnostic correction is committed in `dbb1b8e`, included in the clean
closeout chain through `8e17adf`, packaged, installed, and verified through the
installed-wrapper smoke. The active local RAG dependency was also corrected
from the stale main-checkout process to the committed exact-context source
`0fd28fe9`; current status and the exact `POST /api/article-snippets`
capability passed on the same active loopback instance.

### Representative canary continuation defect

The noisy canary accepted five items and opened the first comparison, but
`need_more_evidence` stopped the whole batch instead of advancing to item two.
No draft or reviewer bundle was written. The implementation had excluded that
outcome from the existing batch-advance path, contrary to the sequential batch
contract. The bounded fix removes that exception and parameterizes the existing
batch-transition test for both `reuse` and `need_more_evidence`.

Ousterhout gate: `not triggered`; no interface, owner, dependency, persistence,
or public schema changes.

### Repeated semantic-submit correction failure

The next fresh noisy canary again stopped before item selection:

- the first five-item submission returned
  `semantic_observation_shape_invalid`;
- Claude corrected one apparent field, but a second submission returned the
  same terminal cause and exhausted the one-use correction;
- no comparison, draft, bundle, or publication action occurred.

This repeated the earlier upstream failure already recorded in this plan. The
implementation exposed one shared code for every observation field, while the
single correction described only the general contract. Tests covered one
malformed field followed by a valid packet, not multiple malformed fields in
one model-generated packet. Continuing after one intervening successful canary
treated feasibility as stability and missed `ENG-PORT-DES-001` and
`ENG-PORT-DEL-006`.

Requested outcome: one validation pass identifies every structurally invalid
observation field so the existing single correction can repair the whole
packet. Only bounded paths such as `issues[0].summary` may be returned; submitted
values, ticket text, source refs, and raw exceptions remain hidden. The retry
budget, fail-closed terminal behavior, semantic ownership, and all downstream
contracts remain unchanged.

Initial acceptance gate: a deterministic multi-error packet returns all invalid field
paths in one correction, succeeds after correcting them, and still permits no
second correction. Operational stability then requires three fresh identical
installed-client runs of `/draft ticket-94893302` to reach native item selection
without terminal semantic shape failure.

The first installed run on `62620a0` passed the structural correction but then
stopped on the independent grounding validator with
`semantic_observation_text_not_extractive`. This is failed N=1, not a retryable
ticket result. It proves that one global correction budget is the wrong boundary
for a staged validator: a valid structural correction can reveal a separate
grounding defect.

Revised bounded contract:

- one structural correction may be followed by one grounding correction;
- the same correction stage cannot repeat, grounding cannot reopen structure,
  and the total remains capped at two;
- non-extractive feedback lists only invalid observation field paths, never
  submitted text, source refs, excerpts, or raw exceptions;
- all terminal, no-manual-draft, no-write, and downstream contracts remain
  unchanged.

Deterministic gate:
`invalid structure -> corrected structure plus invalid grounding -> corrected
grounding -> normal continuation`; repeated structure or grounding remains
terminal.

The next installed N=1 still terminated on repeated
`semantic_observation_shape_invalid`. The first correction exposed
`summary`, but the shape collector only checked that nested `source_refs` was
a list. Core validation also requires non-empty, unique refs and enforces
observation count/text-size limits; unsafe ref/value classes remain separate
terminal safety errors. Those deeper structural constraints could therefore
surface only after the first correction. This was an implementation and test
parity defect in `62620a0`: the acceptance fixture covered multiple shallow
shape failures, not nested structural constraints already owned by core.

Bounded correction: make the existing path collector reuse the core observation
parser for structural constraints while preserving separate safety/ref
classification, and tell the model to correct every listed path while
preserving unlisted fields. Retry counts, stage order, semantic authority,
fail-closed behavior, and downstream contracts do not change. This occurrence
adds evidence to `ENG-PORT-DES-001` and `ENG-PORT-DEL-006`; it does not justify
another process rule.

### Operator-steered semantic boundary correction

Status: target UX selected and Delivery authorized by the operator on
2026-07-26. This is a bounded KCS-15.2b2 sub-slice. It does not attempt to make
automatic semantic partitioning perfect for every super-noisy ticket.

Requested outcome:

When the proposed KCS-item list misses or incorrectly merges a separately
searchable problem, the operator can name the missing boundary in the native
selection interaction. The operator does not have to reconstruct the semantic
proposal, provide source references, or diagnose why extraction missed it.

Operational baseline:

- the semantic review packet already contains bounded sanitized excerpts and
  Python validates every proposed observation against those excerpts;
- after a valid multi-item semantic submission, Python currently clears the
  semantic packet and accepts only one existing item or all existing items;
- Claude Desktop may show a host-provided `Something else` response, but the
  current KCS tool contract cannot safely amend the Python-owned item set from
  that response;
- the installed super-noisy canary demonstrated this gap by returning four
  selectable items while the operator identified an invalid-IP binding issue
  as a separate fifth boundary;
- improving the automatic splitter for this individual ticket is rejected as
  disproportionate complexity.

Selected target UX:

1. Python returns the validated candidate list and native selection options.
2. If the operator accepts the list, the existing single/all selection path is
   unchanged.
3. If the operator says that a problem was missed or merged, Claude may submit
   one complete amended semantic proposal through the existing semantic-submit
   tool, bound to both the original semantic-review ref and current
   operator-selection ref.
4. The operator's prose is steering context only. It is not accepted as ticket
   evidence, persisted, logged, or echoed by Python.
5. Python validates the amended proposal against the same prepared excerpts,
   source-ref allowlist, observation bounds, safety rules, and maximum of five
   candidates.
6. A valid amendment atomically replaces the pending item list and returns a
   fresh selection ref. Drafting and reuse comparison remain blocked until the
   operator chooses from that revised list.
7. An invalid amendment leaves the previous selection usable while following
   the existing bounded structural/grounding correction rules. A second
   operator-requested amendment is not available.

Deterministic owner and enforcement reachability:

```text
operator free-text steering in Claude Desktop
  -> model-controlled amended semantic proposal
  -> kcs_submit_semantic_review with existing review + selection refs
  -> Python verifies pending refs and one-amendment budget
  -> existing Python semantic contract and extractive evidence validators
  -> atomically replaced Python-owned selection, or fail-closed correction
```

The first transition remains model-mediated. The deterministic claim begins at
the semantic-submit tool boundary: no operator prose becomes evidence and no
unvalidated candidate becomes selectable or draftable.

Changed contracts:

- `kcs_submit_semantic_review` accepts optional
  `operator_selection_ref` only for one amendment of an already accepted
  multi-item semantic result;
- split-required results expose a bounded
  `operator_boundary_correction` instruction containing only opaque refs,
  submit-tool identity, availability, and limits;
- successful amendment returns a new selection ref and consumes amendment
  availability.

Unchanged contracts:

- initial semantic preparation, proposal schema, excerpt selection, source-ref
  allowlist, safety validation, item limit, and candidate projection;
- normal single-item/all-items selection and sequential batch behavior;
- RAG retrieval, reuse outcomes, article drafting, renderer, reviewer bundle,
  local storage, publication, and Zendesk behavior;
- `auto_publish_allowed=false`, `public_output_approved=false`, and no manual
  draft fallback;
- operator prose is not a new evidence or persistence source.

Acceptance-to-gate mapping:

| Acceptance criterion | Gate |
| --- | --- |
| A valid first multi-item submission exposes one amendment instruction bound to the active semantic and selection refs. | deterministic MCP schema/result test |
| One amended proposal grounded in the same excerpts replaces the old list and returns a fresh selection ref before drafting. | deterministic workflow transition test |
| Operator prose is neither required in tool arguments nor stored, echoed, logged, or projected as evidence. | deterministic schema/privacy assertions and human privacy review |
| Unknown, stale, mismatched, single-item, or already-consumed selection refs cannot amend the list. | deterministic invalid-state matrix |
| Invalid amended proposals use the existing bounded validation correction path and do not destroy the old selection. | deterministic fail-closed regression |
| A second operator amendment is rejected; duplicate/re-entrant calls cannot replace a newer selection. | deterministic one-use/replay matrix |
| Existing selection, reuse, drafting, bundle, and publish-safety contracts do not drift. | focused regression, full suite, and behavior-drift review |
| The installed Desktop surface lets the operator steer one missed boundary and then choose from the revised list. | bounded-model trial, synthetic five-item fixture, `N=1` feasibility; no stability claim |

Trial contract:

- fixture and provenance: synthetic sanitized noisy ticket with four proposed
  items and one evidence-backed merged/missed boundary;
- `N=1`;
- fixed client/model conditions: installed current KCS Authoring package in
  Claude Desktop; client/model identity recorded at trial time;
- invariants: one amendment maximum, same excerpts, no operator prose in
  evidence, revised native selection before any reuse search or draft;
- acceptable variance: wording and issue labels may vary while the missed
  boundary remains separately selectable;
- threshold: the single feasibility run satisfies every invariant;
- permitted corrections: existing one structural stage followed by one
  grounding stage; no second operator amendment;
- overhead: one operator steering response plus the revised selection;
- false positives: zero ungrounded selectable candidates;
- stop condition: any draft/reuse action before revised selection, lost
  previous selection after invalid amendment, private-text echo, or need for a
  new UI/runtime service.

Ousterhout gate: `reviewed`.
Trigger: additive stateful tool contract and semantic-selection transition.
Complexity hidden: one-use amendment state, ref binding, atomic replacement,
and reuse of existing semantic validators.
Owner and what it must not know: Desktop workflow owns the amendment lifecycle;
core semantic contracts must not know about Claude Desktop UI or operator
selection.
Interface depth and caller cognitive load: Claude submits the same full
semantic proposal plus one opaque selection ref; the operator only names the
missed boundary.
Information leakage and change amplification: no new evidence or persistence
surface; the response adds only bounded opaque control metadata.
Complexity removed, moved, or added: one bounded state transition is added to
avoid automatic-splitter special cases and manual proposal construction.
Residual design risk: the host-provided `Something else` transition remains
model-mediated and requires an installed-client feasibility trial.
Verdict: `pass`.

Delivery evidence on 2026-07-26:

- deterministic contract tests cover schema exposure, a valid one-use
  amendment, fresh selection identity, second-amendment rejection, invalid
  observation shape, mismatched selection refs, preservation of the prior
  selection, and rejection of a single-item amendment that would bypass the
  revised selection;
- focused semantic/workflow validation passed 331 tests before the final
  complexity split; the final focused workflow/policy validation passed 249
  tests;
- the full deterministic suite passed with 1,624 tests and 1 skip when the
  commit-only frozen-path guard was excluded; that guard remains unchanged and
  must pass from committed content;
- Ruff and `git diff --check` passed;
- the advisory complexity sensor reports no new function above the configured
  threshold; the amendment lifecycle was split into small workflow-owner
  helpers rather than adding another service or module;
- after explicit operator authorization, the configured
  `gpt-5.3-codex-spark` reviewer inspected the full intended diff and reported
  no correctness regression or blocker in the amendment, selection, result,
  privacy, or unchanged-contract paths;
- the first post-commit installed-wrapper smoke rejected the new optional
  `operator_selection_ref` because its expected tool surface and packaged
  manifest description still represented the previous submit contract; its
  proposal-reflection assertion also treated the now-required safe schema name
  `semantic_issue_proposal` as if it were a reflected proposal value;
- the bounded Delivery correction updated the manifest, smoke oracle, and
  package fixtures to recognize the optional ref and to detect reflection by
  the synthetic proposal identity rather than by the safe schema name; the
  source-wrapper stdio smoke then passed all checks with the unchanged seven
  production tools;
- the independent follow-up review found the same contract drift in the
  separate Claude Desktop log checker; its exact submit-schema oracle and
  existing latest-surface fixture were updated to require the optional
  `operator_selection_ref`, preventing a valid reloaded Desktop runtime from
  being reported as stale;
- the corrected manifest/smoke follow-up is not yet committed or installed,
  and no Desktop trial is claimed from this source evidence;
- the installed-client `N=1` feasibility trial remains pending a reviewed,
  committed, rebuilt, installed, and reloaded artifact identity.

Real-ticket canary defect evidence on 2026-07-27:

- confirmed: the installed `78b1f86` package reached the five-item native
  selection and the first public-article comparison on approved sanitized
  ticket `ticket-94893302`;
- confirmed: an invalid closed-enum submission (`non_fit`) consumed the active
  comparison, so the operator's corrected `none_fit` could not be applied to
  the still-visible comparison card;
- confirmed: the transport collapsed all result-boundary validation failures
  to `tool_result_invalid` without recording whether the internal cause was
  schema mismatch, unsafe value, oversize, or another closed validation class;
- confirmed: direct current-source and installed-wrapper probes produce a valid
  `reuse_comparison_unavailable` envelope when no pending comparison exists;
- confirmed: a deterministic five-item replay over the same approved sanitized
  ticket produces a valid next-comparison MCP envelope with a fixture provider;
- provisional: the exact first `tool_result_invalid` payload cause remains
  unknown because the running transport discarded the validation class before
  logging. The next installed canary must use the new closed diagnostic marker;
  no ticket facts, tool arguments, tool results, or exception traceback may be
  logged.

Bounded correction:

- a malformed outcome or candidate ref no longer consumes an otherwise valid
  pending comparison; the result returns
  `resubmit_pending_reuse_comparison`, allowing the same operator decision to
  be submitted in canonical form;
- unknown tool fields, expired state, replaced selection identity, and missing
  pending state still clear or reject state and require a workflow restart;
- the stdio transport now writes only
  `tool_result_boundary_failure code=<closed-code> tool=<canonical-name>` to
  local stderr when the MCP result boundary rejects an internal result;
- the operator decision, candidate evidence, ticket content, artifact content,
  and raw exception are not included in that marker;
- this changes only bounded correction and local diagnostics. Reuse semantics,
  RAG ownership, article authoring, storage, reviewer output, and publication
  contracts remain unchanged.

Acceptance-to-gate correction:

| Acceptance criterion | Gate |
| --- | --- |
| A malformed enum/candidate submission does not destroy the active comparison, and the canonical correction succeeds once. | deterministic state-transition regression |
| Unknown fields and stale/replaced state still fail closed and require restart. | deterministic negative matrix |
| Every transport-side result rejection records one closed reason without payload content. | deterministic stderr-capture/privacy test |
| The real five-item ticket accepts `none_fit` and advances to item 2 without `tool_result_invalid`. | installed Desktop canary; `N=1` feasibility |

Ousterhout gate: `reviewed`.
Trigger: stateful continuation behavior and the transport failure boundary
changed across existing Desktop workflow modules.
Complexity hidden: the workflow distinguishes a correctable pre-side-effect
payload rejection from expired, replaced, or structurally unknown state.
Owner and what it must not know: `DesktopDraftWorkflow` owns pending comparison
lifecycle; the stdio transport knows only closed result-validation classes and
must not inspect or log workflow payloads.
Interface depth and caller cognitive load: the existing confirmation tool
returns the same comparison ref and closed outcomes only when correction is
possible, so Claude can normalize an unambiguous submit typo without another
operator question.
Information leakage and change amplification: no payload or exception content
crosses the diagnostic boundary; no provider, renderer, storage, or publishing
interface changes.
Complexity removed, moved, or added: one pending-state preservation condition,
one result-action distinction, and one closed diagnostic mapping were added;
no abstraction, module, service, or persistence layer was introduced.
Residual design risk: the original `tool_result_invalid` class must be observed
again after install because the prior runtime discarded its exact validation
class.
Verdict: `pass`.

Delivery validation and review on 2026-07-27:

- focused runtime and policy validation passed 86 tests;
- the full deterministic suite passed 1,631 tests with 1 skip and the
  commit-only frozen-path guard deselected;
- after commit `5e8a32c`, the complete repository suite, including the
  frozen-path guard, passed 1,632 tests with 1 skip;
- the MCPB package build and source-wrapper stdio smoke passed all 17 checks
  with the unchanged seven-tool production surface;
- Ruff and `git diff --check` passed;
- independent deep review returned `pass` with no blockers or warnings after
  checking pending-state lifecycle, stale-ref isolation, correction wording,
  closed diagnostics, privacy, behavior drift, review-graph ownership, and the
  Ousterhout gate;
The correction is committed and source/package validated. It remains
operationally unproven until install, Desktop reload, and the real-ticket
canary complete.

Post-install dependency and operator-guidance evidence on 2026-07-27:

- confirmed: the installed connector and registry passed all 17 stdio checks,
  Claude Desktop reloaded the new seven-tool package, and the noisy canary
  reached selected-item processing;
- confirmed: no process was listening on the configured RAG loopback port, so
  the Python workflow returned `comparison_provider_unavailable` and generated
  no draft;
- confirmed: the generic terminal tool text named only a comparison provider,
  which led Claude to offer repeated retry/wait choices instead of telling the
  operator that public-article RAG had to be restored;
- bounded correction: provider unavailable, not-ready, and invalid-response
  results now name KCS public-article search (RAG), distinguish the readiness
  failure from missing ticket evidence or an operator decision, prohibit
  manual drafting and same-comparison retries, and give one recovery action:
  restore the configured RAG service and restart `/draft` for the same ticket;
- unchanged: the core status codes, provider-neutral adapter, RAG hosting
  choice, draft gate, ticket evidence, operator outcomes, storage, reviewer
  output, and publication boundaries.
- focused runtime/policy validation passed 70 tests; the full suite passed
  1,634 tests with 1 skip and the commit-only frozen-path guard deselected;
  Ruff and `git diff --check` passed;
- independent deep review first found that the text-only acceptance matrix did
  not assert the complete no-draft/no-retry/manual-draft contract; after those
  assertions were added, final re-review returned `pass` with no blockers or
  warnings;
- the configured public RAG was restored from the exact-context source revision
  `0fd28fe9` with its declared vector dependency; `/api/status` reported 6,150
  articles and 35,695 ready keyword/vector chunks, and a bounded
  `/api/article-snippets` request returned
  `knowledge-exact-article-snippets-v1`;
- the runtime-up command timed out before the warmed process became ready even
  though that process later passed both capability checks. This startup timing
  remains operational evidence, not a reason to add retry logic to KCS
  authoring.

Acceptance-to-gate mapping:

| Acceptance criterion | Gate |
| --- | --- |
| Every public-RAG readiness failure names RAG in operator-visible text and says that no draft was generated. | deterministic tool-result text matrix |
| The text distinguishes service readiness from operator choice and missing ticket evidence. | deterministic wording assertions |
| The model is told not to offer retry/wait choices or draft manually and receives one recovery action. | deterministic positive/negative wording assertions |
| Status codes, result schemas, provider neutrality, and workflow transitions do not change. | focused/full regression and behavior-drift review |

Ousterhout gate: `not triggered`; this is a leaf projection of three existing
closed status codes into operator-facing recovery text. It adds no state,
service, dependency, retry mechanism, persistence, or hosting assumption.

### Representative canary comparison-boundary correction

Current-source forensic replay on 2026-07-28 found that the installed
item-3 stop was not a RAG outage:

- the query projection counted 512 symptom characters without the separators
  inserted between them, so a multi-symptom request could exceed the adapter's
  own 512-character limit before any RAG call;
- public Zendesk snippets could contain HTML markup. RAG returned valid public
  evidence, but the model-visible MCP result correctly rejected the unprojected
  markup;
- the output safety check treated the ordinary word `image` in a public
  article title, URL, or excerpt as a media payload.

Bounded correction:

- query projection now includes separators in the existing 512-character
  bound;
- the local public-RAG adapter projects excerpt markup to bounded plain text
  while retaining the provider token total for response-contract validation
  and recalculating the model-visible text count;
- bare media keys and URL/data variants remain forbidden, while ordinary
  public prose containing `image` or `audio` is permitted;
- no RAG endpoint, hosting, retrieval, ranking, operator outcome, authoring,
  storage, reviewer, or publication contract changes.

Acceptance evidence:

| Acceptance criterion | Gate |
| --- | --- |
| Multiple symptom fragments always produce a query of at most 512 characters. | deterministic boundary regression |
| Public HTML becomes plain model-visible text and the original provider total is still validated. | deterministic adapter/contract regression |
| Media payload keys remain forbidden while ordinary public prose is accepted. | deterministic positive/negative output-safety matrix |
| The approved five-item ticket preserves item 1-3 decisions and reaches item 4 and item 5 comparison without an MCP result error. | direct current-source representative canary; `N=1` feasibility |

Validation:

- focused comparison/RAG/Desktop boundary suite: 337 passed;
- full repository suite excluding the intentionally dirty-worktree frozen-path
  guard: 1646 passed, 1 skipped, 1 deselected;
- direct current-source five-item live-RAG replay: all five transition result
  schemas passed, with the ordered ledger
  `none_fit`, `reuse`, `reuse`, `none_fit`, `none_fit`;
- Ruff, review-graph policy and hashes, and `git diff --check`: passed;
- complexity sensor: no newly changed function exceeds the configured
  threshold;
- final independent correction re-review: `confirmed`, with no blockers.

The direct replay recorded all five comparison outcomes with valid result
schemas. It then reached existing authoring-quality behavior: item 5 was
blocked because its 1,380-character extractive cause exceeds the renderer's
600-character Cause bound. That is not a comparison/RAG failure and is not
silently relaxed by this correction.

Ousterhout closeout:

- Trigger: public-data normalization and the model-visible output-safety
  boundary changed.
- Complexity hidden: provider token totals and public HTML remain behind the
  local public-RAG adapter; forbidden media surfaces remain behind the Desktop
  result validator.
- Owner and non-owner knowledge: `LocalPublicRagAdapter` owns plain-text
  projection and provider-total validation; the Desktop result boundary owns
  media-key and data-URI rejection. Callers do not learn provider HTML, token,
  or media-validation details.
- Interface depth and operator load: the existing evidence, comparison-card,
  and outcome contracts are unchanged, and no operator question was added.
- Leakage and change amplification: recognized public HTML is projected to
  plain text, non-visible script/style content is suppressed, unknown
  technical placeholders remain visible, and media keys/data URIs still fail
  closed.
- Complexity delta: one bounded parser state and one media-key classifier were
  added inside existing owners; no service, workflow state, persistence,
  observability, or abstraction layer was added.
- Residual risk: malformed or uncommon public markup and repeated-ticket
  retrieval stability still require installed representative trials.
- Verdict: `pass` after deterministic boundary regressions and independent
  correction re-review.

## Remaining unknown inventory

- The final comfortable Desktop-integrated surface that directly owns entry and
  operator-choice provenance.
- Whether a future multi-session UI requires per-session comparison state
  instead of the current one-pending-comparison adapter slot.
- Retrieval and recommendation stability across representative tickets.
- Operator comfort and correction overhead during repeated use.

Recorded successful-trial identities:

- Claude Desktop client: `1.24012.1`;
- selected model: `Sonnet 5`, effort/mode `Medium`, confirmed by the operator
  from the successful trial UI;
- source/package/install/registry identity: verified;
- post-install Desktop server start and exact active-RAG article capability:
  verified; dependency revision provenance remains provisional because the
  service does not self-report it.

These unknowns are retained for the Phase B/b3 gates and must not expand
Phase A.

## Approval ledger

```text
Parent requested outcome: agreed
Parent target UX: selected
Bounded public excerpt visibility: approved
Helpful/partially-helpful priority rule: confirmed
URL-only priority or partial match: rejected
Reusable candidate eligibility: Plesk Support/KB articles only; docs pages excluded, confirmed 2026-07-23
KCS-15.2b1 Delivery and closeout: complete
Tracked material Design gate correction: Delivery authorized 2026-07-23
Active Slice Plan review linkage: Delivery authorized 2026-07-23
KCS-15.2b2 Phase A exact public context Delivery: complete; independent review confirmed
KCS-15.2b2 downstream Python Delivery: implemented
KCS-15.2b2 controlled-entrypoint skeleton: implemented and verified; current deterministic entrypoint
KCS-15.2b2 accepted runtime source: committed in dbb1b8e
KCS-15.2b2 artifact/runtime baseline: c31e155 installed and reloaded; current representative boundary correction not installed
KCS-15.2b2 comparison-submit correction source: committed in 5e8a32c and installed as part of c31e155
KCS-15.2b2 parent super-noisy KCS-14.5 canary: installed run accepted five items and recorded item 1 none_fit, item 2 reuse, and item 3 reuse before the next boundary failure; direct current-source replay completed all five comparisons; parent authoring remains open on existing content-quality gates and installation of the current correction
KCS-15.2b2 operator-steered boundary correction: target UX selected and Delivery authorized 2026-07-26
KCS-15.2b2 real-ticket comparison-submit defect correction: Delivery authorized by operator continuation 2026-07-27
KCS-15.2b2 RAG-unavailable operator guidance: Delivery authorized by operator 2026-07-27
KCS-15.2b2 representative comparison-boundary correction: Delivery authorized by operator continuation 2026-07-28; current-source five-item comparison replay passed; commit/install/Desktop recheck pending
KCS-15.2b2 Phase C controlled operator surface: host-blocked and deferred
KCS-15.2b2 final Desktop UX: deferred pending a host-owned direct launcher
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

Stop Phase B and return to Design if it requires:

- raw/private ticket or internal article egress;
- a free-form, evidence-bearing, URL-bearing, or recommendation-bearing submit
  argument;
- Claude-owned KCS action or candidate identity;
- bypassing comparison for a direct, selected, or batch draft path;
- silently replacing a missing approved exact article with semantic results;
- persistence, logging, publication, customer reply, or article-write behavior;
- changing core comparison bounds or depending on a local-provider schema;
- touching KCS-15.2b3 repeated-trial behavior.
