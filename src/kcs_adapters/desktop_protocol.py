"""MCP protocol metadata and initialize response for KCS Desktop."""

from __future__ import annotations

from kcs_core.json_payload import JsonDict

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", MCP_PROTOCOL_VERSION)
MCP_DESKTOP_SERVER_NAME = "kcs-authoring-desktop-mcp"
MCP_DESKTOP_SERVER_VERSION = "0.1.0"

MCP_INITIALIZE_INSTRUCTIONS = (
    "KCS Authoring MCP server. For sanitized support-ticket article "
    "requests, call kcs_draft_article. Prefer ticket_ref when a "
    "trusted source has saved the cleaned ticket transcript under "
    "the configured approved-summaries store. If no ref "
    "exists for an operator-provided sanitized attachment or paste, "
    "first call kcs_register_clean_ticket with the complete visible "
    "sanitized transcript, then call kcs_draft_article with the "
    "returned next_arguments. For short pasted sanitized text, "
    "kcs_draft_article may use approved_summary_text directly. Do "
    "not summarize or redact labeled sections before either tool "
    "call. A Claude Desktop file card is not a filesystem path: "
    "do not inspect upload directories, do not pass upload "
    "filenames or paths, and do not ask the operator to re-upload "
    "while visible text is available. If no visible file text is "
    "available, report file_content_unavailable and do not draft "
    "manually. Do not pass item, item_candidates, or aliases. "
    "Python validates the input and owns semantic extraction, "
    "decision, rendering, and local bundle output. The default "
    "Desktop workflow does not require Claude CLI/Code or an API "
    "key. Successful draft results return compact status plus "
    "local reviewer bundle refs; reviewer-only Zendesk HTML is "
    "written to the local bundle and returned inline only for "
    "explicit debug/smoke compatibility."
)


def initialize_result(protocol_version: object) -> JsonDict:
    if protocol_version not in MCP_SUPPORTED_PROTOCOL_VERSIONS:
        raise ValueError("Unsupported protocol version.")
    return {
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
        },
        "instructions": MCP_INITIALIZE_INSTRUCTIONS,
        "protocolVersion": protocol_version,
        "serverInfo": {
            "name": MCP_DESKTOP_SERVER_NAME,
            "version": MCP_DESKTOP_SERVER_VERSION,
        },
    }


__all__ = [
    "MCP_DESKTOP_SERVER_NAME",
    "MCP_DESKTOP_SERVER_VERSION",
    "MCP_INITIALIZE_INSTRUCTIONS",
    "MCP_PROTOCOL_VERSION",
    "MCP_SUPPORTED_PROTOCOL_VERSIONS",
    "initialize_result",
]
