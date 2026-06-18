from __future__ import annotations

import pytest

import kcs_core
from kcs_core.decision import decide_kcs_action
from kcs_core.errors import ContractValidationError
from kcs_core.models import (
    ArticleType,
    DecisionStatus,
    KcsActionDecisionPacket,
    KcsReviewerPacket,
    NormalizedTicketEvidencePacket,
    RecommendedAction,
    ReuseSearchResultsPacket,
)
from kcs_core.renderer import render_reviewer_packet
from kcs_core.safety import EvidenceVisibility, InputClass


def _evidence(**overrides: object) -> NormalizedTicketEvidencePacket:
    values = {
        "case_ref": "CASE-SYNTH-RENDER",
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "source_refs": ["SRC-SYNTH-RENDER"],
        "issue_candidates": [
            {
                "candidate_id": "ISSUE-SYNTH-RENDER",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk mail task fails: safe queue error",
                "summary": "Mail delivery returns a safe queue error.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "resolution_steps": [
                    "Log in to Plesk.",
                    "Go to Mail > Mail Settings.",
                    "Enable the required mail setting.",
                ],
                "internal_reviewer_notes": [
                    "Reviewer-only sanitized implementation note."
                ],
            }
        ],
        "environment": {
            "product": "Plesk",
            "platform": "Linux",
            "component": "Mail",
        },
        "symptoms": ["Mail delivery returns a safe queue error."],
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


def _decision(
    action: RecommendedAction = RecommendedAction.CREATE_CANDIDATE,
    article_type: ArticleType = ArticleType.TECHNICAL_SCR,
    **overrides: object,
) -> KcsActionDecisionPacket:
    values = {
        "candidate_id": "ISSUE-SYNTH-RENDER",
        "recommended_action": action.value,
        "article_type": article_type.value,
        "confidence": 0.6,
        "blockers": [],
        "evidence_basis": {
            "case_ref": "CASE-SYNTH-RENDER",
            "source_refs": ["SRC-SYNTH-RENDER"],
            "article_type": article_type.value,
            "identity_rule": "article_type_cause_resolution",
        },
        "selected_reuse_match": None,
        "status": DecisionStatus.DECISION_READY.value,
        "auto_publish_allowed": False,
    }
    values.update(overrides)
    return KcsActionDecisionPacket(**values)


def _selected_match(**overrides: object) -> dict[str, object]:
    values = {
        "match_ref": "KB-SYNTH-RENDER",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "content_status": "incomplete",
        "publication_status": "public",
    }
    values.update(overrides)
    return values


def _reuse_results(**overrides: object) -> ReuseSearchResultsPacket:
    values = {
        "search_run_ref": "SEARCH-SYNTH-RENDER",
        "searched": True,
        "search_source": "synthetic_fixture",
        "matches": [],
        "blockers": [],
    }
    values.update(overrides)
    return ReuseSearchResultsPacket(**values)


def _reuse_match(
    content_status: str = "complete", **overrides: object
) -> dict[str, object]:
    values = {
        "match_ref": "KB-SYNTH-RENDER",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "identity": {
            "cause": "A required mail setting is disabled.",
            "resolution_or_answer": "Enable the required mail setting.",
        },
        "content_status": content_status,
    }
    values.update(overrides)
    return values


def test_create_candidate_renders_reviewer_packet_and_zendesk_html() -> None:
    packet = render_reviewer_packet(_evidence(), _decision())

    payload = packet.to_json_dict()
    assert packet.schema_version == KcsReviewerPacket.SCHEMA_VERSION
    assert payload["schema_version"] == KcsReviewerPacket.SCHEMA_VERSION
    assert packet.recommended_action == RecommendedAction.CREATE_CANDIDATE.value
    assert packet.review_required is True
    assert packet.auto_publish_allowed is False
    assert packet.public_article_candidate is not None
    assert packet.zendesk_source_html is not None
    assert (
        "<h1>Plesk mail task fails: safe queue error</h1>"
        in packet.zendesk_source_html
    )
    assert (
        "Reviewer-only sanitized implementation note."
        not in packet.zendesk_source_html
    )
    assert KcsReviewerPacket.from_json_dict(payload).to_json_dict() == payload


