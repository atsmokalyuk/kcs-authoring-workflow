# Spec-first Engineering Playbook: Failure Modes

Failure behavior must be designed before implementation. The default is to fail
closed and report a safe, actionable reason.

## Common Failure Modes

- Proposed solution or architecture precedes confirmed target behavior.
- Nominal behavior is treated as demonstrated operational behavior.
- A fixture, documented schema, or neighboring endpoint is treated as proof
  that the exact runtime/API path required by the design is operational.
- Unknown or missing evidence is treated as a default, permission, or success.
- Feature scope requires an excessive material question batch.
- Acceptance criterion has no deterministic, bounded-model, or named
  human-review gate.
- Model-mediated acceptance has no predeclared trial contract or stop rule.
- Outcome agreement, design selection, and Delivery authorization are
  collapsed into one approval.
- An operator decision is requested without sufficient visible information.
- The operator is asked to diagnose uncertainty before autonomous evidence
  gathering.
- An enabling-slice result is treated as parent UX or integration approval.
- Positive continuation wording is treated as authorization for a new slice.
- A material implementation, refactor, deployment, or integration reaches
  closeout without its compact Ousterhout review record.
- Missing required input.
- Unsafe input.
- Incomplete evidence.
- Ambiguous provenance.
- Unsupported action.
- Schema mismatch.
- Renderer safety failure.
- Validation report not ready.
- Runtime write failure.

## Required Failure Properties

- No unsafe value echo.
- No manual/freehand fallback.
- No publish-ready state.
- No Zendesk write.
- No Help Center publication.
- Actionable debug code or blocker code.
- Safe next step for the operator.

## Discovery And Trial Recovery

Before implementation, recover from discovery failures by returning to the
smallest missing decision:

- confirm the target behavior and intended entrypoint;
- record the relevant fact as provisional or unknown;
- ask only the next material question batch;
- narrow the slice when the question batch exceeds five;
- complete the acceptance-to-gate mapping;
- define or revise the bounded trial contract.
- run the bounded safe exact-path smoke before substantial implementation, or
  cite fresh tracked operational evidence for the same endpoint and mode;
- classify unknowns by evidence owner and resolve autonomous ones first;
- prepare the Operator Decision Readiness packet;
- restore the independent approval ledger and keep Delivery locked;
- close an enabling slice as feasibility evidence without inheriting approval
  into its parent design.
- run the compact Ousterhout review, revise the design when required, or record
  a concrete `not triggered` reason for a small leaf change.

For an experimental slice, repeated corrections without movement against the
predeclared threshold are evidence for `stop`, not authorization to add another
unbounded process or observability layer.

## Slice: KCS reviewer packet generation

## Expected Failures

Missing evidence basis:

```text
blocker = reviewer_packet_evidence_basis_missing
```

Missing or unsupported action:

```text
blocker = reviewer_packet_action_invalid
```

Unsafe output value:

```text
blocker = reviewer_packet_safety_failed
```

Ambiguous reuse/search state:

```text
blocker = reviewer_packet_reuse_provenance_ambiguous
```

Publish flag true:

```text
blocker = reviewer_packet_publish_boundary_violation
```

## Fail-closed Output

The failure result should contain:

- `ok=false`
- safe blocker code
- `auto_publish_allowed=false`
- `public_output_approved=false`
- no reviewer public HTML unless already validated safe
- no raw input echo
- next required action
