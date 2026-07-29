from __future__ import annotations

import pytest

from kcs_core.errors import ContractValidationError
from kcs_core.reuse_comparison import (
    REUSE_COMPARISON_EVIDENCE_SCHEMA_VERSION,
    PublicArticleReference,
    ReuseComparisonCandidate,
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceRequest,
    ReuseComparisonExcerpt,
    is_reusable_kcs_article_candidate,
    request_from_symptoms,
    reusable_kcs_article_key,
    validate_reuse_comparison_evidence,
)


def _excerpt(article_id: str = "123456") -> ReuseComparisonExcerpt:
    public_url = f"https://support.plesk.com/hc/en-us/articles/{article_id}-Example"
    return ReuseComparisonExcerpt(
        excerpt_ref=f"public-excerpt-{article_id}",
        section_path="Resolution",
        citation=f"Example — Resolution — {public_url}",
        text="Restart the affected service.",
        token_count=4,
    )


def _candidate(
    rank: int = 1,
    article_id: str = "123456",
    *,
    origin: str = "search_result",
) -> ReuseComparisonCandidate:
    return ReuseComparisonCandidate(
        rank=rank,
        source_doc_id=f"plesk-support://{article_id}",
        source_type="support",
        title="Example",
        public_url=(
            f"https://support.plesk.com/hc/en-us/articles/{article_id}-Example"
        ),
        article_status="active",
        updated_at="2026-06-10",
        origin=origin,
        excerpts=(_excerpt(article_id),),
    )


def _kb_candidate(rank: int, article_id: str) -> ReuseComparisonCandidate:
    public_url = f"https://kb.plesk.com/en/{article_id}"
    excerpt = ReuseComparisonExcerpt(
        excerpt_ref=f"public-excerpt-kb-{article_id}",
        section_path="Resolution",
        citation=f"Legacy KB {article_id} — Resolution — {public_url}",
        text="Restart the affected service.",
        token_count=4,
    )
    return ReuseComparisonCandidate(
        rank=rank,
        source_doc_id=f"plesk-kb://{article_id}",
        source_type="kb",
        title=f"Legacy KB {article_id}",
        public_url=public_url,
        article_status="active",
        updated_at=None,
        origin="search_result",
        excerpts=(excerpt,),
    )


def test_reuse_comparison_evidence_serializes_provider_neutral_contract() -> None:
    article = PublicArticleReference(
        public_url="https://support.plesk.com/hc/en-us/articles/123456-Example",
        source_doc_id="plesk-support://123456",
    )
    candidate = _candidate(origin="explicit_resolution_reference")

    payload = ReuseComparisonEvidence(
        searched=True,
        status="comparison_evidence_ready",
        search_run_ref="comparison-run-001",
        explicit_reference_status="context_ready",
        explicit_article=article,
        candidates=(candidate,),
    ).to_json_dict()

    assert payload["schema_version"] == REUSE_COMPARISON_EVIDENCE_SCHEMA_VERSION
    assert payload["explicit_article"] == article.to_json_dict()
    assert payload["candidates"] == [candidate.to_json_dict()]
    assert payload["blockers"] == []
    assert validate_reuse_comparison_evidence(
        ReuseComparisonEvidence(
            searched=True,
            status="comparison_evidence_ready",
            search_run_ref="comparison-run-001",
            explicit_reference_status="not_provided",
            candidates=(_candidate(),),
        )
    ).ok


def test_reuse_comparison_request_is_immutable_and_provider_neutral() -> None:
    symptoms = ["Plesk login fails."]

    request = request_from_symptoms(symptoms)
    symptoms.append("Later mutation")

    assert request == ReuseComparisonEvidenceRequest(("Plesk login fails.",))


def test_reuse_comparison_request_rejects_string_sequence() -> None:
    with pytest.raises(ContractValidationError):
        request_from_symptoms("Plesk")


def test_localized_legacy_kb_article_is_reusable() -> None:
    public_url = "https://kb.plesk.com/en/12345"

    assert PublicArticleReference(public_url=public_url).public_url == public_url
    assert _kb_candidate(1, "12345").source_type == "kb"
    assert reusable_kcs_article_key(public_url) == "kb.plesk.com/12345"


def test_distinct_localized_legacy_kb_articles_do_not_share_identity() -> None:
    candidates = (_kb_candidate(1, "12345"), _kb_candidate(2, "67890"))

    evidence = ReuseComparisonEvidence(
        searched=True,
        status="comparison_evidence_ready",
        search_run_ref="comparison-run-kb",
        explicit_reference_status="not_provided",
        candidates=candidates,
    )

    assert [candidate.source_doc_id for candidate in evidence.candidates] == [
        "plesk-kb://12345",
        "plesk-kb://67890",
    ]
    assert reusable_kcs_article_key(
        "https://kb.plesk.com/12345"
    ) == reusable_kcs_article_key("https://kb.plesk.com/en/12345")