def test_update_and_flag_existing_render_zendesk_html() -> None:
    for action in (
        RecommendedAction.UPDATE_EXISTING,
        RecommendedAction.FLAG_EXISTING,
    ):
        packet = render_reviewer_packet(
            _evidence(),
            _decision(action=action, selected_reuse_match=_selected_match()),
        )

        assert packet.public_article_candidate is not None
        assert packet.zendesk_source_html is not None
        assert packet.recommended_action == action.value
        assert packet.auto_publish_allowed is False


@pytest.mark.parametrize(
    ("matches", "expected_action", "expects_html"),
    [
        ([], RecommendedAction.CREATE_CANDIDATE, True),
        ([_reuse_match("complete")], RecommendedAction.REUSE_EXISTING, False),
        (
            [_reuse_match("incomplete", publication_status="internal")],
            RecommendedAction.UPDATE_EXISTING,
            True,
        ),
        (
            [_reuse_match("incomplete", publication_status="public")],
            RecommendedAction.FLAG_EXISTING,
            True,
        ),
    ],
)
def test_decide_then_render_pipeline_paths(
    matches: list[dict[str, object]],
    expected_action: RecommendedAction,
    expects_html: bool,
) -> None:
    evidence = _evidence()
    decision = decide_kcs_action(evidence, _reuse_results(matches=matches))

    packet = render_reviewer_packet(evidence, decision)

    assert packet.recommended_action == expected_action.value
    assert (packet.zendesk_source_html is not None) is expects_html
    assert packet.auto_publish_allowed is False


def test_flag_existing_article_candidate_is_labeled_as_flag_existing() -> None:
    packet = render_reviewer_packet(
        _evidence(),
        _decision(
            action=RecommendedAction.FLAG_EXISTING,
            selected_reuse_match=_selected_match(),
        ),
    )

    assert packet.public_article_candidate is not None
    assert (
        packet.public_article_candidate["recommended_action"]
        == RecommendedAction.FLAG_EXISTING.value
    )
    assert (
        packet.public_article_candidate["status"]
        == DecisionStatus.DECISION_READY.value
    )
    assert "selected_reuse_match" not in packet.public_article_candidate
    assert packet.validation_report["renderer_status"] == (
        "flag_existing_review_required"
    )
    assert packet.validation_report["warnings"] == [
        "flag_existing_requires_existing_article_review"
    ]
    assert packet.validation_report["selected_reuse_match"] == _selected_match()
    assert packet.zendesk_source_html is not None
    assert "flag_existing_requires_existing_article_review" not in (
        packet.zendesk_source_html
    )


def test_technical_scr_html_uses_kcs_section_shape() -> None:
    html = render_reviewer_packet(_evidence(), _decision()).zendesk_source_html

    assert html is not None
    assert "<h2>Applicable to</h2>" in html
    assert "<h2>Symptoms</h2>" in html
    assert "<ol>" in html
    assert "<h2>Cause</h2>" in html
    assert '<div class="resolution">' in html
    assert "<h2>Resolution</h2>" in html
    assert "<h2>Issue</h2>" not in html
    assert "<h2>Environment</h2>" not in html
    assert "<h3>Step 1" not in html
    assert "<pre><code>" not in html


def test_resolution_steps_are_ordered_inside_resolution_container() -> None:
    html = render_reviewer_packet(_evidence(), _decision()).zendesk_source_html

    assert html is not None
    assert '<div class="resolution">\n  <ol>' in html
    assert "<li>Log in to Plesk.</li>" in html
    assert "<li>Go to Mail &gt; Mail Settings.</li>" in html
    assert "<li>Enable the required mail setting.</li>" in html


