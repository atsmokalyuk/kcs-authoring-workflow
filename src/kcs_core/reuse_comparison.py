"""Runtime-independent contracts for bounded reuse comparison evidence."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import ParseResult, urlparse

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.sanitizer import ensure_safe_sanitized_payload

REUSE_COMPARISON_EVIDENCE_SCHEMA_VERSION = "reuse_comparison_evidence_v1"

_MAX_SYMPTOMS = 5
_MAX_QUERY_CHARS = 512
_MAX_CANDIDATES = 3
_MAX_EXCERPTS = 6
_MAX_EXCERPTS_PER_ARTICLE = 2
_MAX_TOKENS = 1200
_MAX_EXCERPT_CHARS = 6000
_MAX_TOTAL_EXCERPT_CHARS = 24_000
_PUBLIC_SOURCE_TYPES = {
    "kb.plesk.com": "kb",
    "support.plesk.com": "support",
    "docs.plesk.com": "docs",
}
_REUSABLE_ARTICLE_SOURCE_TYPES = {
    "kb.plesk.com": "kb",
    "support.plesk.com": "support",
}
_ARTICLE_STATUSES = frozenset({"active", "stale_suspect", "deleted_from_site"})
_ORIGINS = frozenset({"explicit_resolution_reference", "search_result"})
_EVIDENCE_STATES = {
    "comparison_evidence_ready": (True, False),
    "comparison_no_evidence": (True, True),
    "explicit_article_context_missing": (True, True),
    "comparison_provider_unavailable": (False, True),
    "comparison_provider_not_ready": (False, True),
    "comparison_provider_invalid_response": (False, True),
}
_EXPLICIT_STATES = frozenset(
    {"not_provided", "not_checked", "context_ready", "context_missing"}
)
_SAFE_REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_PRIVATE_PATH_RE = re.compile(
    r"(?:/Users/|/home/|C:\\Users\\|\.knowledge(?:/|\\)|\.private(?:/|\\))",
    re.I,
)
_CREDENTIAL_RE = re.compile(
    r"(?:\bauthorization\s*:\s*(?:bearer|basic)\s+\S+|"
    r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+)",
    re.I,
)
_INCIDENT_TITLE_RE = re.compile(r"^\[\s*incident\s*\](?:\s|$)", re.I)


@dataclass(frozen=True)
class PublicArticleReference:
    """Operator-visible public article reference supplied by approved evidence."""

    public_url: str
    source_doc_id: str | None = None

    def __post_init__(self) -> None:
        _reusable_article_url(self.public_url)
        if self.source_doc_id is not None:
            _safe_ref(self.source_doc_id)

    def to_json_dict(self) -> JsonDict:
        return {
            "public_url": self.public_url,
            "source_doc_id": self.source_doc_id,
        }


@dataclass(frozen=True)
class ReuseComparisonEvidenceRequest:
    """Provider-neutral request built from validated public-safe symptoms."""

    symptoms: tuple[str, ...]
    explicit_article: PublicArticleReference | None = None

    def __post_init__(self) -> None:
        _validate_request(self)


@dataclass(frozen=True)
class ReuseComparisonExcerpt:
    """One bounded cited excerpt from an approved public article."""

    excerpt_ref: str
    section_path: str
    citation: str
    text: str
    token_count: int

    def __post_init__(self) -> None:
        _safe_ref(self.excerpt_ref)
        _bounded_public_text(self.section_path, max_chars=300, single_line=True)
        _bounded_public_text(
            self.citation,
            max_chars=1600,
            single_line=True,
            check_sensitive_patterns=False,
        )
        text = _bounded_public_text(self.text, max_chars=_MAX_EXCERPT_CHARS)
        if self.token_count != len(text.split()) or self.token_count < 1:
            raise ContractValidationError("comparison excerpt token count is invalid")

    def to_json_dict(self) -> JsonDict:
        return {
            "excerpt_ref": self.excerpt_ref,
            "section_path": self.section_path,
            "citation": self.citation,
            "text": self.text,
            "token_count": self.token_count,
        }


@dataclass(frozen=True)
class ReuseComparisonCandidate:
    """Public article context that remains unclassified until operator review."""

    rank: int
    source_doc_id: str
    source_type: str
    title: str
    public_url: str
    article_status: str
    updated_at: str | None
    origin: str
    excerpts: tuple[ReuseComparisonExcerpt, ...]

    def __post_init__(self) -> None:
        _validate_candidate(self)

    def to_json_dict(self) -> JsonDict:
        return {
            "rank": self.rank,
            "source_doc_id": self.source_doc_id,
            "source_type": self.source_type,
            "title": self.title,
            "public_url": self.public_url,
            "article_status": self.article_status,
            "updated_at": self.updated_at,
            "origin": self.origin,
            "excerpts": [excerpt.to_json_dict() for excerpt in self.excerpts],
        }


@dataclass(frozen=True)
class ReuseComparisonEvidence:
    """Bounded public evidence; never a KCS identity or action decision."""

    searched: bool
    status: str
    search_run_ref: str
    explicit_reference_status: str
    explicit_article: PublicArticleReference | None = None
    candidates: tuple[ReuseComparisonCandidate, ...] = ()
    blockers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_evidence(self)

    @property
    def schema_version(self) -> str:
        return REUSE_COMPARISON_EVIDENCE_SCHEMA_VERSION

    def to_json_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "searched": self.searched,
            "status": self.status,
            "search_run_ref": self.search_run_ref,
            "explicit_reference_status": self.explicit_reference_status,
            "explicit_article": (
                self.explicit_article.to_json_dict()
                if self.explicit_article is not None
                else None
            ),
            "candidates": [candidate.to_json_dict() for candidate in self.candidates],
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ReuseComparisonValidationResult:
    """Value-safe acceptance result for provider-returned comparison evidence."""

    ok: bool
    blockers: tuple[str, ...] = ()

    def to_json_dict(self) -> JsonDict:
        return {"ok": self.ok, "blockers": list(self.blockers)}


class ReuseComparisonEvidenceProvider(Protocol):
    """Narrow port implemented by local or future approved remote providers."""

    def collect_comparison_evidence(
        self,
        request: ReuseComparisonEvidenceRequest,
    ) -> ReuseComparisonEvidence: ...


def request_from_symptoms(
    symptoms: Sequence[str],
    *,
    explicit_article: PublicArticleReference | None = None,
) -> ReuseComparisonEvidenceRequest:
    """Build an immutable request without assigning search or KCS semantics."""

    if isinstance(symptoms, str):
        raise ContractValidationError("comparison evidence request is invalid")
    return ReuseComparisonEvidenceRequest(tuple(symptoms), explicit_article)


def is_reusable_kcs_article_url(value: object) -> bool:
    """Return whether a public URL may be offered for KCS reuse or update."""

    try:
        reusable_kcs_article_key(value)
    except ContractValidationError:
        return False
    return True


def is_reusable_kcs_article_candidate(
    *,
    public_url: object,
    title: object,
) -> bool:
    """Return whether public metadata may be offered for KCS reuse or update."""

    try:
        _reusable_article_url(public_url)
        _reusable_article_title(title)
    except ContractValidationError:
        return False
    return True


def reusable_kcs_article_key(value: object) -> str:
    """Return the canonical host/article-ID key for an eligible KCS article."""

    parsed = _reusable_article_url(value)
    article_id = _reusable_article_id(parsed)
    if parsed.hostname == "support.plesk.com":
        return f"support.plesk.com/articles/{article_id}"
    return f"kb.plesk.com/{article_id}"


def validate_reuse_comparison_evidence(
    evidence: ReuseComparisonEvidence | object,
) -> ReuseComparisonValidationResult:
    """Validate untrusted provider output without echoing evidence values."""

    try:
        if not isinstance(evidence, ReuseComparisonEvidence):
            raise ContractValidationError("comparison evidence is invalid")
        _validate_evidence(evidence)
    except ContractValidationError:
        return ReuseComparisonValidationResult(
            ok=False,
            blockers=("invalid_reuse_comparison_evidence",),
        )
    return ReuseComparisonValidationResult(ok=True)


def ensure_valid_reuse_comparison_evidence(
    evidence: ReuseComparisonEvidence | object,
) -> None:
    """Fail closed when provider output violates the public evidence contract."""

    result = validate_reuse_comparison_evidence(evidence)
    if not result.ok:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_request(request: ReuseComparisonEvidenceRequest) -> None:
    _validate_symptom_collection(request.symptoms)
    _validate_explicit_article_type(request.explicit_article)


def _validate_symptom_collection(symptoms: tuple[str, ...]) -> None:
    if not isinstance(symptoms, tuple):
        raise ContractValidationError("comparison evidence request is invalid")
    if not 1 <= len(symptoms) <= _MAX_SYMPTOMS:
        raise ContractValidationError("comparison evidence request is invalid")
    total_chars = 0
    for symptom in symptoms:
        _validate_symptom(symptom)
        total_chars += len(symptom)
    if total_chars > _MAX_QUERY_CHARS:
        raise ContractValidationError("comparison evidence request is invalid")


def _validate_symptom(symptom: object) -> None:
    if not isinstance(symptom, str):
        raise ContractValidationError("comparison evidence request is invalid")
    if not symptom.strip():
        raise ContractValidationError("comparison evidence request is invalid")
    ensure_safe_sanitized_payload(symptom)


def _validate_explicit_article_type(value: object) -> None:
    if value is not None and not isinstance(value, PublicArticleReference):
        raise ContractValidationError("comparison evidence request is invalid")


def _validate_candidate(candidate: ReuseComparisonCandidate) -> None:
    _validate_candidate_identity(candidate)
    _validate_candidate_excerpts(candidate)


def _validate_candidate_identity(candidate: ReuseComparisonCandidate) -> None:
    _validate_candidate_rank(candidate.rank)
    _safe_ref(candidate.source_doc_id)
    _validate_candidate_public_identity(candidate)
    _validate_candidate_metadata(candidate)


def _validate_candidate_rank(rank: object) -> None:
    if not isinstance(rank, int):
        raise ContractValidationError("comparison candidate is invalid")
    if isinstance(rank, bool) or rank < 1:
        raise ContractValidationError("comparison candidate is invalid")


def _validate_candidate_public_identity(candidate: ReuseComparisonCandidate) -> None:
    hostname = _reusable_article_url(candidate.public_url).hostname or ""
    if candidate.source_type != _REUSABLE_ARTICLE_SOURCE_TYPES[hostname]:
        raise ContractValidationError("comparison candidate is invalid")


def _validate_candidate_metadata(candidate: ReuseComparisonCandidate) -> None:
    _reusable_article_title(candidate.title)
    if candidate.article_status not in _ARTICLE_STATUSES:
        raise ContractValidationError("comparison candidate is invalid")
    if candidate.updated_at is not None:
        _bounded_public_text(candidate.updated_at, max_chars=64, single_line=True)
    if candidate.origin not in _ORIGINS:
        raise ContractValidationError("comparison candidate is invalid")


def _validate_candidate_excerpts(candidate: ReuseComparisonCandidate) -> None:
    if not isinstance(candidate.excerpts, tuple):
        raise ContractValidationError("comparison candidate is invalid")
    if not 1 <= len(candidate.excerpts) <= _MAX_EXCERPTS_PER_ARTICLE:
        raise ContractValidationError("comparison candidate is invalid")
    if any(
        not isinstance(value, ReuseComparisonExcerpt) for value in candidate.excerpts
    ):
        raise ContractValidationError("comparison candidate is invalid")
    for excerpt in candidate.excerpts:
        expected_citation = (
            f"{candidate.title} — {excerpt.section_path} — {candidate.public_url}"
        )
        if excerpt.citation != expected_citation:
            raise ContractValidationError("comparison candidate is invalid")


def _validate_evidence(evidence: ReuseComparisonEvidence) -> None:
    expected_state = _EVIDENCE_STATES.get(evidence.status)
    if expected_state is None or not isinstance(evidence.searched, bool):
        raise ContractValidationError("comparison evidence is invalid")
    searched, blocked = expected_state
    if evidence.searched is not searched:
        raise ContractValidationError("comparison evidence is invalid")
    if evidence.explicit_reference_status not in _EXPLICIT_STATES:
        raise ContractValidationError("comparison evidence is invalid")
    _validate_evidence_refs_and_bounds(evidence)
    _validate_evidence_state(evidence, blocked=blocked)
    _validate_explicit_reference_state(evidence)


def _validate_evidence_refs_and_bounds(evidence: ReuseComparisonEvidence) -> None:
    _validate_search_ref(evidence)
    _validate_candidate_collection(evidence.candidates)
    _validate_excerpt_collection(evidence.candidates)


def _validate_search_ref(evidence: ReuseComparisonEvidence) -> None:
    if evidence.searched:
        _safe_ref(evidence.search_run_ref)
    elif evidence.search_run_ref:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_candidate_collection(
    candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    if not isinstance(candidates, tuple):
        raise ContractValidationError("comparison evidence is invalid")
    if len(candidates) > _MAX_CANDIDATES:
        raise ContractValidationError("comparison evidence is invalid")
    article_keys: set[str] = set()
    for expected_rank, candidate in enumerate(candidates, start=1):
        _validate_candidate_collection_item(candidate, expected_rank, article_keys)


def _validate_candidate_collection_item(
    candidate: object,
    expected_rank: int,
    article_keys: set[str],
) -> None:
    if not isinstance(candidate, ReuseComparisonCandidate):
        raise ContractValidationError("comparison evidence is invalid")
    if candidate.rank != expected_rank:
        raise ContractValidationError("comparison evidence is invalid")
    article_key = _public_article_key(candidate.public_url)
    if article_key in article_keys:
        raise ContractValidationError("comparison evidence is invalid")
    article_keys.add(article_key)


def _validate_excerpt_collection(
    candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    excerpts = _comparison_excerpts(candidates)
    _validate_excerpt_totals(excerpts)
    _validate_unique_excerpt_refs(excerpts)


def _comparison_excerpts(
    candidates: tuple[ReuseComparisonCandidate, ...],
) -> tuple[ReuseComparisonExcerpt, ...]:
    excerpts: list[ReuseComparisonExcerpt] = []
    for candidate in candidates:
        excerpts.extend(candidate.excerpts)
    return tuple(excerpts)


def _validate_excerpt_totals(
    excerpts: tuple[ReuseComparisonExcerpt, ...],
) -> None:
    if len(excerpts) > _MAX_EXCERPTS:
        raise ContractValidationError("comparison evidence is invalid")
    if sum(excerpt.token_count for excerpt in excerpts) > _MAX_TOKENS:
        raise ContractValidationError("comparison evidence is invalid")
    if sum(len(excerpt.text) for excerpt in excerpts) > _MAX_TOTAL_EXCERPT_CHARS:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_unique_excerpt_refs(
    excerpts: tuple[ReuseComparisonExcerpt, ...],
) -> None:
    refs: set[str] = set()
    for excerpt in excerpts:
        if excerpt.excerpt_ref in refs:
            raise ContractValidationError("comparison evidence is invalid")
        refs.add(excerpt.excerpt_ref)


def _validate_evidence_state(
    evidence: ReuseComparisonEvidence,
    *,
    blocked: bool,
) -> None:
    expected_blockers = (evidence.status,) if blocked else ()
    if evidence.blockers != expected_blockers:
        raise ContractValidationError("comparison evidence is invalid")
    _validate_ready_evidence_state(evidence)
    _validate_empty_evidence_state(evidence)
    _validate_unsearched_evidence_state(evidence)


def _validate_ready_evidence_state(evidence: ReuseComparisonEvidence) -> None:
    if evidence.status != "comparison_evidence_ready":
        return
    if not evidence.candidates:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_empty_evidence_state(evidence: ReuseComparisonEvidence) -> None:
    if evidence.status != "comparison_no_evidence":
        return
    if evidence.candidates:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_unsearched_evidence_state(evidence: ReuseComparisonEvidence) -> None:
    if evidence.searched:
        return
    if evidence.candidates:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_explicit_reference_state(evidence: ReuseComparisonEvidence) -> None:
    explicit_candidates = _explicit_candidates(evidence.candidates)
    _validate_explicit_article_type(evidence.explicit_article)
    if evidence.explicit_article is None:
        _validate_no_explicit_reference(evidence, explicit_candidates)
        return
    validators = {
        "not_checked": _validate_unchecked_explicit_reference,
        "context_missing": _validate_missing_explicit_reference,
        "context_ready": _validate_ready_explicit_reference,
    }
    validator = validators.get(evidence.explicit_reference_status)
    if validator is None:
        raise ContractValidationError("comparison evidence is invalid")
    validator(evidence, explicit_candidates)


def _explicit_candidates(
    candidates: tuple[ReuseComparisonCandidate, ...],
) -> tuple[ReuseComparisonCandidate, ...]:
    return tuple(
        candidate
        for candidate in candidates
        if candidate.origin == "explicit_resolution_reference"
    )


def _validate_no_explicit_reference(
    evidence: ReuseComparisonEvidence,
    explicit_candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    if evidence.explicit_reference_status != "not_provided" or explicit_candidates:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_unchecked_explicit_reference(
    evidence: ReuseComparisonEvidence,
    explicit_candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    if evidence.searched or explicit_candidates:
        raise ContractValidationError("comparison evidence is invalid")


def _validate_missing_explicit_reference(
    evidence: ReuseComparisonEvidence,
    explicit_candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    if explicit_candidates or evidence.status != "explicit_article_context_missing":
        raise ContractValidationError("comparison evidence is invalid")


def _validate_ready_explicit_reference(
    evidence: ReuseComparisonEvidence,
    explicit_candidates: tuple[ReuseComparisonCandidate, ...],
) -> None:
    if (
        len(explicit_candidates) != 1
        or evidence.candidates[0] is not explicit_candidates[0]
    ):
        raise ContractValidationError("comparison evidence is invalid")
    if not _candidate_matches_reference(
        explicit_candidates[0], evidence.explicit_article
    ):
        raise ContractValidationError("comparison evidence is invalid")


def _candidate_matches_reference(
    candidate: ReuseComparisonCandidate,
    reference: PublicArticleReference,
) -> bool:
    if _public_article_key(candidate.public_url) != _public_article_key(
        reference.public_url
    ):
        return False
    return (
        reference.source_doc_id is None
        or candidate.source_doc_id == reference.source_doc_id
    )


def _public_url(value: object) -> ParseResult:
    if not isinstance(value, str):
        raise ContractValidationError("public article reference is invalid")
    if not value or len(value) > 1000:
        raise ContractValidationError("public article reference is invalid")
    parsed, port = _parse_public_url(value)
    _validate_public_url_origin(parsed, port)
    _validate_public_url_shape(parsed, value)
    return parsed


def _reusable_article_url(value: object) -> ParseResult:
    parsed = _public_url(value)
    if parsed.hostname not in _REUSABLE_ARTICLE_SOURCE_TYPES:
        raise ContractValidationError("public article reference is invalid")
    _reusable_article_id(parsed)
    return parsed


def _reusable_article_title(value: object) -> str:
    title = _bounded_public_text(value, max_chars=300, single_line=True)
    if _INCIDENT_TITLE_RE.match(title):
        raise ContractValidationError("comparison candidate is invalid")
    return title


def _reusable_article_id(parsed: ParseResult) -> str:
    parts = parsed.path.strip("/").split("/")
    if parsed.hostname == "support.plesk.com":
        if len(parts) != 4 or parts[0] != "hc" or parts[2] != "articles":
            raise ContractValidationError("public article reference is invalid")
        article_id = parts[3].split("-", 1)[0]
    else:
        article_id = _legacy_kb_article_id(parts)
    if not article_id.isdigit():
        raise ContractValidationError("public article reference is invalid")
    return article_id


def _legacy_kb_article_id(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2 and re.fullmatch(r"[A-Za-z]{2}(?:-[A-Za-z]{2})?", parts[0]):
        return parts[1]
    raise ContractValidationError("public article reference is invalid")


def _parse_public_url(value: str) -> tuple[ParseResult, int | None]:
    try:
        parsed = urlparse(value)
        return parsed, parsed.port
    except ValueError:
        raise ContractValidationError("public article reference is invalid") from None


def _validate_public_url_origin(parsed: ParseResult, port: int | None) -> None:
    actual = (
        parsed.scheme,
        parsed.hostname in _PUBLIC_SOURCE_TYPES,
        parsed.username,
        parsed.password,
        port in {None, 443},
    )
    if actual != ("https", True, None, None, True):
        raise ContractValidationError("public article reference is invalid")


def _validate_public_url_shape(parsed: ParseResult, value: str) -> None:
    if parsed.query or parsed.fragment:
        raise ContractValidationError("public article reference is invalid")
    if any(character.isspace() for character in value):
        raise ContractValidationError("public article reference is invalid")


def _public_article_key(value: str) -> str:
    return reusable_kcs_article_key(value)


def _safe_ref(value: object) -> str:
    if not isinstance(value, str) or not _SAFE_REF_RE.fullmatch(value):
        raise ContractValidationError("comparison reference is invalid")
    return value


def _bounded_public_text(
    value: object,
    *,
    max_chars: int,
    single_line: bool = False,
    check_sensitive_patterns: bool = True,
) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("comparison public text is invalid")
    text = value.strip()
    if not text or len(text) > max_chars:
        raise ContractValidationError("comparison public text is invalid")
    _validate_public_text_line_shape(text, single_line=single_line)
    _validate_public_text_safety(
        text,
        check_sensitive_patterns=check_sensitive_patterns,
    )
    return text


def _validate_public_text_line_shape(text: str, *, single_line: bool) -> None:
    if single_line and ("\r" in text or "\n" in text):
        raise ContractValidationError("comparison public text is invalid")


def _validate_public_text_safety(
    text: str,
    *,
    check_sensitive_patterns: bool,
) -> None:
    if _has_forbidden_control_character(text):
        raise ContractValidationError("comparison public text is invalid")
    if not check_sensitive_patterns:
        return
    if _PRIVATE_PATH_RE.search(text) or _CREDENTIAL_RE.search(text):
        raise ContractValidationError("comparison public text is invalid")


def _has_forbidden_control_character(text: str) -> bool:
    return any(ord(character) < 32 and character not in "\n\r\t" for character in text)


__all__ = [
    "REUSE_COMPARISON_EVIDENCE_SCHEMA_VERSION",
    "PublicArticleReference",
    "ReuseComparisonCandidate",
    "ReuseComparisonEvidence",
    "ReuseComparisonEvidenceProvider",
    "ReuseComparisonEvidenceRequest",
    "ReuseComparisonExcerpt",
    "ReuseComparisonValidationResult",
    "ensure_valid_reuse_comparison_evidence",
    "is_reusable_kcs_article_candidate",
    "is_reusable_kcs_article_url",
    "request_from_symptoms",
    "reusable_kcs_article_key",
    "validate_reuse_comparison_evidence",
]
