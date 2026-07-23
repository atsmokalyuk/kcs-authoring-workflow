from __future__ import annotations

import urllib.error
from collections.abc import Mapping

import pytest

from kcs_adapters.local_public_rag import (
    LocalPublicRagAdapter,
    LocalPublicRagConfig,
    LocalPublicRagTransportError,
    UrlLibLocalPublicRagTransport,
    build_local_public_rag_query,
)
from kcs_core.errors import ContractValidationError
from kcs_core.reuse_comparison import (
    PublicArticleReference,
    ReuseComparisonEvidenceRequest,
)


class FakeTransport:
    def __init__(self, *, readiness: object, search: object | None = None) -> None:
        self.readiness = readiness
        self.search_result = search
        self.get_calls: list[dict[str, object]] = []
        self.post_calls: list[dict[str, object]] = []
        self.get_error: Exception | None = None
        self.post_error: Exception | None = None
        self.post_results_by_url: dict[str, object] = {}
        self.post_errors_by_url: dict[str, Exception] = {}

    def get_json(
        self,
        *,
        url: str,
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object:
        self.get_calls.append(
            {
                "url": url,
                "timeout_seconds": timeout_seconds,
                "max_response_bytes": max_response_bytes,
            }
        )
        if self.get_error is not None:
            raise self.get_error
        return self.readiness

    def post_json(
        self,
        *,
        url: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
        max_response_bytes: int,
    ) -> object:
        self.post_calls.append(
            {
                "url": url,
                "payload": dict(payload),
                "timeout_seconds": timeout_seconds,
                "max_response_bytes": max_response_bytes,
            }
        )
        if url in self.post_errors_by_url:
            raise self.post_errors_by_url[url]
        if self.post_error is not None:
            raise self.post_error
        return self.post_results_by_url.get(url, self.search_result)


class FakeHttpResponse:
    status = 200

    def __init__(
        self,
        body: bytes,
        *,
        content_type: str = "application/json",
    ) -> None:
        self.body = body
        self.headers = {"content-type": content_type}

    def read(self, size: int) -> bytes:
        return self.body[:size]

    def __enter__(self) -> FakeHttpResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class FakeHttpOpener:
    def __init__(self, response: FakeHttpResponse | Exception) -> None:
        self.response = response

    def open(self, request: object, *, timeout: int) -> FakeHttpResponse:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _readiness_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": "knowledge-runtime-status-v1",
        "ok": True,
        "warmed": True,
        "cache_current": True,
        "cache_state": "current",
        "ready_for_keyword_rag": True,
        "ready_for_vector_rag": True,
        "article_count": 6148,
        "chunk_count": 35674,
        "vector_count": 35674,
    }
    result.update(overrides)
    return {"ok": True, "result": result}


def _search_result(*, candidates: list[object] | None = None) -> dict[str, object]:
    if candidates is None:
        candidates = [
            {
                "rank": 1,
                "chunk_id": "chunk-not-projected",
                "source_doc_id": "plesk-kb://123456",
                "canonical_url": (
                    "https://support.plesk.com/hc/en-us/articles/123456-Example"
                ),
                "title": "Unable to open Plesk",
                "section_path": "Symptoms",
                "article_status": "active",
                "updated_at": "2026-06-10",
                "final_score": 0.75,
                "matched_retrievers": ["keyword", "vector"],
                "text": "SECRET_SNIPPET_BODY",
                "vector_score": 0.9,
            }
        ]
    return {
        "ok": True,
        "result": {
            "schema_version": "knowledge-hybrid-search-v1",
            "result_count": len(candidates),
            "candidates": candidates,
            "raw_query": "SECRET_QUERY_TAIL",
        },
    }


def _snippet(
    *,
    rank: int = 1,
    candidate_rank: int = 1,
    source_doc_id: str = "plesk-support://123456",
    canonical_url: str = ("https://support.plesk.com/hc/en-us/articles/123456-Example"),
    title: str = "Unable to open Plesk",
    section_path: str = "Resolution",
    text: str = "Restart the affected service and verify access.",
    token_count: int = 7,
) -> dict[str, object]:
    return {
        "rank": rank,
        "candidate_rank": candidate_rank,
        "chunk_id": f"chunk-{rank}-not-projected",
        "source_doc_id": source_doc_id,
        "canonical_url": canonical_url,
        "title": title,
        "section_path": section_path,
        "article_status": "active",
        "updated_at": "2026-06-10",
        "score": 0.75,
        "bm25_score": 2.0,
        "vector_score": 0.9,
        "final_score": 0.75,
        "token_count": token_count,
        "truncated": False,
        "citation": "UNTRUSTED_RUNTIME_CITATION",
        "text": text,
    }


