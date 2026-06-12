from __future__ import annotations

import kcs_core
from kcs_core.decision import DecisionBlocker, decide_kcs_action
from kcs_core.models import (
    ArticleType,
    KcsActionDecisionPacket,
    NormalizedTicketEvidencePacket,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.safety import EvidenceVisibility, InputClass
from kcs_core.validation import EvidenceBlocker


def _evidence(**overrides: object) -> NormalizedTicketEvidencePacket:
    values = {
        "case_ref": "CASE-SYNTH-DECISION",
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "source_refs": ["SRC-SYNTH-DECISION"],
        "issue_candidates": [
            {
                "candidate_id": "ISSUE-SYNTH-DECISION",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "summary": "Mail delivery returns a generic queue error.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
            }
        ],
        "environment": {"product_area": "mail"},
        "symptoms": ["Mail delivery returns a generic queue error."],
        "confirmed_facts": ["A safe product setting is disabled."],
        "supported_cause": "A required mail setting is disabled.",
        "supported_resolution_or_workaround": "Enable the required mail setting.",
        "open_questions": [],
        "visibility_summary": {
            "classes": [EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value],
        },
        "sanitizer_report": {"status": "passed"},
    }
    values.update(overrides)
    return NormalizedTicketEvidencePacket(**values)


def _reuse_results(**overrides: object) -> ReuseSearchResultsPacket:
    values = {
        "search_run_ref": "SEARCH-SYNTH-DECISION",
        "searched": True,
        "search_source": "synthetic_fixture",
        "matches": [],
        "blockers": [],
    }
    values.update(overrides)
    return ReuseSearchResultsPacket(**values)


def _technical_match(content_status: str = "complete") -> dict[str, object]:
    return {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": content_status,
    }


def _split_candidate(candidate_id: str, **overrides: object) -> dict[str, object]:
    values = {
        "candidate_id": candidate_id,
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "summary": f"Synthetic summary for {candidate_id}.",
        "atomic": True,
        "customer_reported": True,
        "kcs_applicable": True,
        "resolution_state": "solved",
        "public_solution_safe": True,
        "reuse_search_status": "checked",
        "confirmed_facts": [f"Synthetic fact for {candidate_id}."],
        "supported_cause": f"Synthetic cause for {candidate_id}.",
        "supported_resolution_or_workaround": (
            f"Synthetic resolution for {candidate_id}."
        ),
    }
    values.update(overrides)
    return values


def _split_match(candidate_id: str, content_status: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "match_ref": f"KB-SYNTH-{candidate_id}",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": f"Synthetic cause for {candidate_id}.",
            "resolution_or_answer": f"Synthetic resolution for {candidate_id}.",
        },
        "content_status": content_status,
    }


def test_exact_match_reuses_existing_article() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[_technical_match()]),
    )

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value
    assert decision.article_type == ArticleType.TECHNICAL_SCR.value
    assert decision.selected_reuse_match == {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "complete",
    }
    assert decision.auto_publish_allowed is False


def test_single_candidate_ignores_match_scoped_to_other_candidate() -> None:
    other_candidate_match = _technical_match()
    other_candidate_match["candidate_id"] = "ISSUE-SYNTH-OTHER"

    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[other_candidate_match]),
    )

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_existing_same_identity_incomplete_content_updates_existing() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[_technical_match("incomplete")]),
    )

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert decision.selected_reuse_match["content_status"] == "incomplete"


def test_only_howto_match_for_technical_scr_creates_candidate() -> None:
    match = {
        "match_ref": "KB-SYNTH-HOWTO",
        "article_type": ArticleType.HOWTO_QA.value,
        "identity": {
            "question": "How to enable a mail setting?",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": "complete",
    }

    decision = decide_kcs_action(_evidence(), _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_incorrect_related_match_flags_existing() -> None:
    match = {
        "match_ref": "KB-SYNTH-INCORRECT",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": "incorrect",
    }

    decision = decide_kcs_action(_evidence(), _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    assert decision.selected_reuse_match["match_ref"] == "KB-SYNTH-INCORRECT"


def test_unrelated_incorrect_match_does_not_override_create_candidate() -> None:
    matches = [
        {
            "match_ref": "KB-SYNTH-PARTIAL",
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "identity": {
                "cause": "A required mail setting is disabled.",
                "resolution_or_answer": "Enable the required mail setting.",
            },
            "content_status": "partial",
        },
        {
            "match_ref": "KB-SYNTH-UNRELATED-INCORRECT",
            "article_type": ArticleType.HOWTO_QA.value,
            "identity": {
                "question": "How to enable a different setting?",
                "resolution_or_answer": "Enable a different setting.",
            },
            "content_status": "incorrect",
        },
    ]

    decision = decide_kcs_action(_evidence(), _reuse_results(matches=matches))

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_no_search_blocks_possible_duplicate_not_checked() -> None:
    decision = decide_kcs_action(_evidence(), _reuse_results(searched=False))

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.article_type == ArticleType.NONE.value
    assert decision.blockers == [
        DecisionBlocker.POSSIBLE_DUPLICATE_NOT_CHECKED.value
    ]


def test_no_search_preserves_search_layer_blockers() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(searched=False, blockers=["search_unavailable"]),
    )

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [
        DecisionBlocker.POSSIBLE_DUPLICATE_NOT_CHECKED.value,
        "search_unavailable",
    ]


def test_reuse_result_blockers_block_decision() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(blockers=["search_unavailable"]),
    )

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == ["search_unavailable"]


def test_unsolved_issue_returns_no_article() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-UNSOLVED",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "unsolved",
                "public_solution_safe": True,
            }
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.NO_ARTICLE.value
    assert decision.blockers == [DecisionBlocker.NO_SUPPORTED_ANSWER.value]