def test_linux_plesk_resolution_starts_with_ssh_entry_point() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-RENDER",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk monitoring graphs show no data",
                "summary": "Monitoring graphs show no data.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "resolution_steps": [
                    "Disable the custom collectd configuration.",
                    "Restart sw-collectd.",
                ],
            }
        ],
        supported_cause="A custom collectd configuration overrides the data path.",
        supported_resolution_or_workaround=(
            "Disable the custom collectd configuration and restart sw-collectd."
        ),
        symptoms=["Monitoring graphs show no data."],
    )

    packet = render_reviewer_packet(evidence, _decision())

    assert packet.public_article_candidate is not None
    assert packet.public_article_candidate["resolution_steps"] == [
        "Connect to the Plesk server via SSH.",
        "Disable the custom collectd configuration.",
        "Restart sw-collectd.",
    ]
    assert packet.zendesk_source_html is not None
    assert (
        '<li><a href="https://support.plesk.com/hc/en-us/articles/'
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in packet.zendesk_source_html
    )
    assert "<li>Plesk for Linux</li>" in packet.zendesk_source_html


def test_rpm_based_plesk_resolution_uses_linux_applicable_to_and_ssh() -> None:
    evidence = _evidence(
        environment={
            "product": "Plesk with Advanced Monitoring extension",
            "platform": "RPM-based",
            "component": "Grafana / sw-collectd",
        },
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-RENDER",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk monitoring graphs show no data",
                "summary": "Monitoring graphs show no data.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "resolution_steps": [
                    "Disable the custom collectd configuration.",
                    "Restart sw-collectd.",
                ],
            }
        ],
        supported_cause="A custom collectd configuration overrides the data path.",
        supported_resolution_or_workaround=(
            "Disable the custom collectd configuration and restart sw-collectd."
        ),
        symptoms=["Monitoring graphs show no data."],
    )

    packet = render_reviewer_packet(evidence, _decision())

    assert packet.public_article_candidate is not None
    assert packet.public_article_candidate["applicable_to"] == ["Plesk for Linux"]
    assert packet.public_article_candidate["resolution_steps"][0] == (
        "Connect to the Plesk server via SSH."
    )
    assert packet.zendesk_source_html is not None
    assert "<li>Plesk for Linux</li>" in packet.zendesk_source_html
    assert (
        '12377512781975-How-to-connect-to-a-Plesk-server-via-SSH">'
        "Connect to the Plesk server via SSH.</a></li>"
        in packet.zendesk_source_html
    )


def test_windows_resolution_starts_with_rdp_entry_point_link() -> None:
    evidence = _evidence(
        environment={
            "product": "Plesk",
            "platform": "Windows",
            "component": "Mail",
        },
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-RENDER",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk mail task fails on Windows",
                "summary": "Mail delivery returns a safe queue error.",
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "solved",
                "public_solution_safe": True,
                "resolution_steps": [
                    "Open cmd as Administrator.",
                    "Run plesk repair mail.",
                ],
            }
        ],
        supported_cause="A required mail setting is disabled.",
        supported_resolution_or_workaround="Repair the Plesk mail configuration.",
        symptoms=["Mail delivery returns a safe queue error."],
    )

    packet = render_reviewer_packet(evidence, _decision())

    assert packet.public_article_candidate is not None
    assert packet.public_article_candidate["resolution_steps"] == [
        "Connect to the Plesk server via RDP.",
        "Open cmd as Administrator.",
        "Run plesk repair mail.",
    ]
    assert packet.zendesk_source_html is not None
    assert (
        '<li><a href="https://support.plesk.com/hc/en-us/articles/'
        "12377247797271-How-to-connect-to-a-Plesk-server-via-RDP-with-available-"
        'credentials">Connect to the Plesk server via RDP.</a></li>'
        in packet.zendesk_source_html
    )
    assert "<li>Plesk for Windows</li>" in packet.zendesk_source_html