def _snippets_result(
    *,
    snippets: list[object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    selected = [_snippet()] if snippets is None else snippets
    result: dict[str, object] = {
        "schema_version": "knowledge-cited-snippets-v1",
        "query_source": "final_clean_ticket",
        "retriever": "hybrid",
        "keyword_index_ref": "SECRET_LOCAL_INDEX_PATH",
        "top_k": 5,
        "bm25_k1": 1.5,
        "bm25_b": 0.75,
        "keyword_k": 30,
        "vector_k": 30,
        "rrf_k": 60,
        "max_snippets": 6,
        "max_tokens": 1200,
        "per_article_cap": 2,
        "candidate_count": len(
            {
                item.get("source_doc_id")
                for item in selected
                if isinstance(item, Mapping)
            }
        ),
        "selected_count": len(selected),
        "total_token_count": sum(
            int(item.get("token_count", 0))
            for item in selected
            if isinstance(item, Mapping)
        ),
        "snippets": selected,
        "markdown": "SECRET_RENDERED_MARKDOWN",
        "retrieval_run_id": "SECRET_RUNTIME_RUN_ID",
        "raw_query": "SECRET_QUERY_TAIL",
    }
    result.update(overrides)
    return {"ok": True, "result": result}


def _exact_snippets_result(
    *,
    source_doc_id: str = "plesk-support://222222",
    canonical_url: str = (
        "https://support.plesk.com/hc/en-us/articles/222222-Explicit"
    ),
    snippets: list[object] | None = None,
    **overrides: object,
) -> dict[str, object]:
    selected = (
        [
            {
                **_snippet(
                    rank=1,
                    candidate_rank=1,
                    source_doc_id=source_doc_id,
                    canonical_url=canonical_url,
                    title="Ticket resolution article",
                    section_path="Symptoms",
                    text="The affected login returns HTTP 500.",
                    token_count=6,
                ),
            },
            {
                **_snippet(
                    rank=2,
                    candidate_rank=1,
                    source_doc_id=source_doc_id,
                    canonical_url=canonical_url,
                    title="Ticket resolution article",
                    section_path="Cause",
                    text="The service configuration is stale.",
                    token_count=5,
                ),
            },
            {
                **_snippet(
                    rank=3,
                    candidate_rank=1,
                    source_doc_id=source_doc_id,
                    canonical_url=canonical_url,
                    title="Ticket resolution article",
                    section_path="Resolution",
                    text="Refresh the configuration and restart the service.",
                    token_count=7,
                ),
            },
        ]
        if snippets is None
        else snippets
    )
    for rank, item in enumerate(selected, start=1):
        if isinstance(item, dict):
            item.pop("candidate_rank", None)
            item.pop("chunk_id", None)
            item["rank"] = rank
    result: dict[str, object] = {
        "schema_version": "knowledge-exact-article-snippets-v1",
        "source_doc_id": source_doc_id,
        "canonical_url": canonical_url,
        "title": "Ticket resolution article",
        "article_status": "active",
        "updated_at": "2026-06-10",
        "updated_ts": 1781059200,
        "max_snippets": 6,
        "max_tokens": 600,
        "available_chunk_count": len(selected),
        "selected_count": len(selected),
        "total_token_count": sum(
            int(item.get("token_count", 0))
            for item in selected
            if isinstance(item, Mapping)
        ),
        "snippets": selected,
        "markdown": "SECRET_EXACT_MARKDOWN",
    }
    result.update(overrides)
    return {"ok": True, "result": result}


@pytest.mark.parametrize(
    "base_url",
    [
        "https://127.0.0.1:8768",
        "http://0.0.0.0:8768",
        "http://192.0.2.10:8768",
        "http://user:secret@127.0.0.1:8768",
        "http://127.0.0.1:8768/private",
        "http://127.0.0.1:8768?token=secret",
        "http://127.0.0.1",
    ],
)
def test_local_public_rag_config_rejects_unsafe_endpoint(base_url: str) -> None:
    with pytest.raises(ContractValidationError, match="endpoint is invalid"):
        LocalPublicRagConfig(base_url=base_url)


def test_local_public_rag_config_accepts_explicit_loopback_hosts() -> None:
    assert LocalPublicRagConfig().base_url == "http://127.0.0.1:8768"
    assert LocalPublicRagConfig(base_url="http://localhost:8768").top_k == 5
    assert LocalPublicRagConfig(base_url="http://[::1]:8768").timeout_seconds == 30


def test_local_public_rag_transport_disables_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handlers: list[object] = []
    redirect = urllib.error.HTTPError(
        "http://127.0.0.1:8768/api/status",
        302,
        "redirect",
        {},
        None,
    )

    def build_opener(*values: object) -> FakeHttpOpener:
        handlers.extend(values)
        return FakeHttpOpener(redirect)

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)
    transport = UrlLibLocalPublicRagTransport()

    with pytest.raises(LocalPublicRagTransportError):
        transport.get_json(
            url="http://127.0.0.1:8768/api/status",
            timeout_seconds=5,
            max_response_bytes=1024,
        )

    assert [type(handler).__name__ for handler in handlers] == [
        "ProxyHandler",
        "_NoRedirectHandler",
    ]
    assert handlers[0].proxies == {}


def test_local_public_rag_transport_rejects_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeHttpResponse(b"x" * 1025)
    monkeypatch.setattr(
        urllib.request,
        "build_opener",
        lambda *_handlers: FakeHttpOpener(response),
    )
    transport = UrlLibLocalPublicRagTransport()

    with pytest.raises(ContractValidationError, match="response invalid"):
        transport.get_json(
            url="http://127.0.0.1:8768/api/status",
            timeout_seconds=5,
            max_response_bytes=1024,
        )


@pytest.mark.parametrize(
    "response",
    [
        FakeHttpResponse(b"{}", content_type="text/plain"),
        FakeHttpResponse(b"not-json"),
        FakeHttpResponse(b"[" * 1100 + b"]" * 1100),
        FakeHttpResponse(b'{"number":' + b"1" * 5000 + b"}"),
    ],
)
def test_local_public_rag_transport_rejects_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeHttpResponse,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "build_opener",
        lambda *_handlers: FakeHttpOpener(response),
    )
    transport = UrlLibLocalPublicRagTransport()

    with pytest.raises(ContractValidationError, match="response invalid"):
        transport.get_json(
            url="http://127.0.0.1:8768/api/status",
            timeout_seconds=5,
            max_response_bytes=1024,
        )


