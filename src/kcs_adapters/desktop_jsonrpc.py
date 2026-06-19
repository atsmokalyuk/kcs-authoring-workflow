"""JSON-RPC parsing and initialize validation for the Desktop MCP adapter."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload

JSONRPC_VERSION = "2.0"
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
SERVER_NOT_INITIALIZED = -32002

MAX_JSONRPC_LINE_BYTES = 96 * 1024
EMPTY_PARAM_METHOD_RESULTS: Mapping[str, JsonDict] = {
    "ping": {},
    "resources/list": {"resources": []},
    "resources/templates/list": {"resourceTemplates": []},
    "prompts/list": {"prompts": []},
}

_SAFE_REQUEST_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,80}")
_JSONRPC_ALLOWED_KEYS = frozenset({"id", "jsonrpc", "method", "params"})
_INITIALIZE_PARAM_KEYS = frozenset({"capabilities", "clientInfo", "protocolVersion"})
_INITIALIZE_FORBIDDEN_TEXT_FRAGMENTS = (
    "/users/",
    "api_key",
    "apikey",
    "attachment_url",
    "attachmenturl",
    "authorization",
    "bearer ",
    "internal_comment",
    "internalcomment",
    "raw_ticket",
    "rawticket",
    "secret=",
    "token=",
)


@dataclass(frozen=True)
class ParsedJsonRpcMessage:
    request_id: object
    method: str
    params: object
    is_notification: bool
    error_code: int | None = None


def handle_stdio_line(transport: Any, raw_line: str | bytes) -> JsonDict | None:
    try:
        line = decode_stdio_line(raw_line)
        if len(line.encode("utf-8")) > MAX_JSONRPC_LINE_BYTES:
            return error_response(None, PARSE_ERROR, "Parse error.")
        if not line.strip():
            return None
        message = json.loads(line, parse_constant=reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return error_response(None, PARSE_ERROR, "Parse error.")
    return transport.handle_message(message)


def decode_stdio_line(raw_line: str | bytes) -> str:
    if isinstance(raw_line, bytes):
        return raw_line.decode("utf-8")
    return raw_line


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def require_object_params(params: object) -> JsonDict:
    if params is None:
        return {}
    if not isinstance(params, dict):
        raise ValueError("JSON-RPC params must be an object.")
    return params


def require_empty_params(params: object) -> None:
    params_obj = require_object_params(params)
    if params_obj:
        raise ValueError("JSON-RPC params must be empty.")


def require_initialize_params(params: object) -> JsonDict:
    params_obj = require_object_params(params)
    if any(key not in _INITIALIZE_PARAM_KEYS for key in params_obj):
        raise ValueError("Invalid initialize params.")
    ensure_safe_initialize_metadata(params_obj)
    return params_obj


def ensure_safe_initialize_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Invalid initialize params.")
            ensure_no_initialize_private_marker(key)
            ensure_safe_initialize_metadata(item)
        return
    if isinstance(value, list):
        for item in value:
            ensure_safe_initialize_metadata(item)
        return
    ensure_safe_initialize_scalar(value)


def ensure_safe_initialize_scalar(value: object) -> None:
    if value is None or isinstance(value, bool | int):
        return
    if isinstance(value, str):
        ensure_no_initialize_private_marker(value)
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    raise ValueError("Invalid initialize params.")


def ensure_no_initialize_private_marker(value: str) -> None:
    normalized = value.casefold()
    if "@" in normalized or "://" in normalized:
        raise ValueError("Invalid initialize params.")
    if any(fragment in normalized for fragment in _INITIALIZE_FORBIDDEN_TEXT_FRAGMENTS):
        raise ValueError("Invalid initialize params.")


def compact_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":"))


def is_supported_request_id(request_id: object) -> bool:
    if isinstance(request_id, bool):
        return False
    if isinstance(request_id, int):
        return True
    if isinstance(request_id, str):
        if not _SAFE_REQUEST_ID_RE.fullmatch(request_id):
            return False
        try:
            ensure_safe_sanitized_payload(request_id)
        except ContractValidationError:
            return False
        return True
    return False


def parse_jsonrpc_message(message: object) -> ParsedJsonRpcMessage:
    if not isinstance(message, dict):
        return ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    if any(key not in _JSONRPC_ALLOWED_KEYS for key in message):
        return ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    request_id = message.get("id")
    is_notification = "id" not in message
    if "id" in message and not is_supported_request_id(request_id):
        return ParsedJsonRpcMessage(None, "", {}, False, INVALID_REQUEST)
    method = message.get("method")
    if message.get("jsonrpc") != JSONRPC_VERSION or not isinstance(method, str):
        return ParsedJsonRpcMessage(
            request_id,
            "",
            {},
            is_notification,
            INVALID_REQUEST,
        )
    return ParsedJsonRpcMessage(
        request_id,
        method,
        message.get("params", {}),
        is_notification,
    )


def is_error_response(value: object) -> bool:
    return (
        isinstance(value, dict)
        and "error" in value
        and value.get("jsonrpc") == "2.0"
    )


def error_response(request_id: object, code: int, message: str) -> JsonDict:
    return {
        "error": {"code": code, "message": message},
        "id": request_id,
        "jsonrpc": JSONRPC_VERSION,
    }


__all__ = [
    "EMPTY_PARAM_METHOD_RESULTS",
    "INTERNAL_ERROR",
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "JSONRPC_VERSION",
    "METHOD_NOT_FOUND",
    "PARSE_ERROR",
    "SERVER_NOT_INITIALIZED",
    "ParsedJsonRpcMessage",
    "compact_json",
    "decode_stdio_line",
    "error_response",
    "handle_stdio_line",
    "is_error_response",
    "is_supported_request_id",
    "parse_jsonrpc_message",
    "reject_json_constant",
    "require_empty_params",
    "require_initialize_params",
    "require_object_params",
]
