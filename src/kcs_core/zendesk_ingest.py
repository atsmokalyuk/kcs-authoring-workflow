"""Read-only Zendesk ingest boundary for KCS-8 cleanup handoff."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict

ZENDESK_RAW_CLEANUP_SNAPSHOT_SCHEMA_VERSION = "zendesk_raw_cleanup_snapshot_v1"
ZENDESK_SOURCE_KIND = "zendesk_ticket_snapshot"

_SAFE_TICKET_REF_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}")
_RAW_TICKET_REF_RE = re.compile(r"(?:^|[-_])(?:ticket|zendesk|zd)?[-_]?\d{4,}$", re.I)
_FORBIDDEN_CREDENTIAL_RE = re.compile(
    r"(?:password|passwd|api[_-]?key|token|secret|authorization|bearer)"
    r"(?:\s*[:=]\s*|[-_])[^\s/]+",
    re.I,
)
_FORBIDDEN_INLINE_CONFIG_KEYS = frozenset(
    {
        "--api-key",
        "--api-token",
        "--email",
        "--password",
        "--subdomain",
        "--token",
        "--url",
        "--user",
        "--username",
        "zendesk_api_key",
        "zendesk_email",
        "zendesk_oauth_token",
        "zendesk_password",
        "zendesk_subdomain",
        "zendesk_token",
        "zendesk_url",
        "zendesk_user",
    }
)
_FORBIDDEN_WORKSPACE_PARTS = frozenset(
    {
        ".git",
        ".knowledge",
        ".private",
        "artifacts",
        "docs",
        "src",
        "tests",
    }
)
_RAW_SNAPSHOT_NAME = "zendesk-raw-cleanup-snapshot.json"
_SAFE_MANIFEST_NAME = "zendesk-ingest-manifest.json"
_SAFE_REASON_CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,79}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ZendeskSourceClient(Protocol):
    """Read-only source boundary implemented by service/MCP/fake clients."""

    def fetch_ticket_snapshot(self, ticket_ref: str) -> "ZendeskRawTicketSnapshot":
        """Fetch one approved ticket snapshot without writes or broad access."""


@dataclass(frozen=True)
class ZendeskIngestPolicy:
    """KCS-8 access policy for approved ticket refs."""

    approved_ticket_refs: tuple[str, ...]
    allow_partial_comments: bool = False
    allow_raw_handoff_files: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.approved_ticket_refs, tuple):
            raise ContractValidationError("approved ticket allowlist must be a tuple")
        for ticket_ref in self.approved_ticket_refs:
            _ensure_safe_ticket_ref(ticket_ref)


@dataclass(frozen=True)
class ZendeskAdapterConfig:
    """Transport profile metadata; not a transport implementation."""

    mode: str
    service_endpoint: str | None = None
    mcp_command: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"fake", "mcp_stdio", "service_endpoint"}:
            raise ContractValidationError("unsupported zendesk adapter mode")
        if self.service_endpoint is not None:
            _ensure_no_inline_credentials(self.service_endpoint)
        if self.mcp_command is not None:
            _ensure_no_inline_credentials(self.mcp_command)


@dataclass(frozen=True)
class ZendeskRawTicketSnapshot:
    """Raw/pre-cleanup source DTO. Not safe payload and not KCS evidence."""

    ticket_ref: str
    ticket: Mapping[str, Any]
    comments: tuple[Mapping[str, Any], ...] = ()
    comments_complete: bool | None = None
    partial_comment_bodies: bool = False
    attachments_present: bool = False
    source: str = "zendesk_source_client"

    def __post_init__(self) -> None:
        _ensure_safe_ticket_ref(self.ticket_ref)
        _ensure_snapshot_ticket(self.ticket)
        _ensure_snapshot_comments(self.comments)
        _ensure_snapshot_flags(
            comments_complete=self.comments_complete,
            partial_comment_bodies=self.partial_comment_bodies,
            attachments_present=self.attachments_present,
        )


@dataclass(frozen=True)
class ZendeskIngestResult:
    """Safe KCS-8 ingest result for cleanup handoff."""

    ticket_ref: str
    snapshot_sha256: str
    comments_complete: bool
    partial_comment_bodies: bool
    attachments_present: bool
    raw_handoff_written: bool
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _ensure_safe_ticket_ref(self.ticket_ref)
        _ensure_snapshot_hash(self.snapshot_sha256)
        _ensure_ingest_result_flags(
            comments_complete=self.comments_complete,
            partial_comment_bodies=self.partial_comment_bodies,
            attachments_present=self.attachments_present,
            raw_handoff_written=self.raw_handoff_written,
        )
        _ensure_reason_codes(self.reason_codes)

    def safe_payload(self) -> JsonDict:
        """Return the safe reporting surface for logs/CLI/tests."""

        return {
            "schema_version": ZENDESK_RAW_CLEANUP_SNAPSHOT_SCHEMA_VERSION,
            "source_kind": ZENDESK_SOURCE_KIND,
            "ticket_ref": self.ticket_ref,
            "cleanup_required": True,
            "kcs_authoring_ready": False,
            "sanitized_export_ready": False,
            "comments_complete": self.comments_complete,
            "partial_comment_bodies": self.partial_comment_bodies,
            "attachments_present": self.attachments_present,
            "raw_handoff_written": self.raw_handoff_written,
            "snapshot_sha256": self.snapshot_sha256,
            "reason_codes": list(self.reason_codes),
        }


def ingest_zendesk_ticket_for_cleanup(
    *,
    ticket_ref: str,
    client: ZendeskSourceClient,
    policy: ZendeskIngestPolicy,
    cleanup_workspace: Path | None = None,
) -> ZendeskIngestResult:
    """Fetch an allowlisted Zendesk ticket snapshot for local cleanup only."""

    safe_ref = _ensure_safe_ticket_ref(ticket_ref)
    _ensure_allowlisted(safe_ref, policy)
    snapshot = _fetch_snapshot(safe_ref, client)
    if snapshot.ticket_ref != safe_ref:
        raise ContractValidationError("zendesk source client returned invalid snapshot")

    snapshot_payload = _snapshot_payload(snapshot)
    snapshot_hash = _sha256_json(snapshot_payload)
    comments_partial = _comments_are_partial(snapshot)
    attachments_present = snapshot.attachments_present or _has_attachment_metadata(
        snapshot_payload
    )
    reason_codes = _reason_codes(
        partial_comments=comments_partial,
        attachments_present=attachments_present,
    )
    if comments_partial and not policy.allow_partial_comments:
        reason_codes = (*reason_codes, "cleanup_only_partial_comments")

    raw_handoff_written = False
    if cleanup_workspace is not None:
        if not policy.allow_raw_handoff_files:
            raise ContractValidationError("raw handoff files require explicit policy")
        _write_raw_handoff(
            cleanup_workspace=cleanup_workspace,
            snapshot_payload=snapshot_payload,
            safe_manifest=_safe_manifest(
                ticket_ref=safe_ref,
                snapshot_sha256=snapshot_hash,
                comments_complete=not comments_partial,
                partial_comment_bodies=comments_partial,
                attachments_present=attachments_present,
                reason_codes=reason_codes,
            ),
        )
        raw_handoff_written = True

    return ZendeskIngestResult(
        ticket_ref=safe_ref,
        snapshot_sha256=snapshot_hash,
        comments_complete=not comments_partial,
        partial_comment_bodies=comments_partial,
        attachments_present=attachments_present,
        raw_handoff_written=raw_handoff_written,
        reason_codes=reason_codes,
    )


def _fetch_snapshot(
    ticket_ref: str,
    client: ZendeskSourceClient,
) -> ZendeskRawTicketSnapshot:
    client_failed = False
    snapshot: ZendeskRawTicketSnapshot | None = None
    try:
        snapshot = client.fetch_ticket_snapshot(ticket_ref)
    except Exception:
        client_failed = True
    if client_failed or snapshot is None:
        raise ContractValidationError("zendesk source client failed")
    if not isinstance(snapshot, ZendeskRawTicketSnapshot):
        raise ContractValidationError("zendesk source client returned invalid snapshot")
    return snapshot


def _ensure_safe_ticket_ref(ticket_ref: object) -> str:
    if not isinstance(ticket_ref, str) or not _SAFE_TICKET_REF_RE.fullmatch(ticket_ref):
        raise ContractValidationError("ticket_ref must be an opaque safe reference")
    if ticket_ref.isdecimal() or _RAW_TICKET_REF_RE.search(ticket_ref):
        raise ContractValidationError("ticket_ref must be an opaque safe reference")
    return ticket_ref


def _ensure_allowlisted(ticket_ref: str, policy: ZendeskIngestPolicy) -> None:
    if ticket_ref not in policy.approved_ticket_refs:
        raise ContractValidationError("ticket_ref is not approved")


def _ensure_snapshot_ticket(ticket: object) -> None:
    if not isinstance(ticket, Mapping):
        raise ContractValidationError("zendesk snapshot ticket must be an object")


def _ensure_snapshot_comments(comments: object) -> None:
    if not isinstance(comments, tuple):
        raise ContractValidationError("zendesk snapshot comments must be a tuple")
    for comment in comments:
        if not isinstance(comment, Mapping):
            raise ContractValidationError(
                "zendesk snapshot comment must be an object"
            )


def _ensure_snapshot_flags(
    *,
    comments_complete: object,
    partial_comment_bodies: object,
    attachments_present: object,
) -> None:
    if not isinstance(attachments_present, bool):
        raise ContractValidationError("zendesk attachment metadata is invalid")
    if not isinstance(partial_comment_bodies, bool):
        raise ContractValidationError("zendesk comment completeness is invalid")
    if comments_complete is not None and not isinstance(comments_complete, bool):
        raise ContractValidationError("zendesk comment completeness is invalid")


def _ensure_snapshot_hash(value: object) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ContractValidationError("zendesk ingest result hash is invalid")


def _ensure_ingest_result_flags(
    *,
    comments_complete: object,
    partial_comment_bodies: object,
    attachments_present: object,
    raw_handoff_written: object,
) -> None:
    for value in (
        comments_complete,
        partial_comment_bodies,
        attachments_present,
        raw_handoff_written,
    ):
        if not isinstance(value, bool):
            raise ContractValidationError("zendesk ingest result flags are invalid")


def _ensure_reason_codes(reason_codes: object) -> None:
    if not isinstance(reason_codes, tuple):
        raise ContractValidationError("zendesk ingest result reason codes are invalid")
    for code in reason_codes:
        if not isinstance(code, str) or not _SAFE_REASON_CODE_RE.fullmatch(code):
            raise ContractValidationError(
                "zendesk ingest result reason codes are invalid"
            )


def _ensure_no_inline_credentials(value: str) -> None:
    normalized = value.casefold()
    if _FORBIDDEN_CREDENTIAL_RE.search(value):
        raise ContractValidationError("zendesk adapter config contains unsafe value")
    for key in _FORBIDDEN_INLINE_CONFIG_KEYS:
        if key in normalized:
            raise ContractValidationError(
                "zendesk adapter config contains unsafe value"
            )


def _snapshot_payload(snapshot: ZendeskRawTicketSnapshot) -> JsonDict:
    return {
        "schema_version": ZENDESK_RAW_CLEANUP_SNAPSHOT_SCHEMA_VERSION,
        "source_kind": ZENDESK_SOURCE_KIND,
        "ticket_ref": snapshot.ticket_ref,
        "source": snapshot.source,
        "ticket": dict(snapshot.ticket),
        "comments": [dict(comment) for comment in snapshot.comments],
        "comments_complete": snapshot.comments_complete,
        "partial_comment_bodies": snapshot.partial_comment_bodies,
        "attachments_present": snapshot.attachments_present,
        "cleanup_required": True,
        "kcs_authoring_ready": False,
        "sanitized_export_ready": False,
    }


def _safe_manifest(
    *,
    ticket_ref: str,
    snapshot_sha256: str,
    comments_complete: bool,
    partial_comment_bodies: bool,
    attachments_present: bool,
    reason_codes: Sequence[str],
) -> JsonDict:
    return {
        "schema_version": ZENDESK_RAW_CLEANUP_SNAPSHOT_SCHEMA_VERSION,
        "source_kind": ZENDESK_SOURCE_KIND,
        "ticket_ref": ticket_ref,
        "cleanup_required": True,
        "kcs_authoring_ready": False,
        "sanitized_export_ready": False,
        "comments_complete": comments_complete,
        "partial_comment_bodies": partial_comment_bodies,
        "attachments_present": attachments_present,
        "raw_handoff_written": True,
        "snapshot_sha256": snapshot_sha256,
        "reason_codes": list(reason_codes),
    }


def _comments_are_partial(snapshot: ZendeskRawTicketSnapshot) -> bool:
    return snapshot.comments_complete is not True or snapshot.partial_comment_bodies


def _reason_codes(
    *, partial_comments: bool, attachments_present: bool
) -> tuple[str, ...]:
    codes: list[str] = []
    if partial_comments:
        codes.append("partial_comments")
    if attachments_present:
        codes.append("attachments_present")
    return tuple(codes)


def _has_attachment_metadata(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_attachment_key(key) and _has_non_empty_value(item):
                return True
            if _has_attachment_metadata(item):
                return True
        return False
    if isinstance(value, list | tuple):
        return any(_has_attachment_metadata(item) for item in value)
    return False


def _is_attachment_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.casefold()
    return normalized in {
        "attachment",
        "attachment_url",
        "attachments",
        "content_url",
        "inline_images",
        "uploads",
    }


def _has_non_empty_value(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | dict):
        return bool(value)
    return True


def _sha256_json(payload: Mapping[str, Any]) -> str:
    try:
        _ensure_strict_json_value(payload)
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError):
        raise ContractValidationError("zendesk snapshot must be strict JSON") from None
    return sha256(encoded).hexdigest()


def _ensure_strict_json_value(value: object) -> None:
    if isinstance(value, Mapping):
        _ensure_strict_json_object(value)
        return
    if isinstance(value, list):
        _ensure_strict_json_list(value)
        return
    if _is_strict_json_scalar(value):
        return
    raise ContractValidationError("zendesk snapshot must be strict JSON")


def _ensure_strict_json_object(value: Mapping[object, object]) -> None:
    for key, item in value.items():
        if not isinstance(key, str):
            raise ContractValidationError("zendesk snapshot must be strict JSON")
        _ensure_strict_json_value(item)


def _ensure_strict_json_list(value: list[object]) -> None:
    for item in value:
        _ensure_strict_json_value(item)


def _is_strict_json_scalar(value: object) -> bool:
    if value is None or isinstance(value, str | bool | int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def _write_raw_handoff(
    *,
    cleanup_workspace: Path,
    snapshot_payload: Mapping[str, Any],
    safe_manifest: Mapping[str, Any],
) -> None:
    workspace = _prepare_cleanup_workspace(cleanup_workspace)
    snapshot_path = workspace / _RAW_SNAPSHOT_NAME
    manifest_path = workspace / _SAFE_MANIFEST_NAME
    _ensure_no_overwrite((snapshot_path, manifest_path))
    written: list[Path] = []
    try:
        _write_private_text(snapshot_path, _json_text(snapshot_payload))
        written.append(snapshot_path)
        _write_private_text(manifest_path, _json_text(safe_manifest))
        written.append(manifest_path)
    except ContractValidationError:
        _cleanup_written(written)
        raise


def _prepare_cleanup_workspace(cleanup_workspace: Path) -> Path:
    requested_workspace = cleanup_workspace.expanduser()
    _reject_symlink_path(requested_workspace)
    workspace = requested_workspace.resolve(strict=False)
    _reject_workspace_path(workspace)
    _reject_symlink_path(workspace)
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise ContractValidationError(
            "could not create zendesk cleanup workspace"
        ) from None
    return workspace


def _reject_workspace_path(path: Path) -> None:
    cwd = Path.cwd().resolve(strict=False)
    if path == cwd or cwd in path.parents:
        raise ContractValidationError(
            "zendesk cleanup workspace must stay outside repo"
        )
    normalized_parts = {part.casefold() for part in path.parts}
    if normalized_parts & _FORBIDDEN_WORKSPACE_PARTS:
        raise ContractValidationError("zendesk cleanup workspace path is forbidden")


def _reject_symlink_path(path: Path) -> None:
    current = Path(path.anchor) if path.is_absolute() else Path.cwd()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ContractValidationError(
                "zendesk cleanup workspace must not use symlinks"
            )


def _ensure_no_overwrite(paths: Sequence[Path]) -> None:
    for path in paths:
        if path.exists() or path.is_symlink():
            raise ContractValidationError("refusing to overwrite zendesk handoff files")


def _write_private_text(path: Path, text: str) -> None:
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        temp_path.rename(path)
    except OSError:
        _cleanup_written([temp_path])
        raise ContractValidationError("could not write zendesk handoff files") from None


def _json_text(payload: Mapping[str, Any]) -> str:
    try:
        return json.dumps(payload, sort_keys=True, allow_nan=False, indent=2) + "\n"
    except (TypeError, ValueError):
        raise ContractValidationError(
            "zendesk handoff payload must be strict JSON"
        ) from None


def _cleanup_written(paths: Sequence[Path]) -> None:
    for path in paths:
        try:
            if path.exists() or path.is_symlink():
                path.unlink()
        except OSError:
            pass
