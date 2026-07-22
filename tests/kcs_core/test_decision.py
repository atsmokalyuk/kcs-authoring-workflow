from __future__ import annotations

import kcs_core
from kcs_core.decision import DecisionBlocker, decide_kcs_action
from kcs_core.models import (
    ArticleType,
    CandidateOrigin,
    DecisionStatus,
    KcsActionDecisionPacket,
    NormalizedTicketEvidencePacket,
    OperatorOverrideMode,
    OverrideStatus,
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


def _technical_match(
    content_status: str = "complete", **overrides: object
) -> dict[str, object]:
    values = {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": content_status,
    }
    values.update(overrides)
    return values


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


def _split_match(
    candidate_id: str, content_status: str, **overrides: object
) -> dict[str, object]:
    values = {
        "candidate_id": candidate_id,
        "match_ref": f"KB-SYNTH-{candidate_id}",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": f"Synthetic cause for {candidate_id}.",
            "resolution_or_answer": f"Synthetic resolution for {candidate_id}.",
        },
        "content_status": content_status,
    }
    values.update(overrides)
    return values


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
    assert decision.status == DecisionStatus.DECISION_READY.value
    assert decision.operator_override_allowed is True
    assert decision.allowed_override_modes == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]
    assert decision.override_status == OverrideStatus.NOT_REQUESTED.value


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


def test_public_same_identity_with_missing_content_flags_existing() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(
            matches=[
                _technical_match(
                    "incomplete",
                    publication_status="public",
                )
            ]
        ),
    )
    payload = decision.to_json_dict()

    assert decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    assert decision.selected_reuse_match == {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "incomplete",
        "publication_status": "public",
    }
    assert "public_article_candidate" not in payload
    assert "zendesk_source_html" not in payload
    assert decision.auto_publish_allowed is False


def test_internal_same_identity_with_missing_content_updates_existing() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(
            matches=[
                _technical_match(
                    "incomplete",
                    publication_status="internal",
                )
            ]
        ),
    )

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert decision.selected_reuse_match == {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "incomplete",
        "publication_status": "internal",
    }
    assert decision.auto_publish_allowed is False


def test_published_same_identity_with_missing_content_flags_existing() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(
            matches=[
                _technical_match(
                    "outdated",
                    publication_status="published",
                )
            ]
        ),
    )

    assert decision.recommended_action == RecommendedAction.FLAG_EXISTING.value
    assert decision.selected_reuse_match == {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "outdated",
        "publication_status": "published",
    }
    assert decision.auto_publish_allowed is False


def test_not_public_same_identity_with_missing_content_updates_existing() -> None:
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(
            matches=[
                _technical_match(
                    "partial",
                    publication_status="not_public",
                )
            ]
        ),
    )

    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert decision.selected_reuse_match == {
        "match_ref": "KB-SYNTH-MAIL-SETTING",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "partial",
        "publication_status": "not_public",
    }
    assert decision.auto_publish_allowed is False


