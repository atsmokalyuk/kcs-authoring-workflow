"""Live-capable Claude/provider adapter contracts for KCS-11."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import urlparse

from kcs_core.claude_draft import (
    CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
    CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    KcsClaudeDraftRequestPacket,
    KcsClaudeDraftResponsePacket,
    validate_claude_draft_response,
)
from kcs_core.claude_handoff import (
    CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
    CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
    KcsClaudeHandoffRequestPacket,
    KcsClaudeHandoffResponsePacket,
    validate_claude_handoff_response,
)
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict, dumps_payload, require_json_object
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_sanitized_payload,
)

CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION = "kcs_claude_provider_config_v1"
CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION = "kcs_claude_provider_preflight_v1"
CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION = "kcs_claude_provider_attempt_v1"
CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION = "kcs_claude_provider_smoke_result_v1"
CLAUDE_PROVIDER_HTTP_REQUEST_SCHEMA_VERSION = "kcs_claude_provider_http_request_v1"

_MAX_RESPONSE_BYTES = 64 * 1024
_MAX_PROVIDER_PAYLOAD_BYTES = 64 * 1024
_MAX_TIMEOUT_SECONDS = 120
_SAFE_CONFIG_REF_RE = re.compile(r"[a-z][a-z0-9_-]{0,79}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_CONFIG_REF_FORBIDDEN_RE = re.compile(
    r"(?:https?://|api[_-]?key|apikey|token|secret|password|authorization|"
    r"bearer|sk-[a-z0-9]|[/\\:=\s])",
    re.I,
)
_CONFIG_FIELDS = frozenset(
    {
        "credentials_source_ref",
        "endpoint_ref",
        "model_ref",
        "provider_profile",
        "schema_version",
        "timeout_seconds",
        "transport_mode",
    }
)
_PREFLIGHT_FIELDS = frozenset(
    {
        "config_valid",
        "credentials_not_inline",
        "failed_checks",
        "provider_profile",
        "publishes",
        "ready_for_live_smoke",
        "ready_for_real_ticket_use",
        "schema_version",
        "transport_mode",
        "transport_supported",
        "writes_files",
    }
)
_ATTEMPT_FIELDS = frozenset(
    {
        "auto_publish_allowed",
        "provider_profile",
        "publishes",
        "public_output_approved",
        "raw_context_included",
        "ready_for_provider_call",
        "ready_for_real_ticket_use",
        "request_kind",
        "request_schema_version",
        "request_sha256",
        "schema_version",
        "transport_mode",
        "writes_files",
    }
)
_SMOKE_RESULT_FIELDS = frozenset(
    {
        "auto_publish_allowed",
        "provider_called",
        "provider_error_code",
        "provider_status",
        "public_output_approved",
        "raw_error_echoed",
        "ready_for_real_ticket_use",
        "request_kind",
        "response_valid",
        "schema_version",
        "validated_response",
    }
)
_VALIDATED_RESPONSE_FIELDS = frozenset(
    {
        "provider_error_code",
        "provider_status",
        "response_kind",
        "response_schema_version",
        "response_sha256",
        "validation_ok",
    }
)


class ClaudeProviderProfile(StrEnum):
    """Allowed KCS-11 provider profile markers."""

    FAKE_PROVIDER = "fake_provider"
    APPROVED_PROVIDER = "approved_provider"


class ClaudeProviderTransportMode(StrEnum):
    """Allowed KCS-11 provider transport modes."""

    FAKE_PROVIDER = "fake_provider"
    DIRECT_HTTP = "direct_http"
    INTERNAL_SERVICE = "internal_service"
    MCP_CLIENT = "mcp_client"


class ClaudeProviderRequestKind(StrEnum):
    """Provider request family."""

    HANDOFF = "handoff"
    DRAFT = "draft"


class ClaudeProviderSmokeErrorCode(StrEnum):
    """Value-safe smoke result error codes."""

    NONE = "none"
    PROVIDER_FAILED = "provider_failed"
    PROVIDER_RESPONSE_INVALID = "provider_response_invalid"
    TRANSPORT_NOT_SUPPORTED = "transport_not_supported"


class ClaudeProviderClient(Protocol):
    """Provider boundary for KCS-11 smoke tests."""

    @property
    def transport_mode(self) -> str:
        """Return the non-secret transport marker implemented by this client."""

    def submit_handoff(
        self, request: KcsClaudeHandoffRequestPacket
    ) -> KcsClaudeHandoffResponsePacket | Mapping[str, Any]:
        """Return untrusted KCS-9b provider output."""

    def submit_draft(
        self, request: KcsClaudeDraftRequestPacket
    ) -> KcsClaudeDraftResponsePacket | Mapping[str, Any]:
        """Return untrusted KCS-9c provider output."""


class ClaudeHttpTransport(Protocol):
    """Injectable HTTP transport for direct provider smoke tests."""

    def post_json(
        self,
        *,
        endpoint_url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> Mapping[str, Any] | bytes | str:
        """POST JSON and return an untrusted JSON object/body."""


class _ProviderRequestFailed(Exception):
    """Private marker for transport/provider call failures."""


@dataclass(frozen=True)
class ClaudeProviderConfig:
    """Serializable value-safe provider adapter configuration."""

    provider_profile: str = ClaudeProviderProfile.FAKE_PROVIDER.value
    transport_mode: str = ClaudeProviderTransportMode.FAKE_PROVIDER.value
    model_ref: str = "claude-model"
    endpoint_ref: str = ""
    credentials_source_ref: str = ""
    timeout_seconds: int = 30
    schema_version: str = CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider config")
        object.__setattr__(
            self,
            "provider_profile",
            _enum_value(
                self.provider_profile,
                ClaudeProviderProfile,
                "provider_profile",
            ),
        )
        object.__setattr__(
            self,
            "transport_mode",
            _enum_value(
                self.transport_mode,
                ClaudeProviderTransportMode,
                "transport_mode",
            ),
        )
        _validate_profile_transport(self.provider_profile, self.transport_mode)
        object.__setattr__(
            self,
            "model_ref",
            _safe_config_ref(self.model_ref, "model_ref", required=True),
        )
        object.__setattr__(
            self,
            "endpoint_ref",
            _safe_config_ref(self.endpoint_ref, "endpoint_ref", required=False),
        )
        object.__setattr__(
            self,
            "credentials_source_ref",
            _safe_config_ref(
                self.credentials_source_ref,
                "credentials_source_ref",
                required=False,
            ),
        )
        if (
            not isinstance(self.timeout_seconds, int)
            or isinstance(self.timeout_seconds, bool)
            or self.timeout_seconds < 1
            or self.timeout_seconds > _MAX_TIMEOUT_SECONDS
        ):
            raise ContractValidationError("claude provider timeout invalid")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "ClaudeProviderConfig":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _CONFIG_FIELDS, label="claude provider config")
        if data.get("schema_version") != CLAUDE_PROVIDER_CONFIG_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider config")
        return cls(
            provider_profile=_required_string(data, "provider_profile"),
            transport_mode=_required_string(data, "transport_mode"),
            model_ref=_required_string(data, "model_ref"),
            endpoint_ref=_optional_string(data, "endpoint_ref") or "",
            credentials_source_ref=_optional_string(data, "credentials_source_ref")
            or "",
            timeout_seconds=_optional_int(data, "timeout_seconds", 30),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "credentials_source_ref": self.credentials_source_ref,
            "endpoint_ref": self.endpoint_ref,
            "model_ref": self.model_ref,
            "provider_profile": self.provider_profile,
            "schema_version": self.schema_version,
            "timeout_seconds": self.timeout_seconds,
            "transport_mode": self.transport_mode,
        }


@dataclass(frozen=True, repr=False)
class DirectHttpRuntimeConfig:
    """Runtime-only direct HTTP settings. Never serialize this object."""

    endpoint_url: str
    api_key: str
    model: str
    max_response_bytes: int = _MAX_RESPONSE_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint_url, str):
            raise ContractValidationError("claude provider runtime config invalid")
        if any(
            ord(character) < 32 or ord(character) == 127
            for character in self.endpoint_url
        ):
            raise ContractValidationError("claude provider runtime config invalid")
        parsed = urlparse(self.endpoint_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ContractValidationError("claude provider runtime config invalid")
        if (
            not isinstance(self.api_key, str)
            or not self.api_key.strip()
            or "\r" in self.api_key
            or "\n" in self.api_key
        ):
            raise ContractValidationError("claude provider runtime config invalid")
        object.__setattr__(
            self,
            "model",
            _safe_config_ref(self.model, "model", required=True),
        )
        if (
            not isinstance(self.max_response_bytes, int)
            or isinstance(self.max_response_bytes, bool)
            or self.max_response_bytes < 1
            or self.max_response_bytes > _MAX_RESPONSE_BYTES
        ):
            raise ContractValidationError("claude provider runtime config invalid")

    def __repr__(self) -> str:
        return "DirectHttpRuntimeConfig(endpoint_url=<redacted>, api_key=<redacted>)"


@dataclass(frozen=True)
class ClaudeProviderPreflightReport:
    """Value-safe provider adapter preflight report."""

    provider_profile: str
    transport_mode: str
    config_valid: bool
    credentials_not_inline: bool
    transport_supported: bool
    ready_for_live_smoke: bool
    failed_checks: tuple[str, ...] = ()
    ready_for_real_ticket_use: bool = False
    writes_files: bool = False
    publishes: bool = False
    schema_version: str = CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider preflight")
        object.__setattr__(
            self,
            "provider_profile",
            _enum_value(
                self.provider_profile,
                ClaudeProviderProfile,
                "provider_profile",
            ),
        )
        object.__setattr__(
            self,
            "transport_mode",
            _enum_value(
                self.transport_mode,
                ClaudeProviderTransportMode,
                "transport_mode",
            ),
        )
        for key in (
            "config_valid",
            "credentials_not_inline",
            "transport_supported",
            "ready_for_live_smoke",
        ):
            _require_bool(getattr(self, key), key)
        for key in ("ready_for_real_ticket_use", "writes_files", "publishes"):
            _require_false(getattr(self, key), key)
        object.__setattr__(
            self,
            "failed_checks",
            tuple(_safe_code_list(self.failed_checks)),
        )

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "ClaudeProviderPreflightReport":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _PREFLIGHT_FIELDS, label="claude provider preflight")
        if data.get("schema_version") != CLAUDE_PROVIDER_PREFLIGHT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider preflight")
        return cls(
            provider_profile=_required_string(data, "provider_profile"),
            transport_mode=_required_string(data, "transport_mode"),
            config_valid=_optional_bool(data, "config_valid", False),
            credentials_not_inline=_optional_bool(
                data,
                "credentials_not_inline",
                False,
            ),
            transport_supported=_optional_bool(data, "transport_supported", False),
            ready_for_live_smoke=_optional_bool(
                data,
                "ready_for_live_smoke",
                False,
            ),
            failed_checks=tuple(_optional_string_list(data, "failed_checks")),
            ready_for_real_ticket_use=_optional_bool(
                data,
                "ready_for_real_ticket_use",
                False,
            ),
            writes_files=_optional_bool(data, "writes_files", False),
            publishes=_optional_bool(data, "publishes", False),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "config_valid": self.config_valid,
            "credentials_not_inline": self.credentials_not_inline,
            "failed_checks": list(self.failed_checks),
            "provider_profile": self.provider_profile,
            "publishes": self.publishes,
            "ready_for_live_smoke": self.ready_for_live_smoke,
            "ready_for_real_ticket_use": self.ready_for_real_ticket_use,
            "schema_version": self.schema_version,
            "transport_mode": self.transport_mode,
            "transport_supported": self.transport_supported,
            "writes_files": self.writes_files,
        }


@dataclass(frozen=True)
class ClaudeProviderAttemptPacket:
    """Value-safe summary of one provider call attempt."""

    request_kind: str
    request_schema_version: str
    request_sha256: str
    provider_profile: str
    transport_mode: str
    ready_for_provider_call: bool
    ready_for_real_ticket_use: bool = False
    raw_context_included: bool = False
    writes_files: bool = False
    publishes: bool = False
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    schema_version: str = CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider attempt")
        object.__setattr__(
            self,
            "request_kind",
            _enum_value(
                self.request_kind,
                ClaudeProviderRequestKind,
                "request_kind",
            ),
        )
        _validate_request_schema_for_kind(
            self.request_kind,
            self.request_schema_version,
        )
        object.__setattr__(
            self,
            "request_sha256",
            _validate_hash(self.request_sha256, "request_sha256"),
        )
        object.__setattr__(
            self,
            "provider_profile",
            _enum_value(
                self.provider_profile,
                ClaudeProviderProfile,
                "provider_profile",
            ),
        )
        object.__setattr__(
            self,
            "transport_mode",
            _enum_value(
                self.transport_mode,
                ClaudeProviderTransportMode,
                "transport_mode",
            ),
        )
        _require_bool(self.ready_for_provider_call, "ready_for_provider_call")
        for key in (
            "ready_for_real_ticket_use",
            "raw_context_included",
            "writes_files",
            "publishes",
            "auto_publish_allowed",
            "public_output_approved",
        ):
            _require_false(getattr(self, key), key)

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "ClaudeProviderAttemptPacket":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _ATTEMPT_FIELDS, label="claude provider attempt")
        if data.get("schema_version") != CLAUDE_PROVIDER_ATTEMPT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider attempt")
        return cls(
            request_kind=_required_string(data, "request_kind"),
            request_schema_version=_required_string(data, "request_schema_version"),
            request_sha256=_required_string(data, "request_sha256"),
            provider_profile=_required_string(data, "provider_profile"),
            transport_mode=_required_string(data, "transport_mode"),
            ready_for_provider_call=_optional_bool(
                data,
                "ready_for_provider_call",
                False,
            ),
            ready_for_real_ticket_use=_optional_bool(
                data,
                "ready_for_real_ticket_use",
                False,
            ),
            raw_context_included=_optional_bool(
                data,
                "raw_context_included",
                False,
            ),
            writes_files=_optional_bool(data, "writes_files", False),
            publishes=_optional_bool(data, "publishes", False),
            auto_publish_allowed=_optional_bool(
                data,
                "auto_publish_allowed",
                False,
            ),
            public_output_approved=_optional_bool(
                data,
                "public_output_approved",
                False,
            ),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "auto_publish_allowed": self.auto_publish_allowed,
            "provider_profile": self.provider_profile,
            "publishes": self.publishes,
            "public_output_approved": self.public_output_approved,
            "raw_context_included": self.raw_context_included,
            "ready_for_provider_call": self.ready_for_provider_call,
            "ready_for_real_ticket_use": self.ready_for_real_ticket_use,
            "request_kind": self.request_kind,
            "request_schema_version": self.request_schema_version,
            "request_sha256": self.request_sha256,
            "schema_version": self.schema_version,
            "transport_mode": self.transport_mode,
            "writes_files": self.writes_files,
        }


@dataclass(frozen=True)
class ClaudeProviderSmokeResult:
    """Compact value-safe result of one provider smoke attempt."""

    request_kind: str
    provider_called: bool
    response_valid: bool
    provider_status: str
    provider_error_code: str
    validated_response: JsonDict = field(default_factory=dict)
    ready_for_real_ticket_use: bool = False
    auto_publish_allowed: bool = False
    public_output_approved: bool = False
    raw_error_echoed: bool = False
    schema_version: str = CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider smoke result")
        object.__setattr__(
            self,
            "request_kind",
            _enum_value(
                self.request_kind,
                ClaudeProviderRequestKind,
                "request_kind",
            ),
        )
        _require_bool(self.provider_called, "provider_called")
        _require_bool(self.response_valid, "response_valid")
        object.__setattr__(
            self,
            "provider_status",
            _safe_code(self.provider_status, "provider_status"),
        )
        object.__setattr__(
            self,
            "provider_error_code",
            _enum_value(
                self.provider_error_code,
                ClaudeProviderSmokeErrorCode,
                "provider_error_code",
            ),
        )
        object.__setattr__(
            self,
            "validated_response",
            _validate_response_summary(self.validated_response),
        )
        for key in (
            "ready_for_real_ticket_use",
            "auto_publish_allowed",
            "public_output_approved",
            "raw_error_echoed",
        ):
            _require_false(getattr(self, key), key)
        _validate_smoke_result_state(self)

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "ClaudeProviderSmokeResult":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _SMOKE_RESULT_FIELDS, label="claude provider smoke")
        if data.get("schema_version") != CLAUDE_PROVIDER_SMOKE_RESULT_SCHEMA_VERSION:
            raise ContractValidationError("unsupported claude provider smoke result")
        return cls(
            request_kind=_required_string(data, "request_kind"),
            provider_called=_optional_bool(data, "provider_called", False),
            response_valid=_optional_bool(data, "response_valid", False),
            provider_status=_required_string(data, "provider_status"),
            provider_error_code=_required_string(data, "provider_error_code"),
            validated_response=_required_dict(data, "validated_response"),
            ready_for_real_ticket_use=_optional_bool(
                data,
                "ready_for_real_ticket_use",
                False,
            ),
            auto_publish_allowed=_optional_bool(
                data,
                "auto_publish_allowed",
                False,
            ),
            public_output_approved=_optional_bool(
                data,
                "public_output_approved",
                False,
            ),
            raw_error_echoed=_optional_bool(data, "raw_error_echoed", False),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "auto_publish_allowed": self.auto_publish_allowed,
            "provider_called": self.provider_called,
            "provider_error_code": self.provider_error_code,
            "provider_status": self.provider_status,
            "public_output_approved": self.public_output_approved,
            "raw_error_echoed": self.raw_error_echoed,
            "ready_for_real_ticket_use": self.ready_for_real_ticket_use,
            "request_kind": self.request_kind,
            "response_valid": self.response_valid,
            "schema_version": self.schema_version,
            "validated_response": dict(self.validated_response),
        }


class FakeClaudeProviderClient:
    """Test provider that returns preconfigured packet payloads."""

    def __init__(
        self,
        *,
        handoff_response: (
            KcsClaudeHandoffResponsePacket | Mapping[str, Any] | None
        ) = None,
        draft_response: KcsClaudeDraftResponsePacket | Mapping[str, Any] | None = None,
    ) -> None:
        self._handoff_response = handoff_response
        self._draft_response = draft_response

    @property
    def transport_mode(self) -> str:
        return ClaudeProviderTransportMode.FAKE_PROVIDER.value

    def submit_handoff(
        self,
        request: KcsClaudeHandoffRequestPacket,
    ) -> KcsClaudeHandoffResponsePacket | Mapping[str, Any]:
        if self._handoff_response is None:
            raise ContractValidationError("claude provider response missing")
        return self._handoff_response

    def submit_draft(
        self,
        request: KcsClaudeDraftRequestPacket,
    ) -> KcsClaudeDraftResponsePacket | Mapping[str, Any]:
        if self._draft_response is None:
            raise ContractValidationError("claude provider response missing")
        return self._draft_response


class DirectHttpClaudeProviderClient:
    """Direct HTTP provider client with injectable transport."""

    def __init__(
        self,
        *,
        config: ClaudeProviderConfig,
        runtime_config: DirectHttpRuntimeConfig,
        transport: ClaudeHttpTransport | None = None,
    ) -> None:
        if config.transport_mode != ClaudeProviderTransportMode.DIRECT_HTTP.value:
            raise ContractValidationError("claude provider transport invalid")
        self._config = config
        self._runtime_config = runtime_config
        self._transport = transport or UrlLibClaudeHttpTransport()

    @property
    def transport_mode(self) -> str:
        return ClaudeProviderTransportMode.DIRECT_HTTP.value

    def submit_handoff(
        self,
        request: KcsClaudeHandoffRequestPacket,
    ) -> Mapping[str, Any]:
        payload = _http_provider_payload(
            request_kind=ClaudeProviderRequestKind.HANDOFF.value,
            request=request.to_json_dict(),
        )
        return self._post(payload)

    def submit_draft(
        self,
        request: KcsClaudeDraftRequestPacket,
    ) -> Mapping[str, Any]:
        payload = _http_provider_payload(
            request_kind=ClaudeProviderRequestKind.DRAFT.value,
            request=request.to_json_dict(),
        )
        return self._post(payload)

    def _post(self, payload: Mapping[str, object]) -> Mapping[str, Any]:
        headers = {
            "authorization": f"Bearer {self._runtime_config.api_key}",
            "content-type": "application/json",
            "x-kcs-provider-model": self._runtime_config.model,
        }
        try:
            raw = self._transport.post_json(
                endpoint_url=self._runtime_config.endpoint_url,
                headers=headers,
                payload=payload,
                timeout_seconds=self._config.timeout_seconds,
                max_response_bytes=self._runtime_config.max_response_bytes,
            )
        except ContractValidationError:
            raise
        except Exception:
            raise _ProviderRequestFailed from None
        return _strict_response_object(
            raw,
            max_response_bytes=self._runtime_config.max_response_bytes,
        )


class UrlLibClaudeHttpTransport:
    """Small stdlib JSON POST transport for approved manual smoke only."""

    def post_json(
        self,
        *,
        endpoint_url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> Mapping[str, Any] | bytes:
        body = _strict_json_bytes(payload)
        request = urllib.request.Request(
            endpoint_url,
            data=body,
            headers=dict(headers),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.casefold():
                    raise ContractValidationError("claude provider response invalid")
                body = response.read(max_response_bytes + 1)
        except (urllib.error.URLError, OSError, TimeoutError):
            raise _ProviderRequestFailed from None
        if len(body) > max_response_bytes:
            raise ContractValidationError("claude provider response invalid")
        return body


def build_claude_provider_preflight(
    config: ClaudeProviderConfig,
    *,
    runtime_config: DirectHttpRuntimeConfig | None = None,
) -> ClaudeProviderPreflightReport:
    """Build a value-safe provider adapter preflight report."""

    transport_supported = _transport_supported(config.transport_mode, runtime_config)
    failed_checks = _preflight_failed_checks(
        config,
        runtime_config,
        transport_supported,
    )
    return ClaudeProviderPreflightReport(
        provider_profile=config.provider_profile,
        transport_mode=config.transport_mode,
        config_valid=True,
        credentials_not_inline=True,
        transport_supported=transport_supported,
        ready_for_live_smoke=not failed_checks,
        failed_checks=tuple(failed_checks),
    )


def build_claude_provider_attempt_packet(
    request: KcsClaudeHandoffRequestPacket | KcsClaudeDraftRequestPacket,
    config: ClaudeProviderConfig,
) -> ClaudeProviderAttemptPacket:
    """Build a value-safe summary of the provider request attempt."""

    request_kind, schema_version = _request_kind_and_schema(request)
    return ClaudeProviderAttemptPacket(
        request_kind=request_kind,
        request_schema_version=schema_version,
        request_sha256=_sha256_packet(request),
        provider_profile=config.provider_profile,
        transport_mode=config.transport_mode,
        ready_for_provider_call=config.transport_mode
        in {
            ClaudeProviderTransportMode.FAKE_PROVIDER.value,
            ClaudeProviderTransportMode.DIRECT_HTTP.value,
        },
    )


def run_claude_provider_smoke(
    request: KcsClaudeHandoffRequestPacket | KcsClaudeDraftRequestPacket,
    *,
    client: ClaudeProviderClient,
    config: ClaudeProviderConfig,
) -> ClaudeProviderSmokeResult:
    """Run one bounded provider smoke request and return a compact safe result."""

    attempt = build_claude_provider_attempt_packet(request, config)
    if not attempt.ready_for_provider_call:
        return _failed_smoke_result(
            attempt.request_kind,
            ClaudeProviderSmokeErrorCode.TRANSPORT_NOT_SUPPORTED.value,
            provider_called=False,
        )
    if _client_transport_mode(client) != config.transport_mode:
        return _failed_smoke_result(
            attempt.request_kind,
            ClaudeProviderSmokeErrorCode.TRANSPORT_NOT_SUPPORTED.value,
            provider_called=False,
        )
    try:
        response = _submit_and_validate(request, client)
    except _ProviderRequestFailed:
        return _failed_smoke_result(
            attempt.request_kind,
            ClaudeProviderSmokeErrorCode.PROVIDER_FAILED.value,
            provider_called=True,
        )
    except ContractValidationError:
        return _failed_smoke_result(
            attempt.request_kind,
            ClaudeProviderSmokeErrorCode.PROVIDER_RESPONSE_INVALID.value,
            provider_called=True,
        )
    except Exception:
        return _failed_smoke_result(
            attempt.request_kind,
            ClaudeProviderSmokeErrorCode.PROVIDER_FAILED.value,
            provider_called=True,
        )
    return _smoke_result_from_response(attempt.request_kind, response)


def _transport_supported(
    transport_mode: str,
    runtime_config: DirectHttpRuntimeConfig | None,
) -> bool:
    if transport_mode == ClaudeProviderTransportMode.FAKE_PROVIDER.value:
        return True
    if transport_mode == ClaudeProviderTransportMode.DIRECT_HTTP.value:
        return runtime_config is not None
    return False


def _preflight_failed_checks(
    config: ClaudeProviderConfig,
    runtime_config: DirectHttpRuntimeConfig | None,
    transport_supported: bool,
) -> list[str]:
    failed: list[str] = []
    if not transport_supported:
        failed.append("transport_not_supported")
    if (
        config.transport_mode == ClaudeProviderTransportMode.DIRECT_HTTP.value
        and runtime_config is None
    ):
        failed.append("runtime_config_missing")
    if config.transport_mode == ClaudeProviderTransportMode.DIRECT_HTTP.value:
        if not config.endpoint_ref:
            failed.append("endpoint_ref_missing")
        if not config.credentials_source_ref:
            failed.append("credentials_source_ref_missing")
    return failed


def _request_kind_and_schema(
    request: KcsClaudeHandoffRequestPacket | KcsClaudeDraftRequestPacket,
) -> tuple[str, str]:
    if isinstance(request, KcsClaudeHandoffRequestPacket):
        return (
            ClaudeProviderRequestKind.HANDOFF.value,
            CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        )
    if isinstance(request, KcsClaudeDraftRequestPacket):
        return (
            ClaudeProviderRequestKind.DRAFT.value,
            CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
        )
    raise ContractValidationError("claude provider request invalid")


def _submit_and_validate(
    request: KcsClaudeHandoffRequestPacket | KcsClaudeDraftRequestPacket,
    client: ClaudeProviderClient,
) -> KcsClaudeHandoffResponsePacket | KcsClaudeDraftResponsePacket:
    if isinstance(request, KcsClaudeHandoffRequestPacket):
        return validate_claude_handoff_response(
            client.submit_handoff(request),
            request=request,
        )
    if isinstance(request, KcsClaudeDraftRequestPacket):
        return validate_claude_draft_response(
            client.submit_draft(request),
            request=request,
        )
    raise ContractValidationError("claude provider request invalid")


def _smoke_result_from_response(
    request_kind: str,
    response: KcsClaudeHandoffResponsePacket | KcsClaudeDraftResponsePacket,
) -> ClaudeProviderSmokeResult:
    summary = _validated_response_summary(request_kind, response)
    if (
        summary["provider_error_code"] != ClaudeProviderSmokeErrorCode.NONE.value
        or summary["provider_status"] != "accepted"
    ):
        return _failed_smoke_result(
            request_kind,
            ClaudeProviderSmokeErrorCode.PROVIDER_RESPONSE_INVALID.value,
            provider_called=True,
        )
    return ClaudeProviderSmokeResult(
        request_kind=request_kind,
        provider_called=True,
        response_valid=True,
        provider_status=summary["provider_status"],
        provider_error_code=summary["provider_error_code"],
        validated_response=summary,
    )


def _failed_smoke_result(
    request_kind: str,
    provider_error_code: str,
    *,
    provider_called: bool,
) -> ClaudeProviderSmokeResult:
    return ClaudeProviderSmokeResult(
        request_kind=request_kind,
        provider_called=provider_called,
        response_valid=False,
        provider_status="failed",
        provider_error_code=provider_error_code,
        validated_response={},
    )


def _validated_response_summary(
    request_kind: str,
    response: KcsClaudeHandoffResponsePacket | KcsClaudeDraftResponsePacket,
) -> JsonDict:
    if isinstance(response, KcsClaudeHandoffResponsePacket):
        return {
            "provider_error_code": response.provider_error_code,
            "provider_status": response.provider_status,
            "response_kind": request_kind,
            "response_schema_version": CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
            "response_sha256": _sha256_packet(response),
            "validation_ok": True,
        }
    return {
        "provider_error_code": response.provider_error_code,
        "provider_status": response.draft_status,
        "response_kind": request_kind,
        "response_schema_version": CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
        "response_sha256": _sha256_packet(response),
        "validation_ok": True,
    }


def _http_provider_payload(
    *,
    request_kind: str,
    request: Mapping[str, Any],
) -> JsonDict:
    _validate_request_schema_for_kind(request_kind, str(request.get("schema_version")))
    payload = {
        "instruction": _instruction_for_kind(request_kind),
        "request": dict(request),
        "request_kind": request_kind,
        "schema_version": CLAUDE_PROVIDER_HTTP_REQUEST_SCHEMA_VERSION,
    }
    _strict_json_bytes(payload)
    ensure_safe_sanitized_payload(payload)
    return payload


def _instruction_for_kind(request_kind: str) -> str:
    if request_kind == ClaudeProviderRequestKind.HANDOFF.value:
        return (
            "Return only the structured KCS-9b reviewer-assist response JSON. "
            "Do not decide KCS actions, draft articles, write files, publish, "
            "or include raw/private data."
        )
    if request_kind == ClaudeProviderRequestKind.DRAFT.value:
        return (
            "Return only the structured KCS-9c reviewer-only draft response "
            "JSON. Do not decide KCS actions, write files, publish, create "
            "customer replies, or include raw/private data."
        )
    raise ContractValidationError("claude provider request invalid")


def _strict_response_object(
    value: Mapping[str, Any] | bytes | str | object,
    *,
    max_response_bytes: int,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        _strict_json_bytes(value, max_bytes=max_response_bytes)
        return value
    if isinstance(value, bytes):
        body = value
    elif isinstance(value, str):
        body = value.encode("utf-8")
    else:
        raise ContractValidationError("claude provider response invalid")
    if len(body) > max_response_bytes:
        raise ContractValidationError("claude provider response invalid")
    try:
        text = body.decode("utf-8")
        data = json.loads(text, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise ContractValidationError("claude provider response invalid") from None
    if not isinstance(data, Mapping):
        raise ContractValidationError("claude provider response invalid")
    _strict_json_bytes(data, max_bytes=max_response_bytes)
    return data


def _validate_request_schema_for_kind(request_kind: str, schema_version: str) -> None:
    expected = {
        ClaudeProviderRequestKind.HANDOFF.value: CLAUDE_HANDOFF_REQUEST_SCHEMA_VERSION,
        ClaudeProviderRequestKind.DRAFT.value: CLAUDE_DRAFT_REQUEST_SCHEMA_VERSION,
    }.get(request_kind)
    if expected is None or schema_version != expected:
        raise ContractValidationError("claude provider request schema mismatch")


def _validate_response_summary(value: object) -> JsonDict:
    if value == {}:
        return {}
    data = require_json_object(value)
    ensure_allowed_keys(
        data,
        _VALIDATED_RESPONSE_FIELDS,
        label="claude provider validated response",
    )
    summary = {
        "provider_error_code": _safe_code(
            data.get("provider_error_code"),
            "provider_error_code",
        ),
        "provider_status": _safe_code(data.get("provider_status"), "provider_status"),
        "response_kind": _enum_value(
            data.get("response_kind"),
            ClaudeProviderRequestKind,
            "response_kind",
        ),
        "response_schema_version": _response_schema_version(
            data.get("response_schema_version")
        ),
        "response_sha256": _validate_hash(
            data.get("response_sha256"),
            "response_sha256",
        ),
        "validation_ok": _required_bool(data.get("validation_ok"), "validation_ok"),
    }
    _strict_json_bytes(summary)
    _validate_response_schema_for_kind(
        summary["response_kind"],
        summary["response_schema_version"],
    )
    return summary


def _response_schema_version(value: object) -> str:
    if value in {
        CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    }:
        return str(value)
    raise ContractValidationError("claude provider response schema invalid")


def _safe_config_ref(value: object, label: str, *, required: bool) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"claude provider {label} invalid")
    normalized = value.strip()
    if not normalized:
        if required:
            raise ContractValidationError(f"claude provider {label} invalid")
        return ""
    if (
        not _SAFE_CONFIG_REF_RE.fullmatch(normalized)
        or _CONFIG_REF_FORBIDDEN_RE.search(normalized)
    ):
        raise ContractValidationError(f"claude provider {label} invalid")
    ensure_safe_sanitized_payload(normalized)
    return normalized


def _validate_profile_transport(provider_profile: str, transport_mode: str) -> None:
    if (
        transport_mode == ClaudeProviderTransportMode.FAKE_PROVIDER.value
        and provider_profile != ClaudeProviderProfile.FAKE_PROVIDER.value
    ):
        raise ContractValidationError("claude provider config invalid")
    if (
        transport_mode == ClaudeProviderTransportMode.DIRECT_HTTP.value
        and provider_profile != ClaudeProviderProfile.APPROVED_PROVIDER.value
    ):
        raise ContractValidationError("claude provider config invalid")


def _client_transport_mode(client: ClaudeProviderClient) -> str:
    try:
        value = client.transport_mode
        return _enum_value(value, ClaudeProviderTransportMode, "transport_mode")
    except Exception:
        return ""


def _validate_smoke_result_state(result: ClaudeProviderSmokeResult) -> None:
    if result.response_valid:
        _validate_accepted_smoke_result_state(result)
        return
    _validate_failed_smoke_result_state(result)


def _validate_accepted_smoke_result_state(
    result: ClaudeProviderSmokeResult,
) -> None:
    if not result.provider_called:
        raise ContractValidationError("claude provider smoke result invalid")
    if result.provider_error_code != ClaudeProviderSmokeErrorCode.NONE.value:
        raise ContractValidationError("claude provider smoke result invalid")
    if result.validated_response == {}:
        raise ContractValidationError("claude provider smoke result invalid")
    expected = {
        "provider_error_code": result.provider_error_code,
        "provider_status": result.provider_status,
        "response_kind": result.request_kind,
        "validation_ok": True,
    }
    for key, value in expected.items():
        if result.validated_response[key] != value:
            raise ContractValidationError("claude provider smoke result invalid")


def _validate_failed_smoke_result_state(result: ClaudeProviderSmokeResult) -> None:
    if result.provider_error_code == ClaudeProviderSmokeErrorCode.NONE.value:
        raise ContractValidationError("claude provider smoke result invalid")
    if result.validated_response != {}:
        raise ContractValidationError("claude provider smoke result invalid")


def _validate_response_schema_for_kind(
    response_kind: str,
    response_schema_version: str,
) -> None:
    expected = {
        ClaudeProviderRequestKind.HANDOFF.value: CLAUDE_HANDOFF_RESPONSE_SCHEMA_VERSION,
        ClaudeProviderRequestKind.DRAFT.value: CLAUDE_DRAFT_RESPONSE_SCHEMA_VERSION,
    }.get(response_kind)
    if expected is None or response_schema_version != expected:
        raise ContractValidationError("claude provider response schema invalid")


def _safe_code_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        raise ContractValidationError("claude provider code list invalid")
    return [_safe_code(item, "code") for item in value]


def _safe_code(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"claude provider {label} invalid")
    normalized = value.strip()
    if not normalized or not _SAFE_CONFIG_REF_RE.fullmatch(normalized):
        raise ContractValidationError(f"claude provider {label} invalid")
    ensure_safe_sanitized_payload(normalized)
    return normalized


def _enum_value(value: object, enum_type: type[StrEnum], label: str) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"unsupported claude provider {label}")
    ensure_safe_sanitized_payload(value)
    try:
        return enum_type(value).value
    except ValueError:
        raise ContractValidationError(f"unsupported claude provider {label}") from None


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"claude provider {key} invalid")
    return value


def _optional_string(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError(f"claude provider {key} invalid")
    return value


def _optional_string_list(data: Mapping[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise ContractValidationError(f"claude provider {key} invalid")
    if not all(isinstance(item, str) for item in value):
        raise ContractValidationError(f"claude provider {key} invalid")
    return list(value)


def _required_dict(data: Mapping[str, Any], key: str) -> JsonDict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ContractValidationError(f"claude provider {key} invalid")
    return dict(value)


def _optional_bool(data: Mapping[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ContractValidationError(f"claude provider {key} invalid")
    return value


def _optional_int(data: Mapping[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ContractValidationError(f"claude provider {key} invalid")
    return value


def _required_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError(f"claude provider {label} invalid")
    return value


def _require_bool(value: object, label: str) -> None:
    _required_bool(value, label)


def _require_false(value: object, label: str) -> None:
    if value is not False:
        raise ContractValidationError(f"claude provider {label} must be false")


def _validate_hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ContractValidationError(f"claude provider {label} invalid")
    return value


def _sha256_packet(payload: object) -> str:
    return sha256(dumps_payload(payload).encode("utf-8")).hexdigest()


def _strict_json_bytes(
    value: Mapping[str, Any],
    *,
    max_bytes: int = _MAX_PROVIDER_PAYLOAD_BYTES,
) -> bytes:
    try:
        body = json.dumps(
            value,
            sort_keys=True,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise ContractValidationError("claude provider payload invalid") from None
    if len(body) > max_bytes:
        raise ContractValidationError("claude provider payload too large")
    return body


def _reject_json_constant(value: str) -> None:
    raise ValueError("non-standard JSON constant")
