# KCS Core Pipeline - Architecture and Contracts

## Goal
Runtime-independent Python core for KCS Authoring MVP.

## Non-goals
- No Zendesk writes.
- No Help Center publish.
- No customer reply generation.
- No raw ticket processing inside core.
- No Claude-owned decision logic.
- No auto-publish.

## Flow

```text
+----------------+     +----------------------+     +------------------------+
| Source adapter | --> | Evidence preparation | --> | Sanitizer / normalizer |
+----------------+     +----------------------+     +------------------------+
                                                                |
                                                                v
                                                        +-----------------+
                                                        | Evidence packet |
                                                        +-----------------+
                                                                |
                                                                v
+-----------------+     +----------+     +-----------------------+
| Reviewer packet | <-- | KCS core | <-- | Search / reuse packet |
+-----------------+     +----------+     +-----------------------+
```

Evidence preparation may use fixtures, human/operator-prepared sanitized
summaries, deterministic extraction where possible, or bounded Claude-assisted
semantic extraction when approved. Python validation owns packet acceptance.
Claude output is untrusted until validated.

## Core principle
- Code decides
- LLM drafts
- Validators block

## Extraction principle

- LLM may propose candidate evidence fields.
- Python validates and accepts or blocks the packet.
- The KCS core never treats LLM output as trusted input without validation.
- No Gemma or local-model dependency is part of the MVP architecture.

## Packets

```text
normalized_ticket_evidence_packet_v1 {
  schema_version
  case_ref
  input_class
  source_refs
  issue_candidates
  environment
  symptoms
  confirmed_facts
  supported_cause
  supported_resolution_or_workaround
  open_questions
  visibility_summary
  sanitizer_report
}
```

```text
reuse_search_results_packet_v1 {
  schema_version
  search_run_ref
  searched
  search_source
  matches
  blockers
}
```

```text
kcs_action_decision_packet_v1 {
  schema_version
  candidate_id
  recommended_action
  article_type
  confidence
  blockers
  evidence_basis
  selected_reuse_match
  auto_publish_allowed
}
```

```text
kcs_reviewer_packet_v1 {
  schema_version
  case_ref
  recommended_action
  review_required
  public_article_candidate
  internal_reviewer_notes
  evidence_basis
  validation_report
  zendesk_source_html
  auto_publish_allowed
}
```

## Candidate actions
- reuse_existing
- update_existing
- create_candidate
- flag_existing
- split_required
- no_article
- blocked

## Article types
- technical_scr
- howto_qa
- none

## Packet Contract Details

KCS-1 defines schema-versioned JSON packet contracts and basic validation
invariants. Later slices may add richer validators, but they must preserve these
field meanings unless a schema version changes.

### normalized_ticket_evidence_packet_v1

| Field | Type | Required | Notes / invariants |
|---|---|---:|---|
| `schema_version` | string | yes | Must equal `normalized_ticket_evidence_packet_v1`. |
| `case_ref` | string | yes | Opaque case reference. Must not expose a raw ticket ID by default. |
| `input_class` | string | yes | Describes the approved input class, for example synthetic or sanitized fixture input. |
| `source_refs` | list[string] | yes | Opaque/source-safe references only. |
| `issue_candidates` | list[object] | yes | Candidate issue/question records prepared by the evidence layer. |
| `environment` | object | yes | Normalized safe environment facts. |
| `symptoms` | list[string] | yes | Safe symptom/search wording. Search may use symptoms, but issue identity is not symptom-only. |
| `confirmed_facts` | list[string] | yes | Facts accepted by preparation/validation. |
| `supported_cause` | string or null | optional/default null | Null when no supported cause is available. Must not be invented. |
| `supported_resolution_or_workaround` | string or null | optional/default null | Null when no supported resolution/workaround exists. |
| `open_questions` | list[string] | yes | Safe unresolved questions/blockers. |
| `visibility_summary` | object | yes | Safe visibility/data-handling summary. |
| `sanitizer_report` | object | yes | Sanitizer/preparation status summary. |

### reuse_search_results_packet_v1

| Field | Type | Required | Notes / invariants |
|---|---|---:|---|
| `schema_version` | string | yes | Must equal `reuse_search_results_packet_v1`. |
| `search_run_ref` | string | yes | Opaque search run reference. |
| `searched` | boolean | yes | `false` means reuse/duplicate status is not established. |
| `search_source` | string | yes | Structured source label, for example fixture search or public/local RAG. |
| `matches` | list[object] | yes | Structured reuse candidates; no raw snippets/chunks. |
| `blockers` | list[string] | yes | Code-like blockers, for example missing search. |

### kcs_action_decision_packet_v1

| Field | Type | Required | Notes / invariants |
|---|---|---:|---|
| `schema_version` | string | yes | Must equal `kcs_action_decision_packet_v1`. |
| `candidate_id` | string | yes | Opaque candidate reference. |
| `recommended_action` | enum string | yes | One of the candidate actions listed above. |
| `article_type` | enum string | yes | `technical_scr`, `howto_qa`, or `none`. |
| `confidence` | number | yes | Decision confidence/strength indicator. It does not override blockers. |
| `blockers` | list[string] | yes | Code-like blockers. Empty only when no blocker is present. |
| `evidence_basis` | object | yes | Structured evidence references/summary, not raw evidence dumps. |
| `selected_reuse_match` | object or null | optional/default null | Selected reuse/update target when applicable. |
| `auto_publish_allowed` | boolean | optional/default false | Must be `false` for all MVP packets. `true` is invalid. |

### kcs_reviewer_packet_v1

| Field | Type | Required | Notes / invariants |
|---|---|---:|---|
| `schema_version` | string | yes | Must equal `kcs_reviewer_packet_v1`. |
| `case_ref` | string | yes | Opaque case reference. |
| `recommended_action` | enum string | yes | One of the candidate actions listed above. |
| `review_required` | boolean | yes | MVP output always remains reviewer-owned. |
| `public_article_candidate` | object or null | optional/default null | Draft/update content when available; null for blocked/no-article cases. |
| `internal_reviewer_notes` | list[string] | yes | Reviewer-only notes. Must stay separate from public article content. |
| `evidence_basis` | object | yes | Structured support for the recommendation. |
| `validation_report` | object | yes | KCS-1 embedded validation summary object; standalone validation-report schema is deferred to KCS-5 if needed. |
| `zendesk_source_html` | string or null | optional/default null | Copy/paste artifact when available. It does not imply write/publish permission. |
| `auto_publish_allowed` | boolean | optional/default false | Must be `false` for all MVP packets. `true` is invalid. |

### Cross-packet invariants

- Unknown `schema_version` values are rejected.
- Unknown `recommended_action` values are rejected.
- Unknown `article_type` values are rejected.
- `auto_publish_allowed=true` is rejected.
- Raw Zendesk JSON, customer identifiers, live infrastructure identifiers,
  credentials, raw internal comments, snippets, chunks, vectors, and runtime
  artifacts must not appear in committed fixtures.
- KCS-1 fixtures are already-normalized packet fixtures. KCS-1 does not extract
  facts from raw or clean-ticket prose.
