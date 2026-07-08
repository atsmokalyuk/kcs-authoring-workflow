# KCS-14 Slice 8 Review Node: Desktop Protocol And Transport

## Status

Review-only complete.

## Scope

Graph node:

- `desktop_protocol_transport`

Reviewed files:

- `src/kcs_adapters/desktop_jsonrpc.py`
- `src/kcs_adapters/desktop_protocol.py`
- `src/kcs_adapters/desktop_stdio_transport.py`
- `src/kcs_adapters/desktop_payload.py`
- `src/kcs_adapters/desktop_mcp_results.py`
- `tests/kcs_adapters/test_desktop_stdio_transport.py`
- `tests/kcs_adapters/test_desktop_payload.py`
- `tests/kcs_adapters/test_desktop_protocol_results.py`

Related frozen characterization coverage:

- `tests/kcs_adapters/test_mcp_desktop.py`

No runtime code was changed.

## Ownership Assessment

The node owns the Desktop protocol and transport boundary:

- JSON-RPC request parsing and safe initialize metadata;
- MCP initialize response metadata and instructions;
- stdio transport dispatch and tool-call envelope;
- approved-summary payload normalization;
- MCP tool result envelope conversion.

The current split is acceptable:

- `desktop_jsonrpc.py` owns JSON-RPC parsing, request-id validation, and
  protocol error responses.
- `desktop_protocol.py` owns MCP protocol metadata and initialize instructions.
- `desktop_stdio_transport.py` owns transport state, initialization, method
  dispatch, tool name style, and descriptor payload conversion.
- `desktop_payload.py` owns approved-summary argument and payload normalization.
- `desktop_mcp_results.py` owns the MCP result envelope from adapter tool
  results to Desktop-visible content and structured content.

## Must Not Own

This node must not own:

- KCS workflow decisions;
- tool schema business rules;
- semantic-review validation;
- provider calls.

The reviewed files preserve those boundaries.

## Ousterhout Lens

- Information hiding: transport exposes a small JSON-RPC/MCP surface and hides
  line parsing, initialization state, alias conversion, and result envelopes.
- Deep modules: `desktop_payload.py` is dense, but it owns real argument and
  payload normalization rules rather than acting as a pass-through.
- Change amplification: protocol-envelope changes can look internal while
  changing Desktop behavior; snapshot/frozen tests should remain the gate.
- Shallow abstraction risk: further splitting should avoid pass-through helpers
  around JSON-RPC and MCP envelope behavior.

## Behavior Drift Check

Behavior change intended:

- no

Mechanical checks:

- no source files changed in this review
- related tests cover stdio initialization/tool listing/calls, payload
  validation, protocol result shaping, and frozen Desktop MCP characterization

Reviewed drift risks:

- transport remains a protocol boundary.
- payload helpers do not expose raw ticket or provider payload bodies.
- protocol changes do not alter KCS decisions.
- Desktop tool alias behavior remains owned by the tool-surface/name layer, not
  by workflow code.

Review-only drift risks:

- MCP initialize instructions duplicate some packaged/tool guidance. Future
  changes should be checked against Desktop tool snapshots and packaging tests.

Verdict:

- no drift found by listed checks; residual risks are listed above.

## Refactor Decision

Do not refactor this node now.

Slice 6 already covered targeted protocol work for stdio constants and
approved-summary alias tables. Further changes should require a narrow question,
such as:

- Should initialize instructions be generated or checked against a shared
  source with package guidance?
- Should MCP result-envelope behavior move closer to `desktop_tool_results`
  without changing Desktop structured content?

No current blocker justifies code movement.

## Promotion And Demotion Candidates

- Promotion candidates: none.
- Demotion candidates: none.

## Next Recommended Node

Review `desktop_draft_workflow`.
