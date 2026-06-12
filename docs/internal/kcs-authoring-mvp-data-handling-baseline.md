# KCS Authoring MVP - Data Handling Baseline

## Purpose
Define the default data-handling rules for the KCS Authoring MVP: what data may be read, passed to Claude, stored, logged, and included in reviewer-ready output.

## Scope
This baseline applies to:
- KCS core pipeline
- Zendesk read-only ingest adapter
- public knowledge search and reuse checks
- temporary local/public RAG reuse checks used during prototype development
- future approved search adapters, including kcs-search-mcp and internal KB/vector search when available and approved
- Claude Enterprise/Desktop runtime handoff
- fixtures and test packets
- reviewer-ready KCS packets
This MVP is not a publication system and does not perform customer-facing automation.

## Default Rules

### Zendesk Access
- Read-only access only.
- Approved ticket allowlist only.
- No bulk export.
- No background crawling.
- No customer reply, ticket update, tag update, or status update actions.
- No Help Center write or publish actions.
- Zendesk credentials or tokens must never be exposed to Claude or stored in repository files.
- Zendesk token is not needed for [KCS-0](https://webpros.atlassian.net/browse/PAUX-7084) through KCS-7. Zendesk token is needed only for KCS-8: Zendesk read-only ingest adapter.

### Raw Zendesk Data
- Raw Zendesk JSON, full ticket comments, internal comments, requester metadata, author metadata, attachments, and audit metadata are sensitive.
- Raw ticket data is not sent to Claude by default.
- Raw ticket data is not committed to the repository.
- Raw ticket data is not logged.
- Raw ticket data may be processed only inside approved corporate/local runtime storage.
- Any persistent fixture derived from a real ticket must be approved and sanitized first.

### MVP Cleanup Form Lane
During the MVP, an approved cleanup form may act as the temporary sanitizer and
preprocessor for operator-driven testing.

Allowed lane:

```text
raw ticket
  -> approved cleanup form
  -> operator_sanitized_summary / normalized evidence packet
  -> safety gate
  -> evidence readiness validation
  -> later KCS decision/drafting slices
```

Raw Zendesk ticket content may be pasted only into the approved cleanup form or
other approved sanitizer/preprocessor runtime. Raw ticket content must not be
pasted directly into Claude Desktop, committed to the repository, logged, or
stored as a fixture.

The cleanup form output becomes `operator_sanitized_summary` or another
approved sanitized normalized input. The safety gate runs after cleanup form
output and before Claude handoff, KCS decision, drafting, rendering, or
reviewer-ready output. A blocked safety result, or future
`blocked_pre_handoff` status, means the operator must rerun cleanup, simplify
the evidence, or defer the case instead of passing the packet forward.

### Evidence Package
Claude receives only sanitized normalized evidence packets, bounded extraction
requests, bounded decision/reviewer packets, and structured search results when
the corresponding handoff slice is approved.
Evidence packages must not contain:
- personal or customer identifiers: names, email addresses, contact information, raw customer identifiers, or raw ticket IDs in article draft content
- infrastructure identifiers: live domains, URLs, server IP addresses, hostnames, license IDs, or private filesystem paths
- secrets: credentials, passwords, tokens, keys, or other secrets
- raw internal content: raw internal comments or other unsanitized internal-only evidence
- internal-only evidence unless separately approved, summarized, and sanitized
- financial information, including payment card data, bank details, invoices, tax information, or billing identifiers

source code, private scripts, proprietary configuration, or customer-provided application code
Opaque internal references such as `case_ref` or `source_ref` may be used for traceability, but must not appear in article draft content.

### Safety Gate
KCS-2 introduces a deterministic safety gate for accepted
`NormalizedTicketEvidencePacket` inputs. The gate runs before KCS action
decision, drafting, rendering, or Claude handoff.

The safety gate accepts only approved normalized input classes:

- `synthetic_fixture`;
- `approved_sanitized_fixture`;
- `normalized_zendesk_evidence`;
- `operator_sanitized_summary`.

The safety gate blocks unknown input classes, unsafe or unknown visibility
classes, missing sanitizer pass markers, unsafe sanitizer flags, forbidden
source labels, and private identifiers in normalized evidence fields.

This gate does not approve raw Zendesk processing, live Zendesk access, Claude
handoff, customer replies, Zendesk writes, or Help Center publication.

### Semantic Extraction
`NormalizedTicketEvidencePacket` is not trusted just because an LLM produced
candidate fields. Evidence preparation may include human-prepared summaries,
fixtures, deterministic extraction, or bounded Claude-assisted extraction after
approval. The Python sanitizer/normalizer/validator owns packet acceptance.

Claude-assisted extraction, when introduced, may receive only approved
sanitized/clean evidence according to this baseline. It must not receive raw
Zendesk JSON, credentials, attachments, raw internal comments, or unapproved
private data. Its JSON output must pass Python validation before it can become
an accepted `NormalizedTicketEvidencePacket`.

### Internal Comments
- Internal Zendesk comments are internal-only by default and are not passed to Claude by default.
If internal comments are needed for evidence, the Python/runtime layer must first summarize and sanitize them. Sanitized facts derived from internal comments may support reviewer packets, blockers, draft rationale, or reviewer questions when relevant.
- Draft article content must not include raw internal comments, internal-only wording, internal identifiers, or unsupported internal conclusions. Any internal-derived fact must be traceable in reviewer notes and reviewed before publication.

### Attachments
- Attachments are not downloaded or processed in the MVP.
- Attachment handling requires separate approval, scope, storage rules, and sanitization rules.
- Binary files, logs, screenshots, archives, and customer-provided files must not be uploaded to Claude by default.

### Public Knowledge Search and Future Search Adapters
- In the MVP, reuse and duplicate checks use approved public knowledge sources and/or local RAG over public articles.
- Search adapters may return structured metadata and relevance signals. Default returned fields should be limited to article ID, title, public URL, visibility, lifecycle/status if available, score, source type, and safe summary if approved.
- Raw vector values, raw search queries, snippet bodies, and chunk bodies are not passed to Claude by default.
- For prototype testing, temporary local/public RAG over public articles may be used as a replaceable search adapter. The adapter contains only public articles and exposes only structured reuse/search results to the KCS core. Runtime artifacts, including indexes, vectors, chunks, downloaded corpora, and raw query logs, must be stored outside committable repository paths or in explicitly ignored runtime/cache locations.
- Corporate internal article search, kcs-search-mcp, or internal vector DB search are out of scope for the initial MVP until the required access, data-handling rules, and adapter approval are available. If internal-only knowledge is added later, it may support reviewer notes, blockers, draft rationale, or sanitized draft facts when relevant. Raw internal-only article content must not be copied verbatim into Claude prompts, reviewer packets, or draft article body unless separately approved.
- Reviewer-ready draft packets may use sanitized facts from approved evidence sources: source-ticket evidence, public search results, public KB articles, and internal-only knowledge when relevant. Internal-only facts must be traceable in reviewer notes and separated from public-ready article content until KCS reviewer/publisher approval.
- Publication/evolve-loop promotion is outside MVP and requires separate KCS reviewer/publisher approval.

### Source Ticket Quotes
- Reviewer packets may include short sanitized quotes from the source ticket only when the exact wording is needed to preserve context, customer intent, visible error text, technical precision, or the nuance of the reported issue for KCS review.
- Source-ticket quotes must be relevant to the KCS decision, evidence basis, draft wording, blocker, or reviewer question. Do not include quotes for general summarization, convenience, or traceability when a sanitized paraphrase is sufficient.
- Source-ticket quotes must be sanitized before inclusion and must not contain PII, email addresses, personal contact information, financial information, credentials, tokens, secrets, live domains, IPs, hostnames, license IDs, private paths, source code, proprietary configuration, or customer-provided application code.
- Source-ticket quotes must stay in the reviewer packet or evidence basis. They must not be logged, used as run metadata, or copied into public article content unless they are already sanitized, reusable, and appropriate for public KCS wording.

### Claude Usage
- Claude receives only sanitized normalized evidence packets, bounded decision/reviewer packets, and structured search results.
- Claude may propose candidate normalized evidence fields only through an
  approved bounded extraction path.
- Claude does not receive Zendesk tokens or other credentials.
- Claude does not call Zendesk directly.
- Claude does not receive raw Zendesk payloads by default.
- Claude drafts, reviews, suggests wording, and may assist semantic extraction
  when approved, but does not own packet acceptance, final KCS decision, safety
  gates, validation state, or publication readiness.
- Final KCS decision remains with the support engineer or KCS reviewer.

### Logs
- Logs may contain only operational metadata: run_id, opaque case_ref, timestamp, action/status, blocker codes, schema version, and validation summary.
- Validation summary must be code/enum based. It must not include ticket free text, raw comments, raw article text, search snippets, customer wording, copied evidence values, or source-ticket quotes.
- Logs must not contain raw ticket comments, raw Zendesk JSON, PII, email addresses, personal contact information, financial information, credentials, tokens, secrets, source code, private scripts, proprietary configuration, customer-provided application code, domains, IPs, hostnames, license IDs, private paths, raw internal article chunks, raw vector values, raw search queries, raw search result snippets, or source-ticket quotes.

### Fixtures and Test Packets
- Fixtures may be synthetic or derived from approved sanitized tickets.
- Any real-ticket-derived fixture must be sanitized and approved before use.
- Fixtures must not contain customer identifiers, live domains, IPs, hostnames, credentials, license IDs, raw internal comments, private paths, or raw Zendesk JSON.
- Raw Zendesk JSON may be used only for an explicitly approved local-only ingest test.
- Test packets should use placeholders where realistic values are needed.

### Output
- Output is reviewer-ready only.
- `auto_publish_allowed=false` must be explicit in reviewer packets.
- No automatic Zendesk writes.
- No automatic Help Center writes or publication.
- Draft article content must be sanitized before it is included in reviewer-ready packets.
- Reviewer notes, blockers, and rationale must be clearly separated from draft article content.
- Canonical machine output is a JSON reviewer packet.
- Zendesk HTML is a copy/paste artifact only when an article/update candidate is ready.

## Approval and Change Control
Any expansion of this baseline requires explicit approval from the project owner and the relevant security/data-handling reviewer. This includes:
- using non-allowlisted tickets
- accessing or integrating with corporate-managed resources, including internal repositories, databases, vector indexes, MCP servers, Zendesk instances, knowledge systems, credential stores, or hosted infrastructure
- passing raw ticket data to Claude
- processing ticket attachments
- returning raw internal article bodies or snippets
- enabling Zendesk write actions
- enabling Help Center draft, update, or publish actions
- storing real-ticket-derived artifacts outside approved runtime storage

## Policy Alignment Note
`These MVP rules are intentionally conservative and may be stricter than general WebPros operational metadata rules.`
Some operational identifiers, such as domains, server IPs, hostnames, or license IDs, may be allowed in other WebPros contexts, but they are excluded here by default because the MVP does not need them in Claude-visible packets, logs, or reviewer-ready public draft content. A later approved scope may explicitly allow selected operational identifiers if required.
