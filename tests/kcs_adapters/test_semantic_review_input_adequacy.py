from __future__ import annotations

from collections.abc import Callable, Mapping

import pytest

from kcs_adapters.desktop_semantic_review import (
    SEMANTIC_REVIEW_MAX_EXCERPTS,
    SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
    SemanticReviewError,
    _sentence_atoms,
    new_pending_semantic_review,
    selected_semantic_review_excerpts,
    semantic_review_excerpt_role_index,
)

_Fact = tuple[str, str, str]
_Representation = Callable[[tuple[_Fact, ...]], str]

_EXPECTED_FACTS: tuple[_Fact, ...] = (
    (
        "SYNTHETIC_S1",
        "reported_symptom",
        "Customer reports SYNTHETIC_S1: task alpha returns no result.",
    ),
    (
        "SYNTHETIC_C1",
        "supported_cause",
        "Support confirmed SYNTHETIC_C1: dependency alpha is inactive.",
    ),
    (
        "SYNTHETIC_R1",
        "supported_resolution",
        "Support ran SYNTHETIC_R1 to activate dependency alpha.",
    ),
    (
        "SYNTHETIC_V1",
        "confirmed_fact",
        "Support verified SYNTHETIC_V1: task alpha now returns a result.",
    ),
    (
        "SYNTHETIC_S2",
        "reported_symptom",
        "Customer reports SYNTHETIC_S2: task beta returns no result.",
    ),
    (
        "SYNTHETIC_C2",
        "supported_cause",
        "Support confirmed SYNTHETIC_C2: dependency beta is inactive.",
    ),
    (
        "SYNTHETIC_R2",
        "supported_resolution",
        "Support ran SYNTHETIC_R2 to activate dependency beta.",
    ),
    (
        "SYNTHETIC_V2",
        "confirmed_fact",
        "Support verified SYNTHETIC_V2: task beta now returns a result.",
    ),
)

_CURATED_CONTROL_FACTS: tuple[_Fact, ...] = (
    (
        "SYNTHETIC_S1",
        "reported_symptom",
        "Customer reports SYNTHETIC_S1: task alpha fails.",
    ),
    (
        "SYNTHETIC_C1",
        "supported_cause",
        "Support confirmed SYNTHETIC_C1 as the root cause because dependency "
        "alpha is unavailable.",
    ),
    (
        "SYNTHETIC_R1",
        "supported_resolution",
        "Support fixed SYNTHETIC_R1 and restarted dependency alpha.",
    ),
    (
        "SYNTHETIC_V1",
        "confirmed_fact",
        "Support verified SYNTHETIC_V1 using dependency alpha status.",
    ),
    (
        "SYNTHETIC_S2",
        "reported_symptom",
        "Customer reports SYNTHETIC_S2: task beta fails.",
    ),
    (
        "SYNTHETIC_C2",
        "supported_cause",
        "Support confirmed SYNTHETIC_C2 as the root cause because dependency "
        "beta is unavailable.",
    ),
    (
        "SYNTHETIC_R2",
        "supported_resolution",
        "Support fixed SYNTHETIC_R2 and restarted dependency beta.",
    ),
    (
        "SYNTHETIC_V2",
        "confirmed_fact",
        "Support verified SYNTHETIC_V2 using dependency beta status.",
    ),
)


def _paragraphs_by_semantic_field(facts: tuple[_Fact, ...]) -> str:
    role_order = (
        "reported_symptom",
        "supported_cause",
        "supported_resolution",
        "confirmed_fact",
    )
    return "\n\n".join(
        " ".join(text for _, role, text in facts if role == expected_role)
        for expected_role in role_order
    )


def _line_per_claim(facts: tuple[_Fact, ...]) -> str:
    return "\n".join(text for _, _, text in facts)


def _blank_line_per_claim(facts: tuple[_Fact, ...]) -> str:
    return "\n\n".join(text for _, _, text in facts)


def _fully_flattened(facts: tuple[_Fact, ...]) -> str:
    return " ".join(text for _, _, text in facts)


