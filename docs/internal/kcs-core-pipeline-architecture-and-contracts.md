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

## KCS-2 Scope Alignment

KCS-2 is limited to safety and sanitized-evidence readiness gates.

KCS-2 includes:

- `safety.py` as the data-boundary gate;
- `validation.py` as evidence/input readiness validation for sanitized
  normalized evidence;
- value-free blockers and warnings suitable for logs and reports;
- no mutation of packet content;
- no sanitizer implementation inside the KCS core.

KCS-2 does not include:

- KCS action decision validation;
- reviewer packet validation;
- Zendesk HTML validation;
- Claude output validation;
- `ready_for_reviewer` loop state.

Responsibility split:

```text
raw ticket
  -> cleanup form / sanitizer lane
  -> operator_sanitized_summary / normalized evidence packet
  -> safety.py
  -> validate_evidence_packet()
  -> KCS-3 decision
```

`validation.py` validates only sanitized evidence readiness. Decision packet
validation belongs to KCS-3, Zendesk HTML validation belongs to KCS-4, and
`ready_for_reviewer` loop validation belongs to KCS-5.

KCS-2 evidence readiness validation returns value-free blockers and warnings.
It must not echo raw evidence values into results or exceptions.

Evidence readiness blockers:

- `unsafe_input`
- `missing_source_ref`
- `missing_issue_candidate`
- `multi_issue`
- `missing_symptoms`
- `missing_confirmed_facts`
- `missing_supported_resolution`
- `open_questions_present`
- `evidence_not_atomic`

Evidence readiness warnings:

- `missing_supported_cause`

## KCS-3 Scope Alignment

KCS-3 is limited to deterministic KCS action decisions from accepted evidence
and structured reuse/search results.

KCS-3 includes:

- `decision.py` as the KCS action decision core;
- `KcsActionDecisionPacket` output;
- per-candidate preliminary split items when multiple atomic candidates are
  present;
- future-safe operator override metadata only;
- value-free blocker codes;
- no mutation of packet content;
- no Zendesk, Claude, MCP, search, renderer, or publish behavior.

KCS-3 decision match convention for `reuse_search_results_packet_v1.matches`:

- `match_ref`: opaque article/reference id.
- `article_type`: `technical_scr`, `howto_qa`, or `none`.
- `identity`: object with `cause`, `question`, and `resolution_or_answer`
  keys as applicable.
- `content_status`: `complete`, `incomplete`, `outdated`, `partial`, or
  `incorrect`.
- `publication_status` / `visibility` / `article_visibility`: optional
  structured metadata such as `public`, `published`, `internal`, or
  `not_public`.

Reuse identity ignores delivery variants such as GUI vs CLI wording. For
Technical SCR articles, identity is same `article_type` plus same
cause-resolution pair. For How-to Q&A articles, identity is same
question-answer pair. GUI instructions are preferred when renderer output is
created later; CLI steps may be added when missing or more optimal, without
creating a separate KCS identity.

When a same-identity existing article needs new content:

- public/published existing article -> `flag_existing`;
- internal or not-public existing article -> `update_existing`.

KCS-3 may recommend the action and selected target only. Updated reviewer
packet or Zendesk HTML content belongs to the KCS-4 renderer slice.

KCS-3 does not implement renderer behavior, local bundle writing, CLI handoff,
Zendesk ingest, Claude drafting, operator-requested draft generation, Zendesk
writes, Help Center publication, or customer reply generation.

KCS-3 operator override metadata preserves the deterministic recommendation.
`operator_override_allowed=true` only means a later reviewer-only draft request
may be accepted by a future slice. It does not generate draft content, approve
public readiness, or change `recommended_action`.

Override metadata must remain disabled for safety and mandatory-evidence
blockers such as unsafe input, raw/sensitive data not cleaned, missing required
resolution/answer, open questions, or missing reuse search status.

