from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from kcs_adapters.desktop_authoring_tools import DesktopAuthoringTools
from kcs_adapters.desktop_draft_tool import DesktopDraftArticleTool
from kcs_adapters.desktop_reuse_comparison import (
    PendingReuseComparison,
    ReuseComparisonExpiredError,
    ReuseComparisonInvalidError,
    confirmed_helpful_public_article,
    reuse_comparison_required_result,
    validate_reuse_comparison_submit,
)
from kcs_adapters.desktop_tool_results import (
    tool_result_text,
    validate_tool_structured_content,
)
from kcs_adapters.desktop_tool_schemas import tool_output_schema
from kcs_adapters.desktop_workflow import DesktopDraftWorkflow
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict
from kcs_core.reuse_comparison import (
    PublicArticleReference,
    ReuseComparisonCandidate,
    ReuseComparisonEvidence,
    ReuseComparisonEvidenceRequest,
    ReuseComparisonExcerpt,
)

_PUBLIC_URL = (
    "https://support.plesk.com/hc/en-us/articles/123456-Example-article"
)


class _FixtureComparisonProvider:
    def __init__(self, evidence: ReuseComparisonEvidence | None = None) -> None:
        self.evidence = evidence or _ready_evidence()
        self.requests: list[ReuseComparisonEvidenceRequest] = []

    def collect_comparison_evidence(
        self,
        request: ReuseComparisonEvidenceRequest,
    ) -> ReuseComparisonEvidence:
        self.requests.append(request)
        return self.evidence


def _excerpt(article_id: str = "123456") -> ReuseComparisonExcerpt:
    public_url = (
        f"https://support.plesk.com/hc/en-us/articles/{article_id}-Example-article"
    )
    return ReuseComparisonExcerpt(
        excerpt_ref=f"public-excerpt-{article_id}",
        section_path="Resolution",
        citation=f"Example article — Resolution — {public_url}",
        text="Restart the affected service and verify that it remains active.",
        token_count=10,
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
        title="Example article",
        public_url=(
            f"https://support.plesk.com/hc/en-us/articles/"
            f"{article_id}-Example-article"
        ),
        article_status="active",
        updated_at="2026-06-10",
        origin=origin,
        excerpts=(_excerpt(article_id),),
    )


def _ready_evidence() -> ReuseComparisonEvidence:
    return ReuseComparisonEvidence(
        searched=True,
        status="comparison_evidence_ready",
        search_run_ref="comparison-run-001",
        explicit_reference_status="not_provided",
        candidates=(_candidate(),),
    )


def _issue_candidate() -> JsonDict:
    return {
        "article_type": "technical_scr",
        "confirmed_facts": ["The affected service stops after the update."],
        "item_ref": "candidate-001",
        "summary": "The affected service stops after the update.",
        "symptoms": ["The affected service is inactive after the update."],
        "title": "Service is inactive after an update",
    }


def _workflow(
    provider: _FixtureComparisonProvider,
    *,
    ttl_seconds: float = 900,
) -> DesktopDraftWorkflow:
    return DesktopDraftWorkflow(
        provider=None,
        selection_ttl_seconds=ttl_seconds,
        reuse_comparison_provider=provider,
    )


def _draft_tool(
    tmp_path,
    workflow: DesktopDraftWorkflow,
    calls: list[Mapping[str, Any]],
) -> DesktopDraftArticleTool:
    def author_approved_summary(arguments: Mapping[str, Any]) -> JsonDict:
        calls.append(arguments)
        return {
            "debug_code": "stub_not_ready",
            "pipeline_ok": False,
            "ready_for_reviewer": False,
            "result_kind": "approved_summary_authoring",
        }

    def unexpected_author_ticket(arguments: Mapping[str, Any]) -> JsonDict:
        raise AssertionError(f"unexpected ticket authoring call: {arguments!r}")

    return DesktopDraftArticleTool(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
        author_approved_summary=author_approved_summary,
        author_ticket=unexpected_author_ticket,
    )


