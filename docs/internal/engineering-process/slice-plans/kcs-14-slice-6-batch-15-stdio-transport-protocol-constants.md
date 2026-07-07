# KCS-14 Slice 6 Batch 15 Stdio Transport Protocol Constants

Status: ready for staged-diff review.

## Objective

Start a new `desktop_protocol_transport` refactor pass after the aggregate gate
stopped same-node `desktop_draft_workflow` momentum. The target is inline
transport method/key sets in `McpStdioTransport`.

Target:

```text
src/kcs_adapters/desktop_stdio_transport.py
```

## Boundary Questions

What complexity are we hiding?

- The small JSON-RPC transport rule sets for supported tool-name styles,
  pre-initialize methods, and tool-call parameter keys.

What should this module not know?

- KCS workflow decisions, semantic-review validation, tool schema business
  rules, provider behavior, packet schemas, or Zendesk publication behavior.

What input is allowed?

- Existing JSON-RPC method names, tool-call parameter names, and configured
  transport tool-name styles.

What input is forbidden?

- New Desktop schema fields, new tool-call parameters, raw ticket bodies,
  provider payload bodies, credentials, and publication/write intents.

What output contract is stable?

- JSON-RPC responses, MCP tool result envelopes, error messages, and
  initialize/ping readiness behavior remain stable.

What failure mode must be explicit?

- Unsupported tool-name style remains `ValueError`.
- unexpected tool-call parameter remains `McpArgumentError`.
- uninitialized transport still returns server-not-initialized for non-ready
  methods.

What test proves the boundary?

- `tests/kcs_adapters/test_desktop_stdio_transport.py`.
- `tests/kcs_adapters/test_mcp_desktop.py`.
- `tests/policy/test_kcs14_freeze_snapshots.py`.

## Acceptance

- Only `desktop_protocol_transport` stdio transport constants and
  refactor-log/closeout metadata are affected.
- No Desktop tool schema, MCP envelope, packet schema, workflow status,
  result-shaping, reviewer bundle, publication, or customer-reply behavior
  changes.
- Behavior drift check verifies focused stdio transport, MCP Desktop, and
  freeze snapshot tests pass.
- Graph hash for the touched file is updated after validation. Completed:
  `src/kcs_adapters/desktop_stdio_transport.py`.

## Not In Scope

- Desktop tool schema changes.
- MCP response envelope changes.
- KCS workflow decisions.
- Semantic-review behavior changes.
- Reviewer bundle behavior changes.
- KCS-15 style/markup parity.