def test_no_customer_reported_reusable_issue_returns_no_article() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-NOT-KCS",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "atomic": True,
                "customer_reported": False,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
            }
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.NO_ARTICLE.value
    assert decision.blockers == [DecisionBlocker.NO_CUSTOMER_REPORTED_ISSUE.value]


def test_customer_specific_issue_returns_no_article_with_blocker() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-CUSTOMER-SPECIFIC",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "customer_specific": True,
                "public_solution_safe": True,
            }
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.NO_ARTICLE.value
    assert decision.blockers == [DecisionBlocker.CUSTOMER_SPECIFIC.value]


def test_multi_issue_returns_split_required() -> None:
    first_candidate = _split_candidate("ISSUE-SYNTH-1")
    second_candidate = _split_candidate("ISSUE-SYNTH-2")
    evidence = _evidence(
        issue_candidates=[
            first_candidate,
            second_candidate,
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert decision.blockers == [EvidenceBlocker.MULTI_ISSUE.value]
    assert len(decision.split_items) == 2


def test_split_items_without_candidate_ids_get_unique_stable_ids() -> None:
    first_candidate = _split_candidate("ISSUE-SYNTH-1")
    second_candidate = _split_candidate("ISSUE-SYNTH-2")
    first_candidate.pop("candidate_id")
    second_candidate.pop("candidate_id")
    evidence = _evidence(issue_candidates=[first_candidate, second_candidate])

    decision = decide_kcs_action(evidence, _reuse_results())

    assert [item["candidate_id"] for item in decision.split_items] == [
        "CASE-SYNTH-DECISION:issue-1",
        "CASE-SYNTH-DECISION:issue-2",
    ]


def test_single_item_preserves_normal_decision_behavior() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[_technical_match("incomplete")]),
    )

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert decision.split_items == []


def test_split_required_has_no_public_article_draft() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-1"),
            _split_candidate("ISSUE-SYNTH-2"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())
    payload = decision.to_json_dict()

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert "public_article_candidate" not in payload
    assert decision.selected_reuse_match is None


