# KCS Authoring Plugin

Local Claude/Cowork plugin for KCS Authoring MVP validation and smoke checks.

## What It Adds

- One skill: `kcs-authoring-control`
- One local MCP server: `kcs-authoring`
- Read-only KCS tools exposed with `kcs_*` names

## Local Requirements

- Repository checkout at `${HOME}/kcs-authoring-mvp`
- `uv` available on `PATH`
- Project environment installed enough for `uv run kcs-desktop-mcp`

## Boundaries

This plugin is for local validation/control only.

It does not send raw Zendesk payloads, raw comments, internal notes,
attachments, customer replies, credentials, or full evidence basis to Claude.
It does not write files, call providers, write Zendesk, publish to Help Center,
or approve public output.

## Smoke Prompt

After installing the plugin in Claude/Cowork, start a new session and ask:

```text
Use the kcs_run_contract_smoke tool and show the compact result.
```
