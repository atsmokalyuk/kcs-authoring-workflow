"""JSON-RPC stdio transport for the KCS Desktop MCP adapter."""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, replace
from typing import IO, Protocol

from kcs_adapters import desktop_jsonrpc as _desktop_jsonrpc
from kcs_adapters import desktop_protocol as _desktop_protocol
from kcs_adapters import desktop_tool_schemas as _desktop_tool_schemas
from kcs_adapters.desktop_mcp_results import (
    McpToolResult,
    mcp_tool_response,
    tool_error,
)
from kcs_adapters.desktop_tool_descriptors import McpToolDescriptor
from kcs_adapters.desktop_tool_names import (
    CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS,
    DESKTOP_OPERATOR_TOOLS,
    TOOL_NAME_STYLE_CANONICAL,
    TOOL_NAME_STYLE_DESKTOP_ALIASES,
    claude_desktop_tool_alias,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict


class McpArgumentError(ValueError):
    """Tool argument shape error that maps to JSON-RPC invalid params."""


class McpAdapterProtocol(Protocol):
    def list_tools(self) -> tuple[McpToolDescriptor, ...]: ...

    def call_tool(
        self, name: str, arguments: Mapping[str, object] | None = None
    ) -> McpToolResult: ...


class _MethodNotFound:
    pass


_METHOD_NOT_FOUND = _MethodNotFound()
_READY_BEFORE_INITIALIZED_METHODS = frozenset({"initialize", "ping"})
_SUPPORTED_TOOL_NAME_STYLES = frozenset(
    {TOOL_NAME_STYLE_DESKTOP_ALIASES, TOOL_NAME_STYLE_CANONICAL}
)
_TOOL_CALL_PARAM_KEYS = frozenset({"arguments", "name"})


class McpStdioTransport:
    """Line-delimited JSON-RPC stdio transport for Claude Desktop."""

    def __init__(
        self,
        *,
        adapter: McpAdapterProtocol | None = None,
        adapter_factory: Callable[[set[str] | None], McpAdapterProtocol] | None = None,
        tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
    ) -> None:
        if tool_name_style not in _SUPPORTED_TOOL_NAME_STYLES:
            raise ValueError("Unsupported MCP tool name style.")
        visible_tools = (
            DESKTOP_OPERATOR_TOOLS
            if tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES
            else None
        )
        if adapter is None:
            if adapter_factory is None:
                raise ValueError("MCP adapter factory is required.")
            adapter = adapter_factory(visible_tools)
        self._adapter = adapter
        self._tool_name_style = tool_name_style
        self._initialize_responded = False
        self._ready = False

    def handle_message(self, message: object) -> JsonDict | None:
        """Handle one JSON-RPC message."""

        parsed = _desktop_jsonrpc.parse_jsonrpc_message(message)
        if parsed.error_code is not None:
            if parsed.is_notification:
                return None
            return _desktop_jsonrpc.error_response(
                parsed.request_id,
                parsed.error_code,
                "Invalid JSON-RPC request.",
            )
        request_id = parsed.request_id
        method = parsed.method
        params = parsed.params
        is_notification = parsed.is_notification
        if is_notification:
            return self._handle_notification(method)
        if not self._ready and method not in _READY_BEFORE_INITIALIZED_METHODS:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.SERVER_NOT_INITIALIZED,
                "MCP transport is not initialized.",
            )

        result = self._handle_request(
            method=method,
            params=params,
            request_id=request_id,
        )
        if _desktop_jsonrpc.is_error_response(result):
            return result
        if result is _METHOD_NOT_FOUND:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.METHOD_NOT_FOUND,
                "Unknown method.",
            )
        return {
            "jsonrpc": _desktop_jsonrpc.JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    def _handle_request(
        self,
        *,
        method: str,
        params: object,
        request_id: object,
    ) -> object:
        try:
            return self._dispatch(method=method, params=params)
        except McpArgumentError:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INVALID_PARAMS,
                "Invalid tool arguments.",
            )
        except ValueError:
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INVALID_PARAMS,
                "Invalid params.",
            )
        except Exception:  # pragma: no cover - defensive transport boundary
            return _desktop_jsonrpc.error_response(
                request_id,
                _desktop_jsonrpc.INTERNAL_ERROR,
                "Internal transport error.",
            )

    def _handle_notification(self, method: str) -> JsonDict | None:
        if method == "notifications/initialized":
            if self._initialize_responded:
                self._ready = True
            return None
        return None

    def _dispatch(self, *, method: str, params: object) -> object:
        if method == "initialize":
            return self._initialize(params)
        if method in _desktop_jsonrpc.EMPTY_PARAM_METHOD_RESULTS:
            _desktop_jsonrpc.require_empty_params(params)
            return dict(_desktop_jsonrpc.EMPTY_PARAM_METHOD_RESULTS[method])
        if method == "tools/list":
            _desktop_jsonrpc.require_empty_params(params)
            return {
                "tools": [
                    self._tool_descriptor_payload(tool)
                    for tool in self._adapter.list_tools()
                ]
            }
        if method == "tools/call":
            return self._call_tool(params)
        return _METHOD_NOT_FOUND

    def _initialize(self, params: object) -> JsonDict:
        params_obj = _desktop_jsonrpc.require_initialize_params(params)
        protocol_version = params_obj.get("protocolVersion")
        result = _desktop_protocol.initialize_result(protocol_version)
        self._initialize_responded = True
        return result

    def _call_tool(self, params: object) -> JsonDict:
        params_obj = _desktop_jsonrpc.require_object_params(params)
        if any(key not in _TOOL_CALL_PARAM_KEYS for key in params_obj):
            raise McpArgumentError("Unexpected tool call parameter.")
        name = params_obj.get("name")
        if not isinstance(name, str) or not name:
            raise McpArgumentError("Invalid tool name.")
        canonical_name = self._canonical_tool_name(name)
        available = {tool.name: tool for tool in self._adapter.list_tools()}
        descriptor = available.get(canonical_name)
        if descriptor is None:
            raise McpArgumentError("Unknown tool.")
        arguments = params_obj.get("arguments", {})
        if not isinstance(arguments, Mapping):
            raise McpArgumentError("Invalid tool arguments.")
        result = self._adapter.call_tool(canonical_name, arguments)
        try:
            return mcp_tool_response(descriptor=descriptor, result=result)
        except ContractValidationError:
            return mcp_tool_response(
                descriptor=descriptor,
                result=tool_error("tool_result_invalid"),
            )

    def _tool_descriptor_payload(self, tool: McpToolDescriptor) -> JsonDict:
        external = replace(tool, name=self._external_tool_name(tool.name))
        payload = asdict(external)
        descriptor = {
            "annotations": payload["annotations"],
            "description": payload["description"],
            "inputSchema": _desktop_tool_schemas.desktop_input_schema(
                payload["input_schema"]
            ),
            "name": payload["name"],
        }
        if self._tool_name_style == TOOL_NAME_STYLE_CANONICAL:
            descriptor["outputSchema"] = payload["output_schema"]
        return descriptor

    def _external_tool_name(self, name: str) -> str:
        if self._tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES:
            return claude_desktop_tool_alias(name)
        return name

    def _canonical_tool_name(self, name: str) -> str:
        if self._tool_name_style == TOOL_NAME_STYLE_DESKTOP_ALIASES:
            return CANONICAL_TOOL_BY_CLAUDE_DESKTOP_ALIAS.get(name, name + "__invalid")
        return name


def serve_stdio(
    *,
    adapter_factory: Callable[[set[str] | None], McpAdapterProtocol],
    input_stream: Iterable[str | bytes] | None = None,
    output_stream: IO[str] | None = None,
    tool_name_style: str = TOOL_NAME_STYLE_DESKTOP_ALIASES,
) -> None:
    """Serve newline-delimited JSON-RPC over stdio-compatible streams."""

    transport = McpStdioTransport(
        adapter_factory=adapter_factory,
        tool_name_style=tool_name_style,
    )
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    for raw_line in input_stream:
        response = _desktop_jsonrpc.handle_stdio_line(transport, raw_line)
        if response is not None:
            output_stream.write(_desktop_jsonrpc.compact_json(response) + "\n")
            output_stream.flush()


__all__ = [
    "McpAdapterProtocol",
    "McpArgumentError",
    "McpStdioTransport",
    "serve_stdio",
]
