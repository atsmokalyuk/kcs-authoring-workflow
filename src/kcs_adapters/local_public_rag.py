"""Loopback-only metadata adapter for the local public Plesk RAG runtime."""

from __future__ import annotations

import ipaddress
import json
import math
import re
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol
from urllib.parse import ParseResult, urlparse

from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.reuse_comparison import (
    PublicArticleReference,
    ReuseComparisonCandidate,
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceRequest,
    ReuseComparisonExcerpt,
    ensure_valid_reuse_comparison_evidence,
)
from kcs_core.sanitizer import ensure_safe_sanitized_payload

LOCAL_PUBLIC_RAG_SNIPPETS_SCHEMA_VERSION = "knowledge-cited-snippets-v1"
LOCAL_PUBLIC_RAG_STATUS_SCHEMA_VERSION = "knowledge-runtime-status-v1"
LOCAL_PUBLIC_RAG_SEARCH_SCHEMA_VERSION = "knowledge-hybrid-search-v1"

_DEFAULT_BASE_URL = "http://127.0.0.1:8768"
_DEFAULT_TIMEOUT_SECONDS = 30
_DEFAULT_MAX_RESPONSE_BYTES = 128 * 1024
_DEFAULT_TOP_K = 5
_MAX_TIMEOUT_SECONDS = 30
_MAX_TOP_K = 5
_MAX_QUERY_CHARS = 512
_MAX_SYMPTOMS = 5
_COMPARISON_MAX_CANDIDATES = 3
_COMPARISON_MAX_EXCERPTS = 6
_COMPARISON_MAX_TOKENS = 1200
_COMPARISON_PER_ARTICLE_CAP = 2
_MAX_EXCERPT_CHARS = 6000
_MAX_TOTAL_EXCERPT_CHARS = 24_000
_PUBLIC_SOURCE_TYPES = {
    "kb.plesk.com": "kb",
    "support.plesk.com": "support",
    "docs.plesk.com": "docs",
}
_ARTICLE_STATUSES = frozenset({"active", "stale_suspect", "deleted_from_site"})
_MATCHED_RETRIEVERS = frozenset({"keyword", "vector"})
_WHITESPACE_RE = re.compile(r"\s+")
_SOURCE_DOC_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_PRIVATE_EXCERPT_RE = re.compile(
    r"(?:/Users/|/home/|C:\\Users\\|\.knowledge(?:/|\\)|\.private(?:/|\\))",
    re.I,
)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?:\bauthorization\s*:\s*(?:bearer|basic)\s+\S+|"
    r"\b(?:password|passwd|api[_-]?key|token|secret)\s*[:=-]\s*\S+)",
    re.I,
)
_COMPARISON_FAILURE_STATUSES = {
    "rag_runtime_unavailable": "comparison_provider_unavailable",
    "rag_runtime_invalid_response": "comparison_provider_invalid_response",
    "rag_runtime_cold": "comparison_provider_not_ready",
    "rag_runtime_stale": "comparison_provider_not_ready",
    "rag_runtime_hybrid_not_ready": "comparison_provider_not_ready",
    "rag_comparison_invalid_response": "comparison_provider_invalid_response",
}


class LocalPublicRagTransportError(RuntimeError):
    """Value-free transport failure at the local RAG boundary."""