@pytest.mark.parametrize(
    "text",
    [
        f"The article {_PUBLIC_URL} resolved the issue.",
        f"The article {_PUBLIC_URL} partially helped.",
        f"The article {_PUBLIC_URL} was helpful.",
        f"The article {_PUBLIC_URL} solved the issue.",
        f"The article {_PUBLIC_URL} was partially helpful.",
    ],
)
def test_explicit_article_priority_requires_positive_ticket_outcome(
    text: str,
) -> None:
    article = confirmed_helpful_public_article(
        {"symptoms": ["The service is inactive."], "resolution_steps": [text]},
        approved_summary_text=text,
    )

    assert article == PublicArticleReference(public_url=_PUBLIC_URL)


@pytest.mark.parametrize(
    "text",
    [
        f"Refer to {_PUBLIC_URL}.",
        f"Use {_PUBLIC_URL} to resolve the issue.",
        f"The article {_PUBLIC_URL} did not help.",
        f"The article {_PUBLIC_URL} was never confirmed to resolve the issue.",
    ],
)
def test_neutral_or_negative_article_reference_has_no_priority(text: str) -> None:
    assert (
        confirmed_helpful_public_article(
            {"symptoms": ["The service is inactive."], "resolution_steps": [text]},
            approved_summary_text=text,
        )
        is None
    )


@pytest.mark.parametrize(
    "text",
    [
        (
            f"The article {_PUBLIC_URL} was reviewed. "
            "A separate workaround fixed the issue."
        ),
        (
            f"The article {_PUBLIC_URL} describes the failed attempt. "
            "A later solution worked."
        ),
    ],
)
def test_unrelated_later_success_does_not_promote_article(text: str) -> None:
    assert (
        confirmed_helpful_public_article(
            {"resolution_steps": [text]},
            approved_summary_text=text,
        )
        is None
    )


@pytest.mark.parametrize(
    "text",
    [
        f"The article {_PUBLIC_URL} was helpful for a different issue.",
        f"The article {_PUBLIC_URL} solved a different problem, not this issue.",
        (
            f"The article {_PUBLIC_URL} resolved the issue for another customer, "
            "not this case."
        ),
        (
            f"The article {_PUBLIC_URL} was helpful only as background; "
            "a separate workaround fixed this issue."
        ),
    ],
)
def test_positive_wording_for_other_scope_does_not_promote_article(
    text: str,
) -> None:
    assert (
        confirmed_helpful_public_article(
            {"resolution_steps": [text]},
            approved_summary_text=text,
        )
        is None
    )


def test_candidate_relation_must_be_verbatim_in_approved_source() -> None:
    generated = f"The article {_PUBLIC_URL} resolved the issue."

    assert (
        confirmed_helpful_public_article(
            {"resolution_steps": [generated]},
            approved_summary_text=f"The ticket only mentioned {_PUBLIC_URL}.",
        )
        is None
    )


def test_helpful_docs_page_is_not_promoted_as_reusable_article() -> None:
    docs_url = "https://docs.plesk.com/release-notes/obsidian/change-log"
    text = f"The article {docs_url} helped resolve the issue."

    assert (
        confirmed_helpful_public_article(
            {"resolution_steps": [text]},
            approved_summary_text=text,
        )
        is None
    )


def test_comparison_request_is_bounded_and_carries_confirmed_explicit_article() -> None:
    explicit_candidate = _issue_candidate()
    explicit_candidate["supported_resolution_or_workaround"] = (
        f"Using {_PUBLIC_URL} partially resolved the issue."
    )
    provider = _FixtureComparisonProvider(
        ReuseComparisonEvidence(
            searched=True,
            status="comparison_evidence_ready",
            search_run_ref="comparison-run-001",
            explicit_reference_status="context_ready",
            explicit_article=PublicArticleReference(public_url=_PUBLIC_URL),
            candidates=(_candidate(origin="explicit_resolution_reference"),),
        )
    )

    pending = _workflow(provider).start_pending_reuse_comparison(
        issue_candidate=explicit_candidate,
        approved_summary_text=str(
            explicit_candidate["supported_resolution_or_workaround"]
        ),
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )

    assert isinstance(pending, PendingReuseComparison)
    assert provider.requests == [
        ReuseComparisonEvidenceRequest(
            ("The affected service is inactive after the update.",),
            PublicArticleReference(public_url=_PUBLIC_URL),
        )
    ]


