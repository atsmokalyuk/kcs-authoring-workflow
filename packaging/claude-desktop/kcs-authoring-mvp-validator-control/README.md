# KCS Authoring MCPB

This directory is the source for the Claude Desktop MCPB package.

The extension starts the repository-local `kcs-desktop-mcp` stdio server
through `uv`. It exposes read-only validator/control tools only.

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

The package does not embed raw tickets, fixtures, local paths, credentials,
provider configuration, or generated artifacts.