Internal-only or public-output-not-safe findings may allow a later
`reviewer_only_draft` override request, but they do not approve public output.
Future local review bundle artifacts must record the override request/status,
preserve the original deterministic recommendation, and keep
`auto_publish_allowed=false`.

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
  status
  split_items
  operator_override_allowed
  allowed_override_modes
  override_status
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

```text
kcs_validation_report_packet_v1 {
  schema_version
  case_ref
  ok
  ready_for_reviewer
  state
  required_next_step
  checks
  blockers
  warnings
  evidence_validation
  decision_summary
  renderer_validation
  reviewer_packet_sha256
  zendesk_source_sha256
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
| `input_class` | enum string | yes | KCS-2 safety gate accepts only `synthetic_fixture`, `approved_sanitized_fixture`, `normalized_zendesk_evidence`, or `operator_sanitized_summary`. |
| `source_refs` | list[string] | yes | Opaque/source-safe references only. No URLs, raw paths, raw ticket IDs, source labels, or private identifiers. |
| `issue_candidates` | list[object] | yes | Candidate issue/question records prepared by the evidence layer. |
| `environment` | object | yes | Normalized safe environment facts. |
| `symptoms` | list[string] | yes | Safe symptom/search wording. Search may use symptoms, but issue identity is not symptom-only. |
| `confirmed_facts` | list[string] | yes | Facts accepted by preparation/validation. |
| `supported_cause` | string or null | optional/default null | Null when no supported cause is available. Must not be invented. |
| `supported_resolution_or_workaround` | string or null | optional/default null | Null when no supported resolution/workaround exists. |
| `open_questions` | list[string] | yes | Safe unresolved questions/blockers. |
| `visibility_summary` | object | yes | Safe visibility/data-handling summary. KCS-2 expects `classes` or `visibility_classes` containing known visibility classes. |
| `sanitizer_report` | object | yes | Sanitizer/preparation status summary. KCS-2 requires an affirmative pass marker and rejects unsafe flags. |

KCS-2 visibility classes:

- `public_customer_safe`: allowed for public/customer-safe evidence.
- `customer_context_only`: allowed for contextual evidence that must not be copied directly into public article content.
- `internal_reviewer_only`: allowed only when internal-only evidence approval is explicit in `visibility_summary`.
- `unsafe_private`: always blocked.

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
| `status` | enum string | optional/default `decision_ready` | `decision_ready`, `split_required`, or `blocked`. Compact state for future local summaries. |
| `split_items` | list[object] | optional/default empty | Preliminary per-candidate decision cards for `split_required`; empty for normal single-candidate decisions. Each item must use only safe summary/title text and value-free blocker codes. |
| `operator_override_allowed` | boolean | optional/default false | Future-slice metadata only. It does not change `recommended_action` and does not generate drafts. |
| `allowed_override_modes` | list[string] | optional/default empty | Future-slice enum strings. KCS-3 may emit `reviewer_only_draft` only for non-safety reviewer-only cases. |
| `override_status` | enum string | optional/default `not_requested` | Override lifecycle marker for future slices. KCS-3 emits `not_requested`. |
| `auto_publish_allowed` | boolean | optional/default false | Must be `false` for all MVP packets. `true` is invalid. |

`split_items` decision card fields:

- `candidate_id`
- `summary`
- `recommended_action`
- `article_type`
- `status`
- `blockers`
- `evidence_basis`
- `selected_reuse_match`
- `reuse_search_status`
- `auto_publish_allowed`
- `operator_override_allowed`
- `allowed_override_modes`
- `override_status`

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
| `validation_report` | object | yes | KCS-4 embedded renderer validation summary object. KCS-5 adds the standalone `kcs_validation_report_packet_v1` readiness report. |
| `zendesk_source_html` | string or null | optional/default null | Copy/paste artifact when available. It does not imply write/publish permission. |
| `auto_publish_allowed` | boolean | optional/default false | Must be `false` for all MVP packets. `true` is invalid. |

### kcs_validation_report_packet_v1

| Field | Type | Required | Notes / invariants |
|---|---|---:|---|
| `schema_version` | string | yes | Must equal `kcs_validation_report_packet_v1`. |
| `case_ref` | string | yes | Opaque case reference from the evidence packet. |
| `ok` | boolean | yes | True only when the report is ready for reviewer handoff. |
| `ready_for_reviewer` | boolean | yes | Same readiness meaning as `state=ready_for_reviewer`. |
| `state` | enum string | yes | `ready_for_reviewer`, `blocked`, `draft_required`, or `review_blocked`. |
| `required_next_step` | enum string | yes | `none`, `fix_evidence`, `run_reuse_search`, `render_reviewer_packet`, `fix_reviewer_packet`, or `review_split_items`. |
| `checks` | list[string] | yes | Value-safe check codes. |
| `blockers` | list[string] | yes | Value-safe blocker codes. |
| `warnings` | list[string] | yes | Value-safe warning codes. |
| `evidence_validation` | object | yes | Compact KCS-2 evidence validation result. |
| `decision_summary` | object | yes | Compact KCS-3 decision summary without raw evidence. |
| `renderer_validation` | object | yes | Compact KCS-4 renderer validation summary. |
| `reviewer_packet_sha256` | string | yes | Deterministic hash when a reviewer packet is present; empty otherwise. |
| `zendesk_source_sha256` | string | yes | Deterministic hash when Zendesk HTML is present; empty otherwise. |
| `auto_publish_allowed` | boolean | optional/default false | Must be `false` for all MVP packets. `true` is invalid. |

### Cross-packet invariants

- Unknown `schema_version` values are rejected.
- Unknown `recommended_action` values are rejected.
- Unknown `article_type` values are rejected.
- `auto_publish_allowed=true` is rejected.
- Unknown `input_class` values are blocked by the KCS-2 safety gate.
- Unsafe or unknown evidence visibility classes are blocked by the KCS-2
  safety gate.
- Sanitizer reports without an affirmative pass marker are blocked by the
  KCS-2 safety gate.
- Raw Zendesk JSON, customer identifiers, live infrastructure identifiers,
  credentials, raw internal comments, snippets, chunks, vectors, and runtime
  artifacts must not appear in committed fixtures.
- KCS-1 fixtures are already-normalized packet fixtures. KCS-1 does not extract
  facts from raw or clean-ticket prose.

## Future Local Output Model

KCS-4/KCS-5/KCS-6 flow:

```text
KCS pipeline run
  -> identifies KCS items
  -> makes decision per item
  -> renders local review bundle
  -> saves files under ticket_<safe_case_ref>/
  -> Claude/CLI shows only a short index/status + local file paths
