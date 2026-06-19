"""Canonical and Claude Desktop tool names for the KCS Desktop MCP adapter."""

from __future__ import annotations

TOOL_NAME_STYLE_DESKTOP_ALIASES = "claude_desktop_aliases"
TOOL_NAME_STYLE_CANONICAL = "canonical"

TOOL_GET_POLICY_SUMMARY = "kcs.get_policy_summary"
TOOL_GET_MCP_READINESS = "kcs.get_mcp_readiness"
TOOL_VALIDATE_HANDOFF_REQUEST = "kcs.validate_handoff_request"
TOOL_VALIDATE_HANDOFF_RESPONSE = "kcs.validate_handoff_response"
TOOL_VALIDATE_DRAFT_REQUEST = "kcs.validate_draft_request"
TOOL_VALIDATE_DRAFT_RESPONSE = "kcs.validate_draft_response"
TOOL_RUN_CONTRACT_SMOKE = "kcs.run_contract_smoke"
TOOL_RUN_APPROVED_SUMMARY_PIPELINE = "kcs.run_approved_summary_pipeline"
TOOL_AUTHOR_APPROVED_SUMMARY = "kcs.author_approved_summary"
TOOL_AUTHOR_TICKET = "kcs.author_ticket"
TOOL_REGISTER_CLEAN_TICKET = "kcs.register_clean_ticket"
TOOL_DRAFT_ARTICLE = "kcs.draft_article"
TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS = "support.get_behavior_instructions"

DESKTOP_OPERATOR_TOOLS = frozenset(
    {
        TOOL_REGISTER_CLEAN_TICKET,
        TOOL_DRAFT_ARTICLE,
        TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS,
    }
)

CLAUDE_DESKTOP_TOOL_ALIASES = {
    TOOL_GET_POLICY_SUMMARY: "kcs_get_policy_summary",
    TOOL_GET_MCP_READINESS: "kcs_get_mcp_readiness",
    TOOL_VALIDATE_HANDOFF_REQUEST: "kcs_validate_handoff_request",
    TOOL_VALIDATE_HANDOFF_RESPONSE: "kcs_validate_handoff_response",
    TOOL_VALIDATE_DRAFT_REQUEST: "kcs_validate_draft_request",
    TOOL_VALIDATE_DRAFT_RESPONSE: "kcs_validate_draft_response",
    TOOL_RUN_CONTRACT_SMOKE: "kcs_run_contract_smoke",
    TOOL_RUN_APPROVED_SUMMARY_PIPELINE: "kcs_run_approved_summary_pipeline",
    TOOL_AUTHOR_APPROVED_SUMMARY: "kcs_author_approved_summary",
    TOOL_AUTHOR_TICKET: "kcs_author_ticket",
    TOOL_REGISTER_CLEAN_TICKET: "kcs_register_clean_ticket",
    TOOL_DRAFT_ARTICLE: "kcs_draft_article",
    TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS: "support_get_behavior_instructions",
}
CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS = {
    alias: canonical for canonical, alias in CLAUDE_DESKTOP_TOOL_ALIASES.items()
}


def claude_desktop_tool_alias(tool_name: str) -> str:
    try:
        return CLAUDE_DESKTOP_TOOL_ALIASES[tool_name]
    except KeyError as exc:
        raise ValueError("Tool has no Claude Desktop alias mapping.") from exc


def canonical_tool_name_from_claude_desktop_alias(tool_name: str) -> str:
    try:
        return CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS[tool_name]
    except KeyError as exc:
        raise ValueError("Unknown Claude Desktop tool alias.") from exc


__all__ = [
    "CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS",
    "CLAUDE_DESKTOP_TOOL_ALIASES",
    "DESKTOP_OPERATOR_TOOLS",
    "TOOL_AUTHOR_APPROVED_SUMMARY",
    "TOOL_AUTHOR_TICKET",
    "TOOL_DRAFT_ARTICLE",
    "TOOL_GET_MCP_READINESS",
    "TOOL_GET_POLICY_SUMMARY",
    "TOOL_NAME_STYLE_CANONICAL",
    "TOOL_NAME_STYLE_DESKTOP_ALIASES",
    "TOOL_REGISTER_CLEAN_TICKET",
    "TOOL_RUN_APPROVED_SUMMARY_PIPELINE",
    "TOOL_RUN_CONTRACT_SMOKE",
    "TOOL_SUPPORT_GET_BEHAVIOR_INSTRUCTIONS",
    "TOOL_VALIDATE_DRAFT_REQUEST",
    "TOOL_VALIDATE_DRAFT_RESPONSE",
    "TOOL_VALIDATE_HANDOFF_REQUEST",
    "TOOL_VALIDATE_HANDOFF_RESPONSE",
    "canonical_tool_name_from_claude_desktop_alias",
    "claude_desktop_tool_alias",
]