def test_local_public_rag_query_is_symptom_oriented_and_bounded() -> None:
    query = build_local_public_rag_query(
        ["Plesk shows   500 Internal Server Error.", " Login fails.\n"]
    )

    assert query == "Plesk shows 500 Internal Server Error. Login fails."


@pytest.mark.parametrize(
    "symptoms",
    [
        [],
        [""],
        ["Customer server is 192.0.2.10."],
        ["x" * 513],
        ["one", "two", "three", "four", "five", "six"],
    ],
)
def test_local_public_rag_query_rejects_unsafe_or_unbounded_input(
    symptoms: list[str],
) -> None:
    with pytest.raises(ContractValidationError):
        build_local_public_rag_query(symptoms)


def test_local_public_rag_readiness_projects_only_safe_counts() -> None:
    transport = FakeTransport(readiness=_readiness_result())

    readiness = LocalPublicRagAdapter(transport=transport).check_readiness()

    assert readiness.to_json_dict() == {
        "ready": True,
        "status": "rag_runtime_ready",
        "article_count": 6148,
        "chunk_count": 35674,
        "vector_count": 35674,
    }
    assert transport.get_calls[0]["url"] == "http://127.0.0.1:8768/api/status"


@pytest.mark.parametrize(
    ("overrides", "expected_status"),
    [
        ({"warmed": False}, "rag_runtime_cold"),
        ({"cache_current": False, "cache_state": "stale"}, "rag_runtime_stale"),
        ({"ready_for_keyword_rag": False}, "rag_runtime_hybrid_not_ready"),
        ({"ready_for_vector_rag": False}, "rag_runtime_hybrid_not_ready"),
    ],
)
def test_local_public_rag_readiness_fails_closed(
    overrides: dict[str, object], expected_status: str
) -> None:
    transport = FakeTransport(readiness=_readiness_result(**overrides))

    readiness = LocalPublicRagAdapter(transport=transport).check_readiness()

    assert readiness.ready is False
    assert readiness.status == expected_status


