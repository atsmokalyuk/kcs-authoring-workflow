# KCS-14 Slice 9 Final Closeout: Targeted Runtime Design Debt

## Status

Slice 9 targeted runtime design-debt work is complete.

## Purpose

Slice 9 was added after Slice 8 because the operator did not want to leave the
most critical KCS authoring runtime files with only review-only coverage before
moving to KCS-15.

The goal was not to refactor every file. The goal was to inspect the highest
runtime-risk ownership nodes and reduce clear Ousterhout-style design debt only
where behavior-preserving movement was defensible.

## Scope Completed

### Target 1: Packet Validation Decision

Artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-1-packet-validation-decision-audit.md`

Outcome:

- audit-only;
- no source refactor opened;
- current validation, safety, model, and decision boundaries remain coherent.

### Target 2: Semantic Review Fallback

Artifacts:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-2-semantic-review-fallback-audit.md`
- `src/kcs_adapters/desktop_semantic_review_submission.py`

Outcome:

- extracted semantic-review submit validation into a private owner;
- kept Desktop semantic-review public API stable;
- kept provider output untrusted until Python validation.

### Target 3: Reviewer Bundle Output

Artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-3-reviewer-bundle-output-audit.md`

Outcome:

- extracted Desktop reviewer-bundle manifest construction into a private helper;
- kept bundle writing, relative paths, manifest shape, and compact output
  behavior stable.

### Target 4: Renderer Style Gates

Artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-4-renderer-style-gates-audit.md`

Outcome:

- audit-only;
- no source refactor opened;
- renderer/style gates remain deferred to KCS-15 behavior specs and acceptance
  cases.

### Target 5: Provider Approved Summary Resolution Triggers

Artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-5-provider-handoff-boundary-approved-summary.md`

Outcome:

- extracted approved-summary config-resolution trigger checks into private
  predicates;
- kept resolution-step order and wording stable;
- reduced provider target max complexity from `cc=25` to `cc=19`.

### Target 6: Provider Runtime Config Validation

Artifact:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-target-6-provider-runtime-config.md`

Outcome:

- extracted runtime endpoint, API-key, and response-size validation into
  private predicates;
- kept `DirectHttpRuntimeConfig` public fields, `repr`, and runtime-only
  credential boundaries stable;
- reduced provider target max complexity from `cc=19` to `cc=14`.

## Aggregate Reviews

Artifacts:

- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-aggregate-review-targets-2-3.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-aggregate-review-targets-4-5.md`
- `docs/internal/engineering-process/slice-plans/kcs-14-slice-9-aggregate-review-target-6.md`

Aggregate outcomes:

- no `map_error`;
- no blocker `process_error`;
- no `architecture_error`;
- Architecture Patterns with Python was not activated;
- renderer/style gates deferred to KCS-15;
- provider-boundary source refactor stopped once remaining hotspots became
  domain extraction or safety-validation behavior.

## Ousterhout Outcome

Complexity was reduced where the code had a clear private ownership boundary:

- submit validation moved out of the broader semantic-review adapter;
- Desktop reviewer-bundle manifest construction got one private owner;
- provider approved-summary trigger detection got named predicates;
- provider runtime config validation got named private owners.

Large/deep modules were intentionally preserved where splitting would increase
interfaces or blur behavior ownership:

- packet validation and decision boundaries;
- renderer/style gates before KCS-15 specs;
- remaining approved-summary domain extraction behavior;
- safety validators in draft/handoff code without new behavior examples.

## Behavior Drift Summary

Behavior changes intended:

- none.

Mechanical evidence:

- semantic-review and Desktop characterization tests passed after Target 2;
- reviewer-bundle and Desktop bundle tests passed after Target 3;
- renderer/style focused tests passed for Target 4;
- provider-boundary focused tests passed after Targets 5 and 6;
- graph and freeze policy checks passed after each source target.

Review evidence:

- old-to-new behavior mappings were recorded for each source refactor target;
- no test assertion edits were made;
- graph ownership text did not change;
- source changes stayed inside declared graph nodes;
- aggregate reviews found no architecture escalation signal.

## Final Sensor Snapshot

Final sensor for provider and renderer/style target files:

```text
files_scanned: 8
functions_total: 415
cc_average: 3.32
max_cc: 14
high_complexity_functions: 17
import_edges: 3
public_defs: 72
all_exports: 0
```

Top remaining complexity:

- `approved_summary_semantic.py:_semantic_item_from_approved_summary_section`
  with `cc=14`
- `approved_summary_semantic.py:_monitoring_symptoms_from_text` with `cc=12`
- `claude_provider.py:_ensure_safe_runtime_endpoint_url` with `cc=11`
- `zendesk_markup_quality.py:_interactive_markup_findings` with `cc=11`
- `claude_draft.py:_validate_accepted_response_shape` with `cc=11`

These remaining hotspots are domain extraction, renderer/style behavior, or
safety validation. They are parked until an explicit behavior question exists.

## Contracts Preserved

- runtime behavior unchanged;
- packet schemas unchanged;
- Desktop/tool schemas unchanged;
- compact output behavior unchanged;
- renderer output unchanged;
- markup-quality gate behavior unchanged;
- provider output remains untrusted;
- Python validators still own packet acceptance;
- provider runtime endpoints and credentials remain out of serializable packets;
- privacy boundaries unchanged;
- fail-closed behavior unchanged;
- reviewer-bundle locality unchanged;
- publication/customer-reply behavior remains absent;
- `auto_publish_allowed=false`;
- `ticket_ref` primary path remains stable;
- freehand drafting remains blocked.

## Validation Evidence

- `uv run pytest tests/kcs_adapters/test_mcp_desktop.py tests/kcs_adapters/test_desktop_semantic_candidates.py tests/kcs_core/test_semantic_extraction.py tests/kcs_adapters/test_approved_summary_semantic.py tests/kcs_adapters/test_claude_provider.py tests/kcs_core/test_claude_draft.py tests/kcs_core/test_claude_handoff.py tests/kcs_core/test_renderer.py tests/kcs_adapters/test_zendesk_markup_quality.py tests/kcs_core/test_reviewer_bundle.py tests/kcs_adapters/test_desktop_reviewer_preview.py tests/kcs_adapters/test_desktop_draft_output.py -q`
  passed.
- `uv run pytest tests/policy/test_code_review_graph_policy.py tests/policy/test_kcs14_freeze_snapshots.py tests/policy/test_review_context_policy.py -q`
  passed.

## Promotion And Demotion Scan

Promotion candidates:

- `KCS14-PROMO-010` remains the only new Slice 9 promotion candidate: frozen
  path implementation touches need an explicit behavior-preserving protocol.

Demotion candidates:

- none.

## Carry-Over

- KCS-15 should own renderer/style/markup behavior changes with examples and
  acceptance cases.
- Remaining approved-summary extraction complexity needs behavior examples
  before further movement.
- Remaining safety-validator complexity in `claude_draft.py` and
  `claude_handoff.py` should not be split without an explicit behavior question.
- `DirectHttpRuntimeConfig` endpoint validation remains a private `cc=11`
  predicate and is acceptable because it owns one validation family.

## Final Verdict

Slice 9 achieved the targeted runtime design-debt objective.

The branch is ready for an external review checkpoint or final KCS-14 closeout
decision. Do not continue source refactor by mining files for small edits.