class LocalPublicRagTransport(Protocol):
    """Small injectable JSON transport used by the adapter."""

    def get_json(
        self,
        *,
        url: str,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object: ...

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object: ...


@dataclass(frozen=True)
class LocalPublicRagConfig:
    """Explicit bounded connection settings for the local RAG runtime."""

    base_url: str = _DEFAULT_BASE_URL
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES
    top_k: int = _DEFAULT_TOP_K

    def __post_init__(self) -> None:
        _validate_base_url(self.base_url)
        if not 1 <= self.timeout_seconds <= _MAX_TIMEOUT_SECONDS:
            raise ContractValidationError("local public RAG timeout is invalid")
        if not 1024 <= self.max_response_bytes <= _DEFAULT_MAX_RESPONSE_BYTES:
            raise ContractValidationError("local public RAG response bound is invalid")
        if not 1 <= self.top_k <= _MAX_TOP_K:
            raise ContractValidationError("local public RAG result bound is invalid")


@dataclass(frozen=True)
class LocalPublicRagReadiness:
    """Value-safe readiness summary projected from the local runtime."""

    ready: bool
    status: str
    article_count: int = 0
    chunk_count: int = 0
    vector_count: int = 0

    def to_json_dict(self) -> JsonDict:
        return {
            "ready": self.ready,
            "status": self.status,
            "article_count": self.article_count,
            "chunk_count": self.chunk_count,
            "vector_count": self.vector_count,
        }


@dataclass(frozen=True)
class LocalPublicRagCandidate:
    """Allowlisted public metadata for one unclassified search candidate."""

    rank: int
    source_doc_id: str
    source_type: str
    title: str
    public_url: str
    section_path: str | None
    article_status: str
    updated_at: str | None
    score: float
    matched_retrievers: tuple[str, ...]

    def to_json_dict(self) -> JsonDict:
        return {
            "rank": self.rank,
            "source_doc_id": self.source_doc_id,
            "source_type": self.source_type,
            "title": self.title,
            "public_url": self.public_url,
            "section_path": self.section_path,
            "article_status": self.article_status,
            "updated_at": self.updated_at,
            "score": self.score,
            "matched_retrievers": list(self.matched_retrievers),
        }


@dataclass(frozen=True)
class LocalPublicRagSearchResult:
    """Metadata-only result that deliberately carries no KCS identity."""

    searched: bool
    status: str
    search_run_ref: str
    candidates: tuple[LocalPublicRagCandidate, ...] = ()

    def to_json_dict(self) -> JsonDict:
        return {
            "searched": self.searched,
            "status": self.status,
            "search_run_ref": self.search_run_ref,
            "candidates": [candidate.to_json_dict() for candidate in self.candidates],
        }


@dataclass(frozen=True)
class _ParsedComparisonExcerpt:
    candidate_rank: int
    source_doc_id: str
    source_type: str
    title: str
    public_url: str
    section_path: str
    article_status: str
    updated_at: str | None
    excerpt: ReuseComparisonExcerpt


class LocalPublicRagAdapter:
    """Check readiness and run bounded metadata-only local public search."""

    def __init__(
        self,
        config: LocalPublicRagConfig | None = None,
        *,
        transport: LocalPublicRagTransport | None = None,
    ) -> None:
        self._config = config or LocalPublicRagConfig()
        self._transport = transport or UrlLibLocalPublicRagTransport()

    def check_readiness(self) -> LocalPublicRagReadiness:
        try:
            payload = self._transport.get_json(
                url=f"{self._config.base_url.rstrip('/')}/api/status",
                timeout_seconds=self._config.timeout_seconds,
                max_response_bytes=self._config.max_response_bytes,
            )
            return _parse_readiness(payload)
        except LocalPublicRagTransportError:
            return LocalPublicRagReadiness(False, "rag_runtime_unavailable")
        except ContractValidationError:
            return LocalPublicRagReadiness(False, "rag_runtime_invalid_response")

    def search(self, symptoms: Sequence[str]) -> LocalPublicRagSearchResult:
        query = build_local_public_rag_query(symptoms)
        readiness = self.check_readiness()
        if not readiness.ready:
            return LocalPublicRagSearchResult(False, readiness.status, "")
        try:
            payload = self._transport.post_json(
                url=f"{self._config.base_url.rstrip('/')}/api/search-hybrid",
                payload={"query": query, "top_k": self._config.top_k},
                timeout_seconds=self._config.timeout_seconds,
                max_response_bytes=self._config.max_response_bytes,
            )
            return _parse_search_result(payload, top_k=self._config.top_k)
        except LocalPublicRagTransportError:
            return LocalPublicRagSearchResult(False, "rag_runtime_unavailable", "")
        except ContractValidationError:
            return LocalPublicRagSearchResult(False, "rag_search_invalid_response", "")

    def collect_comparison_evidence(
        self,
        request: ReuseComparisonEvidenceRequest,
    ) -> ReuseComparisonEvidence:
        """Return bounded public excerpts without assigning article identity."""

        query = build_local_public_rag_query(request.symptoms)
        explicit_article = _validated_explicit_article(request.explicit_article)
        readiness = self.check_readiness()
        if not readiness.ready:
            return _comparison_failure(
                readiness.status,
                explicit_article=explicit_article,
            )
        max_excerpts = min(
            _COMPARISON_MAX_EXCERPTS,
            self._config.top_k * _COMPARISON_PER_ARTICLE_CAP,
        )
        try:
            payload = self._transport.post_json(
                url=f"{self._config.base_url.rstrip('/')}/api/snippets",
                payload={
                    "query": query,
                    "query_source": "final_clean_ticket",
                    "retrieval_mode": "hybrid",
                    "top_k": self._config.top_k,
                    "keyword_k": 30,
                    "vector_k": 30,
                    "max_snippets": max_excerpts,
                    "max_tokens": _COMPARISON_MAX_TOKENS,
                    "per_article_cap": _COMPARISON_PER_ARTICLE_CAP,
                },
                timeout_seconds=self._config.timeout_seconds,
                max_response_bytes=self._config.max_response_bytes,
            )
            return _parse_comparison_evidence(
                payload,
                explicit_article=explicit_article,
                max_excerpts=max_excerpts,
            )
        except LocalPublicRagTransportError:
            return _comparison_failure(
                "rag_runtime_unavailable",
                explicit_article=explicit_article,
            )
        except ContractValidationError:
            return _comparison_failure(
                "rag_comparison_invalid_response",
                explicit_article=explicit_article,
            )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: object,
        file_pointer: object,
        code: int,
        message: str,
        headers: object,
        new_url: str,
    ) -> None:
        return None


