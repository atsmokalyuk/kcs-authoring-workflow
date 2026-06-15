# KCS Core Pipeline - Technical Design

## Purpose

Define the planned technical workflow for KCS Authoring MVP implementation.

This document closes the design gap between packet contracts and practical
ticket understanding: Python owns packet validation and workflow decisions, but
semantic extraction from narrative ticket text may require bounded LLM-assisted
extraction or human-prepared evidence.

## Design Target

The corporate MVP should preserve the behavior proven in the local
`plesk_support` prototype before local-model experiments:

```text
LLM may help extract and draft.
Python validates, decides, and blocks.
Reviewer owns final approval.
```

There is no Gemma or local-LLM dependency in this MVP design. If semantic model
assistance is needed, the intended path is approved Claude Enterprise/Desktop
bounded handoff, not an implicit local model dependency.

## Core Ownership Model

The key distinction is ownership:

```text
Semantic extraction candidate fields
  -> may be prepared by a human, fixture, deterministic parser, or bounded LLM

Accepted NormalizedTicketEvidencePacket
  -> owned by Python validation and sanitizer/normalizer acceptance

KCS action and readiness
  -> owned by deterministic Python core
```

The LLM may propose normalized evidence fields, but those fields are untrusted
until the Python layer validates and accepts them.

## Internal Packet: CandidateSemanticExtraction

`CandidateSemanticExtraction` is the KCS-9a untrusted internal intermediate
packet for semantic item identification.

Purpose:

```text
Represent what an extractor thinks the ticket means.
```

The extractor may be a human-prepared fixture, deterministic parser, or bounded
Claude handoff. This packet is not canonical evidence and must not be consumed
directly by the KCS action decision engine.

Conceptual shape:

```text
CandidateSemanticExtraction {
  schema_version
  case_ref
  extraction_source_ref
  source_refs[]
  items[] {
    candidate_id
    summary
    product_relation
    supportability
    supportability_basis
    kcs_item_status
    article_type_hint
    visibility_hint
    eol_role
    symptoms[]
    confirmed_facts[]
    supported_cause
    supported_resolution_or_workaround
    question
    supported_answer
    open_questions[]
    environment{}
  }
}
```

Required flow:

```text
CandidateSemanticExtraction
  -> Python sanitizer / normalizer / validator
  -> NormalizedTicketEvidencePacket or blockers
```

Rules:

- Do not persist it as canonical evidence.
- Do not expose it as reviewer-ready output.
- Do not pass it to the KCS decision engine directly.
- Do not let it return KCS actions such as `reuse_existing`,
  `update_existing`, `create_candidate`, `flag_existing`, `split_required`, or
  `blocked`.
- Its free-text fields must follow the Data Handling Baseline and must be
  scanned before normalization.
- EOL/supportability status must come from explicit sanitized input mention in
  this slice; KCS-9a does not perform online EOL lookup.

## Planned End-to-End Flow

```text
Approved input source
  |
  |-- synthetic fixture
  |-- operator sanitized summary
  |-- approved sanitized export / clean-ticket evidence
  |-- Zendesk read-only ingest later
  v
+----------------+
| Source adapter |
+----------------+
        |
        v
+-------------------------------+
| Evidence preparation           |
| - fixture/manual packet        |
| - deterministic extraction     |
| - bounded Claude extraction    |
|   when approved                |
+-------------------------------+
        |
        | candidate evidence fields
        v
+--------------------------------------+
| Sanitizer / normalizer / validator   |
| - privacy checks                     |
| - required fields                    |
| - supported cause/resolution         |
| - unsafe/internal blockers           |
| - schema/version validation          |
+--------------------------------------+
        |
        v
+--------------------------------+
| NormalizedTicketEvidencePacket |
+--------------------------------+
        |
        +-----------------------------+
        |                             |
        v                             v
+----------------------+      +----------------------+
| Safety/evidence gate |      | Search/reuse adapter |
+----------------------+      +----------------------+
        |                             |
        |                             v
        |                   +--------------------------+
        |                   | ReuseSearchResultsPacket |
        |                   +--------------------------+
        |                             |
        +-------------+---------------+
                      v
          +--------------------------+
          | KCS action decision core |
          +--------------------------+
                      |
                      v
          +-------------------------+
          | KcsActionDecisionPacket |
          +-------------------------+
                      |
                      v
          +--------------------------+
          | Reviewer packet renderer |
          +--------------------------+
                      |
                      v
          +-------------------+
          | KcsReviewerPacket |
          +-------------------+
                      |
                      v
          +--------------------------+
          | Validation / loop state  |
          +--------------------------+
                      |
                      v
          ready_for_reviewer | blocked | draft_required | review_blocked
```