def test_technical_identity_ignores_cli_gui_variant_metadata() -> None:
    match = _technical_match()
    match["identity"]["interface"] = "cli"

    decision = decide_kcs_action(_evidence(), _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


def test_technical_identity_uses_canonical_solution_key_for_delivery_variants() -> None:
    candidate = dict(_evidence().issue_candidates[0])
    candidate["solution_key"] = "enable_required_mail_setting"
    evidence = _evidence(
        issue_candidates=[candidate],
        supported_resolution_or_workaround=(
            "GUI: Enable the required mail setting in product settings."
        ),
    )
    match = _technical_match(
        identity={
            "cause": "A required mail setting is disabled.",
            "solution_key": "enable_required_mail_setting",
            "resolution_or_answer": (
                "CLI: Run the product command to enable the required mail setting."
            ),
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value
    assert decision.selected_reuse_match["match_ref"] == "KB-SYNTH-MAIL-SETTING"


def test_technical_identity_uses_canonical_cause_key() -> None:
    candidate = dict(_evidence().issue_candidates[0])
    candidate["cause_key"] = "mail_setting_disabled"
    evidence = _evidence(
        issue_candidates=[candidate],
        supported_cause="Customer-facing wording for the disabled mail setting.",
    )
    match = _technical_match(
        identity={
            "cause_key": "mail_setting_disabled",
            "cause": "Different wording for the same supported cause.",
            "resolution_or_answer": "Enable the required mail setting.",
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


def test_technical_identity_normalizes_explicit_delivery_variant_labels() -> None:
    evidence = _evidence(
        supported_resolution_or_workaround="GUI: Enable the required mail setting."
    )
    match = _technical_match(
        identity={
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "CLI: enable the required mail setting.",
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


def test_technical_identity_does_not_merge_different_delivery_solutions() -> None:
    evidence = _evidence(
        supported_resolution_or_workaround="GUI: Enable the required mail setting."
    )
    match = _technical_match(
        identity={
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "CLI: Disable the required mail setting.",
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_technical_identity_does_not_remove_delivery_words_inside_solution() -> None:
    evidence = _evidence(
        supported_resolution_or_workaround="Open shell access for the safe task."
    )
    match = _technical_match(
        identity={
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Open access for the safe task.",
        }
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_howto_identity_ignores_cli_gui_variant_metadata() -> None:
    answer = "Change the PHP version in the domain settings."
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround=answer,
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO",
                "article_type": ArticleType.HOWTO_QA.value,
                "question": "How to change PHP version?",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "answered",
                "public_solution_safe": True,
            }
        ],
    )
    match = {
        "match_ref": "KB-SYNTH-HOWTO-PHP",
        "article_type": ArticleType.HOWTO_QA.value,
        "identity": {
            "question": "How to change PHP version?",
            "resolution_or_answer": answer,
            "interface": "cli",
        },
        "content_status": "complete",
    }

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


def test_howto_identity_uses_canonical_answer_key_for_delivery_variants() -> None:
    answer = "GUI: Change the PHP version in the domain settings."
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround=answer,
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO",
                "article_type": ArticleType.HOWTO_QA.value,
                "question": "How to change PHP version?",
                "answer_key": "change_domain_php_version",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "answered",
                "public_solution_safe": True,
            }
        ],
    )
    match = {
        "match_ref": "KB-SYNTH-HOWTO-PHP",
        "article_type": ArticleType.HOWTO_QA.value,
        "identity": {
            "question": "How to change PHP version?",
            "answer_key": "change_domain_php_version",
            "resolution_or_answer": "CLI: Run the product command to change PHP.",
        },
        "content_status": "complete",
    }

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value
    assert decision.selected_reuse_match["match_ref"] == "KB-SYNTH-HOWTO-PHP"


def test_howto_identity_uses_canonical_question_key() -> None:
    answer = "Change the PHP version in the domain settings."
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround=answer,
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO",
                "article_type": ArticleType.HOWTO_QA.value,
                "question": "Customer-facing wording for PHP version change?",
                "question_key": "change_domain_php_version",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "answered",
                "public_solution_safe": True,
            }
        ],
    )
    match = {
        "match_ref": "KB-SYNTH-HOWTO-PHP",
        "article_type": ArticleType.HOWTO_QA.value,
        "identity": {
            "question_key": "change_domain_php_version",
            "question": "Different wording for the same how-to question?",
            "resolution_or_answer": answer,
        },
        "content_status": "complete",
    }

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


def test_howto_identity_normalizes_explicit_delivery_variant_labels() -> None:
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround=(
            "GUI: Change the PHP version in the domain settings."
        ),
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO",
                "article_type": ArticleType.HOWTO_QA.value,
                "question": "How to change PHP version?",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "answered",
                "public_solution_safe": True,
            }
        ],
    )
    match = {
        "match_ref": "KB-SYNTH-HOWTO-PHP",
        "article_type": ArticleType.HOWTO_QA.value,
        "identity": {
            "question": "How to change PHP version?",
            "resolution_or_answer": (
                "CLI: change the PHP version in the domain settings."
            ),
        },
        "content_status": "complete",
    }

    decision = decide_kcs_action(evidence, _reuse_results(matches=[match]))

    assert decision.recommended_action == RecommendedAction.REUSE_EXISTING.value


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
    assert decision.operator_override_allowed is True


def test_unrelated_incorrect_match_does_not_override_create_candidate() -> None:
    matches = [
        {
            "match_ref": "KB-SYNTH-PARTIAL",
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "identity": {
                "cause": "A required mail setting is disabled.",
                "resolution_or_answer": "Enable a different product setting.",
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


def test_top_level_decision_does_not_echo_sensitive_values() -> None:
    private_value = "/Users/example/private-path"
    unsafe_match = _technical_match()
    unsafe_match["match_ref"] = private_value
    unsafe_match["debug_identity_source"] = private_value

    match_decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[unsafe_match]),
    )
    blocker_decision = decide_kcs_action(
        _evidence(),
        _reuse_results(blockers=[private_value]),
    )
    evidence_basis_decision = decide_kcs_action(
        _evidence(source_refs=[private_value]),
        _reuse_results(),
    )

    for decision in (
        match_decision,
        blocker_decision,
        evidence_basis_decision,
    ):
        payload = decision.to_json_dict()
        assert private_value not in repr(payload)


def test_publication_status_does_not_echo_sensitive_values() -> None:
    private_value = "/Users/example/private-publication-marker"
    decision = decide_kcs_action(
        _evidence(),
        _reuse_results(
            matches=[
                _technical_match(
                    "incomplete",
                    publication_status=private_value,
                )
            ]
        ),
    )

    payload = decision.to_json_dict()
    assert decision.recommended_action == RecommendedAction.UPDATE_EXISTING.value
    assert "publication_status" not in decision.selected_reuse_match
    assert private_value not in repr(payload)


def test_no_search_blocks_possible_duplicate_not_checked() -> None:
    decision = decide_kcs_action(_evidence(), _reuse_results(searched=False))

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.article_type == ArticleType.NONE.value
    assert decision.status == DecisionStatus.BLOCKED.value
    assert decision.operator_override_allowed is False
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
    assert decision.operator_override_allowed is False


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
    assert decision.operator_override_allowed is True
    assert decision.allowed_override_modes == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]


