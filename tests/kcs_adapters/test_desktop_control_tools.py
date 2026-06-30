from __future__ import annotations

from kcs_adapters import desktop_control_tools
from kcs_adapters.desktop_tool_descriptors import tool_descriptors


def test_policy_summary_result_shape() -> None:
    result = desktop_control_tools.policy_summary_result(
        schema_version="kcs_mcp_tool_result_v1",
        tool_count=3,
    )

    assert result["ok"] is True
    assert result["result_kind"] == "policy_summary"
    assert result["schema_version"] == "kcs_mcp_tool_result_v1"
    assert result["tool_count"] == 3
    assert result["checks"][0]["canonical_values"] == [
        "technical_scr",
        "howto_qa",
    ]
    assert result["auto_publish_allowed"] is False
    assert result["writes_files"] is False


def test_readiness_result_uses_desktop_alias_names() -> None:
    tools = tool_descriptors()

    result = desktop_control_tools.readiness_result(
        schema_version="kcs_mcp_tool_result_v1",
        tools=tools,
    )

    assert result["ok"] is True
    assert result["result_kind"] == "mcp_readiness"
    assert result["tool_count"] == len(tools)
    assert "kcs_draft_article" in result["tools"]
    assert "kcs.draft_article" not in result["tools"]
    assert result["resources_exposed"] is False
    assert result["prompts_exposed"] is False


def test_contract_smoke_result_shape() -> None:
    result = desktop_control_tools.contract_smoke_result(
        schema_version="kcs_mcp_tool_result_v1"
    )

    assert result["ok"] is True
    assert result["result_kind"] == "contract_smoke"
    assert result["smoke_ok"] is True
    assert result["schema_version"] == "kcs_mcp_tool_result_v1"
    assert result["checks"]