def test_required_result_exposes_only_bounded_public_comparison_context() -> None:
    pending = _workflow(_FixtureComparisonProvider()).start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )

    assert isinstance(pending, PendingReuseComparison)
    result = reuse_comparison_required_result(
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_confirm_reuse_comparison",
    )

    assert result["result_kind"] == "reuse_comparison_required"
    assert result["draft_generated"] is False
    assert result["comparison_outcomes"] == [
        "reuse",
        "update",
        "none_fit",
        "need_more_evidence",
    ]
    assert result["submit_tool"] == "kcs_confirm_reuse_comparison"
    assert result["next_tool"] == "kcs_confirm_reuse_comparison"
    assert result["accepted_ticket_facts"] == [
        "The affected service stops after the update.",
        "The affected service is inactive after the update.",
    ]
    card = result["comparison_candidates"][0]
    assert card["candidate_ref"] == "comparison-candidate-001"
    assert card["public_url"] == _PUBLIC_URL
    assert card["excerpts"][0]["text"].startswith("Restart the affected service")
    assert "source_doc_id" not in card
    assert "search_run_ref" not in result
    assert "approved_summary_text" not in result
    text = tool_result_text(result)
    assert "ask exactly one operator question" in text
    assert "clickable Markdown link" in text
    assert "candidate_ref visible" in text
    assert "Do not call the submit tool until the operator answers" in text
    assert _PUBLIC_URL in text
    validate_tool_structured_content(result, tool_output_schema())


def test_public_comparison_safety_exception_is_limited_to_comparison_result() -> None:
    pending = _workflow(_FixtureComparisonProvider()).start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)
    result = reuse_comparison_required_result(
        pending,
        schema_version="kcs_mcp_tool_result_v1",
        submit_tool="kcs_confirm_reuse_comparison",
    )
    result["result_kind"] = "draft_article_authoring"
    result["comparison_candidates"] = [
        {"public_url": "https://private.customer.example.net/article"}
    ]

    with pytest.raises(ContractValidationError):
        validate_tool_structured_content(result, tool_output_schema())


def test_docs_page_cannot_be_constructed_as_reuse_candidate() -> None:
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


def test_invalid_provider_response_blocks_without_authoring(tmp_path) -> None:
    class InvalidProvider:
        def collect_comparison_evidence(
            self,
            request: ReuseComparisonEvidenceRequest,
        ) -> object:
            return {"request_was_seen": bool(request.symptoms)}

    invalid_provider: Any = InvalidProvider()
    workflow = DesktopDraftWorkflow(
        provider=None,
        selection_ttl_seconds=900,
        reuse_comparison_provider=invalid_provider,
    )
    pending_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Approved sanitized summary.",
    )
    author_calls: list[Mapping[str, Any]] = []
    result = _draft_tool(tmp_path, workflow, author_calls).draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )

    assert result["result_kind"] == "reuse_comparison_blocked"
    assert result["debug_code"] == "comparison_provider_invalid_response"
    assert result["draft_generated"] is False
    assert author_calls == []
    assert workflow.pending_reuse_comparison is None


@pytest.mark.parametrize("outcome", ["reuse", "update"])
def test_candidate_outcomes_require_one_displayed_candidate_ref(
    outcome: str,
) -> None:
    pending = _workflow(_FixtureComparisonProvider()).start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)

    with pytest.raises(ReuseComparisonInvalidError):
        validate_reuse_comparison_submit(
            pending,
            comparison_ref=pending.comparison_ref,
            outcome=outcome,
        )

    submission = validate_reuse_comparison_submit(
        pending,
        comparison_ref=pending.comparison_ref,
        outcome=outcome,
        candidate_ref="comparison-candidate-001",
    )

    assert submission.selected_candidate is pending.evidence.candidates[0]


@pytest.mark.parametrize("outcome", ["none_fit", "need_more_evidence"])
def test_candidate_free_outcomes_ignore_displayed_candidate_ref(outcome: str) -> None:
    pending = _workflow(_FixtureComparisonProvider()).start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)

    submission = validate_reuse_comparison_submit(
        pending,
        comparison_ref=pending.comparison_ref,
        outcome=outcome,
        candidate_ref="comparison-candidate-001",
    )

    assert submission.selected_candidate is None


