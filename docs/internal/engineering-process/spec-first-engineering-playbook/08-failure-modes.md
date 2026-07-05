# Spec-first Engineering Playbook: Failure Modes

Failure behavior must be designed before implementation. The default is to fail
closed and report a safe, actionable reason.

## Common Failure Modes

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
