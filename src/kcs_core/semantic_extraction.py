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
from kcs_core.json_payload import JsonDict, require_json_object
from kcs_core.models import ArticleType, NormalizedTicketEvidencePacket
from kcs_core.safety import InputClass
from kcs_core.sanitizer import (
    ensure_allowed_keys,
    ensure_safe_ref,
    ensure_safe_sanitized_payload,
    normalize_optional_string,
    normalize_string_list,
)

CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION = "candidate_semantic_extraction_v1"

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
        "candidate_id",
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
            resolution_steps=tuple(normalize_string_list(data.get("resolution_steps"))),
            question=normalize_optional_string(data.get("question")),
            supported_answer=normalize_optional_string(data.get("supported_answer")),
            open_questions=tuple(normalize_string_list(data.get("open_questions"))),
            environment=_environment(data.get("environment")),
        )

    def to_json_dict(self) -> JsonDict:
        return {
            "article_type_hint": self.article_type_hint,
            "candidate_id": self.candidate_id,
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
    ensure_safe_ref(
        extraction.extraction_source_ref, label="extraction_source_ref"
    )
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
    _ensure_enum_value(
        item.supportability, Supportability, field_name="supportability"
    )
    _ensure_enum_value(
        item.supportability_basis,
        SupportabilityBasis,
        field_name="supportability_basis",
    )
    _ensure_enum_value(
        item.kcs_item_status, KcsItemStatus, field_name="kcs_item_status"
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
    if (
        item.product_relation == ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value
        and item.kcs_item_status != KcsItemStatus.NO_ARTICLE.value
    ):
        raise ContractValidationError("semantic extraction product relation invalid")
    if (
        item.product_relation == ProductRelation.GENERIC_THIRD_PARTY.value
        and item.kcs_item_status != KcsItemStatus.NO_ARTICLE.value
    ):
        raise ContractValidationError("semantic extraction product relation invalid")
    if item.product_relation == (
        ProductRelation.NON_PLESK_OWNED_BUT_SUPPORT_PROVIDED_SOLUTION.value
    ) and (
        item.kcs_item_status != KcsItemStatus.INTERNAL_ONLY_CANDIDATE.value
        or item.visibility_hint != VisibilityHint.INTERNAL_REVIEWER_ONLY.value
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
        "confirmed_facts": list(item.confirmed_facts),
        "customer_reported": True,
        "customer_specific": (
            item.product_relation
            == ProductRelation.CUSTOMER_ENVIRONMENT_SPECIFIC.value
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
        "supported_resolution_or_workaround": (
            item.supported_resolution_or_workaround
        ),
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


def _ensure_enum_value(
    value: object, enum_type: type[StrEnum], *, field_name: str
) -> str:
    if not isinstance(value, str):
        raise ContractValidationError(f"unsupported semantic {field_name}")
    try:
        return enum_type(value).value
    except ValueError:
        raise ContractValidationError(
            f"unsupported semantic {field_name}"
        ) from None


def _source_refs(value: object, *, required: bool = False) -> list[str]:
    return [
        ensure_safe_ref(ref, label="source_ref")
        for ref in normalize_string_list(value, required=required)
    ]


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
