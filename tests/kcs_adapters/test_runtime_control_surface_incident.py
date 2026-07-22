from __future__ import annotations

import pytest

from kcs_adapters import desktop_semantic_review as _desktop_semantic_review
from kcs_adapters.desktop_semantic_review import (
    SEMANTIC_REVIEW_MAX_EXCERPT_BYTES,
    SEMANTIC_REVIEW_MAX_EXCERPTS,
    SEMANTIC_REVIEW_MAX_TOTAL_BYTES,
    selected_semantic_review_excerpts,
)

_EXPECTED_MARKERS = (
    ("CUSTOMER_SYMPTOM_MARKER_001", "Client", "unclassified_evidence"),
    ("SUPPORTED_CAUSE_MARKER_001", "Support", "unclassified_evidence"),
    ("SUPPORTED_RESOLUTION_MARKER_001", "Support", "unclassified_evidence"),
)


@pytest.mark.parametrize(
    ("shape", "separator"),
    [
        pytest.param("blank_line", "\n\n", id="blank-line-separated"),
        pytest.param("line_per_turn", "\n", id="line-per-turn"),
        pytest.param("flattened", " ", id="fully-flattened"),
    ],
)
def test_inc_pred_001_preserves_neutral_evidence_across_transcript_shapes(
    shape: str,
    separator: str,
) -> None:
    transcript = separator.join(
        ["# Customer Ticket Content", *_synthetic_ticket_turns()]
    )

    excerpts = selected_semantic_review_excerpts(transcript)

    _assert_excerpt_bounds(excerpts)
    selected_positions: list[int] = []
    for marker, speaker, role in _EXPECTED_MARKERS:
        matches = [
            (index, excerpt)
            for index, excerpt in enumerate(excerpts)
            if marker in str(excerpt["text"])
        ]
        assert len(matches) == 1, f"{shape}: {marker}"
        index, excerpt = matches[0]
        assert str(excerpt["text"]).startswith(speaker)
        assert excerpt["role"] == role
        selected_positions.append(index)
    assert selected_positions == sorted(selected_positions)


def test_inc_pred_001_segments_two_flattened_turns() -> None:
    transcript = " ".join(
        [
            (
                "Client • Jan 01, 2000 00:00 CUSTOMER_TWO_TURN_MARKER "
                "reports that a product task fails."
            ),
            (
                "Support • Jan 01, 2000 01:00 RESOLUTION_TWO_TURN_MARKER "
                "fixed the supported configuration."
            ),
        ]
    )

    excerpts = selected_semantic_review_excerpts(transcript)

    customer_excerpt = next(
        excerpt
        for excerpt in excerpts
        if "CUSTOMER_TWO_TURN_MARKER" in str(excerpt["text"])
    )
    resolution_excerpt = next(
        excerpt
        for excerpt in excerpts
        if "RESOLUTION_TWO_TURN_MARKER" in str(excerpt["text"])
    )
    assert str(customer_excerpt["text"]).startswith("Client")
    assert customer_excerpt["role"] == "unclassified_evidence"
    assert str(resolution_excerpt["text"]).startswith("Support")
    assert resolution_excerpt["role"] == "unclassified_evidence"


def test_inc_pred_001_splits_oversized_mixed_role_turn_before_ranking() -> None:
    filler = " ".join(
        f"Diagnostic sentence {index:03d} records neutral detail."
        for index in range(300)
    )
    support_turn = (
        "Support • Jan 01, 2000 01:00 "
        "OVERSIZED_CAUSE_MARKER confirmed the root cause because a required "
        f"component is disabled. {filler} "
        "OVERSIZED_RESOLUTION_MARKER enabled the required component and "
        "restarted the affected service."
    )
    transcript = " ".join(
        [
            (
                "Client • Jan 01, 2000 00:00 OVERSIZED_SYMPTOM_MARKER "
                "reports that a product task fails."
            ),
            support_turn,
        ]
    )

    segments = _desktop_semantic_review._segments(transcript)
    support_chunks = [
        text
        for _, text in segments
        if (
            "OVERSIZED_CAUSE_MARKER" in text
            or "OVERSIZED_RESOLUTION_MARKER" in text
            or "Diagnostic sentence" in text
        )
    ]
    excerpts = selected_semantic_review_excerpts(transcript)
    symptom_excerpt = next(
        excerpt
        for excerpt in excerpts
        if "OVERSIZED_SYMPTOM_MARKER" in str(excerpt["text"])
    )
    cause_index, cause_excerpt = next(
        (index, excerpt)
        for index, excerpt in enumerate(excerpts)
        if "OVERSIZED_CAUSE_MARKER" in str(excerpt["text"])
    )
    resolution_index, resolution_excerpt = next(
        (index, excerpt)
        for index, excerpt in enumerate(excerpts)
        if "OVERSIZED_RESOLUTION_MARKER" in str(excerpt["text"])
    )

    assert len(support_chunks) > 1
    assert all(
        len(chunk.encode("utf-8"))
        <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES
        for chunk in support_chunks
    )
    assert " ".join(support_chunks) == support_turn
    assert symptom_excerpt["speaker_kind"] == "customer"
    assert cause_excerpt["role"] == "unclassified_evidence"
    assert cause_excerpt["speaker_kind"] == "support"
    assert resolution_excerpt["role"] == "unclassified_evidence"
    assert resolution_excerpt["speaker_kind"] == "support"
    assert cause_index < resolution_index