def test_howto_qa_renders_question_and_answer_sections() -> None:
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround="Change the PHP version in Plesk.",
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO",
                "article_type": ArticleType.HOWTO_QA.value,
                "title": "How to change PHP version in Plesk",
                "question": "How to change PHP version in Plesk?",
                "answer_steps": [
                    "Log in to Plesk.",
                    "Open Domains > example.com > Hosting Settings.",
                    "Select the required PHP version.",
                ],
                "atomic": True,
                "customer_reported": True,
                "kcs_applicable": True,
                "resolution_state": "answered",
                "public_solution_safe": True,
            }
        ],
    )

    packet = render_reviewer_packet(
        evidence,
        _decision(article_type=ArticleType.HOWTO_QA, candidate_id="ISSUE-SYNTH-HOWTO"),
    )

    assert packet.zendesk_source_html is not None
    assert "<h2>Question</h2>" in packet.zendesk_source_html
    assert "<h2>Answer</h2>" in packet.zendesk_source_html
    assert "<h2>Symptoms</h2>" not in packet.zendesk_source_html
    assert (
        "Domains &gt; example.com &gt; Hosting Settings"
        in packet.zendesk_source_html
    )


def test_internal_notes_are_separated_from_public_html() -> None:
    packet = render_reviewer_packet(_evidence(), _decision())

    assert packet.internal_reviewer_notes == [
        "Reviewer-only sanitized implementation note."
    ]
    assert packet.public_article_candidate is not None
    assert "Reviewer-only sanitized implementation note." not in repr(
        packet.public_article_candidate
    )
    assert packet.zendesk_source_html is not None
    assert (
        "Reviewer-only sanitized implementation note."
        not in packet.zendesk_source_html
    )


def test_renderer_escapes_html_sensitive_evidence_values() -> None:
    evidence = _evidence(
        symptoms=["Task fails with <script>alert(1)</script>."],
        supported_cause="A setting contains <unsafe> characters.",
        supported_resolution_or_workaround="Set value to A & B.",
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-ESCAPE",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk task fails: <unsafe>",
                "summary": "Task fails with <script>alert(1)</script>.",
                "public_solution_safe": True,
                "resolution_steps": ["Set value to A & B."],
            }
        ],
    )

    html = render_reviewer_packet(
        evidence,
        _decision(candidate_id="ISSUE-SYNTH-ESCAPE"),
    ).zendesk_source_html

    assert html is not None
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A &amp; B" in html
    assert "Plesk task fails: &lt;unsafe&gt;" in html


def test_howto_escapes_question_and_single_answer_paths() -> None:
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround="Set A & B <unsafe>.",
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-HOWTO-ESCAPE",
                "article_type": ArticleType.HOWTO_QA.value,
                "title": "How to configure safe value",
                "question": "How to set <unsafe> value?",
                "public_solution_safe": True,
                "answer_steps": ["Set A & B <unsafe>."],
            }
        ],
    )

    html = render_reviewer_packet(
        evidence,
        _decision(
            article_type=ArticleType.HOWTO_QA,
            candidate_id="ISSUE-SYNTH-HOWTO-ESCAPE",
        ),
    ).zendesk_source_html

    assert html is not None
    assert "How to set &lt;unsafe&gt; value?" in html
    assert "Set A &amp; B &lt;unsafe&gt;." in html
    assert "<unsafe>" not in html


