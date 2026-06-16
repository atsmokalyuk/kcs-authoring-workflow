# KCS Authoring Tool Surface

The plugin exposes one local stdio MCP server named `kcs-authoring`.

Claude Desktop operator-visible tools:

- `kcs_get_policy_summary`
- `kcs_get_mcp_readiness`
- `kcs_run_contract_smoke`
- `kcs_run_approved_summary_pipeline`

Low-level KCS-9b/KCS-9c packet validators are internal development tools.
They are intentionally hidden from the Claude Desktop operator-facing tool
list because the supported ticket-summary workflow must go through
`kcs_run_approved_summary_pipeline`.

The tools are read-only validation/control tools. They do not perform network
calls, provider calls, file writes, Zendesk writes, Help Center publication, or
customer replies.