@pytest.mark.parametrize(
    "public_url",
    [
        "https://docs.plesk.com/release-notes/obsidian/change-log",
        "https://support.plesk.com/hc/en-us/categories/123456",
        "https://kb.plesk.com/",
    ],
)
def test_explicit_reference_rejects_non_reusable_public_pages(
    public_url: str,
) -> None:
    with pytest.raises(ContractValidationError):
        PublicArticleReference(public_url=public_url)


def test_reuse_candidate_rejects_docs_supporting_evidence() -> None:
    public_url = "https://docs.plesk.com/release-notes/obsidian/change-log"
    excerpt = ReuseComparisonExcerpt(
        excerpt_ref="public-excerpt-docs",
        section_path="Monitoring",
        citation=f"Plesk change log — Monitoring — {public_url}",
        text="Monitoring no longer shows empty graphs.",
        token_count=6,
    )

    with pytest.raises(ContractValidationError):
        ReuseComparisonCandidate(
            rank=1,
            source_doc_id="plesk-docs://change-log",
            source_type="docs",
            title="Plesk change log",
            public_url=public_url,
            article_status="active",
            updated_at="2026-07-01",
            origin="search_result",
            excerpts=(excerpt,),
        )


@pytest.mark.parametrize(
    "title",
    [
        "[Incident] Websites show no data",
        "[ incident ] Websites show no data",
        "[INCIDENT]\tWebsites show no data",
    ],
)
def test_reuse_candidate_rejects_incident_notice(title: str) -> None:
    public_url = "https://support.plesk.com/hc/en-us/articles/123456-Incident"
    excerpt = ReuseComparisonExcerpt(
        excerpt_ref="public-excerpt-incident",
        section_path="Symptoms",
        citation=f"{title} — Symptoms — {public_url}",
        text="Websites temporarily show no data.",
        token_count=5,
    )

    assert not is_reusable_kcs_article_candidate(
        public_url=public_url,
        title=title,
    )
    with pytest.raises(ContractValidationError):
        ReuseComparisonCandidate(
            rank=1,
            source_doc_id="plesk-support://123456",
            source_type="support",
            title=title,
            public_url=public_url,
            article_status="active",
            updated_at="2026-07-25",
            origin="search_result",
            excerpts=(excerpt,),
        )


@pytest.mark.parametrize(
    ("text", "token_count"),
    [
        ("one two", 1),
        ("Authorization: Bearer SECRET", 3),
        ("Read /Users/example/private.txt", 2),
    ],
)
def test_reuse_comparison_excerpt_rejects_unsafe_or_false_bounds(
    text: str,
    token_count: int,
) -> None:
    with pytest.raises(ContractValidationError):
        ReuseComparisonExcerpt(
            excerpt_ref="public-excerpt-invalid",
            section_path="Resolution",
            citation=(
                "Example — Resolution — "
                "https://support.plesk.com/hc/en-us/articles/123456-Example"
            ),
            text=text,
            token_count=token_count,
        )


def test_reuse_comparison_validation_rejects_non_contract_provider_output() -> None:
    result = validate_reuse_comparison_evidence({"status": "ready"})

    assert result.to_json_dict() == {
        "ok": False,
        "blockers": ["invalid_reuse_comparison_evidence"],
    }


def test_reuse_comparison_candidate_rejects_unknown_origin() -> None:
    with pytest.raises(ContractValidationError):
        _candidate(origin="local_runtime")


def test_reuse_comparison_candidate_rejects_injected_citation_tail() -> None:
    public_url = "https://support.plesk.com/hc/en-us/articles/123456-Example"
    excerpt = ReuseComparisonExcerpt(
        excerpt_ref="public-excerpt-injected",
        section_path="Resolution",
        citation=f"Authorization: Bearer SECRET — {public_url}",
        text="Restart the affected service.",
        token_count=4,
    )

    with pytest.raises(ContractValidationError):
        ReuseComparisonCandidate(
            rank=1,
            source_doc_id="plesk-support://123456",
            source_type="support",
            title="Example",
            public_url=public_url,
            article_status="active",
            updated_at="2026-06-10",
            origin="search_result",
            excerpts=(excerpt,),
        )


def test_reuse_comparison_evidence_rejects_unknown_status() -> None:
    with pytest.raises(ContractValidationError):
        ReuseComparisonEvidence(
            searched=True,
            status="ready",
            search_run_ref="comparison-run-001",
            explicit_reference_status="not_provided",
            candidates=(_candidate(),),
        )


def test_reuse_comparison_evidence_rejects_more_than_three_articles() -> None:
    with pytest.raises(ContractValidationError):
        ReuseComparisonEvidence(
            searched=True,
            status="comparison_evidence_ready",
            search_run_ref="comparison-run-001",
            explicit_reference_status="not_provided",
            candidates=tuple(
                _candidate(rank=index, article_id=str(100000 + index))
                for index in range(1, 5)
            ),
        )
