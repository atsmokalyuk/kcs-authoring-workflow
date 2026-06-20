"""Compact Desktop draft result shaping."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType


def compact_draft_result(
    result: Mapping[str, Any],
    bundle: Mapping[str, Any],
    *,
    include_reviewer_only_html: bool,
    reviewer_only_html: str,
) -> JsonDict:
    """Return compact Claude-visible draft status plus local bundle refs."""

    compact_keys = (
        "article_type",
        "auto_publish_allowed",
        "blockers",
        "debug_code",
        "draft_request_ready",
        "failure_stage",
        "item_ref",
        "network_calls",
        "ok",
        "pipeline_ok",
        "provider_calls",
        "public_output_approved",
        "quality_gaps",
        "ready_for_real_ticket_use",
        "ready_for_reviewer",
        "recommended_action",
        "result_kind",
        "reuse_search_status",
        "schema_version",
        "should_be_kcs_article",
        "validation_ok",
        "writes_files",
    )
    compact: JsonDict = {
        key: result[key]
        for key in compact_keys
        if key in result
    }
    compact.update(
        {
            "bundle_ref": bundle["bundle_ref"],
            "draft_generated": True,
            "html_path": bundle["html_path"],
            "html_sha256": bundle["html_sha256"],
            "kcs_ready": result.get("ready_for_reviewer") is True,
            "manifest_path": bundle["manifest_path"],
            "reviewer_bundle_written": True,
            "writes_files": True,
        }
    )
    for storage_key in ("bundle_storage_hint", "bundle_storage_ref"):
        storage_value = bundle.get(storage_key)
        if isinstance(storage_value, str) and storage_value:
            compact[storage_key] = storage_value
    if result.get("reuse_search_status") == "skipped":
        compact.update(
            {
                "blockers": ["reuse_search_not_checked"],
                "debug_code": "draft_only_reuse_search_missing",
                "kcs_ready": False,
                "pipeline_ok": False,
                "ready_for_reviewer": False,
                "recommended_action": "draft_only",
            }
        )
    compact["auto_publish_allowed"] = False
    compact["public_output_approved"] = False
    compact["ready_for_real_ticket_use"] = False
    if include_reviewer_only_html:
        compact["reviewer_only_html"] = reviewer_only_html
    return compact


def quality_blocker_gaps(result: Mapping[str, Any]) -> list[JsonDict]:
    """Return blocker-severity quality gaps from an author result."""

    quality_gaps = result.get("quality_gaps")
    if not isinstance(quality_gaps, list):
        return []
    return [
        dict(gap)
        for gap in quality_gaps
        if isinstance(gap, Mapping) and gap.get("severity") == "blocker"
    ]


def quality_blocked_result(
    result: Mapping[str, Any],
    quality_blockers: list[JsonDict],
    *,
    schema_version: str,
) -> JsonDict:
    """Return a controlled draft result when reviewer HTML quality blocks."""

    return {
        "article_type": result.get("article_type", ArticleType.NONE.value),
        "auto_publish_allowed": False,
        "blockers": [
            str(gap.get("kind", "reviewer_html_quality_blocked"))
            for gap in quality_blockers
        ],
        "debug_code": "reviewer_html_quality_blocked",
        "draft_generated": False,
        "draft_request_ready": False,
        "failure_stage": "renderer",
        "item_ref": result.get("item_ref"),
        "kcs_ready": False,
        "network_calls": False,
        "ok": False,
        "pipeline_ok": False,
        "provider_calls": False,
        "public_output_approved": False,
        "quality_gaps": result.get("quality_gaps", []),
        "ready_for_real_ticket_use": False,
        "ready_for_reviewer": False,
        "recommended_action": "blocked",
        "result_kind": "draft_article_authoring",
        "reuse_search_status": result.get("reuse_search_status"),
        "review_summary": {
            "draft_available": False,
            "reason": "reviewer_html_quality_blocked",
        },
        "reviewer_bundle_written": False,
        "schema_version": schema_version,
        "should_be_kcs_article": result.get("should_be_kcs_article") is True,
        "validation_ok": False,
        "writes_files": False,
    }


__all__ = [
    "compact_draft_result",
    "quality_blocked_result",
    "quality_blocker_gaps",
]
