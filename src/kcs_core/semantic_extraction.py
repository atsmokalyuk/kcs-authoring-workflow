"""Untrusted semantic KCS item identification contracts for KCS-9a."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import (
    APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
    EvidenceBuildPolicy,
    build_evidence_packet_from_zendesk_export,
)
from kcs_core.json_payload import JsonDict, dumps_payload, require_json_object
from kcs_core.models import ArticleType, CandidateOrigin, NormalizedTicketEvidencePacket
from kcs_core.safety import InputClass
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
    normalize_optional_string,
    normalize_string_list,
)

CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION = "candidate_semantic_extraction_v1"
SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION = "semantic_issue_proposal_v1"
SEMANTIC_ISSUE_PROPOSAL_MAX_ISSUES = 12
SEMANTIC_ISSUE_PROPOSAL_MAX_COVERAGE_RECORDS = 24
SEMANTIC_ISSUE_PROPOSAL_MAX_OBSERVATIONS_PER_FIELD = 24
SEMANTIC_ISSUE_PROPOSAL_MAX_OBSERVATION_BYTES = 4_000
SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS = 48
SEMANTIC_ISSUE_PROPOSAL_MAX_TOTAL_BYTES = 64_000

_ALLOWED_EXTRACTION_FIELDS = frozenset(
    {
        "case_ref",
        "extraction_source_ref",
        "items",
        "schema_version",
        "source_refs",
    }
)
_ALLOWED_ITEM_FIELDS = frozenset(
    {
        "article_type_hint",
        "answer_steps",
        "candidate_id",
        "candidate_origin",
        "confirmed_facts",
        "eol_role",
        "environment",
        "item_type_hint",
        "kcs_item_status",
        "open_questions",
        "product_relation",
        "question",
        "resolution_steps",
        "source_refs",
        "summary",
        "supportability",
        "supportability_basis",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "visibility_hint",
    }
)

_ALLOWED_ISSUE_PROPOSAL_PACKET_FIELDS = frozenset(
    {
        "case_ref",
        "coverage_records",
        "extraction_source_ref",
        "issues",
        "schema_version",
        "source_refs",
    }
)
_ALLOWED_ISSUE_PROPOSAL_FIELDS = frozenset(
    {
        "answer_evidence",
        "cause_evidence",
        "context_evidence",
        "error_evidence",
        "issue_ref",
        "question",
        "resolution_evidence",
        "summary",
        "symptoms",
        "verification_evidence",
    }
)
_ALLOWED_SEMANTIC_OBSERVATION_FIELDS = frozenset({"source_refs", "text"})
_ALLOWED_SEMANTIC_COVERAGE_FIELDS = frozenset(
    {"coverage_ref", "duplicate_of_source_ref", "reason_code", "source_refs"}
)
class SemanticCoverageReason(StrEnum):
    """Closed non-issue coverage reason proposed for deterministic review."""

    INTERNAL_WORKFLOW_NOTE = "internal_workflow_note"
    TICKET_METADATA = "ticket_metadata"
    DUPLICATE_EXCERPT = "duplicate_excerpt"
    FORMATTING_ARTIFACT = "formatting_artifact"


@dataclass(frozen=True)
class SemanticObservation:
    """One bounded semantic observation with field-level provenance."""

    text: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _ensure_required_text(self.text, field_name="observation text")
        text_bytes = len(self.text.encode("utf-8"))
        if text_bytes > SEMANTIC_ISSUE_PROPOSAL_MAX_OBSERVATION_BYTES:
            raise ContractValidationError("semantic observation text invalid")
        _ensure_nonempty_source_ref_tuple(
            self.source_refs,
            field_name="observation source_refs",
        )
        ensure_safe_sanitized_payload(self.to_json_dict())

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "SemanticObservation":
        data = require_json_object(payload)
        ensure_allowed_keys(
            data,
            _ALLOWED_SEMANTIC_OBSERVATION_FIELDS,
            label="semantic observation",
        )
        return cls(
            text=_string_field(data, "text"),
            source_refs=tuple(
                _proposal_source_refs(data.get("source_refs"), required=True)
            ),
        )

    def to_json_dict(self) -> JsonDict:
        return {"source_refs": list(self.source_refs), "text": self.text}


@dataclass(frozen=True)
class SemanticIssueProposal:
    """Untrusted observation-only issue proposal without KCS action fields."""

    issue_ref: str
    summary: SemanticObservation
    symptoms: tuple[SemanticObservation, ...] = ()
    error_evidence: tuple[SemanticObservation, ...] = ()
    question: SemanticObservation | None = None
    cause_evidence: tuple[SemanticObservation, ...] = ()
    resolution_evidence: tuple[SemanticObservation, ...] = ()
    verification_evidence: tuple[SemanticObservation, ...] = ()
    answer_evidence: tuple[SemanticObservation, ...] = ()
    context_evidence: tuple[SemanticObservation, ...] = ()

    def __post_init__(self) -> None:
        ensure_safe_ref(self.issue_ref, label="issue_ref")
        if not isinstance(self.summary, SemanticObservation):
            raise ContractValidationError("semantic issue summary invalid")
        if self.question is not None and not isinstance(
            self.question, SemanticObservation
        ):
            raise ContractValidationError("semantic issue question invalid")
        for field_name in _ISSUE_OBSERVATION_SEQUENCE_FIELDS:
            _ensure_observation_tuple(
                getattr(self, field_name),
                field_name=field_name,
            )
        ensure_safe_sanitized_payload(self.to_json_dict())

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "SemanticIssueProposal":
        data = require_json_object(payload)
        ensure_allowed_keys(
            data,
            _ALLOWED_ISSUE_PROPOSAL_FIELDS,
            label="semantic issue proposal",
        )
        return cls(
            issue_ref=_safe_ref_field(data, "issue_ref"),
            summary=SemanticObservation.from_json_dict(data.get("summary")),
            symptoms=_observation_tuple(data.get("symptoms"), field_name="symptoms"),
            error_evidence=_observation_tuple(
                data.get("error_evidence", []), field_name="error_evidence"
            ),
            question=_optional_observation(data.get("question")),
            cause_evidence=_observation_tuple(
                data.get("cause_evidence"), field_name="cause_evidence"
            ),
            resolution_evidence=_observation_tuple(
                data.get("resolution_evidence"), field_name="resolution_evidence"
            ),
            verification_evidence=_observation_tuple(
                data.get("verification_evidence"),
                field_name="verification_evidence",
            ),
            answer_evidence=_observation_tuple(
                data.get("answer_evidence", []), field_name="answer_evidence"
            ),
            context_evidence=_observation_tuple(
                data.get("context_evidence"), field_name="context_evidence"
            ),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "answer_evidence": _observations_json(self.answer_evidence),
            "cause_evidence": _observations_json(self.cause_evidence),
            "context_evidence": _observations_json(self.context_evidence),
            "error_evidence": _observations_json(self.error_evidence),
            "issue_ref": self.issue_ref,
            "question": self.question.to_json_dict() if self.question else None,
            "resolution_evidence": _observations_json(self.resolution_evidence),
            "summary": self.summary.to_json_dict(),
            "symptoms": _observations_json(self.symptoms),
            "verification_evidence": _observations_json(self.verification_evidence),
        }

    def source_refs(self) -> tuple[str, ...]:
        refs = list(self.summary.source_refs)
        if self.question is not None:
            refs.extend(self.question.source_refs)
        for field_name in _ISSUE_OBSERVATION_SEQUENCE_FIELDS:
            for observation in getattr(self, field_name):
                refs.extend(observation.source_refs)
        return tuple(dict.fromkeys(refs))


@dataclass(frozen=True)
class SemanticCoverageRecord:
    """Non-issue source coverage proposal with no candidate authority."""

    coverage_ref: str
    reason_code: str
    source_refs: tuple[str, ...]
    duplicate_of_source_ref: str | None = None

    def __post_init__(self) -> None:
        ensure_safe_ref(self.coverage_ref, label="coverage_ref")
        _ensure_enum_value(
            self.reason_code,
            SemanticCoverageReason,
            field_name="coverage_reason",
        )
        _ensure_nonempty_source_ref_tuple(
            self.source_refs,
            field_name="coverage source_refs",
        )
        if self.reason_code == SemanticCoverageReason.DUPLICATE_EXCERPT.value:
            if self.duplicate_of_source_ref is None:
                raise ContractValidationError(
                    "semantic duplicate coverage source ref required"
                )
            ensure_safe_ref(
                self.duplicate_of_source_ref,
                label="duplicate_of_source_ref",
            )
            if self.duplicate_of_source_ref in self.source_refs:
                raise ContractValidationError(
                    "semantic duplicate coverage source ref invalid"
                )
        elif self.duplicate_of_source_ref is not None:
            raise ContractValidationError(
                "semantic coverage duplicate source ref not allowed"
            )
        ensure_safe_sanitized_payload(self.to_json_dict())

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "SemanticCoverageRecord":
        data = require_json_object(payload)
        ensure_allowed_keys(
            data,
            _ALLOWED_SEMANTIC_COVERAGE_FIELDS,
            label="semantic coverage record",
        )
        duplicate_ref = data.get("duplicate_of_source_ref")
        if duplicate_ref is not None and not isinstance(duplicate_ref, str):
            raise ContractValidationError(
                "semantic coverage duplicate source ref invalid"
            )
        return cls(
            coverage_ref=_safe_ref_field(data, "coverage_ref"),
            reason_code=_enum_field(
                data,
                "reason_code",
                SemanticCoverageReason,
            ),
            source_refs=tuple(
                _proposal_source_refs(data.get("source_refs"), required=True)
            ),
            duplicate_of_source_ref=duplicate_ref,
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "coverage_ref": self.coverage_ref,
            "duplicate_of_source_ref": self.duplicate_of_source_ref,
            "reason_code": self.reason_code,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class SemanticIssueProposalPacket:
    """Validated observation and coverage proposals for later projection."""

    case_ref: str
    extraction_source_ref: str
    source_refs: tuple[str, ...]
    issues: tuple[SemanticIssueProposal, ...]
    coverage_records: tuple[SemanticCoverageRecord, ...]
    schema_version: str = SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported semantic issue proposal schema_version"
            )
        ensure_safe_ref(self.case_ref, label="case_ref")
        ensure_safe_ref(self.extraction_source_ref, label="extraction_source_ref")
        _ensure_nonempty_source_ref_tuple(self.source_refs, field_name="source_refs")
        _validate_issue_proposal_packet_items(self)
        ensure_safe_sanitized_payload(self.to_json_dict())
        packet_bytes = len(dumps_payload(self).encode("utf-8"))
        if packet_bytes > SEMANTIC_ISSUE_PROPOSAL_MAX_TOTAL_BYTES:
            raise ContractValidationError("semantic issue proposal packet too large")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "SemanticIssueProposalPacket":
        data = require_json_object(payload)
        ensure_safe_sanitized_payload(data)
        ensure_allowed_keys(
            data,
            _ALLOWED_ISSUE_PROPOSAL_PACKET_FIELDS,
            label="semantic issue proposal packet",
        )
        if data.get("schema_version") != SEMANTIC_ISSUE_PROPOSAL_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported semantic issue proposal schema_version"
            )
        raw_issues = data.get("issues")
        raw_coverage = data.get("coverage_records")
        if (
            not isinstance(raw_issues, list)
            or len(raw_issues) > SEMANTIC_ISSUE_PROPOSAL_MAX_ISSUES
            or not isinstance(raw_coverage, list)
            or len(raw_coverage) > SEMANTIC_ISSUE_PROPOSAL_MAX_COVERAGE_RECORDS
        ):
            raise ContractValidationError("semantic issue proposal items invalid")
        return cls(
            case_ref=_safe_ref_field(data, "case_ref"),
            extraction_source_ref=_safe_ref_field(data, "extraction_source_ref"),
            source_refs=tuple(
                _proposal_source_refs(data.get("source_refs"), required=True)
            ),
            issues=tuple(
                SemanticIssueProposal.from_json_dict(item) for item in raw_issues
            ),
            coverage_records=tuple(
                SemanticCoverageRecord.from_json_dict(item) for item in raw_coverage
            ),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "case_ref": self.case_ref,
            "coverage_records": [
                record.to_json_dict() for record in self.coverage_records
            ],
            "extraction_source_ref": self.extraction_source_ref,
            "issues": [issue.to_json_dict() for issue in self.issues],
            "schema_version": self.schema_version,
            "source_refs": list(self.source_refs),
        }


_ISSUE_OBSERVATION_SEQUENCE_FIELDS = (
    "symptoms",
    "error_evidence",
    "cause_evidence",
    "resolution_evidence",
    "verification_evidence",
    "answer_evidence",
    "context_evidence",
)


class ProductRelation(StrEnum):
    """Semantic product-relation hint for a candidate KCS item."""

    PLESK_OWNED = "plesk_owned"
    PLESK_SHIPPED_OR_BUNDLED_COMPONENT = "plesk_shipped_or_bundled_component"
    PLESK_EXTENSION_CATALOG = "plesk_extension_catalog"
    PLESK_MANAGED_PROCESS_OR_SERVICE = "plesk_managed_process_or_service"
    NON_PLESK_OWNED_BUT_SUPPORT_PROVIDED_SOLUTION = (
        "non_plesk_owned_but_support_provided_solution"
    )
    GENERIC_THIRD_PARTY = "generic_third_party"
    CUSTOMER_ENVIRONMENT_SPECIFIC = "customer_environment_specific"
    EOL_OR_UNSUPPORTED_ONLY = "eol_or_unsupported_only"
    UNCLEAR = "unclear"


class Supportability(StrEnum):
    """Semantic supportability hint for a candidate KCS item."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    EOL_ONLY = "eol_only"
    UNCLEAR = "unclear"