@pytest.mark.parametrize("outcome", ["none_fit", "need_more_evidence"])
def test_candidate_free_outcomes_reject_unknown_candidate_ref(outcome: str) -> None:
    pending = _workflow(_FixtureComparisonProvider()).start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)

    with pytest.raises(ReuseComparisonInvalidError):
        validate_reuse_comparison_submit(
            pending,
            comparison_ref=pending.comparison_ref,
            outcome=outcome,
            candidate_ref="comparison-candidate-999",
        )


def test_pre_draft_comparison_blocks_authoring_until_none_fit(tmp_path) -> None:
    provider = _FixtureComparisonProvider()
    workflow = _workflow(provider)
    pending_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Approved sanitized summary.",
    )
    author_calls: list[Mapping[str, Any]] = []
    tool = _draft_tool(tmp_path, workflow, author_calls)

    comparison = tool.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )

    assert comparison["result_kind"] == "reuse_comparison_required"
    assert comparison["draft_generated"] is False
    assert author_calls == []

    result = tool.confirm_reuse_comparison(
        {
            "candidate_ref": "comparison-candidate-001",
            "comparison_ref": comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )

    assert result["comparison_sequence_outcomes"][0]["comparison_outcome"] == (
        "none_fit"
    )
    assert len(author_calls) == 1
    item = author_calls[0]["item"]
    assert isinstance(item, Mapping)
    assert item["reuse_search_checked"] is True
    assert item["reuse_search_run_ref"] == "comparison-run-001"


def test_none_fit_suppresses_legacy_url_partial_match(tmp_path) -> None:
    candidate = _issue_candidate()
    candidate["environment"] = {
        "applicable_to": ["Plesk for Linux"],
        "platform": "Linux",
        "product": "Plesk",
    }
    candidate["supported_cause"] = "A required service stops after the update."
    candidate["supported_resolution_or_workaround"] = (
        "Run systemctl restart sw-cp-server and verify that it remains active."
    )
    candidate["resolution_steps"] = [
        f"Apply {_PUBLIC_URL} and verify the service.",
        "Run systemctl restart sw-cp-server.",
        "Verify that the service remains active.",
    ]
    workflow = _workflow(_FixtureComparisonProvider())
    pending_selection = workflow.start_pending_selection(
        [candidate],
        approved_summary_text="Approved sanitized summary.",
    )
    tools = DesktopAuthoringTools(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
    )
    comparison = tools.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )

    result = tools.confirm_reuse_comparison(
        {
            "comparison_ref": comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )

    assert result["recommended_action"] == "create_candidate"
    assert result.get("selected_reuse_match") is None
    assert result["reuse_search_status"] == "checked"


@pytest.mark.parametrize(
    ("outcome", "expected_action"),
    [
        ("reuse", "reuse_existing"),
        ("update", "flag_existing"),
        ("need_more_evidence", "blocked"),
    ],
)
def test_terminal_comparison_outcomes_do_not_draft(
    tmp_path,
    outcome: str,
    expected_action: str,
) -> None:
    workflow = _workflow(_FixtureComparisonProvider())
    pending_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Approved sanitized summary.",
    )
    author_calls: list[Mapping[str, Any]] = []
    tool = _draft_tool(tmp_path, workflow, author_calls)
    comparison = tool.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )
    arguments: JsonDict = {
        "comparison_ref": comparison["comparison_ref"],
        "outcome": outcome,
    }
    if outcome in {"reuse", "update"}:
        arguments["candidate_ref"] = "comparison-candidate-001"

    result = tool.confirm_reuse_comparison(arguments)

    assert result["recommended_action"] == expected_action
    assert result["draft_generated"] is False
    assert author_calls == []


def test_invalid_submit_consumes_pending_state_and_replay_fails(tmp_path) -> None:
    workflow = _workflow(_FixtureComparisonProvider())
    pending_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Approved sanitized summary.",
    )
    tool = _draft_tool(tmp_path, workflow, [])
    comparison = tool.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )

    with pytest.raises(ReuseComparisonInvalidError):
        tool.confirm_reuse_comparison(
            {
                "comparison_ref": comparison["comparison_ref"],
                "outcome": "reuse",
            }
        )

    assert workflow.pending_reuse_comparison is None