def test_support_discovered_reusable_issue_remains_candidate_eligible() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-SUPPORT-DISCOVERED",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "atomic": True,
                "candidate_origin": CandidateOrigin.SUPPORT_DISCOVERED.value,
                "customer_reported": False,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
            }
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert DecisionBlocker.NO_CUSTOMER_REPORTED_ISSUE.value not in decision.blockers


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
    assert decision.status == DecisionStatus.SPLIT_REQUIRED.value
    assert decision.blockers == [EvidenceBlocker.MULTI_ISSUE.value]
    assert len(decision.split_items) == 2
    assert decision.operator_override_allowed is False
    assert decision.allowed_override_modes == []


def test_split_items_include_required_decision_card_fields() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-1"),
            _split_candidate("ISSUE-SYNTH-2"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    required_fields = {
        "candidate_id",
        "summary",
        "recommended_action",
        "article_type",
        "status",
        "blockers",
        "evidence_basis",
        "reuse_search_status",
        "auto_publish_allowed",
        "operator_override_allowed",
        "allowed_override_modes",
    }
    assert required_fields <= set(decision.split_items[0])
    assert all(item["auto_publish_allowed"] is False for item in decision.split_items)


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
    assert update_item["status"] == DecisionStatus.DECISION_READY.value
    assert update_item["blockers"] == []
    assert update_item["reuse_search_status"] == "checked"
    assert update_item["auto_publish_allowed"] is False
    assert update_item["operator_override_allowed"] is False
    assert update_item["allowed_override_modes"] == []
    assert update_item["override_status"] == OverrideStatus.NOT_REQUESTED.value


def test_public_split_item_with_missing_content_flags_existing() -> None:
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-PUBLIC-UPDATE"),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(
        evidence,
        _reuse_results(
            matches=[
                _split_match(
                    "ISSUE-SYNTH-PUBLIC-UPDATE",
                    "partial",
                    publication_status="public",
                )
            ]
        ),
    )

    update_item = decision.split_items[0]
    assert update_item["recommended_action"] == RecommendedAction.FLAG_EXISTING.value
    assert update_item["selected_reuse_match"] == {
        "match_ref": "KB-SYNTH-ISSUE-SYNTH-PUBLIC-UPDATE",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "partial",
        "publication_status": "public",
    }
    assert update_item["auto_publish_allowed"] is False


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
    assert reuse_item["operator_override_allowed"] is True
    assert reuse_item["allowed_override_modes"] == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]
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
    assert create_item["operator_override_allowed"] is False


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
            ),
            _split_candidate("ISSUE-SYNTH-CREATE"),
        ]
    )

    decision = decide_kcs_action(evidence, _reuse_results())

    no_article_item = decision.split_items[0]
    assert no_article_item["recommended_action"] == RecommendedAction.NO_ARTICLE.value
    assert no_article_item["blockers"] == [DecisionBlocker.THIRD_PARTY_ONLY.value]
    assert no_article_item["operator_override_allowed"] is True
    assert no_article_item["allowed_override_modes"] == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]


def test_split_item_no_article_does_not_bypass_missing_resolution() -> None:
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

    blocked_item = decision.split_items[0]
    assert blocked_item["recommended_action"] == RecommendedAction.BLOCKED.value
    assert blocked_item["blockers"] == [
        EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value
    ]
    assert blocked_item["operator_override_allowed"] is False
    assert blocked_item["allowed_override_modes"] == []


def test_override_metadata_preserves_original_recommended_action() -> None:
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
    assert decision.operator_override_allowed is True
    assert decision.override_status == OverrideStatus.NOT_REQUESTED.value


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
    assert blocked_item["status"] == DecisionStatus.BLOCKED.value
    assert blocked_item["blockers"] == [
        EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value
    ]
    assert blocked_item["operator_override_allowed"] is False
    assert blocked_item["allowed_override_modes"] == []


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
    assert blocked_item["operator_override_allowed"] is False


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