class SupportabilityBasis(StrEnum):
    """Evidence basis for supportability hints."""

    EXPLICIT_INPUT_MENTION = "explicit_input_mention"
    NOT_CHECKED = "not_checked"


class KcsItemStatus(StrEnum):
    """Pre-decision semantic status for candidate KCS items."""

    CANDIDATE_ALLOWED = "candidate_allowed"
    INTERNAL_ONLY_CANDIDATE = "internal_only_candidate"
    NO_ARTICLE = "no_article"
    BLOCKED_NEED_MORE_EVIDENCE = "blocked_need_more_evidence"


class EolRole(StrEnum):
    """Role of an explicitly mentioned EOL subject in the candidate."""

    AFFECTED_RUNTIME = "affected_runtime"
    SOURCE_FOR_MIGRATION_OR_UPGRADE = "source_for_migration_or_upgrade"
    HISTORICAL_CONTEXT = "historical_context"
    UNCLEAR = "unclear"


class VisibilityHint(StrEnum):
    """Semantic visibility hint for candidate evidence."""

    PUBLIC_CUSTOMER_SAFE = "public_customer_safe"
    CUSTOMER_CONTEXT_ONLY = "customer_context_only"
    INTERNAL_REVIEWER_ONLY = "internal_reviewer_only"
    UNSAFE_PRIVATE = "unsafe_private"
    UNCLEAR = "unclear"