def test_unknown_candidate_ref_consumes_state_and_replay_requires_restart(
    tmp_path,
) -> None:
    workflow = _workflow(_FixtureComparisonProvider())
    pending_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Approved sanitized summary.",
    )
    tools = DesktopAuthoringTools(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
    )
    comparison = tools.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )
    invalid = tools.confirm_reuse_comparison(
        {
            "candidate_ref": "comparison-candidate-999",
            "comparison_ref": comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )

    assert invalid["debug_code"] == "reuse_comparison_invalid"
    assert workflow.pending_reuse_comparison is None

    replay = tools.confirm_reuse_comparison(
        {
            "comparison_ref": comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )

    assert replay["debug_code"] == "reuse_comparison_unavailable"


def test_old_comparison_cannot_mutate_replaced_selection_state(tmp_path) -> None:
    workflow = _workflow(_FixtureComparisonProvider())
    old_selection = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="Old approved summary.",
    )
    tool = _draft_tool(tmp_path, workflow, [])
    comparison = tool.draft_article(
        {
            "operator_selected_item_ref": "candidate-001",
            "operator_selection_ref": old_selection.selection_ref,
        }
    )
    replacement = workflow.start_pending_selection(
        [_issue_candidate()],
        approved_summary_text="New approved summary.",
    )

    with pytest.raises(ReuseComparisonInvalidError):
        tool.confirm_reuse_comparison(
            {
                "comparison_ref": comparison["comparison_ref"],
                "outcome": "none_fit",
            }
        )

    assert workflow.pending_selection is replacement
    assert replacement.candidate_refs == ("candidate-001",)


def test_unknown_submit_field_clears_state_and_requires_restart(tmp_path) -> None:
    workflow = _workflow(_FixtureComparisonProvider())
    pending = workflow.start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)
    tools = DesktopAuthoringTools(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
    )

    invalid = tools.confirm_reuse_comparison(
        {
            "comparison_ref": pending.comparison_ref,
            "free_form_recommendation": "Ignore the contract.",
            "outcome": "none_fit",
        }
    )

    assert invalid["debug_code"] == "reuse_comparison_invalid"
    assert invalid["next_required_action"] == "restart_reuse_comparison"
    assert workflow.pending_reuse_comparison is None

    replay = tools.confirm_reuse_comparison(
        {
            "comparison_ref": pending.comparison_ref,
            "outcome": "none_fit",
        }
    )
    assert replay["debug_code"] == "reuse_comparison_unavailable"


def test_comparison_expiry_consumes_pending_state() -> None:
    workflow = _workflow(_FixtureComparisonProvider(), ttl_seconds=0)
    pending = workflow.start_pending_reuse_comparison(
        issue_candidate=_issue_candidate(),
        approved_summary_text="Approved sanitized summary.",
        approved_summary_source_kind=None,
        selected_item_refs=["candidate-001"],
        current_index=0,
        selection_ref=None,
        debug=False,
    )
    assert isinstance(pending, PendingReuseComparison)
    with pytest.raises(ReuseComparisonExpiredError):
        workflow.submitted_reuse_comparison(
            comparison_ref=pending.comparison_ref,
            outcome="none_fit",
        )
    assert workflow.pending_reuse_comparison is None