@pytest.mark.parametrize(
    ("field_name", "private_value"),
    [
        ("title", "Customer domain customer.example.net fails"),
        ("summary", "Task fails for admin@example.net."),
        ("supported_cause", "Server uses PLSK.12345678.1234."),
        ("resolution_steps", "Run command for ticket-123456."),
        ("answer_steps", "Use token-abc123."),
    ],
)
def test_public_article_text_rejects_private_values_without_echo(
    field_name: str, private_value: str
) -> None:
    candidate = {
        "candidate_id": "ISSUE-SYNTH-PRIVATE-TEXT",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "title": "Plesk task fails: public text safety",
        "summary": "Task fails with a public-safe error.",
        "public_solution_safe": True,
        "resolution_steps": ["Apply a public-safe resolution."],
    }
    if field_name in {"resolution_steps", "answer_steps"}:
        candidate[field_name] = [private_value]
    else:
        candidate[field_name] = private_value

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(issue_candidates=[candidate]),
            _decision(candidate_id="ISSUE-SYNTH-PRIVATE-TEXT"),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "filename",
    [
        "setup.php",
        "service.log",
        "application.ini",
        "worker-process.pid",
        "service.conf",
        "02component-feature.conf",
        "settings.yaml",
        "metadata.json",
    ],
)
def test_public_article_text_allows_standalone_safe_filenames(
    filename: str,
) -> None:
    candidate = {
        "candidate_id": "ISSUE-SYNTH-SAFE-FILENAME",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "title": "Product task fails with reusable symptom",
        "summary": f"Diagnostic evidence references {filename}.",
        "public_solution_safe": True,
        "resolution_steps": [f"Review the standalone filename {filename}."],
    }

    packet = render_reviewer_packet(
        _evidence(issue_candidates=[candidate]),
        _decision(candidate_id="ISSUE-SYNTH-SAFE-FILENAME"),
    )

    assert packet.public_article_candidate is not None
    assert packet.auto_publish_allowed is False


@pytest.mark.parametrize(
    "private_value",
    [
        "Open customer.example.net/index.php.",
        "Open https://customer.example.net/index.php.",
    ],
)
def test_public_article_text_filename_allowlist_does_not_allow_domains(
    private_value: str,
) -> None:
    candidate = {
        "candidate_id": "ISSUE-SYNTH-UNSAFE-FILENAME",
        "article_type": ArticleType.TECHNICAL_SCR.value,
        "title": "Product task fails with reusable symptom",
        "summary": private_value,
        "public_solution_safe": True,
        "resolution_steps": ["Apply a public-safe resolution."],
    }

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(issue_candidates=[candidate]),
            _decision(candidate_id="ISSUE-SYNTH-UNSAFE-FILENAME"),
        )

    assert private_value not in str(captured.value)


def test_renderer_rejects_unbounded_title_without_echoing_value() -> None:
    long_title = "x" * 181
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-LONG",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": long_title,
                "summary": "Bounded summary.",
                "public_solution_safe": True,
                "resolution_steps": ["Bounded step."],
            }
        ],
    )

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(evidence, _decision(candidate_id="ISSUE-SYNTH-LONG"))

    assert "title exceeds bound" in str(captured.value)
    assert long_title not in str(captured.value)


def test_renderer_rejects_too_many_list_items() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-MANY-STEPS",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk task fails: bounded item count",
                "summary": "Bounded summary.",
                "public_solution_safe": True,
                "resolution_steps": [f"Bounded step {index}." for index in range(21)],
            }
        ],
    )

    with pytest.raises(ContractValidationError, match="list item count"):
        render_reviewer_packet(
            evidence,
            _decision(candidate_id="ISSUE-SYNTH-MANY-STEPS"),
        )


def test_renderer_rejects_unbounded_list_item_without_echoing_value() -> None:
    long_item = "x" * 601
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-LONG-ITEM",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk task fails: bounded item length",
                "summary": "Bounded summary.",
                "public_solution_safe": True,
                "resolution_steps": [long_item],
            }
        ],
    )

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            evidence,
            _decision(candidate_id="ISSUE-SYNTH-LONG-ITEM"),
        )

    assert "list item exceeds bound" in str(captured.value)
    assert long_item not in str(captured.value)


def test_renderer_rejects_unbounded_cause_without_echoing_value() -> None:
    long_cause = "x" * 601
    evidence = _evidence(supported_cause=long_cause)

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(evidence, _decision())

    assert "cause exceeds bound" in str(captured.value)
    assert long_cause not in str(captured.value)


