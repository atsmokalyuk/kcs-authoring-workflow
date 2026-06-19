"""Local reviewer bundle output for the Claude Desktop adapter."""

from __future__ import annotations

import json
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
    manifest: JsonDict = {
        "article_type": result.get("article_type"),
        "auto_publish_allowed": False,
        "bundle_ref": bundle_ref,
        "html_path": relative_html_path,
        "html_sha256": html_sha256,
        "item_ref": item_ref,
        "manifest_path": relative_manifest_path,
        "public_output_approved": False,
        "ready_for_reviewer": result.get("ready_for_reviewer") is True,
        "reuse_search_status": result.get("reuse_search_status"),
        "schema_version": "kcs_reviewer_bundle_v1",
    }
    (bundle_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def reviewer_bundle_relative_path(bundle_ref: str) -> str:
    """Return the Claude-visible relative path for a reviewer bundle."""

    return f"local-data/reviewer-bundles/{bundle_ref}"


def _require_reviewer_bundle_root(root: Path) -> None:
    expected = DEFAULT_REVIEWER_BUNDLE_ROOT.parts
    if root.parts[-len(expected) :] != expected:
        raise ContractValidationError("reviewer bundle root invalid")


def _safe_bundle_segment(value: str, *, fallback: str) -> str:
    segment = _SAFE_BUNDLE_SEGMENT_RE.sub("-", value).strip(".-")
    return segment[:80] if segment else fallback
