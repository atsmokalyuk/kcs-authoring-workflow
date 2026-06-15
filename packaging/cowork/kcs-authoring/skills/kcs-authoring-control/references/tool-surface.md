# KCS Authoring Tool Surface

The plugin exposes one local stdio MCP server named `kcs-authoring`.

Expected tools:

- `kcs_get_policy_summary`
- `kcs_get_mcp_readiness`
- `kcs_validate_handoff_request`
- `kcs_validate_handoff_response`
- `kcs_validate_draft_request`
- `kcs_validate_draft_response`
- `kcs_run_contract_smoke`

The tools are read-only validation/control tools. They do not perform network
calls, provider calls, file writes, Zendesk writes, Help Center publication, or
customer replies.
