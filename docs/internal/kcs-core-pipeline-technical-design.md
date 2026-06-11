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

## Future Internal Packet: CandidateSemanticExtraction

`CandidateSemanticExtraction` may be introduced in KCS-7 or KCS-9 as an
untrusted internal intermediate packet.

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
  symptoms[]
  confirmed_facts[]
  environment{}
  supported_cause
  supported_resolution_or_workaround
  open_questions[]
  issue_split_signals[]
  visibility_notes{}
  confidence_notes[]
}
```

Required flow:

```text
CandidateSemanticExtraction
  -> Python sanitizer / normalizer / validator
  -> NormalizedTicketEvidencePacket or blockers
```

Rules:

- Do not implement `CandidateSemanticExtraction` in KCS-1.
- Do not persist it as canonical evidence.
- Do not expose it as reviewer-ready output.
- Do not pass it to the KCS decision engine directly.
- If implemented later, keep it internal-only and untrusted.
- Its free-text fields must follow the Data Handling Baseline and must be
  scanned before normalization.

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

If semantic extraction is needed, KCS-7 should define the extraction interface
and blockers, not silently make the core depend on an LLM.

### KCS-8: Zendesk Read-only Ingest Adapter

KCS-8 fetches approved allowlisted Zendesk ticket data through a read-only
adapter and passes it to the evidence package builder.

The adapter does not own KCS decisions and does not pass raw Zendesk payloads to
Claude by default.

### KCS-9: Bounded Claude Handoff

KCS-9 may include bounded Claude-assisted extraction if approved.

Allowed role:

```text
approved sanitized input
  -> Claude proposes candidate evidence JSON
  -> Python validates/sanitizes/normalizes
  -> accepted NormalizedTicketEvidencePacket or blockers
```

Forbidden role:

```text
raw Zendesk ticket
  -> Claude decides KCS action directly
  -> article output without Python validation
```

Claude output remains untrusted candidate data until the Python validation layer
accepts it.

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
