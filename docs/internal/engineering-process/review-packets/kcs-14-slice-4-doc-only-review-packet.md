# KCS-14 Slice 4 Review Packet

## Review Task

Review the Slice 4 process/docs/test change for the review-context protocol and
promotion-candidate registry.

## Slice Intent

Define a compact review packet protocol and an explicit promotion-candidate
workflow so recurring review findings can move from notes to checklist items,
tests, tools, freeze checks, or reusable-infrastructure candidates.

## Changed Files

- `AGENTS.md`
- `docs/internal/engineering-process/review-context-protocol.md`
- `docs/internal/engineering-process/promotion-candidates.md`
- `docs/internal/engineering-process/review-packets/kcs-14-slice-4-doc-only-review-packet.md`
- `docs/internal/engineering-process/kcs-14-review-notes.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-engineering-and-codebase-design-hardening.md`
- `tests/policy/test_review_context_policy.py`

## Affected Contracts

- KCS-14 engineering process docs.
- KCS-14 review packet expectations.
- KCS-14 promotion-candidate closeout expectations.

Runtime packet contracts, Desktop tool schemas, reviewer-bundle runtime
behavior, publication behavior, and customer-reply behavior are unchanged.

## Relevant Tests

- `tests/policy/test_kcs14_docs_policy.py`
- `tests/policy/test_tool_entrypoints.py`
- `tests/policy/test_functional_test_policy.py`
- `tests/policy/test_review_context_policy.py`

## Validation

Run the policy test group and Ruff on touched policy tests before commit.

## Known Deferred Risks

- Slice 5 still needs the code-review graph baseline.
- Slice 7 still decides which stable manual checks become tooling.
- Reusable extraction remains deferred until after a later retrospective.

## Must Not Change

- Runtime behavior.
- Packet schemas.
- Desktop/tool schema behavior.
- Privacy and fail-closed boundaries.
- Reviewer-bundle runtime behavior.
- Zendesk writes, Help Center publication, customer replies, and auto-publish
  boundaries.

## Stale Context To Ignore

- Earlier pre-renumbering references that used the old active-slice label.
- Older planning notes that treated unavailable development harnesses as
  active.
- Chat-only review notes superseded by tracked KCS-14 planning decisions and
  review notes.

## Promotion Candidates

This slice introduces the promotion-candidate registry. It does not promote a
new runtime rule.

## Questions For Reviewer

- Does the packet format contain enough context for staged-diff review?
- Does the promotion cadence avoid premature automation?
- Are forbidden-content boundaries clear without duplicating runtime contracts?
