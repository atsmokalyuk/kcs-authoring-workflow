# Feature Note: Enforcement Ladder And Promotion Workflow

## Problem

KCS-14 introduces many process rules. If they stay only as prose, future agents
can miss them, repeat old review findings, or keep fixing the same problem
manually.

At the same time, promoting every rule immediately into blocking checks would
create noise, false positives, and automation around an unstable process.

## Decision

Use an explicit enforcement ladder:

```text
tracked Markdown rule
  -> policy test
  -> tool entrypoint
  -> functional/contract test
  -> code map / freeze-list / hash check
  -> later automation or reusable infrastructure
```

Markdown is the first authority layer, not the final enforcement layer.
Mechanically checkable and stable rules should move toward deterministic
checks. Design judgment stays in review.

## Grounding

`docs/internal/engineering-process/references.md` grounds this feature:

- enforcement ladder and blocking/advisory split: Tricorder and SWE at Google;
- prose-to-check promotion: SWE at Google and kaizen synthesis;
- recurring finding -> check/boundary candidate: kaizen synthesis and
  Tricorder;
- closeout metadata: Accelerate and DORA;
- approval/change-control gates: NIST AI RMF and ISO/IEC 42001.

Fable review suggested the compact ladder wording:

```text
structural -> deterministic -> review gate -> measurement
```

Fable is not the source of truth; it provided useful packaging for rules
grounded in references and local planning decisions.

## Promotion Workflow

The agent does not decide promotion by intuition.

```text
agent detects and proposes
  -> promotion gate classifies
  -> operator/reviewer approves material promotion
  -> small scoped action or commit implements it
  -> validation proves the stronger enforcement
```

The agent must check for candidates:

- during staged-diff review;
- during slice closeout before commit;
- after repeated validation or review failure with the same cause.

Every material closeout must say either:

```text
Promotion candidates: none
```

or list the candidates.

## Promotion Readiness

The agent must propose a candidate when any trigger is true:

- the same finding code appears in two or more material slice reviews or
  closeouts;
- the same validation or review failure happens two or more times in one
  material slice;
- the same command or check is required in three or more consecutive slices;
- a rule is stable, mechanically checkable, and low false-positive risk;
- a runtime or safety contract is repeatedly checked manually;
- a reviewer explicitly asks for a test, tool, freeze-list check, code-map
  entry, or reusable-infrastructure candidate.

The agent must not implement promotion automatically when promotion changes
runtime behavior, adds broad tooling, has medium/high false-positive risk,
requires design judgment, misclassifies KCS-specific rules as generic
infrastructure, or touches unrelated files.

Implicit approval is allowed only when all must-not conditions are false and
the diff is limited to `tests/policy/` plus the current slice's process docs.

AI reviewer suggestions may trigger a proposal, but model output never grants
implicit approval.

## Registry As Memory

Promotion counts must come from tracked artifacts, not chat memory:

```text
docs/internal/engineering-process/promotion-candidates.md
docs/internal/engineering-process/kcs-14-review-notes.md
```

Use stable value-safe finding codes:

```text
KCS14-PROMO-NNN
```

Without a finding code or closeout entry, a finding does not count toward the
repeated-finding threshold.

## Probation And Demotion

New deterministic checks should run advisory for one slice before becoming
blocking, unless they directly lock in the current slice's accepted outcome.

A blocking check that produces a false positive must be demoted to advisory and
recorded in the promotion registry before it can become blocking again.

Candidates in `note`, `checklist-item`, `candidate`, or `deferred` status
expire after three completed slices without new evidence.

## Not In Scope

- Runtime behavior changes.
- Packet schema changes.
- Desktop/tool schema changes.
- Broad policy-test framework.
- Wrapper CLI or review-packet generator.
- Code map, freeze-list, or schema-hash implementation.
- KCS-15 style/markup parity.
- Reusable infrastructure extraction before a KCS-14/KCS-15 retrospective.

## Implemented In Slice 4

- `docs/internal/engineering-process/review-context-protocol.md`: review
  packet protocol, output budget, forbidden content, promotion gates, and
  probation/demotion rules.
- `docs/internal/engineering-process/promotion-candidates.md`: promotion
  registry and implemented promotion list.
- `docs/internal/engineering-process/review-packets/kcs-14-slice-4-doc-only-review-packet.md`:
  dry-run file-based review packet.
- `tests/policy/test_review_context_policy.py`: policy tests for packet shape,
  forbidden-content anchors, promotion fields, cadence, checkpoint anchors,
  and finding-code integrity.
- `AGENTS.md`: compact pointer requiring the development agent to surface
  repeated or mechanically checkable findings as promotion candidates.

## Later Use

Slice 5 should use this ladder when code-map review reveals repeated
orientation or ownership problems.

Slice 6 should use it when refactor review repeatedly checks the same
freeze-list, schema, Desktop/tool-surface, or privacy boundary.

Slice 7 should automate only promoted, stable, mechanically checkable rules
from the registry.

KCS-16 or a downstream Personal Agentic Engineering Kit may extract only the
generic parts after the workflow proves useful outside this project.