def _recognized_speaker_turns(facts: tuple[_Fact, ...]) -> str:
    turns: list[str] = []
    for index, (_, role, text) in enumerate(facts):
        speaker = "Client" if role == "reported_symptom" else "Support"
        turns.append(f"{speaker} • Jan {index + 1:02d}, 2000 00:00 {text}")
    return " ".join(turns)


_REPRESENTATIONS: tuple[tuple[str, _Representation], ...] = (
    ("paragraphs-by-semantic-field", _paragraphs_by_semantic_field),
    ("line-per-claim", _line_per_claim),
    ("blank-line-per-claim", _blank_line_per_claim),
    ("fully-flattened", _fully_flattened),
    ("recognized-speaker-turns", _recognized_speaker_turns),
)


def test_curated_keyword_control_satisfies_atomic_inventory_oracle() -> None:
    transcript = _blank_line_per_claim(_CURATED_CONTROL_FACTS)

    excerpts, role_index = _prepared_evidence(transcript)

    _assert_inventory_preserved(
        excerpts=excerpts,
        expected_facts=_CURATED_CONTROL_FACTS,
        source_text=transcript,
    )
    _assert_roles_model_neutral(
        excerpts=excerpts,
        role_index=role_index,
        expected_facts=_CURATED_CONTROL_FACTS,
    )


@pytest.mark.parametrize(
    ("representation",),
    [
        pytest.param(
            representation,
            id=name,
        )
        for name, representation in _REPRESENTATIONS
    ],
)
def test_multi_issue_pre_model_preserves_atomic_inventory(
    representation: _Representation,
) -> None:
    transcript = representation(_EXPECTED_FACTS)

    excerpts, _ = _prepared_evidence(transcript)

    _assert_inventory_preserved(
        excerpts=excerpts,
        expected_facts=_EXPECTED_FACTS,
        source_text=transcript,
    )


@pytest.mark.parametrize(
    ("representation",),
    [
        pytest.param(
            representation,
            id=name,
        )
        for name, representation in _REPRESENTATIONS
    ],
)
def test_multi_issue_pre_model_roles_are_model_neutral(
    representation: _Representation,
) -> None:
    transcript = representation(_EXPECTED_FACTS)

    excerpts, role_index = _prepared_evidence(transcript)

    _assert_roles_model_neutral(
        excerpts=excerpts,
        role_index=role_index,
        expected_facts=_EXPECTED_FACTS,
    )


def test_one_turn_keeps_cause_and_resolution_in_one_original_block() -> None:
    support_turn = (
        "Support • Jan 01, 2000 00:00 "
        "Support confirmed SYNTHETIC_SHARED_TURN_CAUSE because dependency "
        "alpha is inactive. "
        "Support fixed SYNTHETIC_SHARED_TURN_RESOLUTION and restarted "
        "dependency alpha."
    )

    excerpts, _ = _prepared_evidence(support_turn)
    cause_excerpt = next(
        excerpt
        for excerpt in excerpts
        if "SYNTHETIC_SHARED_TURN_CAUSE" in str(excerpt["text"])
    )
    resolution_excerpt = next(
        excerpt
        for excerpt in excerpts
        if "SYNTHETIC_SHARED_TURN_RESOLUTION" in str(excerpt["text"])
    )

    assert cause_excerpt["source_ref"] == resolution_excerpt["source_ref"]
    assert cause_excerpt["text"] == support_turn
    assert cause_excerpt["speaker_kind"] == "support"
    assert resolution_excerpt["speaker_kind"] == "support"