def test_local_public_rag_readiness_normalizes_transport_failure() -> None:
    transport = FakeTransport(readiness={})
    transport.get_error = LocalPublicRagTransportError("SECRET upstream detail")

    readiness = LocalPublicRagAdapter(transport=transport).check_readiness()

    assert readiness.to_json_dict()["status"] == "rag_runtime_unavailable"
    assert "SECRET" not in str(readiness.to_json_dict())


def test_local_public_rag_search_returns_metadata_only_candidates() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_search_result(),
    )
    adapter = LocalPublicRagAdapter(transport=transport)

    result = adapter.search(["Plesk shows 500 Internal Server Error."])

    assert result.searched is True
    assert result.status == "rag_search_completed"
    assert result.search_run_ref.startswith("local-rag-")
    assert transport.post_calls[0]["payload"] == {
        "query": "Plesk shows 500 Internal Server Error.",
        "top_k": 5,
    }
    payload = result.to_json_dict()
    assert payload["candidates"] == [
        {
            "rank": 1,
            "source_doc_id": "plesk-kb://123456",
            "source_type": "support",
            "title": "Unable to open Plesk",
            "public_url": (
                "https://support.plesk.com/hc/en-us/articles/123456-Example"
            ),
            "section_path": "Symptoms",
            "article_status": "active",
            "updated_at": "2026-06-10",
            "score": 0.75,
            "matched_retrievers": ["keyword", "vector"],
        }
    ]
    assert "SECRET_SNIPPET_BODY" not in str(payload)
    assert "SECRET_QUERY_TAIL" not in str(payload)
    assert "chunk_id" not in str(payload)


@pytest.mark.parametrize(
    ("public_url", "source_type"),
    [
        ("https://kb.plesk.com/123456", "kb"),
        ("https://support.plesk.com/hc/en-us/articles/123456", "support"),
        ("https://docs.plesk.com/en-US/obsidian/administrator-guide/", "docs"),
    ],
)
def test_local_public_rag_search_accepts_approved_public_sources(
    public_url: str,
    source_type: str,
) -> None:
    candidate = {
        "rank": 1,
        "source_doc_id": "plesk-public://123456",
        "canonical_url": public_url,
        "title": "How to configure Node.js in Plesk",
        "section_path": "Resolution",
        "article_status": "active",
        "updated_at": None,
        "final_score": 0.5,
        "matched_retrievers": ["vector"],
    }
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_search_result(candidates=[candidate]),
    )

    result = LocalPublicRagAdapter(transport=transport).search(["Plesk login fails."])

    assert result.searched is True
    assert result.candidates[0].source_type == source_type
    assert result.candidates[0].title == "How to configure Node.js in Plesk"


def test_local_public_rag_search_does_not_call_search_when_not_ready() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(ready_for_keyword_rag=False),
        search=_search_result(),
    )

    result = LocalPublicRagAdapter(transport=transport).search(["Plesk login fails."])

    assert result.to_json_dict() == {
        "searched": False,
        "status": "rag_runtime_hybrid_not_ready",
        "search_run_ref": "",
        "candidates": [],
    }
    assert transport.post_calls == []


@pytest.mark.parametrize(
    "search_payload",
    [
        {"ok": True, "result": {"schema_version": "wrong", "candidates": []}},
        _search_result(
            candidates=[
                {
                    "rank": 1,
                    "source_doc_id": "plesk-kb://123456",
                    "canonical_url": "https://customer.example/private",
                    "title": "Unsafe candidate",
                    "section_path": "Symptoms",
                    "article_status": "active",
                    "updated_at": None,
                    "final_score": 0.5,
                    "matched_retrievers": ["vector"],
                }
            ]
        ),
        _search_result(candidates=[{}]),
        _search_result(candidates=[{}, {}, {}, {}, {}, {}]),
    ],
)
def test_local_public_rag_search_rejects_invalid_response(
    search_payload: object,
) -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=search_payload,
    )

    result = LocalPublicRagAdapter(transport=transport).search(["Plesk login fails."])

    assert result.to_json_dict() == {
        "searched": False,
        "status": "rag_search_invalid_response",
        "search_run_ref": "",
        "candidates": [],
    }