def test_split_item_can_update_existing() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-UPDATE"),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[_split_match("ISSUE-SYNTH-UPDATE", "incomplete")]),
    )

    update_item = decision.split_items[0]
    assert update_item["candidate_id"] == "ISSUE-SYNTH-UPDATE"
    assert update_item["recommended_action"] == RecommendedAction.UPDATE_EXISTING.value
    assert update_item["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert update_item["blockers"] == []
    assert update_item["reuse_search_status"] == "checked"


def test_split_item_can_use_unscoped_identity_match() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-UNSCOPED"),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )
    unscoped_match = _split_match("ISSUE-SYNTH-UNSCOPED", "complete")
    unscoped_match.pop("candidate_id")

    decision = decide_kcs_action(
        evidence,
        _reuse_results(matches=[unscoped_match]),
    )

    reuse_item = decision.split_items[0]
    assert reuse_item["recommended_action"] == RecommendedAction.REUSE_EXISTING.value
    assert reuse_item["selected_reuse_match"] == {
        "match_ref": "KB-SYNTH-ISSUE-SYNTH-UNSCOPED",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "complete",
    }


def test_split_item_can_create_candidate() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-CREATE"),
            _split_candidate("ISSUE-SYNTH-OTHER"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    create_item = decision.split_items[0]
    assert create_item["recommended_action"] == RecommendedAction.CREATE_CANDIDATE.value
    assert create_item["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert create_item["blockers"] == []


def test_split_item_compact_candidate_inherits_root_evidence() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-COMPACT",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "summary": "Compact candidate inherits root evidence.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "reuse_search_status": "checked",
            },
            _split_candidate("ISSUE-SYNTH-OTHER"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    compact_item = decision.split_items[0]
    assert compact_item["recommended_action"] == (
        RecommendedAction.CREATE_CANDIDATE.value
    )
    assert compact_item["blockers"] == []


def test_split_item_can_return_no_article() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate(
                "ISSUE-SYNTH-DNS",
                summary="Third-party DNS question.",
                third_party_only=True,
                supported_resolution_or_workaround=None,
            ),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    no_article_item = decision.split_items[0]
    assert no_article_item["recommended_action"] == RecommendedAction.NO_ARTICLE.value
    assert no_article_item["blockers"] == [DecisionBlocker.THIRD_PARTY_ONLY.value]


def test_split_item_blocks_missing_resolution() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate(
                "ISSUE-SYNTH-MISSING-RESOLUTION",
                supported_resolution_or_workaround=None,
            ),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    blocked_item = decision.split_items[0]
    assert blocked_item["recommended_action"] == RecommendedAction.BLOCKED.value
    assert blocked_item["blockers"] == [
        EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value
    ]


def test_split_item_blocks_missing_reuse_search_status() -> None:
    candidate_without_search = _split_candidate("ISSUE-SYNTH-NO-SEARCH")
    candidate_without_search.pop("reuse_search_status")
    evidence = _evidence(
        issue_candidates=[
            candidate_without_search,
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    blocked_item = decision.split_items[0]
    assert blocked_item["recommended_action"] == RecommendedAction.BLOCKED.value
    assert blocked_item["article_type"] == ArticleType.NONE.value
    assert blocked_item["blockers"] == [
        DecisionBlocker.REUSE_SEARCH_STATUS_MISSING.value
    ]
    assert blocked_item["reuse_search_status"] == "missing"


def test_split_items_preserve_root_open_question_blocker() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-QUESTION-1"),
            _split_candidate("ISSUE-SYNTH-QUESTION-2"),
        ],
        open_questions=["Need safe confirmation before decision."],
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert all(
        item["recommended_action"] == RecommendedAction.BLOCKED.value
        for item in decision.split_items
    )
    assert all(
        item["blockers"] == [EvidenceBlocker.OPEN_QUESTIONS_PRESENT.value]
        for item in decision.split_items
    )


def test_split_items_respect_global_search_not_performed() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-SEARCH-1"),
            _split_candidate("ISSUE-SYNTH-SEARCH-2"),
        ]
    )

    decision = decide_kcs_action(
        evidence,
        _reuse_results(searched=False, blockers=["search_unavailable"]),
    )

    assert decision.recommended_action == RecommendedAction.SPLIT_REQUIRED.value
    assert all(
        item["recommended_action"] == RecommendedAction.BLOCKED.value
        for item in decision.split_items
    )
    assert all(
        item["reuse_search_status"] == "missing" for item in decision.split_items
    )
    assert all(
        item["blockers"]
        == [
            DecisionBlocker.REUSE_SEARCH_STATUS_MISSING.value,
            "search_unavailable",
        ]
        for item in decision.split_items
    )


def test_split_items_do_not_echo_reuse_match_identity_values() -> None:
    private_path = "/Users/example/private-path"
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-SAFE"),
            _split_candidate("ISSUE-SYNTH-OTHER"),
        ]
    )
    unsafe_match = {
        "candidate_id": "ISSUE-SYNTH-SAFE",
        "match_ref": "KB-SYNTH-SAFE",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": private_path,
            "resolution_or_answer": "Synthetic resolution for ISSUE-SYNTH-SAFE.",
        },
        "content_status": "partial",
    }

    decision = decide_kcs_action(evidence, _reuse_results(matches=[unsafe_match]))

    assert private_path not in repr(decision.to_json_dict())


def test_internal_only_solution_blocks_public_candidate() -> None:
    evidence = _evidence(
        visibility_summary={
            "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
            "internal_only_evidence_approved": True,
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [DecisionBlocker.INTERNAL_ONLY_SOLUTION.value]


def test_no_reusable_match_creates_candidate() -> None:
    decision = decide_kcs_action(_evidence(), _reuse_results())

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_unsafe_or_not_ready_evidence_blocks() -> None:
    evidence = _evidence(symptoms=["Contact person@example.com for details."])

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [EvidenceBlocker.UNSAFE_INPUT.value]


def test_unsafe_input_takes_priority_over_multi_issue() -> None:
    evidence = _evidence(
        symptoms=["Contact person@example.com for details."],
        issue_candidates=[
            {"candidate_id": "ISSUE-SYNTH-1", "atomic": True},
            {"candidate_id": "ISSUE-SYNTH-2", "atomic": True},
        ],
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [
        EvidenceBlocker.UNSAFE_INPUT.value,
        EvidenceBlocker.MULTI_ISSUE.value,
    ]


def test_decision_does_not_mutate_inputs_and_serializes() -> None:
    evidence = _evidence()
    reuse_results = _reuse_results(matches=[_technical_match("outdated")])
    evidence_before = evidence.to_json_dict()
    reuse_before = reuse_results.to_json_dict()

    decision = decide_kcs_action(evidence, reuse_results)

    assert evidence.to_json_dict() == evidence_before
    assert reuse_results.to_json_dict() == reuse_before
    assert KcsActionDecisionPacket.from_json_dict(decision.to_json_dict()) == decision
    assert decision.auto_publish_allowed is False


def test_decision_api_is_exported_from_package() -> None:
    assert kcs_core.DecisionBlocker.INTERNAL_ONLY_SOLUTION.value == (
        "internal_only_solution"
    )
    assert kcs_core.decide_kcs_action is decide_kcs_action