def test_selected_inline_turn_preserves_adjacent_causal_detail() -> None:
    support_turn = (
        "Support • Jan 01, 2000 00:00 "
        "Support fixed SYNTHETIC_SELECTED_ACTION and verified the current state. "
        "The earlier state used SYNTHETIC_ADJACENT_OLD_VALUE. "
        "The configuration obtains its value dynamically, so configure "
        "SYNTHETIC_ADJACENT_SUPPORTED_ASSIGNMENT first. "
        "Afterward, move affected resources by following "
        "SYNTHETIC_ADJACENT_PROCEDURE."
    )
    transcript = " ".join(
        (
            "Client • Jan 01, 2000 00:00 "
            "Customer reports SYNTHETIC_SELECTED_SYMPTOM.",
            support_turn,
        )
    )

    excerpts, _ = _prepared_evidence(transcript)

    matching = [
        excerpt
        for excerpt in excerpts
        if "SYNTHETIC_SELECTED_ACTION" in str(excerpt["text"])
    ]
    assert len(matching) == 1
    assert matching[0]["text"] == support_turn
    for marker in (
        "SYNTHETIC_ADJACENT_OLD_VALUE",
        "SYNTHETIC_ADJACENT_SUPPORTED_ASSIGNMENT",
        "SYNTHETIC_ADJACENT_PROCEDURE",
    ):
        assert marker in str(matching[0]["text"])


def test_bounded_speaker_inventory_is_not_reduced_by_semantic_ranking() -> None:
    turns = [
        (
            f"{'Client' if index % 2 == 0 else 'Support'} "
            f"• Jan {index + 1:02d}, 2000 00:00 "
            f"SYNTHETIC_TURN_INVENTORY_{index:03d} records original evidence."
        )
        for index in range(30)
    ]

    excerpts, _ = _prepared_evidence(" ".join(turns))

    assert len(excerpts) == len(turns)
    for index, (excerpt, turn) in enumerate(zip(excerpts, turns, strict=True)):
        assert excerpt["text"] == turn
        assert f"SYNTHETIC_TURN_INVENTORY_{index:03d}" in str(excerpt["text"])


def test_speaker_turns_take_precedence_over_embedded_section_headings() -> None:
    customer_turn = (
        "Client • Jan 01, 2000 00:00\n"
        "Symptoms:\n"
        "SYNTHETIC_HEADING_CUSTOMER_SYMPTOM is visible."
    )
    support_turn = (
        "Support • Jan 01, 2000 01:00\n"
        "Resolution:\n"
        "SYNTHETIC_HEADING_SUPPORT_RESOLUTION restored the operation."
    )

    excerpts, _ = _prepared_evidence(f"{customer_turn}\n\n{support_turn}")

    assert [(excerpt["speaker_kind"], excerpt["text"]) for excerpt in excerpts] == [
        ("customer", customer_turn),
        ("support", support_turn),
    ]


def test_internal_support_turns_are_not_model_visible() -> None:
    transcript = " ".join(
        (
            "Client • Jan 01, 2000 00:00 "
            "SYNTHETIC_EXTERNAL_CUSTOMER_EVIDENCE is visible.",
            "Support Internal • Jan 01, 2000 00:30 "
            "SYNTHETIC_INTERNAL_SUPPORT_NOTE must remain local.",
            "Support • Jan 01, 2000 01:00 "
            "SYNTHETIC_EXTERNAL_SUPPORT_EVIDENCE is visible.",
        )
    )

    excerpts, _ = _prepared_evidence(transcript)
    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)

    assert "SYNTHETIC_EXTERNAL_CUSTOMER_EVIDENCE" in excerpt_text
    assert "SYNTHETIC_EXTERNAL_SUPPORT_EVIDENCE" in excerpt_text
    assert "SYNTHETIC_INTERNAL_SUPPORT_NOTE" not in excerpt_text


def test_transcript_preamble_is_not_model_visible() -> None:
    transcript = " ".join(
        (
            "# Customer Ticket Content",
            "Client • Jan 01, 2000 00:00 "
            "SYNTHETIC_PREAMBLE_CUSTOMER_EVIDENCE is visible.",
            "Support • Jan 01, 2000 01:00 "
            "SYNTHETIC_PREAMBLE_SUPPORT_EVIDENCE is visible.",
        )
    )

    excerpts, _ = _prepared_evidence(transcript)
    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)

    assert "# Customer Ticket Content" not in excerpt_text
    assert len(excerpts) == 2