def test_split_items_do_not_echo_sensitive_publication_metadata() -> None:
    private_value = "/Users/example/private-article-visibility"
    evidence = _evidence(
        issue_candidates=[
            _split_candidate("ISSUE-SYNTH-SAFE"),
            _split_candidate("ISSUE-SYNTH-OTHER"),
        ]
    )
    unsafe_match = _split_match(
        "ISSUE-SYNTH-SAFE",
        "incomplete",
        article_visibility=private_value,
    )

    decision = decide_kcs_action(evidence, _reuse_results(matches=[unsafe_match]))

    assert decision.split_items[0]["recommended_action"] == (
        RecommendedAction.UPDATE_EXISTING.value
    )
    assert "publication_status" not in decision.split_items[0]["selected_reuse_match"]
    assert private_value not in repr(decision.to_json_dict())


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
    assert decision.operator_override_allowed is True
    assert decision.allowed_override_modes == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]
    assert decision.auto_publish_allowed is False


def test_public_solution_not_safe_allows_reviewer_only_override() -> None:
    candidate = dict(_evidence().issue_candidates[0])
    candidate["public_solution_safe"] = False

    decision = decide_kcs_action(
        _evidence(issue_candidates=[candidate]),
        _reuse_results(),
    )

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [DecisionBlocker.INTERNAL_ONLY_SOLUTION.value]
    assert decision.operator_override_allowed is True
    assert decision.allowed_override_modes == [
        OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value
    ]
    assert decision.auto_publish_allowed is False


def test_possible_duplicate_still_disallows_operator_override() -> None:
    decision = decide_kcs_action(_evidence(), _reuse_results(searched=False))

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [
        DecisionBlocker.POSSIBLE_DUPLICATE_NOT_CHECKED.value
    ]
    assert decision.operator_override_allowed is False
    assert decision.allowed_override_modes == []


def test_missing_supported_resolution_still_disallows_operator_override() -> None:
    decision = decide_kcs_action(
        _evidence(supported_resolution_or_workaround=None),
        _reuse_results(),
    )

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.blockers == [EvidenceBlocker.MISSING_SUPPORTED_RESOLUTION.value]
    assert decision.operator_override_allowed is False
    assert decision.allowed_override_modes == []


def test_no_reusable_match_creates_candidate() -> None:
    decision = decide_kcs_action(_evidence(), _reuse_results())

    assert decision.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert decision.selected_reuse_match is None


def test_create_and_update_decisions_include_non_empty_evidence_basis() -> None:
    create_decision = decide_kcs_action(_evidence(), _reuse_results())
    update_decision = decide_kcs_action(
        _evidence(),
        _reuse_results(matches=[_technical_match("incomplete")]),
    )

    for decision in (create_decision, update_decision):
        assert decision.recommended_action in {
            RecommendedAction.CREATE_CANDIDATE.value,
            RecommendedAction.UPDATE_EXISTING.value,
        }
        assert decision.evidence_basis["case_ref"] == "CASE-SYNTH-DECISION"
        assert decision.evidence_basis["source_refs"] == ["SRC-SYNTH-DECISION"]
        assert decision.evidence_basis["article_type"] == (
            ArticleType.TECHNICAL_SCR.value
        )
        assert decision.evidence_basis["identity_rule"] == (
            "article_type_cause_resolution"
        )


def test_unsafe_or_not_ready_evidence_blocks() -> None:
    evidence = _evidence(symptoms=["Contact person@example.com for details."])

    decision = decide_kcs_action(evidence, _reuse_results())

    assert decision.recommended_action == RecommendedAction.BLOCKED.value
    assert decision.status == DecisionStatus.BLOCKED.value
    assert decision.blockers == [EvidenceBlocker.UNSAFE_INPUT.value]
    assert decision.operator_override_allowed is False
    assert decision.allowed_override_modes == []


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
    assert decision.override_status == OverrideStatus.NOT_REQUESTED.value


def test_decision_api_is_exported_from_package() -> None:
    assert kcs_core.DecisionBlocker.INTERNAL_ONLY_SOLUTION.value == (
        "internal_only_solution"
    )
    assert kcs_core.DecisionStatus.BLOCKED.value == "blocked"
    assert kcs_core.OperatorOverrideMode.REVIEWER_ONLY_DRAFT.value == (
        "reviewer_only_draft"
    )
    assert kcs_core.decide_kcs_action is decide_kcs_action