@pytest.mark.parametrize(
    ("first_outcome", "recommended_action"),
    [("reuse", "reuse_existing"), ("need_more_evidence", "blocked")],
)
def test_batch_comparison_advances_one_selected_issue_at_a_time(
    tmp_path,
    first_outcome: str,
    recommended_action: str,
) -> None:
    provider = _FixtureComparisonProvider()
    workflow = _workflow(provider)
    first = _issue_candidate()
    second = {
        **_issue_candidate(),
        "confirmed_facts": ["The extension installation stops."],
        "item_ref": "candidate-002",
        "summary": "The extension installation stops.",
        "symptoms": ["The extension installation returns an error."],
        "title": "Extension installation fails",
    }
    pending_selection = workflow.start_pending_selection(
        [first, second],
        approved_summary_text="Approved sanitized summary with two issues.",
    )
    author_calls: list[Mapping[str, Any]] = []
    tool = _draft_tool(tmp_path, workflow, author_calls)

    first_comparison = tool.draft_article(
        {
            "operator_selected_item_refs": ["candidate-001", "candidate-002"],
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )
    assert first_comparison["result_kind"] == "reuse_comparison_required"
    assert len(provider.requests) == 1

    second_comparison = tool.confirm_reuse_comparison(
        {
            "comparison_ref": first_comparison["comparison_ref"],
            "outcome": first_outcome,
            **(
                {"candidate_ref": "comparison-candidate-001"}
                if first_outcome == "reuse"
                else {}
            ),
        }
    )
    assert second_comparison["result_kind"] == "reuse_comparison_required"
    assert second_comparison["comparison_sequence_outcomes"] == [
        {
            "comparison_outcome": first_outcome,
            "draft_generated": False,
            "item_ref": "candidate-001",
            "recommended_action": recommended_action,
            "reviewer_bundle_written": False,
        }
    ]
    assert len(provider.requests) == 2
    assert author_calls == []

    result = tool.confirm_reuse_comparison(
        {
            "comparison_ref": second_comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )
    assert [
        entry["comparison_outcome"] for entry in result["comparison_sequence_outcomes"]
    ] == [first_outcome, "none_fit"]
    assert len(author_calls) == 1


def test_duplicate_none_fit_replays_result_without_consuming_next_comparison(
    tmp_path,
) -> None:
    provider = _FixtureComparisonProvider()
    workflow = _workflow(provider)
    first = _issue_candidate()
    second = {
        **_issue_candidate(),
        "item_ref": "candidate-002",
        "title": "Extension installation fails",
    }
    pending_selection = workflow.start_pending_selection(
        [first, second],
        approved_summary_text="Approved sanitized summary with two issues.",
    )
    author_calls: list[Mapping[str, Any]] = []

    def author_approved_summary(arguments: Mapping[str, Any]) -> JsonDict:
        author_calls.append(arguments)
        return {
            "auto_publish_allowed": False,
            "draft_generated": True,
            "public_output_approved": False,
            "ready_for_reviewer": False,
            "recommended_action": "create_candidate",
            "result_kind": "approved_summary_authoring",
            "reviewer_bundle_written": False,
        }

    tool = DesktopDraftArticleTool(
        draft_workflow=workflow,
        reviewer_bundle_root=tmp_path / "local-data" / "reviewer-bundles",
        schema_version="kcs_mcp_tool_result_v1",
        author_approved_summary=author_approved_summary,
        author_ticket=lambda arguments: {},
    )
    first_comparison = tool.draft_article(
        {
            "operator_selected_item_refs": ["candidate-001", "candidate-002"],
            "operator_selection_ref": pending_selection.selection_ref,
        }
    )
    first_submit = {
        "comparison_ref": first_comparison["comparison_ref"],
        "outcome": "none_fit",
    }

    second_comparison = tool.confirm_reuse_comparison(first_submit)
    replay = tool.confirm_reuse_comparison(first_submit)
    redundant_ref_replay = tool.confirm_reuse_comparison(
        {
            **first_submit,
            "candidate_ref": "comparison-candidate-001",
        }
    )

    assert replay == second_comparison
    assert redundant_ref_replay == second_comparison
    assert len(author_calls) == 1
    assert workflow.pending_reuse_comparison is not None
    assert (
        workflow.pending_reuse_comparison.comparison_ref
        == second_comparison["comparison_ref"]
    )
    with pytest.raises(ReuseComparisonInvalidError):
        tool.confirm_reuse_comparison(
            {
                "candidate_ref": "comparison-candidate-001",
                "comparison_ref": first_comparison["comparison_ref"],
                "outcome": "reuse",
            }
        )
    assert workflow.pending_reuse_comparison is not None
    assert (
        workflow.pending_reuse_comparison.comparison_ref
        == second_comparison["comparison_ref"]
    )

    final = tool.confirm_reuse_comparison(
        {
            "comparison_ref": second_comparison["comparison_ref"],
            "outcome": "none_fit",
        }
    )

    assert len(author_calls) == 2
    assert [
        outcome["item_ref"]
        for outcome in final["comparison_sequence_outcomes"]
    ] == ["candidate-001", "candidate-002"]