def test_speaker_inventory_accepts_exact_ref_bound_and_rejects_overflow() -> None:
    def transcript(turn_count: int) -> str:
        return " ".join(
            (
                f"{'Client' if index % 2 == 0 else 'Support'} "
                "• Jan 01, 2000 00:00 "
                f"SYNTHETIC_BOUNDARY_TURN_{index:03d} records evidence."
            )
            for index in range(turn_count)
        )

    accepted = selected_semantic_review_excerpts(
        transcript(SEMANTIC_REVIEW_MAX_EXCERPTS)
    )

    assert len(accepted) == SEMANTIC_REVIEW_MAX_EXCERPTS
    assert selected_semantic_review_excerpts(
        transcript(SEMANTIC_REVIEW_MAX_EXCERPTS + 1)
    ) == []
    with pytest.raises(SemanticReviewError) as captured:
        new_pending_semantic_review(
            approved_summary_text=transcript(SEMANTIC_REVIEW_MAX_EXCERPTS + 1),
            source_kind="clean_ticket",
            ticket_ref="ticket-synthetic-input-overflow",
            ttl_seconds=60,
        )
    assert captured.value.debug_code == "semantic_review_packet_unavailable"


def test_speaker_inventory_rejects_total_byte_overflow() -> None:
    large_detail = " ".join("synthetic-detail" for _ in range(550))
    transcript = " ".join(
        (
            f"{'Client' if index % 2 == 0 else 'Support'} "
            "• Jan 01, 2000 00:00 "
            f"SYNTHETIC_TOTAL_BOUND_{index:03d} {large_detail}."
        )
        for index in range(20)
    )

    assert len(transcript.encode("utf-8")) > SEMANTIC_REVIEW_MAX_TOTAL_BYTES
    assert selected_semantic_review_excerpts(transcript) == []


def test_sentence_atoms_preserve_quoted_commands() -> None:
    python_command = """Run python -c "print('alpha. beta')" to inspect output."""
    awk_command = """Run awk '{print $1 ". " $2}' input.log to inspect fields."""

    assert _sentence_atoms(f"{python_command} Verification passed.") == [
        python_command,
        "Verification passed.",
    ]
    assert _sentence_atoms(f"{awk_command} Verification passed.") == [
        awk_command,
        "Verification passed.",
    ]
    assert _sentence_atoms("Customers' servers fail. Verify next.") == [
        "Customers' servers fail.",
        "Verify next.",
    ]
    assert _sentence_atoms('A 12" pipe failed. Verify next.') == [
        'A 12" pipe failed.',
        "Verify next.",
    ]


@pytest.mark.parametrize(
    "include_cause", (False, True), ids=("two-sections", "three-sections")
)
def test_explicit_section_atoms_remain_selected_and_model_neutral(
    include_cause: bool,
) -> None:
    lines = [
        "Symptoms:",
        "SYNTHETIC_LABELED_SYMPTOM_A was observed on task alpha. "
        "SYNTHETIC_LABELED_SYMPTOM_B was observed on task beta.",
    ]
    expected = [
        "SYNTHETIC_LABELED_SYMPTOM_A",
        "SYNTHETIC_LABELED_SYMPTOM_B",
    ]
    if include_cause:
        lines.extend(
            (
                "Confirmed Cause:",
                "SYNTHETIC_LABELED_CAUSE_A identifies dependency alpha. "
                "SYNTHETIC_LABELED_CAUSE_B identifies dependency beta.",
            )
        )
        expected.extend(("SYNTHETIC_LABELED_CAUSE_A", "SYNTHETIC_LABELED_CAUSE_B"))
    lines.extend(
        (
            "Resolution:",
            "SYNTHETIC_LABELED_RESOLUTION_A restored alpha. "
            "SYNTHETIC_LABELED_RESOLUTION_B restored beta.",
        )
    )
    expected.extend(
        ("SYNTHETIC_LABELED_RESOLUTION_A", "SYNTHETIC_LABELED_RESOLUTION_B")
    )

    transcript = "\n".join(lines)
    excerpts, role_index = _prepared_evidence(transcript)

    for marker in expected:
        matches = [
            excerpt for excerpt in excerpts if marker in str(excerpt.get("text"))
        ]
        assert len(matches) == 1
        assert role_index[str(matches[0]["source_ref"])]["roles"] == [
            "unclassified_evidence"
        ]


