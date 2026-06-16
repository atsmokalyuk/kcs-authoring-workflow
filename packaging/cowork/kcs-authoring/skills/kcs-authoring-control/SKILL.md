---
name: kcs-authoring-control
description: >
  Use this skill when the user asks to validate KCS Authoring packets,
  run "kcs_run_contract_smoke", process an approved sanitized summary, check
  KCS Authoring MCP readiness, or use the local KCS Authoring tools from
  Claude/Cowork.
metadata:
  version: "0.1.0"
  author: "KCS Authoring MVP"
---

# KCS Authoring Control

Use the local KCS Authoring MCP tools for compact validation and smoke checks.

## Required First Step

Before explaining that tools are unavailable, check the active tool list for
these MCP tools:

- `kcs_get_policy_summary`
- `kcs_get_mcp_readiness`
- `kcs_run_contract_smoke`
- `kcs_run_approved_summary_pipeline`

If the user asks to run the smoke check, call `kcs_run_contract_smoke` and show
the compact result.

If the user provides an approved sanitized support summary and asks whether it
can flow through KCS, call `kcs_run_approved_summary_pipeline` with
`debug: true`. Extract a single structured `item` from the approved summary
with:

- `title`
- `article_type`
- `symptoms`
- `confirmed_facts`
- `supported_cause`
- `supported_resolution_or_workaround`
- `resolution_steps`
- `applicable_to`
- `environment`

If this tool returns `pipeline_ok: false`, report the returned `failure_stage`
and `debug_code` instead of guessing KCS-9b or KCS-9c packet schemas.

Do not try to construct KCS-9b or KCS-9c packet schemas manually from chat.

If the tools are not visible in the active session, tell the user that the KCS
Authoring plugin is installed but its MCP tools are not loaded into this chat,
then ask them to enable or reload the KCS Authoring plugin/tool access for the
current session.

## Boundaries

Do not send raw Zendesk payloads, raw comments, internal notes, attachments,
customer replies, credentials, local private paths, or full evidence basis to
the KCS tools.

Do not claim publication readiness from these tools. The MVP keeps:

- `auto_publish_allowed=false`
- `public_output_approved=false`
- no Zendesk writes
- no Help Center publication
- no customer replies

## Tool Usage

Use:

- `kcs_get_policy_summary` for compact policy/scope status.
- `kcs_get_mcp_readiness` for visible MCP metadata.
- `kcs_run_contract_smoke` for synthetic in-memory validation.
- `kcs_run_approved_summary_pipeline` for one approved sanitized summary
  converted into compact pipeline status.

Do not call low-level KCS-9b/KCS-9c packet validators from Claude Desktop.
They are internal development tools and are intentionally hidden from the
operator-facing tool list.

Keep user-facing output brief and concrete. Report only compact safe metadata,
not raw packet bodies.
