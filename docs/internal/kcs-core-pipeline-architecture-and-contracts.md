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
+----------------+     +------------------------+     +-----------------+
| Source adapter | --> | Sanitizer / normalizer | --> | Evidence packet |
+----------------+     +------------------------+     +-----------------+
                                                            |
                                                            v
+-----------------+     +----------+     +-----------------------+
| Reviewer packet | <-- | KCS core | <-- | Search / reuse packet |
+-----------------+     +----------+     +-----------------------+
```

## Core principle
- Code decides
- LLM drafts
- Validators block

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

## Article types
- technical_scr
- howto_qa
- none
