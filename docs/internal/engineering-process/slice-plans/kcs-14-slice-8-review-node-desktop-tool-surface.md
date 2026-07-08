# KCS-14 Slice 8 Review Node: desktop_tool_surface

Status: review-only complete.

## Scope

Graph node:

- `desktop_tool_surface`

Node owns:

- Desktop MCP tool registration;
- Desktop-visible input schemas;
- Desktop protocol result shaping.

Node must not own:

- KCS action decisions;
- semantic candidate validation policy;
- article rendering policy;
- reviewer bundle persistence.

Files reviewed:

- `src/kcs_adapters/mcp_desktop.py`
- `src/kcs_adapters/desktop_tool_schemas.py`
- `src/kcs_adapters/desktop_tool_results.py`
- `src/kcs_adapters/desktop_mcp_adapter.py`
- `src/kcs_adapters/desktop_authoring_tools.py`
- `src/kcs_adapters/desktop_control_tools.py`
- `src/kcs_adapters/desktop_tool_descriptors.py`
- `src/kcs_adapters/desktop_tool_names.py`

Related tests and gates:

- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/kcs_adapters/test_desktop_mcp_adapter.py`
- `tests/kcs_adapters/test_desktop_protocol_results.py`
- `tests/kcs_adapters/test_desktop_authoring_tools.py`
- `tests/kcs_adapters/test_desktop_control_tools.py`
- `tests/policy/test_kcs14_freeze_snapshots.py`

## Review Question

Does `desktop_tool_surface` need immediate behavior-preserving refactor, or
should it remain protected by snapshots until a concrete ownership question is
declared?

## Current Protection

This node is already protected by Slice 6 commit-0 freeze/snapshot checks:

- Desktop `tools/list` names, aliases, input properties, required fields, and
  read-only hints;
- packet schema/version/field-set snapshots;
- compact-result key-set snapshots;
- frozen contract path checks.

The result-shaping ownership decision is also written and active:

- MCP envelope ownership: `desktop_mcp_results.py`;
- Desktop presentation and safety ownership: `desktop_tool_results.py`;
- workflow status/result semantics: `desktop_workflow_results.py`,
  `desktop_workflow_status.py`, and `desktop_draft_output.py`.

## Findings

The node has high contract risk because schema/result drift changes Desktop
behavior even when core KCS decisions remain correct.

No immediate refactor target is justified from this review alone:

- the important contract surfaces are already snapshotted;
- broad source movement would risk Desktop/tool schema behavior;
- result-shaping ownership is documented, but moving logic across those
  boundaries would need its own declared slice;
- `tests/kcs_adapters/test_mcp_desktop.py` remains a frozen characterization
  suite and should not be refactored as part of this node review.

Potential future ownership questions:

- Are `desktop_tool_descriptors.py`, `desktop_tool_schemas.py`, and
  `desktop_tool_names.py` still the right split for tool identity, schemas, and
  descriptions?
- Does `desktop_tool_results.py` hide Desktop presentation/safety complexity
  behind a small enough interface?
- Are any result-shaping rules duplicated between tool-surface files and
  workflow-result files?

These are review questions. They do not yet authorize code movement.

## Ousterhout Lens

The current split appears ownership-based rather than purely temporal:

- names own identity and alias mapping;
- schemas own input/output schema surfaces;
- descriptors own tool descriptors;
- MCP adapter registers and exposes tools;
- tool results own Desktop-visible compact presentation and safety filtering.

The main risk is information leakage between tool result presentation and
workflow semantics. The existing result-shaping ownership decision is the right
guardrail. Future refactors should use that decision before moving code.

## Behavior Drift Check

Behavior change intended:

- no.

Mechanical checks:

- freeze/snapshot policy tests protect Desktop tool list, schema, packet, and
  compact-result contracts;
- graph hash checks protect this node from stale orientation.

Reviewed drift risks:

- no source files changed;
- no Desktop/tool schema changed;
- no result-shaping ownership moved.

Review-only drift risks:

- if a later refactor moves logic between descriptor/schema/result modules,
  snapshot checks can show public stability, but review must still inspect
  whether ownership became clearer or leaked workflow knowledge.

Verdict:

- no code refactor should start for this node without a narrower ownership
  question.

## Decision

Status for this node:

- `review-only-complete`.

Recommended action:

- keep current structure;
- preserve freeze/snapshot checks as the main mechanical gate;
- open a future node-specific refactor only if it names one of the ownership
  questions above and includes behavior-drift mapping.

Promotion candidates:

- none. Existing freeze/snapshot and behavior-drift mapping rules already cover
  the mechanically checkable part.

Demotion candidates:

- none. No noisy snapshot or policy check appeared in this review.

## Next Node

Recommended next review-only node:

- `clean_ticket_storage`

Reason:

- high-value proven workflow path;
- strong safety/path-contract surface;
- smaller node than semantic/reviewer/packet validation boundaries.