## Evidence Preparation Modes

### KCS-1: Fixtures Only

KCS-1 defines packet contracts and safe fixtures. It does not build packets
from raw or clean ticket prose.

Input examples:

- synthetic `normalized_ticket_evidence_packet_v1` fixture;
- blocked/rejection fixture;
- reuse/search fixture.

### KCS-7: Evidence Package Builder

KCS-7 introduces a builder for approved fixtures, exported sanitized tickets,
or clean-ticket evidence packages.

It may include deterministic extraction for obvious structure, but it should
not pretend that Python can reliably understand long support narratives without
semantic assistance.

KCS-7 may define the structured extraction interface and blockers for future
semantic KCS item identification. It does not call Claude, perform semantic
classification from ticket narrative, or make the core depend on an LLM.

### KCS-8: Zendesk Read-only Ingest Adapter

KCS-8 fetches approved allowlisted Zendesk ticket data through an injected
read-only source client and produces a raw/pre-cleanup cleanup handoff
manifest. It does not pass raw Zendesk payloads to the evidence package
builder.

`ZendeskIngestPolicy` owns the approved ticket-reference allowlist.
`ingest_zendesk_ticket_for_cleanup()` validates `ticket_ref` against that
policy before calling `ZendeskSourceClient`.

The intended production deployment shape is an approved internal service
endpoint implementing the source-client contract. Local/dev may use an
MCP-backed source client, but no MCP path, service endpoint, Zendesk token, URL,
or secret is hardcoded in the KCS core.

The adapter does not own KCS decisions, semantic extraction, cleanup, rendering,
readiness, Claude handoff, attachment processing, Zendesk writes, Help Center
publication, or customer replies. Attachment bodies are not downloaded in this
slice. The source client exposes no broad ticket search, list, bulk export, or
background crawl entrypoint.

Raw ticket/comment bodies remain local-only and pre-Claude until a later
approved cleanup/sanitizer lane produces a KCS-7 approved sanitized export.
Raw handoff files are local cleanup inputs only. They must not be committed as
fixtures and must not be included in reviewer, CLI, or publication artifacts.
`ZendeskIngestResult.safe_payload()` is the default reporting surface for logs,
tests, CLI/debug output, and exceptions.

### KCS-9: Bounded Claude Handoff

KCS-9 is the bounded Claude handoff umbrella. It has planned sub-slices:

- KCS-9a-prep: chronology-preserving sanitized conversation context builder;
- KCS-9a: semantic KCS item identification;
- KCS-9b: bounded reviewer-assist handoff contract;
- KCS-9c: Claude-assisted reviewer-only draft generation.

KCS-9a-prep produces the safe semantic input context for KCS-9a. It preserves
conversation order and the meaning needed to identify KCS items while removing
or replacing private values. It is not a broad redaction engine inside KCS core;
it is an approved cleanup/preparation layer that outputs bounded safe context.
The sanitizer/context builder should remove only explicit noise and unsafe
values, such as transport metadata, quoted mail footers, signatures, tracking
headers, attachment links, and private identifiers. Relevant context from the
actual customer/support conversation must remain in the sanitized data.

Required preserved context:

```text
sanitized_turns[]
  turn_index
  role = customer | support | internal_note | system
  visibility
  text

known_safe_facts[]
explicit_status_mentions[]
operator_notes[]
```

The context builder must preserve:

- chronological order;
- who said what at a role level;
- customer-visible symptom/question;
- relevant troubleshooting context exchanged during the conversation;
- support checks, answer, workaround, or resolution;
- customer confirmation or remaining open questions;
- explicit EOL/unsupported mentions from the sanitized input.

The context builder must remove or replace:

