"""Local reviewer bundle output for the Claude Desktop adapter."""

from __future__ import annotations

import json
import os
import re
import secrets
import time
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict

DEFAULT_REVIEWER_BUNDLE_ROOT = Path("local-data") / "reviewer-bundles"
REVIEWER_BUNDLE_ROOT_ENV = "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_ROOT"
REVIEWER_BUNDLE_STORAGE_HINT_ENV = "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_HINT"
REVIEWER_BUNDLE_STORAGE_REF_ENV = "KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_REF"

_SAFE_BUNDLE_SEGMENT_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def write_desktop_reviewer_bundle(
    *,
    root: Path,
    result: Mapping[str, Any],
    reviewer_only_html: str,
) -> JsonDict:
    """Write a Desktop reviewer bundle and return relative refs/hashes only."""

    _require_reviewer_bundle_root(root)
    bundle_ref = f"run-{time.strftime('%Y%m%dT%H%M%S')}-{secrets.token_urlsafe(6)}"
    item_ref = str(result.get("item_ref") or "item-001")
    item_dir_name = _safe_bundle_segment(item_ref, fallback="item-001")
    bundle_dir = root / bundle_ref
    item_dir = bundle_dir / item_dir_name
    item_dir.mkdir(parents=True, exist_ok=False)
    html_path = item_dir / "reviewer_only.html"
    html_path.write_text(reviewer_only_html, encoding="utf-8")
    html_sha256 = sha256(reviewer_only_html.encode("utf-8")).hexdigest()
    relative_bundle_dir = reviewer_bundle_relative_path(bundle_ref)
    relative_html_path = f"{relative_bundle_dir}/{item_dir_name}/reviewer_only.html"
    relative_manifest_path = f"{relative_bundle_dir}/manifest.json"
    manifest = _desktop_reviewer_bundle_manifest(
        bundle_ref=bundle_ref,
        html_sha256=html_sha256,
        item_ref=item_ref,
        relative_html_path=relative_html_path,
        relative_manifest_path=relative_manifest_path,
        result=result,
    )
    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _desktop_reviewer_bundle_manifest(
    *,
    bundle_ref: str,
    html_sha256: str,
    item_ref: str,
    relative_html_path: str,
    relative_manifest_path: str,
    result: Mapping[str, Any],
) -> JsonDict:
    """Return the compact Desktop reviewer-bundle manifest."""

    reuse_search_status = result.get("reuse_search_status")
    draft_only = reuse_search_status == "skipped"
    ready_for_reviewer = result.get("ready_for_reviewer") is True and not draft_only
    manifest: JsonDict = {
        "article_type": result.get("article_type"),
        "auto_publish_allowed": False,
        "bundle_ref": bundle_ref,
        "debug_code": (
            "draft_only_reuse_search_missing"
            if draft_only
            else result.get("debug_code")
        ),
        "html_path": relative_html_path,
        "html_sha256": html_sha256,
        "item_ref": item_ref,
        "kcs_ready": ready_for_reviewer,
        "manifest_path": relative_manifest_path,
        "public_output_approved": False,
        "ready_for_reviewer": ready_for_reviewer,
        "recommended_action": (
            "draft_only" if draft_only else result.get("recommended_action")
        ),
        "reuse_search_status": reuse_search_status,
        "schema_version": "kcs_reviewer_bundle_v1",
    }
    storage_hint = reviewer_bundle_storage_hint()
    storage_ref = reviewer_bundle_storage_ref()
    if storage_hint:
        manifest["bundle_storage_hint"] = storage_hint
    if storage_ref:
        manifest["bundle_storage_ref"] = storage_ref
    return manifest


def reviewer_bundle_relative_path(bundle_ref: str) -> str:
    """Return the Claude-visible relative path for a reviewer bundle."""

    return f"local-data/reviewer-bundles/{bundle_ref}"


def reviewer_bundle_root_from_environment() -> Path:
    """Return the configured reviewer bundle root for this Desktop process."""

    configured = os.environ.get(REVIEWER_BUNDLE_ROOT_ENV, "").strip()
    if not configured:
        return DEFAULT_REVIEWER_BUNDLE_ROOT
    return Path(configured).expanduser()


def reviewer_bundle_storage_hint() -> str:
    """Return a Claude-visible storage hint without expanding the user home."""

    return os.environ.get(REVIEWER_BUNDLE_STORAGE_HINT_ENV, "").strip()


def reviewer_bundle_storage_ref() -> str:
    """Return a stable storage ref for the configured reviewer bundle root."""

    return os.environ.get(REVIEWER_BUNDLE_STORAGE_REF_ENV, "").strip()


def _require_reviewer_bundle_root(root: Path) -> None:
    expected = DEFAULT_REVIEWER_BUNDLE_ROOT.parts
    if root.parts[-len(expected) :] != expected:
        raise ContractValidationError("reviewer bundle root invalid")


def _safe_bundle_segment(value: str, *, fallback: str) -> str:
    segment = _SAFE_BUNDLE_SEGMENT_RE.sub("-", value).strip(".-")
    return segment[:80] if segment else fallback
