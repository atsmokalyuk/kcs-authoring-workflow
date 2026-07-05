# Spec-first Engineering Playbook: Clarifications

Use this file before implementation to remove ambiguity from a slice. Do not
start code work until the slice has a bounded goal, operator, allowed inputs,
forbidden inputs, output contract, and failure behavior.

## Slice Template

```markdown
# Slice: <name>

## Goal
What are we building?

## User / operator
Who uses this?

## Allowed inputs
What data may enter?

## Forbidden inputs
What must never enter?

## Output contract
What must be produced?

## Failure behavior
How should it fail closed?

## Tests / evals
What proves correctness?

## Acceptance criteria
What must be true before merge?

## Review checklist
What should reviewer verify?
```

## Slice: KCS reviewer packet generation

## Goal

Produce reviewer-only KCS packets from accepted, sanitized workflow outputs.
The packet must explain the recommended KCS action, evidence basis, validation
state, blockers, risks, and manual review boundary.

## User / operator

- Support engineer preparing KCS output.
- KCS reviewer checking whether the output is ready for review.
- Technical lead auditing the workflow behavior.

## Allowed inputs

- Sanitized clean-ticket evidence.
- Validated semantic extraction output.
- Deterministic KCS action decision.
- Renderer output.
- Readiness validation report.
- Local reviewer bundle metadata.
- Explicit existing-article references detected from sanitized evidence.

## Forbidden inputs

- Raw Zendesk ticket bodies.
- Raw internal comments.
- Credentials, tokens, private endpoints, private paths.
- Unsanitized customer identifiers.
- Existing public KB article body unless fetched by an approved read-only
  adapter and explicitly marked as source evidence.
- LLM-generated article prose that bypasses Python validation.

## Output contract

The packet must include:

- `candidate_kcs_action`
- reviewer readiness state
- bundle manifest or bundle reference
- evidence basis
- reuse/search or reuse-evidence provenance
- draft, update, flag, no-article, or blocker content summary
- blockers
- risks
- related candidate outcomes
- manual review reminder
- `auto_publish_allowed=false`
- `public_output_approved=false`

## Failure behavior

Fail closed when:

- required packet fields are missing;
- unsafe values are detected;
- provenance is ambiguous;
- reuse/search state is overstated;
- candidate evidence is incomplete;
- output would imply publish readiness.

## Tests / evals

- Golden reviewer packet fixture.
- JSON schema or typed model validation.
- Tests for missing required fields.
- Tests for unsafe input echo blocking.
- Tests for `flag_existing`, `draft_only`, and blocked candidates.
- Tests proving no Zendesk write and no auto-publish.

## Acceptance criteria

- Reviewer packet is machine-readable and human-readable.
- Output is reviewer-only.
- Public output is not approved.
- Auto-publish is disabled.
- Provenance is explicit.
- Failure states are actionable and safe.

## Review checklist

- Does the packet satisfy the output contract?
- Does it preserve the privacy boundary?
- Does it fail closed?
- Does it avoid unsafe input echo?
- Is the output schema stable?
- Are happy and forbidden paths covered by tests?
- Did AI invent behavior outside the spec?
