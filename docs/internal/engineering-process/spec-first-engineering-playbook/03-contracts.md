# Spec-first Engineering Playbook: Contracts

Contracts define exact inputs, outputs, invariants, and stable field meanings.
They are stronger than narrative design notes.

## Contract Rules

- Runtime packets should be JSON-compatible.
- Required fields must be explicit.
- Unknown fields must not silently change behavior.
- Safety flags must be present and false for publish-related output.
- Contract changes require tests and review.

## Slice: KCS reviewer packet generation

## Input Contract

Reviewer packet generation may consume:

```text
Normalized evidence packet
KCS action decision packet
Reviewer renderer packet
Validation report
Reviewer bundle manifest
Related candidate outcome summaries
```

Inputs must already be sanitized and validated by upstream gates.

## Output Contract

Machine-readable packet:

```json
{
  "schema_version": "kcs_showcase_reviewer_packet_v1",
  "source_ticket_ref": "ticket-...",
  "primary_item_ref": "candidate-...",
  "candidate_kcs_action": "flag_existing",
  "reviewer_state": {
    "kcs_ready": true,
    "ready_for_reviewer": true,
    "auto_publish_allowed": false,
    "public_output_approved": false,
    "manual_review_required": true
  },
  "evidence_basis": {},
  "reuse_search": {},
  "validation_results": {},
  "blockers": {},
  "risks": [],
  "related_candidates_summary": [],
  "manual_review_reminder": "..."
}
```

Human-readable packet must contain:

- packet status;
- recommended action;
- readiness and publication boundary;
- evidence basis;
- provenance;
- existing article or draft/block reason;
- validation results;
- related candidates;
- risks and manual review notes.

## Invariants

- `auto_publish_allowed` must be false.
- `public_output_approved` must be false.
- Zendesk write must be false or absent.
- Missing reuse/search must not be represented as completed live search.
- Existing article body must not be implied as source unless explicitly fetched
  through an approved adapter.
- Reviewer packet must not contain raw private input.

## Schema Stability

Schema changes require:

- updated example packet;
- updated tests;
- reviewer note explaining compatibility impact.