def test_local_public_rag_search_normalizes_transport_failure() -> None:
    transport = FakeTransport(readiness=_readiness_result(), search=None)
    transport.post_error = LocalPublicRagTransportError("SECRET upstream detail")

    result = LocalPublicRagAdapter(transport=transport).search(["Plesk login fails."])

    assert result.status == "rag_runtime_unavailable"
    assert "SECRET" not in str(result.to_json_dict())


def test_comparison_evidence_posts_bounded_request_and_projects_public_data() -> None:
    snippets = [
        _snippet(),
        _snippet(
            rank=2,
            candidate_rank=2,
            source_doc_id="plesk-kb://654321",
            canonical_url="https://kb.plesk.com/654321",
            title="Repair Plesk access",
            section_path="Symptoms",
            text="Plesk returns an internal server error after login.",
            token_count=8,
        ),
    ]
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(snippets=snippets),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        ReuseComparisonEvidenceRequest(("Plesk login returns HTTP 500.",))
    )

    assert result.searched is True
    assert result.status == "comparison_evidence_ready"
    assert result.explicit_reference_status == "not_provided"
    assert len(result.candidates) == 2
    assert transport.post_calls == [
        {
            "url": "http://127.0.0.1:8768/api/snippets",
            "payload": {
                "query": "Plesk login returns HTTP 500.",
                "query_source": "final_clean_ticket",
                "retrieval_mode": "hybrid",
                "top_k": 5,
                "keyword_k": 30,
                "vector_k": 30,
                "max_snippets": 6,
                "max_tokens": 1200,
                "per_article_cap": 2,
            },
            "timeout_seconds": 30,
            "max_response_bytes": 128 * 1024,
        }
    ]
    projected = str(result.to_json_dict())
    assert "Restart the affected service" in projected
    assert "SECRET_LOCAL_INDEX_PATH" not in projected
    assert "SECRET_RENDERED_MARKDOWN" not in projected
    assert "SECRET_RUNTIME_RUN_ID" not in projected
    assert "SECRET_QUERY_TAIL" not in projected
    assert "UNTRUSTED_RUNTIME_CITATION" not in projected
    assert "chunk-not-projected" not in projected


def test_explicit_resolution_article_is_prioritized_over_rag_rank() -> None:
    snippets = [
        _snippet(
            source_doc_id="plesk-support://111111",
            canonical_url="https://support.plesk.com/hc/en-us/articles/111111-First",
            title="First RAG result",
        ),
        _snippet(
            rank=2,
            candidate_rank=2,
            source_doc_id="plesk-support://222222",
            canonical_url="https://support.plesk.com/hc/en-us/articles/222222-Explicit",
            title="Ticket resolution article",
        ),
    ]
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(
            snippets=snippets,
            max_snippets=4,
            max_tokens=600,
            per_article_cap=1,
        ),
    )
    transport.post_results_by_url[
        "http://127.0.0.1:8768/api/article-snippets"
    ] = _exact_snippets_result()
    request = ReuseComparisonEvidenceRequest(
        ("Plesk login returns HTTP 500.",),
        PublicArticleReference(
            "https://support.plesk.com/hc/en-us/articles/222222-Older-Slug"
        ),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        request
    )

    assert result.explicit_reference_status == "context_ready"
    assert [candidate.source_doc_id for candidate in result.candidates] == [
        "plesk-support://222222",
        "plesk-support://111111",
    ]
    assert result.candidates[0].rank == 1
    assert result.candidates[0].origin == "explicit_resolution_reference"
    assert result.candidates[1].origin == "search_result"
    assert len(result.candidates[0].excerpts) == 2
    assert "HTTP 500" in result.candidates[0].excerpts[0].text
    assert "stale" in result.candidates[0].excerpts[0].text
    assert "restart the service" in result.candidates[0].excerpts[1].text
    assert transport.post_calls[0] == {
        "url": "http://127.0.0.1:8768/api/article-snippets",
        "payload": {
            "canonical_url": (
                "https://support.plesk.com/hc/en-us/articles/222222-Older-Slug"
            ),
            "max_snippets": 6,
            "max_tokens": 600,
        },
        "timeout_seconds": 30,
        "max_response_bytes": 128 * 1024,
    }
    assert transport.post_calls[1]["url"].endswith("/api/snippets")
    assert transport.post_calls[1]["payload"]["max_snippets"] == 4
    assert transport.post_calls[1]["payload"]["max_tokens"] == 600
    assert transport.post_calls[1]["payload"]["per_article_cap"] == 1


