# KCS-14 Slice 8 Review Node: Desktop Draft Workflow

## Status

Review-only complete.

## Scope

Graph node:

- `desktop_draft_workflow`

Reviewed files:

- `src/kcs_adapters/desktop_draft_tool.py`
- `src/kcs_adapters/desktop_workflow.py`
- `src/kcs_adapters/desktop_operator_selection.py`
- `src/kcs_adapters/desktop_authoring_pipeline.py`
- `src/kcs_adapters/desktop_draft_arguments.py`
- `src/kcs_adapters/desktop_draft_output.py`
- `src/kcs_adapters/desktop_workflow_results.py`
- `src/kcs_adapters/desktop_workflow_status.py`
- `tests/kcs_adapters/test_desktop_draft_tool.py`
- `tests/kcs_adapters/test_desktop_workflow.py`
- `tests/kcs_adapters/test_desktop_operator_selection.py`
- `tests/kcs_adapters/test_desktop_draft_output.py`
- `tests/kcs_adapters/test_desktop_workflow_results.py`
- `tests/kcs_adapters/test_desktop_workflow_status.py`

Related frozen characterization coverage:

- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed.

## Ownership Assessment

The node owns Desktop draft orchestration:

- primary Desktop draft call shape;
- operator selection state;
- semantic-review continuation;
- semantic provider handoff through the approved provider boundary;
- approved-summary authoring pipeline orchestration;
- compact workflow status and controlled result shaping.

The current split is acceptable:

- `desktop_draft_tool.py` owns Desktop-visible state-machine routing for
  summary, `ticket_ref`, operator selection, prepare semantic review, and submit
  semantic review calls.
- `desktop_workflow.py` owns the in-memory workflow object, pending selection
  and semantic-review state, provider handoff, and compatibility exports.
- `desktop_operator_selection.py` owns split-choice state and exact submit
  arguments.
- `desktop_authoring_pipeline.py` owns approved-summary pipeline execution via
  core validators, decision, renderer, and readiness.
- `desktop_draft_arguments.py` owns draft argument normalization and
  fail-closed Desktop primary argument sets.
- `desktop_draft_output.py`, `desktop_workflow_results.py`, and
  `desktop_workflow_status.py` own compact result/status builders.

## Must Not Own

This node must not own:

- clean-ticket storage rules;
- semantic-review schema internals;
- core KCS decision rules;
- Zendesk publication.

The reviewed files preserve those boundaries.

## Ousterhout Lens

- Information hiding: operator selection, semantic-review state, draft argument
  normalization, and workflow result shaping have explicit owner modules.
- Deep modules: `DesktopDraftArticleTool` and `DesktopDraftWorkflow` hide a
  large state machine behind a stable Desktop tool surface.
- Temporal decomposition risk: the existing modules mostly group by knowledge
  ownership, not by "prepare/submit/continue" execution order.
- Change amplification: this node has many contract edges; broad cleanup risks
  touching clean-ticket storage, semantic review, packet decisions, result
  envelopes, and reviewer bundles.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover Desktop draft routing, workflow pipeline stage order,
  operator selection, draft output, workflow results, workflow status, and
  frozen Desktop MCP characterization

Reviewed drift risks:

- Python owns workflow state and validated decisions.
- split/single/block decisions stay deterministic.
- reviewer bundle writing only happens after validated packet decisions allow
  it.
- primary Desktop calls remain fail-closed to `ticket_ref`, short
  `approved_summary_text`, or exact operator-selection refs.
- manual/freehand drafting remains blocked.

Review-only drift risks:

- `desktop_workflow.py` still carries compatibility reexports for older import
  paths. Removing those exports is not a refactor-only change unless import
  contracts are explicitly reviewed.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Slice 6 already performed many targeted behavior-preserving batches inside this
node. The aggregate reviews stopped further node mining because remaining
changes lacked a concrete ownership question.

Future work should require a narrow question, such as:

- Should compatibility reexports from `desktop_workflow.py` be retired through
  an explicit import-contract slice?
- Should result-shaping ownership be consolidated only after a concrete
  repeated conflict appears?
- Should frozen Desktop characterization tests be refactored in a separately
  approved test-maintainability slice?

No current blocker justifies code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Nodes

Aggregate this pair before opening deferred-risk nodes.