_PRODUCT_RELATION_VALUE_REQUIREMENTS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value: {
        "kcs_item_status": (KcsItemStatus.NO_ARTICLE.value,),
    },
    ProductRelation.GENERIC_THIRD_PARTY.value: {
        "kcs_item_status": (KcsItemStatus.NO_ARTICLE.value,),
    },
    ProductRelation.NON_PLESK_OWNED_BUT_SUPPORT_PROVIDED_SOLUTION.value: {
        "kcs_item_status": (KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,),
        "visibility_hint": (VisibilityHint.INTERNAL_REVIEWER_ONLY.value,),
    },
}


def product_relation_value_requirements() -> JsonDict:
    """Return fresh machine-readable cross-field product-relation rules."""

    return {
        relation: {
            field_name: list(accepted_values)
            for field_name, accepted_values in requirements.items()
        }
        for relation, requirements in _PRODUCT_RELATION_VALUE_REQUIREMENTS.items()
    }


class SemanticExtractionProvider(Protocol):
    """Provider boundary for bounded semantic item identification."""

    def propose_candidates(
        self, context: Mapping[str, Any]
    ) -> "CandidateSemanticExtraction | Mapping[str, Any]":
        """Return untrusted candidate semantic extraction output."""


@dataclass(frozen=True)
class CandidateKcsItem:
    """Untrusted semantic KCS item candidate."""

    candidate_id: str
    summary: str
    product_relation: str
    supportability: str
    kcs_item_status: str
    candidate_origin: str = CandidateOrigin.CUSTOMER_REPORTED.value
    supportability_basis: str = SupportabilityBasis.NOT_CHECKED.value
    article_type_hint: str = ArticleType.NONE.value
    visibility_hint: str = VisibilityHint.UNCLEAR.value
    eol_role: str = EolRole.UNCLEAR.value
    source_refs: tuple[str, ...] = ()
    symptoms: tuple[str, ...] = ()
    confirmed_facts: tuple[str, ...] = ()
    supported_cause: str | None = None
    supported_resolution_or_workaround: str | None = None
    resolution_steps: tuple[str, ...] = ()
    question: str | None = None
    supported_answer: str | None = None
    open_questions: tuple[str, ...] = ()
    environment: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_item(self)

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any] | object) -> "CandidateKcsItem":
        data = require_json_object(payload)
        ensure_allowed_keys(data, _ALLOWED_ITEM_FIELDS, label="semantic item")
        return cls(
            candidate_id=_safe_ref_field(data, "candidate_id"),
            summary=_string_field(data, "summary"),
            product_relation=_enum_field(data, "product_relation", ProductRelation),
            supportability=_enum_field(data, "supportability", Supportability),
            supportability_basis=_enum_field(
                data,
                "supportability_basis",
                SupportabilityBasis,
                default=SupportabilityBasis.NOT_CHECKED,
            ),
            kcs_item_status=_enum_field(data, "kcs_item_status", KcsItemStatus),
            candidate_origin=_enum_field(
                data,
                "candidate_origin",
                CandidateOrigin,
                default=CandidateOrigin.CUSTOMER_REPORTED,
            ),
            article_type_hint=_article_type_hint(data),
            visibility_hint=_enum_field(
                data, "visibility_hint", VisibilityHint, default=VisibilityHint.UNCLEAR
            ),
            eol_role=_enum_field(data, "eol_role", EolRole, default=EolRole.UNCLEAR),
            source_refs=tuple(_source_refs(data.get("source_refs"))),
            symptoms=tuple(normalize_string_list(data.get("symptoms"))),
            confirmed_facts=tuple(normalize_string_list(data.get("confirmed_facts"))),
            supported_cause=normalize_optional_string(data.get("supported_cause")),
            supported_resolution_or_workaround=normalize_optional_string(
                data.get("supported_resolution_or_workaround")
            ),
            resolution_steps=tuple(_semantic_resolution_steps(data)),
            question=normalize_optional_string(data.get("question")),
            supported_answer=normalize_optional_string(data.get("supported_answer")),
            open_questions=tuple(normalize_string_list(data.get("open_questions"))),
            environment=_environment(data.get("environment")),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "article_type_hint": self.article_type_hint,
            "candidate_id": self.candidate_id,
            "candidate_origin": self.candidate_origin,
            "confirmed_facts": list(self.confirmed_facts),
            "eol_role": self.eol_role,
            "environment": dict(self.environment),
            "kcs_item_status": self.kcs_item_status,
            "open_questions": list(self.open_questions),
            "product_relation": self.product_relation,
            "question": self.question,
            "source_refs": list(self.source_refs),
            "summary": self.summary,
            "supportability": self.supportability,
            "supportability_basis": self.supportability_basis,
            "supported_answer": self.supported_answer,
            "supported_cause": self.supported_cause,
            "supported_resolution_or_workaround": (
                self.supported_resolution_or_workaround
            ),
            "resolution_steps": list(self.resolution_steps),
            "symptoms": list(self.symptoms),
            "visibility_hint": self.visibility_hint,
        }