- message transport metadata and duplicated quoted mail noise;
- email footers, signatures, and boilerplate that do not affect KCS meaning;
- customer names, emails, live domains, IPs, hostnames, license IDs, raw ticket
  IDs, private paths, credentials, tokens, and secrets;
- attachment URLs/bodies;
- raw internal comments as-is.

It must not infer KCS actions, run online EOL lookup, call Claude, decide
article readiness, or create canonical evidence directly.

KCS-9a may introduce Claude-assisted extraction if approved and smoke-testable.
It identifies candidate KCS items/questions/issues from approved sanitized
context, but it does not accept packets or decide KCS actions.
Detailed item-identification rules are tracked in
`docs/internal/kcs-item-identification-decision-rules.md`.

Allowed role:

```text
approved sanitized input
  -> Claude proposes KCS item candidates
       problems/questions to address
       atomic issue boundaries
       answered vs unresolved items
       suggested article type
       public/internal visibility hints
  -> Python validates/sanitizes/normalizes
  -> accepted NormalizedTicketEvidencePacket or blockers
  -> KCS-2..6 decide/render/report
```

Forbidden role:

```text
raw Zendesk ticket
  -> Claude decides KCS action directly
  -> article output without Python validation
```

Claude output remains untrusted candidate data until the Python validation layer
accepts it.

KCS-9b defines the bounded provider handoff contract. It builds compact safe
reviewer-assist requests from deterministic decision/readiness summaries and
optional safe artifact refs. It does not generate drafts, write files, call a
live provider, implement MCP/service transport, or let the provider decide KCS
actions.

KCS-9c is the first slice that may allow provider-proposed reviewer-only draft
wording. It consumes validated KCS-9b-style bounded context for eligible
article-output paths only. Python owns validation and artifact writing. Style
compliance must be layered through prompt constraints, structured draft schema,
deterministic Python validators, optional style judge feedback, and human
review.

## NormalizedTicketEvidencePacket Acceptance Rules

The packet is accepted only after Python validation confirms:

- schema version is supported;
- input class is allowed;
- source references are opaque and safe;
- issue candidates are atomic or marked for split;
- symptoms are sanitized and relevant;
- confirmed facts are supported by allowed evidence;
- cause is supported or empty;
- resolution/workaround is supported or blocker-coded;
- open questions are explicit;
- visibility summary separates public-safe facts from reviewer-only/internal
  facts;
- sanitizer report is present;
- forbidden values and source labels are absent.

If validation fails, the output is a blocker, not a partially trusted packet.

## Search and Issue Identity

Search is symptom-oriented. Existing knowledge may be searched by customer
visible symptoms, error text, product area, and environment signals.

Issue identity is not symptom-only:

- Technical SCR identity: article type plus supported cause-resolution pair.
- How-to Q&A identity: question-answer pair.

Symptoms may differ across tickets while the reusable issue remains the same.
GUI and CLI variants of the same solution are delivery variants, not separate
KCS identities. GUI wording should be preferred in later rendered output. CLI
steps may be added when they are missing or more optimal, but they should not
force a separate article when the underlying cause-resolution or
question-answer identity is the same.

## KCS Action Decision

The deterministic KCS decision core chooses one of:

- `reuse_existing`
- `update_existing`
- `create_candidate`
- `flag_existing`
- `split_required`
- `no_article`
- `blocked`

The decision engine uses accepted evidence packet fields and structured
reuse/search results. It does not read raw tickets and does not call Claude.

For same-identity matches that need content changes, public or published
existing articles are flagged for reviewer update with `flag_existing`.
Internal or not-public existing articles use `update_existing`. The decision
packet selects the action and target only; reviewer packet and Zendesk HTML
content are produced by later renderer slices.

For multiple KCS-relevant issue/question candidates, the decision engine returns
top-level `split_required` plus preliminary per-item decision cards. It does
not create a combined article draft for multiple issues.

KCS-3 may expose future-safe operator override metadata:

- `operator_override_allowed`
- `allowed_override_modes`
- `override_status=not_requested`

This metadata does not change the deterministic recommendation and does not
generate draft text. It only tells later slices whether a reviewer-only draft
request could be considered after operator selection. Safety blockers, raw or
sensitive data, open questions, missing duplicate/reuse checks, and missing
mandatory resolution/answer evidence keep override disabled.