def test_inc_pred_001_hard_bounds_one_oversized_sentence() -> None:
    turn = (
        "Support • Jan 01, 2000 01:00 "
        f"{'diagnostic-word ' * 900}"
        "finished."
    )

    chunks = _desktop_semantic_review._bounded_inline_turn_chunk(turn)

    assert len(chunks) > 1
    assert all(
        len(chunk.encode("utf-8"))
        <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES
        for chunk in chunks
    )
    assert " ".join(chunks) == turn


def test_inc_pred_001_resolution_volume_keeps_customer_and_cause() -> None:
    resolution_turns = [
        (
            f"Support • Jan {index + 2:02d}, 2000 03:00 "
            f"RESOLUTION_VOLUME_MARKER_{index:03d} fixed the supported setting."
        )
        for index in range(8)
    ]
    transcript = "\n\n".join(
        [
            _synthetic_ticket_turns()[0],
            _synthetic_ticket_turns()[2],
            *resolution_turns,
        ]
    )

    excerpts = selected_semantic_review_excerpts(transcript)

    _assert_excerpt_bounds(excerpts)
    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)
    assert "CUSTOMER_SYMPTOM_MARKER_001" in excerpt_text
    assert "SUPPORTED_CAUSE_MARKER_001" in excerpt_text
    assert any(
        "RESOLUTION_VOLUME_MARKER_" in str(excerpt["text"])
        for excerpt in excerpts
    )


def test_multi_issue_transcript_keeps_four_core_evidence_threads() -> None:
    transcript = "\n\n".join(
        segment
        for issue_number in range(1, 5)
        for segment in (
            (
                f"Customer reports MULTI_SYMPTOM_{issue_number:03d}: "
                f"operation {issue_number} fails."
            ),
            (
                f"Support confirmed MULTI_CAUSE_{issue_number:03d} because "
                f"dependency {issue_number} is unavailable."
            ),
            (
                f"Support resolved MULTI_RESOLUTION_{issue_number:03d} by "
                f"restarting dependency {issue_number}."
            ),
        )
    )

    excerpts = selected_semantic_review_excerpts(transcript)

    _assert_excerpt_bounds(excerpts)
    assert len(excerpts) == 12
    assert [excerpt["role"] for excerpt in excerpts] == [
        "unclassified_evidence"
    ] * 12
    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)
    for issue_number in range(1, 5):
        assert f"MULTI_SYMPTOM_{issue_number:03d}" in excerpt_text
        assert f"MULTI_CAUSE_{issue_number:03d}" in excerpt_text
        assert f"MULTI_RESOLUTION_{issue_number:03d}" in excerpt_text


def test_role_volume_keeps_early_and_late_meaningful_evidence() -> None:
    middle_segments = [
        (
            f"Support fixed MIDDLE_RESOLUTION_{index:03d}, resolved the "
            "operation, restarted the dependency, and verified the resolution."
        )
        for index in range(6)
    ]
    transcript = "\n\n".join(
        [
            (
                "Support resolved EARLY_RESOLUTION_ANCHOR and restarted the "
                "affected dependency."
            ),
            *middle_segments,
            (
                "Support resolved LATE_RESOLUTION_ANCHOR and restarted the "
                "affected dependency."
            ),
        ]
    )

    excerpts = selected_semantic_review_excerpts(transcript)

    excerpt_text = "\n".join(str(excerpt["text"]) for excerpt in excerpts)
    assert "EARLY_RESOLUTION_ANCHOR" in excerpt_text
    assert "LATE_RESOLUTION_ANCHOR" in excerpt_text


def test_lexical_core_roles_are_not_model_visible() -> None:
    excerpts = selected_semantic_review_excerpts(
        "\n\n".join(
            [
                (
                    "Support confirmed CORE_CAUSE_MARKER because a configuration "
                    "option has the wrong value."
                ),
                (
                    "Support resolved CORE_RESOLUTION_MARKER by enabling the "
                    "required setting."
                ),
            ]
        )
    )

    role_by_marker = {
        marker: next(
            str(excerpt["role"])
            for excerpt in excerpts
            if marker in str(excerpt["text"])
        )
        for marker in ("CORE_CAUSE_MARKER", "CORE_RESOLUTION_MARKER")
    }
    assert role_by_marker == {
        "CORE_CAUSE_MARKER": "unclassified_evidence",
        "CORE_RESOLUTION_MARKER": "unclassified_evidence",
    }


def _synthetic_ticket_turns() -> list[str]:
    early_noise = " ".join(
        f"diagnostic_filler_{index:04d}" for index in range(1_000)
    )
    return [
        (
            "Client • Jan 01, 2000 00:00 CUSTOMER_SYMPTOM_MARKER_001 "
            "reports that a product task fails with an error."
        ),
        f"Support • Jan 01, 2000 00:30 {early_noise}",
        (
            "Support • Jan 01, 2000 01:00 SUPPORTED_CAUSE_MARKER_001 "
            "confirmed the root cause as a supported configuration mismatch."
        ),
        (
            "Support • Jan 01, 2000 02:00 SUPPORTED_RESOLUTION_MARKER_001 "
            "fixed the configuration and restarted the affected service."
        ),
    ]


def _assert_excerpt_bounds(excerpts: list[dict[str, object]]) -> None:
    assert 0 < len(excerpts) <= SEMANTIC_REVIEW_MAX_EXCERPTS
    assert all(
        excerpt["speaker_kind"] in {"customer", "support", "unknown"}
        for excerpt in excerpts
    )
    assert all(
        len(str(excerpt["text"]).encode("utf-8"))
        <= SEMANTIC_REVIEW_MAX_EXCERPT_BYTES
        for excerpt in excerpts
    )
    assert sum(
        len(str(excerpt["text"]).encode("utf-8")) for excerpt in excerpts
    ) <= SEMANTIC_REVIEW_MAX_TOTAL_BYTES