@dataclass(frozen=True)
class CandidateSemanticExtraction:
    """Untrusted KCS-9a semantic item identification packet."""

    case_ref: str
    extraction_source_ref: str
    source_refs: tuple[str, ...]
    items: tuple[CandidateKcsItem, ...]
    schema_version: str = CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported semantic extraction schema_version"
            )
        ensure_safe_ref(self.case_ref, label="case_ref")
        ensure_safe_ref(self.extraction_source_ref, label="extraction_source_ref")
        if not isinstance(self.source_refs, tuple):
            raise ContractValidationError("semantic extraction source refs invalid")
        for source_ref in self.source_refs:
            ensure_safe_ref(source_ref, label="source_ref")
        if not isinstance(self.items, tuple) or not self.items:
            raise ContractValidationError("semantic extraction requires items")
        for item in self.items:
            if not isinstance(item, CandidateKcsItem):
                raise ContractValidationError("semantic extraction item invalid")

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any] | object
    ) -> "CandidateSemanticExtraction":
        data = require_json_object(payload)
        ensure_safe_sanitized_payload(data)
        ensure_allowed_keys(
            data, _ALLOWED_EXTRACTION_FIELDS, label="semantic extraction"
        )
        if data.get("schema_version") != CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION:
            raise ContractValidationError(
                "unsupported semantic extraction schema_version"
            )
        items = data.get("items")
        if not isinstance(items, list):
            raise ContractValidationError("semantic extraction requires items")
        return cls(
            case_ref=_safe_ref_field(data, "case_ref"),
            extraction_source_ref=_safe_ref_field(data, "extraction_source_ref"),
            source_refs=tuple(_source_refs(data.get("source_refs"), required=True)),
            items=tuple(CandidateKcsItem.from_json_dict(item) for item in items),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "case_ref": self.case_ref,
            "extraction_source_ref": self.extraction_source_ref,
            "items": [item.to_json_dict() for item in self.items],
            "schema_version": self.schema_version,
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class SemanticExtractionValidationResult:
    """Value-safe validation result for KCS-9a extraction output."""

    ok: bool
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_json_dict(self) -> JsonDict:
        return {
            "ok": self.ok,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


def validate_candidate_semantic_extraction(
    payload: CandidateSemanticExtraction | Mapping[str, Any] | object,
) -> SemanticExtractionValidationResult:
    """Validate untrusted semantic extraction output without echoing values."""

    try:
        _coerce_extraction(payload)
    except ContractValidationError:
        return SemanticExtractionValidationResult(
            ok=False,
            blockers=("invalid_semantic_extraction",),
        )
    return SemanticExtractionValidationResult(ok=True)


def normalize_candidate_semantic_extraction(
    payload: CandidateSemanticExtraction | Mapping[str, Any] | object,
) -> JsonDict:
    """Normalize accepted semantic extraction into KCS-7 approved export JSON."""

    extraction = _coerce_extraction(payload)
    candidates = [
        _export_candidate(item, default_source_refs=extraction.source_refs)
        for item in extraction.items
    ]
    return {
        "schema_version": APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
        "input_class": InputClass.NORMALIZED_ZENDESK_EVIDENCE.value,
        "source_refs": list(extraction.source_refs),
        "environment": {},
        "symptoms": [],
        "confirmed_facts": [],
        "supported_cause": None,
        "supported_resolution_or_workaround": None,
        "open_questions": [],
        "visibility_summary": {
            "classes": [_overall_visibility(extraction.items)],
            "semantic_extraction_source_ref": extraction.extraction_source_ref,
        },
        "sanitizer_report": {
            "status": "passed",
            "semantic_extraction_validated": True,
        },
        "issue_candidates": candidates,
    }


def build_evidence_packet_from_semantic_extraction(
    payload: CandidateSemanticExtraction | Mapping[str, Any] | object,
    *,
    policy: EvidenceBuildPolicy | None = None,
) -> NormalizedTicketEvidencePacket:
    """Build accepted normalized evidence from validated semantic extraction."""

    extraction = _coerce_extraction(payload)
    export_payload = normalize_candidate_semantic_extraction(extraction)
    return build_evidence_packet_from_zendesk_export(
        export_payload,
        case_ref=extraction.case_ref,
        policy=policy or EvidenceBuildPolicy(),
    )


def propose_semantic_kcs_items(
    context: Mapping[str, Any] | object,
    *,
    provider: SemanticExtractionProvider,
) -> CandidateSemanticExtraction:
    """Call a bounded provider and validate its untrusted extraction output."""

    if not isinstance(context, Mapping):
        raise ContractValidationError("semantic extraction context invalid")
    ensure_safe_sanitized_payload(context)
    provider_failed = False
    extraction: CandidateSemanticExtraction | Mapping[str, Any] | object | None = None
    try:
        extraction = provider.propose_candidates(context)
    except Exception:
        provider_failed = True
    if provider_failed or extraction is None:
        raise ContractValidationError("semantic extraction provider failed") from None
    return _coerce_extraction(extraction)


def _coerce_extraction(
    payload: CandidateSemanticExtraction | Mapping[str, Any] | object,
) -> CandidateSemanticExtraction:
    if isinstance(payload, CandidateSemanticExtraction):
        _validate_extraction(payload)
        return payload
    return CandidateSemanticExtraction.from_json_dict(payload)


def _validate_extraction(extraction: CandidateSemanticExtraction) -> None:
    if extraction.schema_version != CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION:
        raise ContractValidationError("unsupported semantic extraction schema_version")
    ensure_safe_ref(extraction.case_ref, label="case_ref")
    ensure_safe_ref(extraction.extraction_source_ref, label="extraction_source_ref")
    _ensure_source_ref_tuple(extraction.source_refs, field_name="source_refs")
    if not isinstance(extraction.items, tuple) or not extraction.items:
        raise ContractValidationError("semantic extraction requires items")
    for item in extraction.items:
        if not isinstance(item, CandidateKcsItem):
            raise ContractValidationError("semantic extraction item invalid")
        _validate_item(item)


def _validate_item(item: CandidateKcsItem) -> None:
    ensure_safe_ref(item.candidate_id, label="candidate_id")
    _ensure_required_text(item.summary, field_name="summary")
    _ensure_source_ref_tuple(item.source_refs, field_name="source_refs")
    _ensure_string_tuple(item.symptoms, field_name="symptoms")
    _ensure_string_tuple(item.confirmed_facts, field_name="confirmed_facts")
    _ensure_string_tuple(item.open_questions, field_name="open_questions")
    _ensure_optional_text(item.supported_cause, field_name="supported_cause")
    _ensure_optional_text(
        item.supported_resolution_or_workaround,
        field_name="supported_resolution_or_workaround",
    )
    _ensure_string_tuple(item.resolution_steps, field_name="resolution_steps")
    _ensure_optional_text(item.question, field_name="question")
    _ensure_optional_text(item.supported_answer, field_name="supported_answer")
    if not isinstance(item.environment, Mapping):
        raise ContractValidationError("semantic item environment invalid")
    ensure_safe_sanitized_payload(item.environment)
    ensure_safe_sanitized_payload(item.to_json_dict())
    _ensure_enum_value(
        item.product_relation, ProductRelation, field_name="product_relation"
    )
    _ensure_enum_value(item.supportability, Supportability, field_name="supportability")
    _ensure_enum_value(
        item.supportability_basis,
        SupportabilityBasis,
        field_name="supportability_basis",
    )
    _ensure_enum_value(
        item.kcs_item_status, KcsItemStatus, field_name="kcs_item_status"
    )
    _ensure_enum_value(
        item.candidate_origin, CandidateOrigin, field_name="candidate_origin"
    )
    _ensure_enum_value(
        item.article_type_hint, ArticleType, field_name="article_type_hint"
    )
    _ensure_enum_value(
        item.visibility_hint, VisibilityHint, field_name="visibility_hint"
    )
    _ensure_enum_value(item.eol_role, EolRole, field_name="eol_role")
    _validate_classification_rules(item)


def _validate_classification_rules(item: CandidateKcsItem) -> None:
    _validate_eol_rules(item)
    _validate_product_relation_rules(item)


def _semantic_resolution_steps(data: Mapping[str, Any]) -> list[str]:
    resolution_steps = normalize_string_list(data.get("resolution_steps"))
    answer_steps = normalize_string_list(data.get("answer_steps"))
    if resolution_steps:
        return resolution_steps
    return answer_steps


def _validate_eol_rules(item: CandidateKcsItem) -> None:
    if (
        item.supportability
        in {Supportability.EOL_ONLY.value, Supportability.UNSUPPORTED.value}
        and item.supportability_basis
        != SupportabilityBasis.EXPLICIT_INPUT_MENTION.value
    ):
        raise ContractValidationError("semantic extraction eol basis invalid")
    if (
        item.supportability
        in {Supportability.EOL_ONLY.value, Supportability.UNSUPPORTED.value}
        and item.eol_role == EolRole.AFFECTED_RUNTIME.value
        and item.kcs_item_status != KcsItemStatus.NO_ARTICLE.value
    ):
        raise ContractValidationError("semantic extraction eol status invalid")
    if (
        item.supportability
        in {Supportability.EOL_ONLY.value, Supportability.UNSUPPORTED.value}
        and item.eol_role == EolRole.SOURCE_FOR_MIGRATION_OR_UPGRADE.value
        and item.kcs_item_status != KcsItemStatus.CANDIDATE_ALLOWED.value
    ):
        raise ContractValidationError("semantic extraction eol status invalid")
    if (
        item.supportability
        in {Supportability.EOL_ONLY.value, Supportability.UNSUPPORTED.value}
        and item.eol_role == EolRole.UNCLEAR.value
        and item.kcs_item_status != KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value
    ):
        raise ContractValidationError("semantic extraction eol status invalid")


def _validate_product_relation_rules(item: CandidateKcsItem) -> None:
    requirements = _PRODUCT_RELATION_VALUE_REQUIREMENTS.get(item.product_relation, {})
    if any(
        getattr(item, field_name) not in accepted_values
        for field_name, accepted_values in requirements.items()
    ):
        raise ContractValidationError("semantic extraction product relation invalid")


def _export_candidate(
    item: CandidateKcsItem, *, default_source_refs: Sequence[str]
) -> JsonDict:
    source_refs = item.source_refs or tuple(default_source_refs)
    return {
        "article_type": item.article_type_hint,
        "atomic": True,
        "candidate_id": item.candidate_id,
        "candidate_origin": item.candidate_origin,
        "confirmed_facts": list(item.confirmed_facts),
        "customer_reported": (
            item.candidate_origin == CandidateOrigin.CUSTOMER_REPORTED.value
        ),
        "customer_specific": (
            item.product_relation == ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value
        ),
        "environment": item.environment,
        "kcs_applicable": item.kcs_item_status
        in {
            KcsItemStatus.CANDIDATE_ALLOWED.value,
            KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,
        },
        "open_questions": list(item.open_questions),
        "public_solution_safe": (
            item.kcs_item_status == KcsItemStatus.CANDIDATE_ALLOWED.value
            and item.visibility_hint == VisibilityHint.PUBLIC_CUSTOMER_SAFE.value
        ),
        "question": item.question,
        "resolution_state": _resolution_state(item),
        "resolution_steps": list(item.resolution_steps),
        "source_refs": list(source_refs),
        "summary": item.summary,
        "supported_answer": item.supported_answer,
        "supported_cause": item.supported_cause,
        "supported_resolution_or_workaround": (item.supported_resolution_or_workaround),
        "symptoms": list(item.symptoms),
        "third_party_generic": (
            item.product_relation == ProductRelation.GENERIC_THIRD_PARTY.value
        ),
        "third_party_only": (
            item.product_relation == ProductRelation.GENERIC_THIRD_PARTY.value
        ),
        "unsupported_public_article": item.kcs_item_status
        in {
            KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value,
            KcsItemStatus.NO_ARTICLE.value,
        },
    }


def _resolution_state(item: CandidateKcsItem) -> str:
    if item.kcs_item_status == KcsItemStatus.BLOCKED_NEED_MORE_EVIDENCE.value:
        return "unsolved"
    if item.supported_answer or item.supported_resolution_or_workaround:
        return "answered"
    return "unknown"


def _overall_visibility(items: Sequence[CandidateKcsItem]) -> str:
    if any(
        item.visibility_hint == VisibilityHint.UNSAFE_PRIVATE.value for item in items
    ):
        return VisibilityHint.UNSAFE_PRIVATE.value
    if any(
        item.visibility_hint == VisibilityHint.INTERNAL_REVIEWER_ONLY.value
        for item in items
    ):
        return VisibilityHint.INTERNAL_REVIEWER_ONLY.value
    if any(
        item.visibility_hint == VisibilityHint.CUSTOMER_CONTEXT_ONLY.value
        for item in items
    ):
        return VisibilityHint.CUSTOMER_CONTEXT_ONLY.value
    if any(item.visibility_hint == VisibilityHint.UNCLEAR.value for item in items):
        return VisibilityHint.CUSTOMER_CONTEXT_ONLY.value
    return VisibilityHint.PUBLIC_CUSTOMER_SAFE.value


def _safe_ref_field(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ContractValidationError(f"{key} must be an opaque safe reference")
    return ensure_safe_ref(value, label=key)


def _ensure_required_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"semantic {field_name} invalid")
    normalized = normalize_optional_string(value)
    if normalized is None:
        raise ContractValidationError(f"semantic {field_name} invalid")
    return normalized


def _ensure_optional_text(value: object, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError(f"semantic {field_name} invalid")
    return normalize_optional_string(value)


def _ensure_string_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ContractValidationError(f"semantic {field_name} invalid")
    for item in value:
        if not isinstance(item, str):
            raise ContractValidationError(f"semantic {field_name} invalid")
        ensure_safe_sanitized_payload(item)
    return value


def _ensure_source_ref_tuple(value: object, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ContractValidationError(f"semantic {field_name} invalid")
    for ref in value:
        if not isinstance(ref, str):
            raise ContractValidationError(f"semantic {field_name} invalid")
        ensure_safe_ref(ref, label="source_ref")
    return value


def _ensure_nonempty_source_ref_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    refs = _ensure_source_ref_tuple(value, field_name=field_name)
    if (
        not refs
        or len(refs) > SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS
        or len(refs) != len(set(refs))
    ):
        raise ContractValidationError(f"semantic {field_name} invalid")
    return refs


def _observation_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[SemanticObservation, ...]:
    if not isinstance(value, list):
        raise ContractValidationError(f"semantic {field_name} invalid")
    if len(value) > SEMANTIC_ISSUE_PROPOSAL_MAX_OBSERVATIONS_PER_FIELD:
        raise ContractValidationError(f"semantic {field_name} invalid")
    return tuple(SemanticObservation.from_json_dict(item) for item in value)


def _optional_observation(value: object) -> SemanticObservation | None:
    if value is None:
        return None
    return SemanticObservation.from_json_dict(value)


def _ensure_observation_tuple(value: object, *, field_name: str) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) > SEMANTIC_ISSUE_PROPOSAL_MAX_OBSERVATIONS_PER_FIELD
        or any(not isinstance(item, SemanticObservation) for item in value)
    ):
        raise ContractValidationError(f"semantic {field_name} invalid")


def _observations_json(
    observations: tuple[SemanticObservation, ...],
) -> list[JsonDict]:
    return [observation.to_json_dict() for observation in observations]


def _validate_issue_proposal_packet_items(
    packet: SemanticIssueProposalPacket,
) -> None:
    _validate_proposal_item_collections(packet)
    _validate_proposal_item_refs(packet)
    _validate_proposal_source_coverage(packet)


def _validate_proposal_item_collections(
    packet: SemanticIssueProposalPacket,
) -> None:
    if (
        not isinstance(packet.issues, tuple)
        or len(packet.issues) > SEMANTIC_ISSUE_PROPOSAL_MAX_ISSUES
        or any(not isinstance(item, SemanticIssueProposal) for item in packet.issues)
    ):
        raise ContractValidationError("semantic issue proposal items invalid")
    if (
        not isinstance(packet.coverage_records, tuple)
        or len(packet.coverage_records) > SEMANTIC_ISSUE_PROPOSAL_MAX_COVERAGE_RECORDS
        or any(
            not isinstance(item, SemanticCoverageRecord)
            for item in packet.coverage_records
        )
    ):
        raise ContractValidationError("semantic coverage records invalid")


def _validate_proposal_item_refs(packet: SemanticIssueProposalPacket) -> None:
    issue_refs = [item.issue_ref for item in packet.issues]
    coverage_refs = [item.coverage_ref for item in packet.coverage_records]
    if len(issue_refs) != len(set(issue_refs)):
        raise ContractValidationError("semantic issue proposal refs invalid")
    if len(coverage_refs) != len(set(coverage_refs)):
        raise ContractValidationError("semantic coverage refs invalid")


def _validate_proposal_source_coverage(
    packet: SemanticIssueProposalPacket,
) -> None:
    allowed_refs = set(packet.source_refs)
    covered_refs: set[str] = set()
    for issue in packet.issues:
        covered_refs.update(_validated_issue_refs(issue, allowed_refs))
    for record in packet.coverage_records:
        covered_refs.update(_validated_coverage_refs(record, allowed_refs))
    if covered_refs != allowed_refs:
        raise ContractValidationError("semantic issue proposal coverage incomplete")


def _validated_issue_refs(
    issue: SemanticIssueProposal,
    allowed_refs: set[str],
) -> set[str]:
    refs = set(issue.source_refs())
    if not refs.issubset(allowed_refs):
        raise ContractValidationError("semantic issue proposal source refs invalid")
    return refs


def _validated_coverage_refs(
    record: SemanticCoverageRecord,
    allowed_refs: set[str],
) -> set[str]:
    refs = set(record.source_refs)
    if not refs.issubset(allowed_refs):
        raise ContractValidationError("semantic coverage source refs invalid")
    duplicate_ref = record.duplicate_of_source_ref
    if duplicate_ref is not None and duplicate_ref not in allowed_refs:
        raise ContractValidationError("semantic duplicate coverage source ref invalid")
    return refs


def _ensure_enum_value(
    value: object, enum_type: type[StrEnum], *, field_name: str
) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"unsupported semantic {field_name}")
    try:
        return enum_type(value).value
    except ValueError:
        raise ContractValidationError(f"unsupported semantic {field_name}") from None


def _source_refs(value: object, *, required: bool = False) -> list[str]:
    return [
        ensure_safe_ref(ref, label="source_ref")
        for ref in normalize_string_list(value, required=required)
    ]


def _proposal_source_refs(value: object, *, required: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > SEMANTIC_ISSUE_PROPOSAL_MAX_SOURCE_REFS
    ):
        raise ContractValidationError("semantic source_refs invalid")
    return _source_refs(value, required=required)


def _string_field(data: Mapping[str, Any], key: str) -> str:
    value = normalize_optional_string(data.get(key))
    if value is None:
        raise ContractValidationError(f"{key} must be a non-empty string")
    return value


def _enum_field(
    data: Mapping[str, Any],
    key: str,
    enum_type: type[StrEnum],
    *,
    default: StrEnum | None = None,
) -> str:
    value = data.get(key, default.value if default else None)
    if not isinstance(value, str):
        raise ContractValidationError(f"unsupported semantic {key}")
    try:
        return enum_type(value).value
    except ValueError:
        raise ContractValidationError(f"unsupported semantic {key}") from None


def _article_type_hint(data: Mapping[str, Any]) -> str:
    raw = data.get(
        "article_type_hint", data.get("item_type_hint", ArticleType.NONE.value)
    )
    if not isinstance(raw, str):
        raise ContractValidationError("unsupported semantic article_type_hint")
    try:
        return ArticleType(raw).value
    except ValueError:
        raise ContractValidationError(
            "unsupported semantic article_type_hint"
        ) from None


def _environment(value: object) -> JsonDict:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ContractValidationError("semantic item environment invalid")
    ensure_safe_sanitized_payload(value)
    return dict(value)
