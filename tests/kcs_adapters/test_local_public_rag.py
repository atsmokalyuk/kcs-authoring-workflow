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


class FakeTransport:
    def __init__(self, *, readiness: object, search: object | None = None) -> None:
        self.readiness = readiness
        self.search_result = search
        self.get_calls: list[dict[str, object]] = []
        self.post_calls: list[dict[str, object]] = []
        self.get_error: Exception | None = None
        self.post_error: Exception | None = None

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
        if self.post_error is not None:
            raise self.post_error
        return self.search_result


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
