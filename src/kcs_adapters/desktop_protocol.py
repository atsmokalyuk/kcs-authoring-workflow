"""MCP protocol metadata and initialize response for KCS Desktop."""

from __future__ import annotations

from kcs_core.json_payload import JsonDict

MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", MCP_PROTOCOL_VERSION)
MCP_DESKTOP_SERVER_NAME = "kcs-authoring-desktop-mcp"
MCP_DESKTOP_SERVER_VERSION = "0.1.0"

MCP_INITIALIZE_INSTRUCTIONS = (
    "KCS Authoring MCP server. For `/draft <ticket_ref>` or any "
    "existing ticket_ref draft request, call kcs_draft_ticket with "
    "only ticket_ref from the configured approved-summaries store. "
    "Use only the listed KCS Authoring tools. If a legacy instruction "
    "requires support_get_behavior_instructions, call it at most once, "
    "use its returned route, and continue with KCS tools. Do not report "
    "Plesk Support Assistant Local as missing. "
    "Do not ask for an attachment first. For a "
    "sanitized attachment or long paste with no ref, first call "
    "kcs_register_clean_ticket with the complete visible sanitized "
    "text, then call kcs_draft_article with returned next_arguments. "
    "A Claude Desktop file card is not a filesystem path; do not "
    "inspect upload directories. "
    "For short inline sanitized text, kcs_draft_article uses "
    "approved_summary_text. "
    "If semantic_review_required is returned, call "
    "kcs_prepare_semantic_review, then kcs_submit_semantic_review. "
    "Do not draft manually or pass item/item_candidates."
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
