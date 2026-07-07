# KCS-14 Slice 6 Result-Shaping Ownership Decision

Status: active ownership gate for Slice 6.

Purpose: record the result-shaping boundary before refactoring
`desktop_draft_workflow`, `desktop_tool_surface`, or result/status/output
files. This decision is behavior-preserving guidance; it does not authorize
runtime behavior changes.

## Decision

Protocol envelope ownership:

- `src/kcs_adapters/desktop_mcp_results.py` owns the MCP tool-result envelope:
  `content`, `isError`, `structuredContent`, `McpToolResult`, and
  `tool_error`.
- It may validate the structured payload against the descriptor output schema
  before building the envelope.
- It must not own workflow status semantics, KCS decisions, draft readiness,
  reviewer-bundle meaning, or article/output policy.

Desktop-visible tool-result presentation ownership:

- `src/kcs_adapters/desktop_tool_results.py` owns Claude Desktop-visible tool
  result text, compact `structuredContent` filtering, result payload safety,
  output-size limits, HTML visibility rules, and forbidden-key/fragment gates.
- It may translate a validated structured workflow result into compact
  Desktop-facing text and structured content.
- It must not decide whether a draft should exist, whether semantic review is
  required, whether reuse was checked, whether publication is allowed, or
  whether a reviewer bundle should be written.

Workflow status and compact result semantics ownership:

- `src/kcs_adapters/desktop_workflow_results.py` owns workflow failure/status
  result semantics such as `failure_stage`, `debug_code`, blockers,
  `recommended_action`, semantic-review breakpoint results, operator selection
  results, and split-required results.
- `src/kcs_adapters/desktop_workflow_status.py` owns approved-summary pipeline
  status and reuse-search status semantics.
- `src/kcs_adapters/desktop_draft_output.py` owns compact draft result shaping
  from validated authoring result plus reviewer bundle metadata, including
  quality-blocked draft output.
- These modules may build structured result dictionaries for downstream
  Desktop presentation.
- They must not own MCP envelope fields, Desktop descriptor/schema validation,
  text rendering for Claude Desktop, or generic forbidden-payload scanning.

Adjacent layer boundaries:

- `desktop_draft_workflow` orchestration may call workflow/draft result
  builders, but must not inline presentation text, MCP envelope keys, or
  descriptor validation rules.
- `desktop_tool_surface` may wire descriptors, names, schemas, and tool calls,
  but must not duplicate workflow status semantics or presentation text policy.
- `desktop_protocol_transport` may pass MCP envelopes across JSON-RPC/stdio
  boundaries, but must not inspect workflow decisions or Desktop-visible text
  policy.
- Core modules remain owners of KCS decisions, validation, rendering, and packet
  semantics; adapter result-shaping modules must not reinterpret those
  decisions.

## Boundary Questions

What complexity are we hiding?

- The distinction between workflow semantics, Desktop presentation, and MCP
  protocol envelope construction.

What should each module not know?

- Workflow result builders should not know MCP envelope details.
- MCP envelope builders should not know KCS workflow semantics.
- Desktop presentation gates should not know provider, storage, or core
  decision internals.

What input is allowed?

- Structured workflow result dictionaries that have already been produced by
  the approved adapter/core workflow.
- MCP descriptor output schemas for validation at the envelope boundary.
- Reviewer bundle metadata that has already been validated/written by the
  workflow.

What input is forbidden?

- Raw ticket text, provider payload bodies, private logs, credentials, local
  paths outside approved compact refs, unpublished Zendesk write intents, and
  unvalidated article bodies.

What output contract is stable?

- MCP responses keep the current `content`, `isError`, and
  `structuredContent` envelope.
- Desktop tool-result text and compact structured content remain value-safe and
  bounded.
- Workflow result dictionaries keep current status, blocker, debug-code, and
  next-action semantics unless a later behavior-change slice explicitly
  approves a change.

What failure mode must be explicit?

- Schema mismatch, forbidden payload content, too-large tool results, blocked
  draft status, semantic-review requirements, operator-selection requirements,
  and reviewer HTML quality blockers remain explicit value-safe failures.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_protocol_results.py`
- `tests/kcs_adapters/test_desktop_draft_output.py`
- `tests/kcs_adapters/test_desktop_workflow_results.py`
- `tests/kcs_adapters/test_desktop_draft_tool.py`
- `tests/kcs_adapters/test_mcp_desktop.py`
- `tests/policy/test_kcs14_freeze_snapshots.py`

## Refactor Rule

Future Slice 6 refactor batches that touch these files must state which owner
is being simplified:

- envelope owner: `desktop_mcp_results.py`;
- Desktop presentation/safety owner: `desktop_tool_results.py`;
- workflow semantics owner: `desktop_workflow_results.py`,
  `desktop_workflow_status.py`, or `desktop_draft_output.py`.

If a batch needs to move logic across those ownership groups, it must call that
out as the declared scope before editing code. Otherwise, graph/file hash
updates may travel with the code commit, but ownership-definition changes must
remain separate.

## Non-Goals

- No packet schema changes.
- No Desktop tool schema changes.
- No customer reply, Zendesk write, Help Center publish, or auto-publish path.
- No KCS-15 style/markup parity work.
- No Architecture Patterns with Python activation; this decision does not
  diagnose an `architecture_error`.