class UrlLibLocalPublicRagTransport:
    """Bounded stdlib transport with redirect following disabled."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )

    def get_json(
        self,
        *,
        url: str,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object:
        return self._request_json(
            urllib.request.Request(url, headers={"Accept": "application/json"}),
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._request_json(
            request,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
        )

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object:
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type.casefold():
                    raise ContractValidationError("local public RAG response invalid")
                body = response.read(max_response_bytes + 1)
        except (urllib.error.URLError, OSError, TimeoutError):
            raise LocalPublicRagTransportError from None
        if len(body) > max_response_bytes:
            raise ContractValidationError("local public RAG response invalid")
        try:
            return json.loads(body)
        except (RecursionError, UnicodeDecodeError, ValueError):
            raise ContractValidationError("local public RAG response invalid") from None


def build_local_public_rag_query(symptoms: Sequence[str]) -> str:
    """Build one bounded symptom-oriented query from validated public-safe text."""

    if isinstance(symptoms, str) or not 1 <= len(symptoms) <= _MAX_SYMPTOMS:
        raise ContractValidationError("local public RAG symptoms are invalid")
    normalized: list[str] = []
    for symptom in symptoms:
        if not isinstance(symptom, str):
            raise ContractValidationError("local public RAG symptoms are invalid")
        ensure_safe_sanitized_payload(symptom)
        value = _WHITESPACE_RE.sub(" ", symptom).strip()
        if not value:
            raise ContractValidationError("local public RAG symptoms are invalid")
        normalized.append(value)
    query = " ".join(normalized)
    if len(query) > _MAX_QUERY_CHARS:
        raise ContractValidationError("local public RAG query is too large")
    return query


def _parse_readiness(payload: object) -> LocalPublicRagReadiness:
    result = _wrapped_result(payload)
    if result.get("schema_version") != LOCAL_PUBLIC_RAG_STATUS_SCHEMA_VERSION:
        raise ContractValidationError("local public RAG readiness response invalid")
    if result.get("ok") is not True:
        raise ContractValidationError("local public RAG readiness response invalid")
    article_count = _nonnegative_int(result.get("article_count"))
    chunk_count = _nonnegative_int(result.get("chunk_count"))
    vector_count = _nonnegative_int(result.get("vector_count"))
    if result.get("warmed") is not True:
        return LocalPublicRagReadiness(
            False, "rag_runtime_cold", article_count, chunk_count, vector_count
        )
    if (
        result.get("cache_current") is not True
        or result.get("cache_state") != "current"
    ):
        return LocalPublicRagReadiness(
            False, "rag_runtime_stale", article_count, chunk_count, vector_count
        )
    if not _hybrid_ready(result):
        return LocalPublicRagReadiness(
            False,
            "rag_runtime_hybrid_not_ready",
            article_count,
            chunk_count,
            vector_count,
        )
    return LocalPublicRagReadiness(
        True, "rag_runtime_ready", article_count, chunk_count, vector_count
    )


def _hybrid_ready(result: Mapping[str, Any]) -> bool:
    return (
        result.get("ready_for_keyword_rag") is True
        and result.get("ready_for_vector_rag") is True
    )


def _parse_search_result(payload: object, *, top_k: int) -> LocalPublicRagSearchResult:
    result = _wrapped_result(payload)
    if result.get("schema_version") != LOCAL_PUBLIC_RAG_SEARCH_SCHEMA_VERSION:
        raise ContractValidationError("local public RAG search response invalid")
    raw_candidates = result.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) > top_k:
        raise ContractValidationError("local public RAG search response invalid")
    candidates = tuple(_parse_candidate(item) for item in raw_candidates)
    projected = [candidate.to_json_dict() for candidate in candidates]
    result_hash = sha256(
        json.dumps(projected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return LocalPublicRagSearchResult(
        True,
        "rag_search_completed",
        f"local-rag-{result_hash}",
        candidates,
    )


def _comparison_failure(
    status: str,
    *,
    explicit_article: PublicArticleReference | None,
) -> ReuseComparisonEvidence:
    projected_status = _COMPARISON_FAILURE_STATUSES[status]
    evidence = ReuseComparisonEvidence(
        searched=False,
        status=projected_status,
        search_run_ref="",
        explicit_reference_status=(
            "not_checked" if explicit_article is not None else "not_provided"
        ),
        explicit_article=explicit_article,
        blockers=(projected_status,),
    )
    ensure_valid_reuse_comparison_evidence(evidence)
    return evidence


def _parse_comparison_evidence(
    payload: object,
    *,
    explicit_article: PublicArticleReference | None,
    max_excerpts: int,
) -> ReuseComparisonEvidence:
    result = _wrapped_result(payload)
    raw_excerpts = _comparison_raw_excerpts(result, max_excerpts=max_excerpts)
    parsed = tuple(_parse_comparison_excerpt(value) for value in raw_excerpts)
    _validate_comparison_totals(result, parsed)
    candidates, explicit_status = _comparison_candidates(
        parsed,
        explicit_article=explicit_article,
    )
    status, blockers = _comparison_status(
        candidates,
        explicit_article=explicit_article,
        explicit_status=explicit_status,
    )
    projected = [candidate.to_json_dict() for candidate in candidates]
    result_hash = sha256(
        json.dumps(projected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    evidence = ReuseComparisonEvidence(
        searched=True,
        status=status,
        search_run_ref=f"comparison-{result_hash}",
        explicit_reference_status=explicit_status,
        explicit_article=explicit_article,
        candidates=candidates,
        blockers=blockers,
    )
    ensure_valid_reuse_comparison_evidence(evidence)
    return evidence


def _comparison_raw_excerpts(
    result: Mapping[str, Any],
    *,
    max_excerpts: int,
) -> list[object]:
    actual_contract = (
        result.get("schema_version"),
        result.get("query_source"),
        result.get("retriever"),
        result.get("max_snippets"),
        result.get("max_tokens"),
        result.get("per_article_cap"),
    )
    expected_contract = (
        LOCAL_PUBLIC_RAG_SNIPPETS_SCHEMA_VERSION,
        "final_clean_ticket",
        "hybrid",
        max_excerpts,
        _COMPARISON_MAX_TOKENS,
        _COMPARISON_PER_ARTICLE_CAP,
    )
    if actual_contract != expected_contract:
        raise ContractValidationError("local public RAG comparison response invalid")
    raw_excerpts = result.get("snippets")
    if not isinstance(raw_excerpts, list) or len(raw_excerpts) > max_excerpts:
        raise ContractValidationError("local public RAG comparison response invalid")
    if result.get("selected_count") != len(raw_excerpts):
        raise ContractValidationError("local public RAG comparison response invalid")
    _nonnegative_int(result.get("candidate_count"))
    return raw_excerpts


def _validate_comparison_totals(
    result: Mapping[str, Any],
    parsed: tuple[_ParsedComparisonExcerpt, ...],
) -> None:
    total_chars = sum(len(item.excerpt.text) for item in parsed)
    if total_chars > _MAX_TOTAL_EXCERPT_CHARS:
        raise ContractValidationError("local public RAG comparison response invalid")
    total_token_count = _nonnegative_int(result.get("total_token_count"))
    projected_tokens = sum(item.excerpt.token_count for item in parsed)
    if total_token_count != projected_tokens:
        raise ContractValidationError("local public RAG comparison response invalid")
    if total_token_count > _COMPARISON_MAX_TOKENS:
        raise ContractValidationError("local public RAG comparison response invalid")


def _parse_comparison_excerpt(value: object) -> _ParsedComparisonExcerpt:
    if not isinstance(value, Mapping):
        raise ContractValidationError("local public RAG comparison excerpt invalid")
    public_url = _public_url(value.get("canonical_url"))
    source_doc_id = _source_doc_id(value.get("source_doc_id"))
    title = _bounded_public_metadata_string(value.get("title"), max_chars=300)
    section_path = _bounded_public_metadata_string(
        value.get("section_path"), max_chars=300
    )
    text = _public_excerpt_text(value.get("text"))
    token_count = _positive_int(value.get("token_count"))
    excerpt_hash = sha256(
        f"{source_doc_id}\n{section_path}\n{text}".encode("utf-8")
    ).hexdigest()[:20]
    return _ParsedComparisonExcerpt(
        candidate_rank=_positive_int(value.get("candidate_rank")),
        source_doc_id=source_doc_id,
        source_type=_PUBLIC_SOURCE_TYPES[urlparse(public_url).hostname or ""],
        title=title,
        public_url=public_url,
        section_path=section_path,
        article_status=_choice(value.get("article_status"), _ARTICLE_STATUSES),
        updated_at=_optional_public_metadata_string(
            value.get("updated_at"), max_chars=64
        ),
        excerpt=ReuseComparisonExcerpt(
            excerpt_ref=f"public-excerpt-{excerpt_hash}",
            section_path=section_path,
            citation=f"{title} — {section_path} — {public_url}",
            text=text,
            token_count=token_count,
        ),
    )


def _comparison_candidates(
    excerpts: tuple[_ParsedComparisonExcerpt, ...],
    *,
    explicit_article: PublicArticleReference | None,
) -> tuple[tuple[ReuseComparisonCandidate, ...], str]:
    groups = _comparison_article_groups(excerpts)
    explicit_group = _explicit_article_group(groups, explicit_article)
    ordered = ([explicit_group] if explicit_group is not None else []) + [
        values for values in groups if values is not explicit_group
    ]
    selected = ordered[:_COMPARISON_MAX_CANDIDATES]
    candidates = tuple(
        _comparison_candidate(
            values,
            rank=index,
            explicit=values is explicit_group,
        )
        for index, values in enumerate(selected, start=1)
    )
    explicit_status = _explicit_reference_status(explicit_article, explicit_group)
    return candidates, explicit_status


def _comparison_article_groups(
    excerpts: tuple[_ParsedComparisonExcerpt, ...],
) -> list[list[_ParsedComparisonExcerpt]]:
    grouped: dict[str, list[_ParsedComparisonExcerpt]] = {}
    for excerpt in excerpts:
        grouped.setdefault(excerpt.source_doc_id, []).append(excerpt)
    groups = sorted(grouped.values(), key=lambda values: values[0].candidate_rank)
    for values in groups:
        _validate_comparison_article_group(values)
    return groups


def _explicit_reference_status(
    explicit_article: PublicArticleReference | None,
    explicit_group: list[_ParsedComparisonExcerpt] | None,
) -> str:
    if explicit_article is None:
        return "not_provided"
    if explicit_group is not None:
        return "context_ready"
    return "context_missing"


def _validate_comparison_article_group(
    values: list[_ParsedComparisonExcerpt],
) -> None:
    if not values or len(values) > _COMPARISON_PER_ARTICLE_CAP:
        raise ContractValidationError("local public RAG comparison response invalid")
    first = values[0]
    expected = (
        first.candidate_rank,
        first.source_type,
        first.title,
        first.public_url,
        first.article_status,
        first.updated_at,
    )
    if any(
        (
            value.candidate_rank,
            value.source_type,
            value.title,
            value.public_url,
            value.article_status,
            value.updated_at,
        )
        != expected
        for value in values[1:]
    ):
        raise ContractValidationError("local public RAG comparison response invalid")


def _explicit_article_group(
    groups: list[list[_ParsedComparisonExcerpt]],
    explicit_article: PublicArticleReference | None,
) -> list[_ParsedComparisonExcerpt] | None:
    if explicit_article is None:
        return None
    for values in groups:
        first = values[0]
        if _matches_explicit_article(first, explicit_article):
            return values
    return None


def _matches_explicit_article(
    candidate: _ParsedComparisonExcerpt,
    explicit_article: PublicArticleReference,
) -> bool:
    url_matches = _public_article_key(candidate.public_url) == _public_article_key(
        explicit_article.public_url
    )
    if explicit_article.source_doc_id is None:
        return url_matches
    return url_matches and candidate.source_doc_id == explicit_article.source_doc_id


def _comparison_candidate(
    values: list[_ParsedComparisonExcerpt],
    *,
    rank: int,
    explicit: bool,
) -> ReuseComparisonCandidate:
    first = values[0]
    return ReuseComparisonCandidate(
        rank=rank,
        source_doc_id=first.source_doc_id,
        source_type=first.source_type,
        title=first.title,
        public_url=first.public_url,
        article_status=first.article_status,
        updated_at=first.updated_at,
        origin="explicit_resolution_reference" if explicit else "search_result",
        excerpts=tuple(value.excerpt for value in values),
    )


def _comparison_status(
    candidates: tuple[ReuseComparisonCandidate, ...],
    *,
    explicit_article: PublicArticleReference | None,
    explicit_status: str,
) -> tuple[str, tuple[str, ...]]:
    if explicit_article is not None and explicit_status == "context_missing":
        return "explicit_article_context_missing", ("explicit_article_context_missing",)
    if not candidates:
        return "comparison_no_evidence", ("comparison_no_evidence",)
    return "comparison_evidence_ready", ()


def _parse_candidate(value: object) -> LocalPublicRagCandidate:
    if not isinstance(value, Mapping):
        raise ContractValidationError("local public RAG candidate invalid")
    public_url = _public_url(value.get("canonical_url"))
    matched_retrievers = _matched_retrievers(value.get("matched_retrievers"))
    return LocalPublicRagCandidate(
        rank=_positive_int(value.get("rank")),
        source_doc_id=_source_doc_id(value.get("source_doc_id")),
        source_type=_PUBLIC_SOURCE_TYPES[urlparse(public_url).hostname or ""],
        title=_bounded_public_metadata_string(value.get("title"), max_chars=300),
        public_url=public_url,
        section_path=_optional_public_metadata_string(
            value.get("section_path"), max_chars=300
        ),
        article_status=_choice(value.get("article_status"), _ARTICLE_STATUSES),
        updated_at=_optional_public_metadata_string(
            value.get("updated_at"), max_chars=64
        ),
        score=_finite_number(value.get("final_score")),
        matched_retrievers=matched_retrievers,
    )


def _wrapped_result(payload: object) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping) or payload.get("ok") is not True:
        raise ContractValidationError("local public RAG response invalid")
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ContractValidationError("local public RAG response invalid")
    return result


def _validate_base_url(value: str) -> None:
    parsed, port = _parse_url(value, "local public RAG endpoint is invalid")
    if not _is_explicit_http_origin(parsed, port):
        raise ContractValidationError("local public RAG endpoint is invalid")
    if not _is_clean_root_url(parsed):
        raise ContractValidationError("local public RAG endpoint is invalid")
    if not _is_loopback_host(parsed.hostname or ""):
        raise ContractValidationError("local public RAG endpoint is invalid")


def _is_loopback_host(hostname: str) -> bool:
    if hostname.casefold() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _public_url(value: object) -> str:
    text = _bounded_public_url_string(value)
    parsed, port = _parse_url(text, "local public RAG candidate invalid")
    if not _is_approved_public_origin(parsed, port):
        raise ContractValidationError("local public RAG candidate invalid")
    if parsed.query or parsed.fragment:
        raise ContractValidationError("local public RAG candidate invalid")
    return text


def _validated_explicit_article(
    value: PublicArticleReference | None,
) -> PublicArticleReference | None:
    if value is None:
        return None
    public_url = _public_url(value.public_url)
    source_doc_id = (
        _source_doc_id(value.source_doc_id) if value.source_doc_id is not None else None
    )
    return PublicArticleReference(
        public_url=public_url,
        source_doc_id=source_doc_id,
    )


def _public_article_key(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/")
    if parsed.hostname == "support.plesk.com" and "/articles/" in path:
        article_part = path.split("/articles/", 1)[1].split("/", 1)[0]
        return f"support.plesk.com/articles/{article_part.split('-', 1)[0]}"
    if parsed.hostname == "kb.plesk.com":
        article_part = path.strip("/").split("/", 1)[0]
        return f"kb.plesk.com/{article_part}"
    return f"{parsed.hostname}{path}"


def _bounded_public_url_string(value: object) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("local public RAG candidate invalid")
    if (
        not value
        or len(value) > 1000
        or any(character.isspace() for character in value)
    ):
        raise ContractValidationError("local public RAG candidate invalid")
    return value


def _parse_url(value: str, error: str) -> tuple[ParseResult, int | None]:
    try:
        parsed = urlparse(value)
        return parsed, parsed.port
    except ValueError:
        raise ContractValidationError(error) from None


def _is_explicit_http_origin(parsed: ParseResult, port: int | None) -> bool:
    return (
        parsed.scheme == "http"
        and parsed.hostname is not None
        and port is not None
        and 1 <= port <= 65535
    )


def _is_clean_root_url(parsed: ParseResult) -> bool:
    return (
        parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def _is_approved_public_origin(parsed: ParseResult, port: int | None) -> bool:
    return (
        parsed.scheme == "https"
        and parsed.hostname in _PUBLIC_SOURCE_TYPES
        and parsed.username is None
        and parsed.password is None
        and port in {None, 443}
    )


def _bounded_public_metadata_string(value: object, *, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("local public RAG candidate invalid")
    normalized = _WHITESPACE_RE.sub(" ", value).strip()
    if not normalized or len(normalized) > max_chars:
        raise ContractValidationError("local public RAG candidate invalid")
    return normalized


def _optional_public_metadata_string(value: object, *, max_chars: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractValidationError("local public RAG candidate invalid")
    normalized = _WHITESPACE_RE.sub(" ", value).strip()
    if not normalized:
        return None
    return _bounded_public_metadata_string(normalized, max_chars=max_chars)


def _public_excerpt_text(value: object) -> str:
    if not isinstance(value, str):
        raise ContractValidationError("local public RAG comparison excerpt invalid")
    text = value.strip()
    if not text or len(text) > _MAX_EXCERPT_CHARS:
        raise ContractValidationError("local public RAG comparison excerpt invalid")
    if _has_forbidden_control_character(text):
        raise ContractValidationError("local public RAG comparison excerpt invalid")
    if _PRIVATE_EXCERPT_RE.search(text) or _SECRET_ASSIGNMENT_RE.search(text):
        raise ContractValidationError("local public RAG comparison excerpt invalid")
    return text


def _has_forbidden_control_character(text: str) -> bool:
    return any(ord(character) < 32 and character not in "\n\r\t" for character in text)


def _source_doc_id(value: object) -> str:
    if not isinstance(value, str) or not _SOURCE_DOC_ID_RE.fullmatch(value):
        raise ContractValidationError("local public RAG candidate invalid")
    return value


def _choice(value: object, choices: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ContractValidationError("local public RAG candidate invalid")
    return value


def _matched_retrievers(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ContractValidationError("local public RAG candidate invalid")
    normalized = tuple(value)
    if any(
        not isinstance(item, str) or item not in _MATCHED_RETRIEVERS
        for item in normalized
    ):
        raise ContractValidationError("local public RAG candidate invalid")
    return normalized


def _positive_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ContractValidationError("local public RAG candidate invalid")
    return value


def _nonnegative_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractValidationError("local public RAG readiness response invalid")
    return value


def _finite_number(value: object) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ContractValidationError("local public RAG candidate invalid")
    result = float(value)
    if not math.isfinite(result):
        raise ContractValidationError("local public RAG candidate invalid")
    return result


__all__ = [
    "LOCAL_PUBLIC_RAG_SEARCH_SCHEMA_VERSION",
    "LOCAL_PUBLIC_RAG_SNIPPETS_SCHEMA_VERSION",
    "LOCAL_PUBLIC_RAG_STATUS_SCHEMA_VERSION",
    "LocalPublicRagAdapter",
    "LocalPublicRagCandidate",
    "LocalPublicRagConfig",
    "LocalPublicRagReadiness",
    "LocalPublicRagSearchResult",
    "LocalPublicRagTransport",
    "LocalPublicRagTransportError",
    "UrlLibLocalPublicRagTransport",
    "build_local_public_rag_query",
]