def test_renderer_rejects_unbounded_question_without_echoing_value() -> None:
    long_question = "x" * 601
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround="Bounded answer.",
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-LONG-QUESTION",
                "article_type": ArticleType.HOWTO_QA.value,
                "title": "How to configure a bounded setting",
                "question": long_question,
                "public_solution_safe": True,
                "answer_steps": ["Bounded answer."],
            }
        ],
    )

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            evidence,
            _decision(
                article_type=ArticleType.HOWTO_QA,
                candidate_id="ISSUE-SYNTH-LONG-QUESTION",
            ),
        )

    assert "question exceeds bound" in str(captured.value)
    assert long_question not in str(captured.value)


def test_renderer_rejects_unbounded_single_answer_without_echoing_value() -> None:
    long_answer = "x" * 601
    evidence = _evidence(
        supported_cause=None,
        supported_resolution_or_workaround=long_answer,
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-LONG-ANSWER",
                "article_type": ArticleType.HOWTO_QA.value,
                "title": "How to configure a bounded answer",
                "question": "How to configure the bounded answer?",
                "public_solution_safe": True,
                "answer_steps": [long_answer],
            }
        ],
    )

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            evidence,
            _decision(
                article_type=ArticleType.HOWTO_QA,
                candidate_id="ISSUE-SYNTH-LONG-ANSWER",
            ),
        )

    assert "answer exceeds bound" in str(captured.value)
    assert long_answer not in str(captured.value)


def test_renderer_rejects_decision_with_auto_publish_allowed_true() -> None:
    decision = _decision()
    object.__setattr__(decision, "auto_publish_allowed", True)

    with pytest.raises(ContractValidationError, match="auto_publish_allowed"):
        render_reviewer_packet(_evidence(), decision)


def test_article_ready_action_rejects_blocked_decision() -> None:
    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(
                status=DecisionStatus.BLOCKED.value,
                blockers=["unsafe_input"],
            ),
        )

    assert "decision_ready" in str(captured.value)
    assert "unsafe_input" not in str(captured.value)


def test_article_ready_action_rejects_decision_with_blockers() -> None:
    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(blockers=["open_questions_present"]),
        )

    assert "empty decision blockers" in str(captured.value)
    assert "open_questions_present" not in str(captured.value)


def test_create_candidate_requires_public_customer_safe_visibility() -> None:
    for visibility_summary in (
        {"classes": [EvidenceVisibility.CUSTOMER_CONTEXT_ONLY.value]},
        {
            "classes": [EvidenceVisibility.INTERNAL_REVIEWER_ONLY.value],
            "internal_only_evidence_approved": True,
        },
        {
            "classes": [
                EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value,
                EvidenceVisibility.CUSTOMER_CONTEXT_ONLY.value,
            ],
        },
    ):
        with pytest.raises(ContractValidationError, match="public_customer_safe"):
            render_reviewer_packet(
                _evidence(visibility_summary=visibility_summary),
                _decision(),
            )


def test_public_solution_safe_false_does_not_render_public_html() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-INTERNAL",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Internal-only workaround",
                "summary": "Safe-looking symptom.",
                "public_solution_safe": False,
                "resolution_steps": ["Use an internal-only workaround."],
            }
        ]
    )

    with pytest.raises(ContractValidationError, match="public_solution_safe"):
        render_reviewer_packet(
            evidence,
            _decision(candidate_id="ISSUE-SYNTH-INTERNAL"),
        )


def test_update_existing_requires_selected_reuse_match() -> None:
    with pytest.raises(ContractValidationError, match="selected reuse match"):
        render_reviewer_packet(
            _evidence(),
            _decision(action=RecommendedAction.UPDATE_EXISTING),
        )


def test_flag_existing_requires_selected_reuse_match() -> None:
    with pytest.raises(ContractValidationError, match="selected reuse match"):
        render_reviewer_packet(
            _evidence(),
            _decision(action=RecommendedAction.FLAG_EXISTING),
        )


def test_selected_reuse_match_sensitive_values_not_echoed() -> None:
    private_value = "/private/raw_ticket"

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(
                action=RecommendedAction.UPDATE_EXISTING,
                selected_reuse_match={
                    "match_ref": private_value,
                    "article_type": ArticleType.TECHNICAL_SCR.value,
                    "content_status": "incomplete",
                },
            ),
        )

    assert private_value not in str(captured.value)