def test_missing_explicit_article_context_blocks_silent_rag_substitution() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(
            max_snippets=4,
            max_tokens=600,
            per_article_cap=1,
        ),
    )
    transport.post_errors_by_url[
        "http://127.0.0.1:8768/api/article-snippets"
    ] = LocalPublicRagTransportError()
    request = ReuseComparisonEvidenceRequest(
        ("Plesk login returns HTTP 500.",),
        PublicArticleReference(
            "https://support.plesk.com/hc/en-us/articles/999999-Referenced"
        ),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        request
    )

    assert result.searched is True
    assert result.status == "explicit_article_context_missing"
    assert result.explicit_reference_status == "context_missing"
    assert result.blockers == ("explicit_article_context_missing",)
    assert result.candidates[0].origin == "search_result"


def test_comparison_evidence_does_not_post_when_runtime_is_not_ready() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(cache_current=False, cache_state="stale"),
        search=_snippets_result(),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        ReuseComparisonEvidenceRequest(("Plesk login fails.",))
    )

    assert result.to_json_dict() == {
        "schema_version": "reuse_comparison_evidence_v1",
        "searched": False,
        "status": "comparison_provider_not_ready",
        "search_run_ref": "",
        "explicit_reference_status": "not_provided",
        "explicit_article": None,
        "candidates": [],
        "blockers": ["comparison_provider_not_ready"],
    }
    assert transport.post_calls == []


@pytest.mark.parametrize(
    "snippets_payload",
    [
        _snippets_result(schema_version="wrong"),
        _snippets_result(query_source="manual_public"),
        _snippets_result(retriever="keyword"),
        _snippets_result(max_snippets=5),
        _snippets_result(max_tokens=1199),
        _snippets_result(per_article_cap=1),
        _snippets_result(selected_count=2),
        _snippets_result(total_token_count=8),
        _snippets_result(snippets=[_snippet(canonical_url="https://example.com/x")]),
        _snippets_result(snippets=[_snippet(text="Read /Users/example/private.txt")]),
        _snippets_result(snippets=[_snippet(text="api_key=SECRET_VALUE")]),
        _snippets_result(
            snippets=[_snippet(text="Authorization: Bearer SECRET", token_count=3)]
        ),
        _snippets_result(
            snippets=[_snippet(text=" ".join(["x"] * 2000), token_count=1)]
        ),
        _snippets_result(snippets=[_snippet(text="x" * 6001)]),
        _snippets_result(snippets=[_snippet(token_count=1201)]),
        _snippets_result(
            snippets=[
                _snippet(),
                _snippet(rank=2, title="Conflicting title"),
            ]
        ),
        _snippets_result(
            snippets=[
                _snippet(),
                _snippet(rank=2),
                _snippet(rank=3),
            ]
        ),
        _snippets_result(
            snippets=[
                _snippet(rank=index, candidate_rank=index) for index in range(1, 8)
            ]
        ),
    ],
)
def test_comparison_evidence_rejects_invalid_or_unbounded_response(
    snippets_payload: object,
) -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=snippets_payload,
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        ReuseComparisonEvidenceRequest(("Plesk login fails.",))
    )

    assert result.status == "comparison_provider_invalid_response"
    assert result.searched is False
    assert result.candidates == ()


def test_comparison_evidence_reports_no_public_evidence() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(snippets=[]),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        ReuseComparisonEvidenceRequest(("Plesk login fails.",))
    )

    assert result.searched is True
    assert result.status == "comparison_no_evidence"
    assert result.blockers == ("comparison_no_evidence",)


def test_comparison_evidence_normalizes_transport_failure() -> None:
    transport = FakeTransport(readiness=_readiness_result(), search=None)
    transport.post_error = LocalPublicRagTransportError("SECRET upstream detail")

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        ReuseComparisonEvidenceRequest(("Plesk login fails.",))
    )

    assert result.status == "comparison_provider_unavailable"
    assert result.searched is False
    assert "SECRET" not in str(result.to_json_dict())


