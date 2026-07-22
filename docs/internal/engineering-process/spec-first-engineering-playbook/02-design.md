# Spec-first Engineering Playbook: Design

Design explains how the slice should work before code changes begin. Keep it
small enough to review and strict enough to test.

## Design Rules

- State the deterministic owner.
- State where AI may assist, if anywhere.
- State where validation happens.
- State what is persisted.
- State what is never persisted.
- State whether the slice changes runtime behavior or only documentation.

## Slice: KCS reviewer packet generation

## Architecture

```text
Sanitized clean-ticket evidence
        |
        v
Validated semantic extraction or deterministic extraction
        |
        v
KCS action decision
        |
        v
Renderer output
        |
        v
Readiness validation
        |
        v
Reviewer packet writer
        |
        v
reviewer_packet.json / reviewer_packet.md
```

## Deterministic Owner

Python owns:

- packet validation;
- action decision;
- rendering;
- readiness state;
- bundle writing;
- publish-safety flags.

AI may help identify candidate KCS items only through bounded semantic review.
AI must not decide the KCS action, publish state, or output schema.

## Data Flow

Reviewer packet generation consumes already accepted workflow artifacts. It
does not fetch raw tickets, browse public articles, or call an LLM.

## Storage

Allowed:

- reviewer-only local packet files;
- compact bundle manifest;
- safe hashes and relative bundle references.

Forbidden:

- raw ticket text;
- raw transcript bodies;
- credentials;
- private paths;
- unapproved article bodies;
- customer-identifying data.

## Design Constraints

- Prefer typed Python data structures for runtime contracts.
- Use JSON for machine-readable reviewer packet output.
- Use Markdown for human-readable reviewer packet output.
- Keep provenance fields explicit and conservative.
- Do not collapse `explicit_reference_detected` into `live_search_checked`.
