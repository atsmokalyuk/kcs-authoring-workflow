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
    request_from_symptoms,
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
