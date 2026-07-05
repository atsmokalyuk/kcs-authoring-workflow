# Feature Note: Review Context Protocol

## Problem

Review quality drops when reviewers receive long chat history, raw artifacts,
unclear changed-file scope, missing contract context, or no explicit statement
of what must not change.

KCS-14 needs a compact review packet protocol that works across Codex,
ChatGPT Pro review, Fable 5 review, and a possible future internal runner.

## Decision

Use `docs/internal/engineering-process/review-context-protocol.md` as the
authoritative protocol for file-based review packets, forbidden-content rules,
output budget, review harness routing, and closeout expectations.

Use `docs/internal/engineering-process/review-packets/` for persistent
file-based review packets when a material or external review needs a durable
artifact.

## Workflow

A material review packet should include:

- review task;
- slice intent;
- changed files;
- affected contracts;
- relevant tests;
- validation;
- known deferred risks;
- what must not change;
- stale context to ignore;
- promotion candidates;
- questions for reviewer.

The packet must stay compact and must not include raw tickets, raw internal
comments, semantic-review excerpt text, reviewer bundle bodies, provider
payloads, credentials, private paths, full logs, or full HTML.

## Not In Scope

- Runtime behavior changes.
- Packet schema changes.
- Desktop/tool schema changes.
- Review packet generator.
- Machine-readable review packet schema.
- Code-map-based diff-to-contract automation.
- Reusable infrastructure extraction.

## Implemented In Slice 4

- `docs/internal/engineering-process/review-context-protocol.md` defines the
  review packet protocol and closeout expectations.
- `docs/internal/engineering-process/review-packets/kcs-14-slice-4-doc-only-review-packet.md`
  is a dry-run file-based review packet.
- `tests/policy/test_review_context_policy.py` checks required packet
  sections and forbidden-content anchors.
- `docs/internal/engineering-process/agent-operable-engineering-workflow.md`
  points review handoff rules to the authoritative protocol.

## Later Use

Slice 5 should add code-map node references to `Affected Contracts` where
practical.

Slice 7 may automate packet generation only after dry-run packets match the
documented protocol and forbidden-content tests remain stable.