def test_selected_excerpts_preserve_inline_quoted_commands() -> None:
    python_command = """python -c "print('alpha. beta')\""""
    awk_command = """awk '{print $1 ". " $2}' input.log"""
    transcript = "\n".join(
        (
            "Symptoms:",
            "SYNTHETIC_COMMAND_SYMPTOM was observed.",
            "Resolution:",
            f"Run {python_command}. Run {awk_command}.",
        )
    )

    excerpts, role_index = _prepared_evidence(transcript)

    for command in (python_command, awk_command):
        matches = [
            excerpt for excerpt in excerpts if command in str(excerpt.get("text"))
        ]
        assert len(matches) == 1
        assert role_index[str(matches[0]["source_ref"])]["roles"] == [
            "unclassified_evidence"
        ]


def _prepared_evidence(
    transcript: str,
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    pending = new_pending_semantic_review(
        approved_summary_text=transcript,
        source_kind="clean_ticket",
        ticket_ref="ticket-synthetic-input-adequacy",
        ttl_seconds=60,
    )
    selected_excerpts = pending.packet["selected_excerpts"]
    assert isinstance(selected_excerpts, list)
    assert all(isinstance(excerpt, dict) for excerpt in selected_excerpts)
    return selected_excerpts, semantic_review_excerpt_role_index(pending)


def _assert_inventory_preserved(
    *,
    excerpts: list[dict[str, object]],
    expected_facts: tuple[_Fact, ...],
    source_text: str,
) -> None:
    all_markers = tuple(marker for marker, _, _ in expected_facts)
    excerpt_texts = tuple(str(excerpt.get("text")) for excerpt in excerpts)
    for marker, _, _ in expected_facts:
        marker_occurrence_count = sum(text.count(marker) for text in excerpt_texts)
        assert marker_occurrence_count == 1, (
            f"{marker}: expected one selected occurrence, "
            f"found {marker_occurrence_count}"
        )
        matches = [
            excerpt
            for excerpt, text in zip(excerpts, excerpt_texts, strict=True)
            if marker in text
        ]
        assert len(matches) == 1, (
            f"{marker}: expected one selected excerpt, found {len(matches)}"
        )
        excerpt = matches[0]
        excerpt_text = str(excerpt["text"])
        markers_in_excerpt = [
            candidate for candidate in all_markers if candidate in excerpt_text
        ]
        assert markers_in_excerpt == [marker], (
            f"{marker}: excerpt is not identity-atomic: {markers_in_excerpt}"
        )
    source_order = sorted(all_markers, key=source_text.index)
    selected_order = [
        marker
        for excerpt_text in excerpt_texts
        for marker in sorted(
            (candidate for candidate in all_markers if candidate in excerpt_text),
            key=excerpt_text.index,
        )
    ]
    assert selected_order == source_order


def _assert_roles_model_neutral(
    *,
    excerpts: list[dict[str, object]],
    role_index: Mapping[str, Mapping[str, object]],
    expected_facts: tuple[_Fact, ...],
) -> None:
    for marker, _, _ in expected_facts:
        matches = [
            excerpt for excerpt in excerpts if marker in str(excerpt.get("text"))
        ]
        assert len(matches) == 1, (
            f"{marker}: expected one selected excerpt, found {len(matches)}"
        )
        excerpt = matches[0]
        source_ref = excerpt["source_ref"]
        assert isinstance(source_ref, str)
        indexed_roles = role_index[source_ref]["roles"]
        assert indexed_roles == ["unclassified_evidence"], (
            f"{marker}: expected model-neutral role, found {indexed_roles}"
        )
