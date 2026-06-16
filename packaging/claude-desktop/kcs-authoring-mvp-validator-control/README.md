# KCS Authoring MCPB

This directory is the source for the Claude Desktop MCPB package.

The extension starts the repository-local `kcs-desktop-mcp` stdio server
through `uv`. It exposes read-only validator/control tools and one compact
approved-summary pipeline check.

Build:

```bash
python scripts/build_kcs_mcpb.py
```

Output:

```text
dist/kcs-authoring-mvp-validator-control.mcpb
```

Install the generated MCPB in Claude Desktop, configure the local repository
root, enable the extension, then start a new Claude Desktop chat.

For approved sanitized support summaries, use:

```text
kcs_run_approved_summary_pipeline
```

This tool accepts structured safe fields and returns compact pipeline status.
Pass `debug: true` during manual smoke to receive value-safe `failure_stage`
and `debug_code` fields when validation fails.
It does not write files, call a provider, publish, or return article HTML.

The package does not embed raw tickets, fixtures, local paths, credentials,
provider configuration, or generated artifacts.