```

Future Claude/CLI compact summaries may include only:

- bundle folder path;
- item_id;
- short title;
- recommended_action;
- article_type;
- status;
- reason/blocker codes;
- local review packet path;
- local Zendesk HTML draft path, if generated;
- operator_override_allowed / allowed_override_modes;
- auto_publish_allowed=false.

Future Claude/CLI compact summaries must not include:

- full reviewer packet body;
- full Zendesk HTML;
- raw ticket;
- redaction map;
- raw internal comments;
- full evidence basis;
- raw search snippets/chunks/vector values.

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
- approved allowlist and read-only source-client boundary;
- production uses approved internal service endpoint behind the source-client
  protocol;
- local/dev MCP source client is optional and never hardcoded in KCS core;
- raw Zendesk snapshots remain local-only/pre-cleanup and are not KCS-7
  approved exports.

KCS-9:

- Claude Enterprise/Desktop bounded handoff;
- KCS-9a: semantic KCS item identification from approved sanitized context;
- KCS-9b: bounded reviewer-assist handoff contract from compact safe packets;
- KCS-9c: reviewer-only draft generation and artifact writer;
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

- optional debug browser reviewer view if Claude chat review is not enough;
- reads local reviewer bundles as a read-only inspection surface;
- deferred until real ticket or pilot testing shows a browser view is needed.