def test_comparison_evidence_rejects_unsafe_explicit_article_before_io() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(),
    )
    with pytest.raises(ContractValidationError):
        request = ReuseComparisonEvidenceRequest(
            ("Plesk login fails.",),
            PublicArticleReference("https://customer.example/private"),
        )
        LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(request)

    assert transport.get_calls == []
    assert transport.post_calls == []


def test_conflicting_explicit_article_identifiers_do_not_prioritize_wrong_hit() -> None:
    snippets = [
        _snippet(
            source_doc_id="plesk-support://111111",
            canonical_url="https://support.plesk.com/hc/en-us/articles/111111-First",
        ),
        _snippet(
            rank=2,
            candidate_rank=2,
            source_doc_id="plesk-support://222222",
            canonical_url="https://support.plesk.com/hc/en-us/articles/222222-Second",
        ),
    ]
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(
            snippets=snippets,
            max_snippets=4,
            max_tokens=600,
            per_article_cap=1,
        ),
    )
    transport.post_errors_by_url[
        "http://127.0.0.1:8768/api/article-snippets"
    ] = LocalPublicRagTransportError()
    request = ReuseComparisonEvidenceRequest(
        ("Plesk login fails.",),
        PublicArticleReference(
            "https://support.plesk.com/hc/en-us/articles/222222-Second",
            source_doc_id="plesk-support://111111",
        ),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        request
    )

    assert result.status == "explicit_article_context_missing"
    assert result.explicit_reference_status == "context_missing"
    assert all(candidate.origin == "search_result" for candidate in result.candidates)


def test_exact_article_evidence_survives_optional_semantic_transport_failure() -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(),
    )
    transport.post_results_by_url[
        "http://127.0.0.1:8768/api/article-snippets"
    ] = _exact_snippets_result()
    transport.post_errors_by_url[
        "http://127.0.0.1:8768/api/snippets"
    ] = LocalPublicRagTransportError()
    request = ReuseComparisonEvidenceRequest(
        ("Plesk login fails.",),
        PublicArticleReference(
            "https://support.plesk.com/hc/en-us/articles/222222-Explicit"
        ),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        request
    )

    assert result.status == "comparison_evidence_ready"
    assert result.explicit_reference_status == "context_ready"
    assert len(result.candidates) == 1
    assert result.candidates[0].origin == "explicit_resolution_reference"


@pytest.mark.parametrize(
    "exact_payload",
    [
        _exact_snippets_result(schema_version="wrong"),
        _exact_snippets_result(selected_count=99),
        _exact_snippets_result(available_chunk_count=0),
        _exact_snippets_result(total_token_count=999),
        _exact_snippets_result(
            canonical_url="https://example.com/articles/222222-Explicit"
        ),
        _exact_snippets_result(
            snippets=[
                {
                    **_snippet(
                        source_doc_id="plesk-support://222222",
                        canonical_url=(
                            "https://support.plesk.com/hc/en-us/articles/"
                            "222222-Explicit"
                        ),
                        title="Ticket resolution article",
                    ),
                    "article_status": "stale_suspect",
                }
            ],
            article_status="stale_suspect",
        ),
        _exact_snippets_result(
            snippets=[
                _snippet(
                    source_doc_id="plesk-support://222222",
                    canonical_url=(
                        "https://support.plesk.com/hc/en-us/articles/"
                        "222222-Explicit"
                    ),
                    title="Ticket resolution article",
                    text="api_key=SECRET",
                    token_count=1,
                )
            ]
        ),
    ],
)
def test_invalid_exact_article_response_blocks_before_semantic_substitution(
    exact_payload: object,
) -> None:
    transport = FakeTransport(
        readiness=_readiness_result(),
        search=_snippets_result(),
    )
    transport.post_results_by_url[
        "http://127.0.0.1:8768/api/article-snippets"
    ] = exact_payload
    request = ReuseComparisonEvidenceRequest(
        ("Plesk login fails.",),
        PublicArticleReference(
            "https://support.plesk.com/hc/en-us/articles/222222-Explicit"
        ),
    )

    result = LocalPublicRagAdapter(transport=transport).collect_comparison_evidence(
        request
    )

    assert result.status == "comparison_provider_invalid_response"
    assert result.searched is False
    assert len(transport.post_calls) == 1