def test_selected_reuse_match_license_id_not_echoed() -> None:
    private_value = "PLSK.12345678.1234"

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(
                action=RecommendedAction.UPDATE_EXISTING,
                selected_reuse_match=_selected_match(match_ref=private_value),
            ),
        )

    assert private_value not in str(captured.value)


def test_evidence_basis_sensitive_values_not_echoed() -> None:
    private_value = "/private/raw_ticket"

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(evidence_basis={"source_refs": [private_value]}),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "private_value",
    [
        "PLSK.12345678.1234",
        "ZD123456",
        "ticket-123456",
        "customer.example.com",
        "api_key:abc123",
    ],
)
def test_evidence_basis_private_identifier_values_rejected(
    private_value: str,
) -> None:
    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(evidence_basis={"source_refs": [private_value]}),
        )

    assert private_value not in str(captured.value)


def test_evidence_basis_rejects_unbounded_metadata_without_echo() -> None:
    private_value = "x" * 181

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(evidence_basis={"source_refs": [private_value]}),
        )

    assert private_value not in str(captured.value)


@pytest.mark.parametrize(
    "payload",
    [
        {True: "SRC-SYNTH"},
        {"raw_ticket": "SRC-SYNTH"},
        {"internal_comment": "SRC-SYNTH"},
        {"api_key": "SRC-SYNTH"},
        {"token": "SRC-SYNTH"},
        {"source_refs": [123456789]},
        {"source_refs": [float("nan")]},
        {"source_refs": [float("inf")]},
        {"source_refs": ["token-abc123"]},
        {"source_refs": ["secret-abc123"]},
        {"source_refs": ["api-key-abc123"]},
    ],
)
def test_evidence_basis_rejects_unsafe_metadata_shapes(
    payload: dict[object, object],
) -> None:
    with pytest.raises(ContractValidationError):
        render_reviewer_packet(
            _evidence(),
            _decision(evidence_basis=payload),  # type: ignore[arg-type]
        )


def test_non_article_decision_rejects_unsafe_blocker_value_without_echo() -> None:
    private_value = "/private/raw_ticket"

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(
                action=RecommendedAction.BLOCKED,
                article_type=ArticleType.NONE,
                status=DecisionStatus.BLOCKED.value,
                blockers=[private_value],
            ),
        )

    assert private_value not in str(captured.value)


def test_non_article_decision_rejects_unbounded_blocker_without_echo() -> None:
    private_value = "x" * 81

    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(
                action=RecommendedAction.BLOCKED,
                article_type=ArticleType.NONE,
                status=DecisionStatus.BLOCKED.value,
                blockers=[private_value],
            ),
        )

    assert private_value not in str(captured.value)


def test_no_article_no_public_draft_even_with_candidate_text() -> None:
    packet = render_reviewer_packet(
        _evidence(),
        _decision(
            action=RecommendedAction.NO_ARTICLE,
            article_type=ArticleType.TECHNICAL_SCR,
        ),
    )

    assert packet.public_article_candidate is None
    assert packet.zendesk_source_html is None


def test_blocked_no_public_draft_even_with_candidate_text() -> None:
    packet = render_reviewer_packet(
        _evidence(),
        _decision(
            action=RecommendedAction.BLOCKED,
            article_type=ArticleType.TECHNICAL_SCR,
            status=DecisionStatus.BLOCKED.value,
            blockers=["missing_supported_resolution"],
        ),
    )

    assert packet.public_article_candidate is None
    assert packet.zendesk_source_html is None


