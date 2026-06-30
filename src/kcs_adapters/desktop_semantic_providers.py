"""Desktop semantic extraction providers and explicit provider selection."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Any, Protocol

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType
from kcs_core.sanitizer import ensure_safe_ref, ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    CandidateSemanticExtraction,
    KcsItemStatus,
    ProductRelation,
    SemanticExtractionProvider,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
)

SEMANTIC_PROVIDER_ENV = "KCS_AUTHORING_SEMANTIC_PROVIDER"
SEMANTIC_PROVIDER_APPROVED_SUMMARY = "approved_summary"
SEMANTIC_PROVIDER_FIXTURE = "fixture"
SEMANTIC_PROVIDER_APPROVED = "approved"
SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET = "approved_clean_ticket"

_SEMANTIC_TEXT_TOOL_ARTIFACT_RE = re.compile(
    r"</?\s*(?:function|parameter|tool_call)\b|<\s*parameter\s+name\s*=",
    re.I,
)
_SEMANTIC_TEXT_SECRET_ARTIFACT_RE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"\bauthorization\s*:\s*bearer\s+\S+|"
    r"\b(?:api[_-]?key|password|passwd|secret|token)\s*[:=]\s*\S+",
    re.I,
)


class SemanticExtractionProviderUnavailableError(RuntimeError):
    """Approved semantic extraction provider is not configured."""


class NoSemanticCandidatesError(RuntimeError):
    """Provider completed but found no candidate KCS items."""


class ApprovedSemanticExtractionClient(Protocol):
    """Small boundary for an approved semantic extraction runtime client."""

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> CandidateSemanticExtraction | Mapping[str, Any]:
        """Return untrusted provider output."""


class UnavailableSemanticExtractionProvider:
    """Production default when no approved semantic provider is configured."""

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> CandidateSemanticExtraction | Mapping[str, Any]:
        ensure_safe_sanitized_payload(context)
        raise SemanticExtractionProviderUnavailableError


class ApprovedSemanticExtractionProvider:
    """Approved-provider adapter with safe refs and bounded public surface."""

    def __init__(
        self,
        *,
        provider_ref: str,
        client: ApprovedSemanticExtractionClient | None = None,
    ) -> None:
        ensure_safe_ref(provider_ref, label="provider_ref")
        self._provider_ref = provider_ref
        self._client = client

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> CandidateSemanticExtraction | Mapping[str, Any]:
        ensure_safe_sanitized_payload(context)
        if self._client is None:
            raise SemanticExtractionProviderUnavailableError
        provider_context: JsonDict = {
            "approved_summary_text": str(context.get("approved_summary_text", "")),
            "provider_ref": self._provider_ref,
            "schema_version": "kcs_desktop_semantic_request_v1",
        }
        ensure_safe_sanitized_payload(provider_context)
        return self._client.propose_candidates(provider_context)


class ApprovedSummarySemanticExtractionProvider:
    """Local production provider for explicit approved sanitized summaries."""

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> CandidateSemanticExtraction | Mapping[str, Any]:
        _ensure_semantic_provider_context_safe(context)
        text = str(context.get("approved_summary_text", "")).strip()
        if not text:
            raise NoSemanticCandidatesError
        from kcs_adapters.approved_summary_semantic import (
            semantic_extraction_from_approved_summary_text,
        )

        extraction = semantic_extraction_from_approved_summary_text(
            text,
            approved_clean_ticket=(
                context.get("source_kind") == SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET
            ),
        )
        if extraction is None:
            raise NoSemanticCandidatesError
        ensure_safe_sanitized_payload(extraction)
        return extraction


class FixtureSemanticExtractionProvider:
    """Fixture-only provider for deterministic smoke and unit tests."""

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> CandidateSemanticExtraction | Mapping[str, Any]:
        ensure_safe_sanitized_payload(context)
        text = str(context.get("approved_summary_text", ""))
        if text.strip() == (
            "Approved sanitized summary: Monitoring graphs show no data."
        ):
            raise NoSemanticCandidatesError
        if "Item 2:" in text or "another independent issue" in text:
            items = [
                _fixture_linux_monitoring_item(candidate_id="candidate-001"),
                _fixture_linux_extension_item(candidate_id="candidate-002"),
            ]
        elif "Plesk for Windows" in text or "via RDP" in text:
            items = [_fixture_windows_service_item()]
        elif "how to restart" in text.casefold() or "Question:" in text:
            items = [_fixture_howto_item()]
        else:
            items = [_fixture_linux_monitoring_item(candidate_id="candidate-001")]
        return _fixture_extraction(items)


def semantic_provider_from_environment() -> SemanticExtractionProvider:
    """Return the Desktop semantic provider selected by explicit environment."""

    provider_name = os.environ.get(SEMANTIC_PROVIDER_ENV, "").strip().casefold()
    if provider_name in {
        "",
        SEMANTIC_PROVIDER_APPROVED_SUMMARY,
        SEMANTIC_PROVIDER_APPROVED,
    }:
        return ApprovedSummarySemanticExtractionProvider()
    if provider_name == SEMANTIC_PROVIDER_FIXTURE:
        return FixtureSemanticExtractionProvider()
    return UnavailableSemanticExtractionProvider()


def _ensure_semantic_provider_context_safe(context: Mapping[str, Any]) -> None:
    if context.get("source_kind") != SEMANTIC_SOURCE_APPROVED_CLEAN_TICKET:
        ensure_safe_sanitized_payload(context)
        return
    text = str(context.get("approved_summary_text", ""))
    if not text.strip():
        raise ContractValidationError("approved_summary_text is empty")
    if _SEMANTIC_TEXT_TOOL_ARTIFACT_RE.search(text):
        raise ContractValidationError("approved clean ticket contains tool artifact")
    if _SEMANTIC_TEXT_SECRET_ARTIFACT_RE.search(text):
        raise ContractValidationError("approved clean ticket contains secret artifact")


def _fixture_extraction(items: list[JsonDict]) -> JsonDict:
    return {
        "case_ref": "desktop-fixture-case-001",
        "extraction_source_ref": "desktop-fixture-run-001",
        "items": items,
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": ["desktop-fixture-source-001"],
    }


def _fixture_linux_monitoring_item(*, candidate_id: str) -> JsonDict:
    return _fixture_technical_item(
        candidate_id=candidate_id,
        summary=(
            "Monitoring graphs show no data in Plesk due to custom collectd "
            "RRD data directory"
        ),
        symptoms=["Monitoring graphs show no data."],
        confirmed_facts=[
            (
                "The collectd configuration file is present under "
                "/etc/sw-collectd/conf.d/."
            ),
            (
                "The Monitoring backend does not query the configured metric "
                "data location."
            ),
        ],
        supported_cause=(
            "The collectd configuration file "
            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf pointed "
            "Monitoring metric data to a location that the Plesk Monitoring "
            "backend does not query."
        ),
        supported_resolution_or_workaround=(
            "Verify, back up, and disable "
            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf, restart "
            "sw-collectd, and confirm that Monitoring graphs start displaying "
            "new data."
        ),
        resolution_steps=[
            (
                "Run rpm -qf /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "to verify that the file is not owned by any package."
            ),
            (
                "Run cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "to review the DataDir setting."
            ),
            "Run mkdir -p /root/monitoring-case-backup to create a backup directory.",
            (
                "Run cp -a /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "/root/monitoring-case-backup/ to back up the custom collectd "
                "configuration file."
            ),
            (
                "Run mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
                "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled "
                "to disable the custom collectd configuration file."
            ),
            "Run systemctl restart sw-collectd.",
            (
                "Open the Monitoring page in Plesk and confirm graphs start "
                "displaying data."
            ),
            (
                "Wait for graphs to repopulate with newly collected metrics; "
                "historical data from before the correction may not be visible."
            ),
        ],
        environment={
            "applicable_to": ["Plesk for Linux"],
            "platform": "Plesk for Linux",
        },
    )


def _fixture_linux_extension_item(*, candidate_id: str) -> JsonDict:
    return _fixture_technical_item(
        candidate_id=candidate_id,
        summary="Monitoring extension post-install fails",
        symptoms=["Monitoring extension post-install fails."],
        confirmed_facts=["The module directory ownership is incorrect."],
        supported_cause="The module directory is owned by root instead of psaadm.",
        supported_resolution_or_workaround=(
            "Check module directory ownership and reinstall the Monitoring extension."
        ),
        resolution_steps=[
            (
                "Verify that /usr/local/psa/var/modules/monitoring/ is owned "
                "by psaadm:psaadm."
            ),
            "Reinstall the Monitoring extension from Plesk Extensions.",
        ],
        environment={
            "applicable_to": ["Plesk for Linux"],
            "platform": "Plesk for Linux",
        },
    )


def _fixture_windows_service_item() -> JsonDict:
    return _fixture_technical_item(
        candidate_id="candidate-001",
        summary="Plesk scheduled task fails on Windows",
        symptoms=["A Plesk scheduled task fails on Windows."],
        confirmed_facts=["The diagnostic summary references Windows service status."],
        supported_cause="A required Plesk Windows service is stopped.",
        supported_resolution_or_workaround=(
            "Connect to the Plesk server via RDP, check the Windows service, "
            "and repair the supported installation."
        ),
        resolution_steps=[
            "Connect to the Plesk server via RDP.",
            "Open the Windows Services screen and confirm the Plesk service status.",
            "Run plesk repair installation to repair the supported installation.",
        ],
        environment={
            "applicable_to": ["Plesk for Windows"],
            "platform": "Plesk for Windows",
        },
    )


def _fixture_howto_item() -> JsonDict:
    return {
        "article_type_hint": ArticleType.HOWTO_QA.value,
        "candidate_id": "candidate-001",
        "confirmed_facts": ["The operator needs to restart a Plesk service."],
        "environment": {
            "applicable_to": ["Plesk for Linux"],
            "platform": "Plesk for Linux",
        },
        "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
        "product_relation": ProductRelation.PLESK_OWNED.value,
        "question": "How to restart a Plesk service on Linux?",
        "source_refs": ["desktop-fixture-source-item-001"],
        "summary": "How to restart a Plesk service on Linux",
        "supportability": Supportability.SUPPORTED.value,
        "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
        "supported_answer": (
            "Connect to the Plesk server via SSH and run "
            "systemctl restart product-service."
        ),
        "symptoms": [],
        "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
    }


def _fixture_technical_item(
    *,
    candidate_id: str,
    summary: str,
    symptoms: list[str],
    confirmed_facts: list[str],
    supported_cause: str,
    supported_resolution_or_workaround: str,
    resolution_steps: list[str],
    environment: JsonDict,
) -> JsonDict:
    return {
        "article_type_hint": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": candidate_id,
        "confirmed_facts": confirmed_facts,
        "environment": environment,
        "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
        "product_relation": ProductRelation.PLESK_OWNED.value,
        "resolution_steps": resolution_steps,
        "source_refs": [f"desktop-fixture-source-{candidate_id}"],
        "summary": summary,
        "supportability": Supportability.SUPPORTED.value,
        "supportability_basis": SupportabilityBasis.NOT_CHECKED.value,
        "supported_cause": supported_cause,
        "supported_resolution_or_workaround": supported_resolution_or_workaround,
        "symptoms": symptoms,
        "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
    }


__all__ = [
    "ApprovedSemanticExtractionClient",
    "ApprovedSemanticExtractionProvider",
    "ApprovedSummarySemanticExtractionProvider",
    "FixtureSemanticExtractionProvider",
    "NoSemanticCandidatesError",
    "SEMANTIC_PROVIDER_APPROVED",
    "SEMANTIC_PROVIDER_APPROVED_SUMMARY",
    "SEMANTIC_PROVIDER_ENV",
    "SEMANTIC_PROVIDER_FIXTURE",
    "SemanticExtractionProviderUnavailableError",
    "UnavailableSemanticExtractionProvider",
    "semantic_provider_from_environment",
]