Internal-only or public-output-not-safe findings may allow a later
reviewer-only draft request, but public readiness remains unapproved. When a
future slice implements operator-requested override handling, the local review
bundle and persisted packet artifacts must record the override request/status,
preserve the original deterministic recommendation, and keep
`auto_publish_allowed=false`.

## Drafting and Reviewer Output

The renderer prepares reviewer-ready output from accepted packets and decisions.

Zendesk HTML, if produced, is a copy/paste artifact for reviewer use. It is not
a write/publish operation.

`auto_publish_allowed=false` remains required for MVP outputs.

## Implementation Invariants

- No Gemma/local-model dependency.
- No raw Zendesk payloads to Claude by default.
- No Claude-owned safety decision.
- No Claude-owned KCS action decision.
- No automatic Zendesk writes.
- No Help Center publication.
- No customer reply generation.
- No repo artifacts during normal runtime workflow.
- Python validation owns packet acceptance.
- Python deterministic core owns readiness state.

## Deferred Local Output Model

Later slices may use this local-output flow:

```text
KCS pipeline run
  -> identifies KCS items
  -> makes decision per item
  -> renders local review bundle
  -> saves files under ticket_<safe_case_ref>/
  -> Claude/CLI shows only a short index/status + local file paths
```

The future compact Claude/CLI summary may include only the bundle path, item id,
short title, recommended action, article type, status, reason/blocker codes,
local review packet path, local Zendesk HTML draft path when generated,
operator override metadata, and `auto_publish_allowed=false`.

If an operator override is requested later, the local bundle must persist that
fact in the review packet or adjacent metadata artifact. The compact summary may
show only the override status/mode and local artifact paths, not the full draft
body or raw evidence.

It must not include full reviewer packet bodies, full Zendesk HTML, raw tickets,
redaction maps, raw internal comments, full evidence basis, raw search snippets,
chunks, or vector values.

## Slice Boundaries

KCS-4:

- reviewer packet renderer;
- Zendesk HTML renderer;
- no local bundle writing yet.

KCS-5:

- validation report / ready_for_reviewer loop state;
- no Claude chat integration yet.

KCS-6:

- CLI entrypoint and compact run index;
- local file paths only in CLI/chat summary.

KCS-7:

- evidence package builder from approved fixtures/exported tickets;
- no live Zendesk dependency.

KCS-8:

- Zendesk read-only ingest adapter;
- approved allowlist and token only here.

KCS-9:

- Claude Enterprise/Desktop bounded handoff;
- KCS-9a semantic KCS item identification from approved sanitized context;
- KCS-9b bounded reviewer-assist handoff contract;
- KCS-9c reviewer-only draft generation and artifact writer;
- Claude output remains untrusted and validators rerun.

KCS-10:

- local reviewer bundle writer for deterministic audit/debug artifacts;
- writes safe local bundles from existing validated packets and reviewer-only
  draft artifacts;
- not a production review UI, Zendesk write path, Help Center publication path,
  or customer-reply path.

KCS-11:

- live Claude provider adapter for real provider smoke tests;
- sends only validated compact safe request packets;
- provider output remains untrusted and Python validators still own acceptance;
- no raw Zendesk data, provider-owned file writing, KCS action authority, or
  publication behavior.

KCS-12:

- Claude Desktop MCP validator/control adapter under `kcs_adapters`;
- installable local Claude Desktop MCPB package source under
  `packaging/claude-desktop/`;
- exposes read-only stdio MCP tools for KCS-9b/KCS-9c packet validation and
  synthetic contract smoke;
- returns compact safe summaries only, with no resources, prompts, file writes,
  network calls, provider calls, raw Zendesk data, publication behavior, or
  customer replies.

Future remote MCP / intranet deployment:

- separate from the KCS-12 local MCPB implementation;
- reuse the safe tool facade and packet validators where possible;
- replace the local Node/stdout wrapper with an approved internal MCP service
  endpoint;
- connect Claude Desktop through a custom remote connector URL;
- keep runtime credentials, auth, ACLs, audit logs, service health checks, and
  deployment packaging outside the deterministic KCS core.