def test_non_article_actions_do_not_render_public_html() -> None:
    for action in (
        RecommendedAction.REUSE_EXISTING,
        RecommendedAction.NO_ARTICLE,
        RecommendedAction.BLOCKED,
        RecommendedAction.SPLIT_REQUIRED,
    ):
        packet = render_reviewer_packet(
            _evidence(),
            _decision(
                action=action,
                article_type=(
                    ArticleType.NONE
                    if action
                    in {
                        RecommendedAction.BLOCKED,
                        RecommendedAction.SPLIT_REQUIRED,
                    }
                    else ArticleType.TECHNICAL_SCR
                ),
                status=(
                    DecisionStatus.SPLIT_REQUIRED.value
                    if action == RecommendedAction.SPLIT_REQUIRED
                    else DecisionStatus.BLOCKED.value
                    if action == RecommendedAction.BLOCKED
                    else DecisionStatus.DECISION_READY.value
                ),
            ),
        )

        assert packet.public_article_candidate is None
        assert packet.zendesk_source_html is None
        assert packet.auto_publish_allowed is False


def test_article_ready_decision_rejects_unknown_candidate_id() -> None:
    with pytest.raises(ContractValidationError) as captured:
        render_reviewer_packet(
            _evidence(),
            _decision(candidate_id="ISSUE-SYNTH-UNKNOWN"),
        )

    assert "candidate_id" in str(captured.value)
    assert "ISSUE-SYNTH-UNKNOWN" not in str(captured.value)


def test_article_ready_decision_rejects_case_ref_as_candidate_id() -> None:
    with pytest.raises(ContractValidationError):
        render_reviewer_packet(
            _evidence(),
            _decision(candidate_id="CASE-SYNTH-RENDER"),
        )


def test_split_required_does_not_render_combined_public_article() -> None:
    evidence = _evidence(
        issue_candidates=[
            {"candidate_id": "ISSUE-SYNTH-1", "summary": "First issue."},
            {"candidate_id": "ISSUE-SYNTH-2", "summary": "Second issue."},
        ],
    )
    decision = _decision(
        action=RecommendedAction.SPLIT_REQUIRED,
        article_type=ArticleType.NONE,
        candidate_id="CASE-SYNTH-RENDER",
        status=DecisionStatus.SPLIT_REQUIRED.value,
        split_items=[
            {
                "candidate_id": "ISSUE-SYNTH-1",
                "summary": "First issue.",
                "recommended_action": RecommendedAction.CREATE_CANDIDATE.value,
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "status": DecisionStatus.DECISION_READY.value,
                "blockers": [],
                "evidence_basis": {},
                "reuse_search_status": "checked",
                "auto_publish_allowed": False,
                "operator_override_allowed": False,
                "allowed_override_modes": [],
                "override_status": "not_requested",
            }
        ],
    )

    packet = render_reviewer_packet(evidence, decision)

    assert packet.public_article_candidate is None
    assert packet.zendesk_source_html is None
    assert packet.validation_report["renderer_status"] == "split_required"


def test_split_selected_item_renders_only_selected_candidate() -> None:
    evidence = _evidence(
        issue_candidates=[
            {
                "candidate_id": "ISSUE-SYNTH-1",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk first task fails: selected issue",
                "summary": "Selected issue symptom.",
                "supported_cause": "Selected issue cause.",
                "public_solution_safe": True,
                "resolution_steps": ["Apply the selected issue resolution."],
            },
            {
                "candidate_id": "ISSUE-SYNTH-2",
                "article_type": ArticleType.TECHNICAL_SCR.value,
                "title": "Plesk second task fails: non-selected issue",
                "summary": "Non-selected issue symptom.",
                "supported_cause": "Non-selected issue cause.",
                "public_solution_safe": True,
                "resolution_steps": ["Apply the non-selected issue resolution."],
            },
        ],
    )

    packet = render_reviewer_packet(
        evidence,
        _decision(candidate_id="ISSUE-SYNTH-1"),
    )
    serialized = repr(packet.to_json_dict())

    assert packet.public_article_candidate is not None
    assert "selected issue" in serialized
    assert "non-selected issue" not in serialized


def test_renderer_api_is_exported_from_package_root() -> None:
    assert kcs_core.render_reviewer_packet is render_reviewer_packet
