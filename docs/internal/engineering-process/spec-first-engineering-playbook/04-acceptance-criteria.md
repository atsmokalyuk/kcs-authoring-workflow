# Spec-first Engineering Playbook: Acceptance Criteria

Acceptance criteria define what must be true before merge. They should be
observable, testable, and reviewable.

## Slice Template

```markdown
# Slice: <name>

## Must be true before merge
- ...

## Must not happen
- ...

## Evidence required
- ...
```

## Slice: KCS reviewer packet generation

## Must Be True Before Merge

- Reviewer packet JSON validates.
- Reviewer packet Markdown is readable without access to raw runtime logs.
- Packet states the selected KCS action.
- Packet states readiness and manual review status.
- Packet states `auto_publish_allowed=false`.
- Packet states `public_output_approved=false`.
- Packet distinguishes explicit-reference detection from live reuse/search.
- Packet records blockers for unsafe or incomplete candidates.
- Packet records related candidate outcomes.
- Tests cover happy path and forbidden path behavior.

## Must Not Happen

- No raw ticket body is written into the packet.
- No private path is written into the packet.
- No credential or token is written into the packet.
- No existing KB article body is treated as source unless approved.
- No output implies Zendesk write readiness.
- No output implies Help Center publication readiness.
- No LLM freehand article text bypasses Python validation.

## Evidence Required

- JSON validation command.
- Targeted tests for reviewer packet generation.
- `git diff --check`.
- Privacy boundary review note.
- Contract preservation or intentional contract-change note.
