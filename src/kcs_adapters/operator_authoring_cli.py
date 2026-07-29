"""Interactive local entrypoint for operator-confirmed reuse comparison."""

from __future__ import annotations

import argparse
import unicodedata
from collections.abc import Mapping, Sequence
from typing import IO

from kcs_adapters.desktop_mcp_adapter import KcsDesktopMcpAdapter
from kcs_adapters.desktop_reuse_comparison import REUSE_COMPARISON_OUTCOMES
from kcs_adapters.local_public_rag import LocalPublicRagAdapter
from kcs_adapters.operator_authoring_controller import (
    OperatorAuthoringController,
    OperatorAuthoringControllerError,
)

_MAX_INPUT_ATTEMPTS = 3
_MAX_DISPLAY_FACT_CHARS = 600
_MAX_DISPLAY_EXCERPT_CHARS = 600


def run_interactive(
    *,
    controller: OperatorAuthoringController,
    ticket_ref: str,
    input_stream: IO[str],
    output_stream: IO[str],
) -> int:
    """Run one bounded comparison and collect the choice through a local menu."""

    try:
        first = controller.begin(ticket_ref)
        if first["result_kind"] == "reuse_comparison_blocked":
            _write_blocked(first, output_stream)
            return 2
        _write_comparison(first, output_stream)
        outcome = _read_outcome(input_stream, output_stream)
        candidate_ref = _read_candidate_ref(
            first,
            outcome=outcome,
            input_stream=input_stream,
            output_stream=output_stream,
        )
        final = controller.confirm(
            comparison_ref=str(first["comparison_ref"]),
            outcome=outcome,
            candidate_ref=candidate_ref,
        )
        _write_final(final, output_stream)
        return 0
    except OperatorAuthoringControllerError as exc:
        output_stream.write(f"Blocked: {exc}\n")
        return 2


def run_preflight(
    *,
    controller: OperatorAuthoringController,
    ticket_ref: str,
    output_stream: IO[str],
) -> int:
    """Show the first comparison result without accepting an operator outcome."""

    try:
        first = controller.begin(ticket_ref)
        if first["result_kind"] == "reuse_comparison_blocked":
            _write_blocked(first, output_stream)
            return 2
        _write_comparison(first, output_stream)
        output_stream.write("Preflight complete. No outcome was submitted.\n")
        return 0
    except OperatorAuthoringControllerError as exc:
        output_stream.write(f"Blocked: {exc}\n")
        return 2


def production_controller() -> OperatorAuthoringController:
    """Build the direct production composition root with the approved provider."""

    return OperatorAuthoringController(
        KcsDesktopMcpAdapter(reuse_comparison_provider=LocalPublicRagAdapter())
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Start the KCS reuse-comparison gate directly for an existing "
            "approved ticket_ref."
        )
    )
    parser.add_argument("ticket_ref", help="Existing approved local ticket_ref.")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Show comparison evidence and exit without accepting an outcome.",
    )
    import sys

    args = parser.parse_args(argv)
    if args.preflight:
        return run_preflight(
            controller=production_controller(),
            ticket_ref=args.ticket_ref,
            output_stream=sys.stdout,
        )
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        sys.stderr.write("Blocked: operator_entrypoint_interactive_tty_required\n")
        return 2
    return run_interactive(
        controller=production_controller(),
        ticket_ref=args.ticket_ref,
        input_stream=sys.stdin,
        output_stream=sys.stdout,
    )


def _write_comparison(result: Mapping[str, object], output: IO[str]) -> None:
    output.write("Accepted ticket facts:\n")
    for fact in _string_items(result.get("accepted_ticket_facts")):
        output.write(f"- {_compact_display_text(fact, _MAX_DISPLAY_FACT_CHARS)}\n")
    output.write("\nReusable article candidates:\n")
    for index, candidate in enumerate(_candidate_cards(result), start=1):
        output.write(
            f"{index}. {candidate.get('title', '')}\n"
            f"   {candidate.get('public_url', '')}\n"
        )
        for excerpt in _mapping_items(candidate.get("excerpts")):
            excerpt_text = _compact_display_text(
                excerpt.get("text"),
                _MAX_DISPLAY_EXCERPT_CHARS,
            )
            output.write(
                f"   [{excerpt.get('section_path', '')}] "
                f"{excerpt_text}\n"
            )
    output.write("\n")


def _write_blocked(result: Mapping[str, object], output: IO[str]) -> None:
    blockers = ", ".join(_string_items(result.get("blockers")))
    output.write(f"Comparison blocked: {blockers or 'provider unavailable'}\n")


def _write_final(result: Mapping[str, object], output: IO[str]) -> None:
    outcome = result.get("comparison_outcome")
    if outcome in {"reuse", "update", "need_more_evidence"}:
        output.write(f"Recorded outcome: {outcome}. No draft was generated.\n")
        return
    if result.get("draft_generated") is True:
        output.write("Recorded outcome: none_fit. Reviewer draft created.\n")
        return
    output.write(
        "Comparison submitted. Workflow stopped without a reviewer draft; "
        f"status={result.get('debug_code') or result.get('result_kind')}.\n"
    )


def _read_outcome(input_stream: IO[str], output_stream: IO[str]) -> str:
    output_stream.write(
        "Choose outcome: 1=reuse, 2=update, 3=none_fit, "
        "4=need_more_evidence\n"
    )
    return _read_menu_choice(
        input_stream,
        output_stream,
        choices=REUSE_COMPARISON_OUTCOMES,
        error_code="operator_entrypoint_outcome_not_confirmed",
    )


def _read_candidate_ref(
    result: Mapping[str, object],
    *,
    outcome: str,
    input_stream: IO[str],
    output_stream: IO[str],
) -> str | None:
    if outcome not in {"reuse", "update"}:
        return None
    candidates = _candidate_cards(result)
    if not candidates:
        raise OperatorAuthoringControllerError(
            "operator_entrypoint_candidate_unavailable"
        )
    output_stream.write(f"Choose article: 1-{len(candidates)}\n")
    selected = _read_menu_choice(
        input_stream,
        output_stream,
        choices=tuple(str(index) for index in range(1, len(candidates) + 1)),
        error_code="operator_entrypoint_candidate_not_confirmed",
    )
    candidate_ref = candidates[int(selected) - 1].get("candidate_ref")
    if not isinstance(candidate_ref, str) or not candidate_ref:
        raise OperatorAuthoringControllerError(
            "operator_entrypoint_candidate_invalid"
        )
    return candidate_ref


def _read_menu_choice(
    input_stream: IO[str],
    output_stream: IO[str],
    *,
    choices: tuple[str, ...],
    error_code: str,
) -> str:
    aliases = {str(index): choice for index, choice in enumerate(choices, start=1)}
    aliases.update({choice: choice for choice in choices})
    output_stream.flush()
    for _ in range(_MAX_INPUT_ATTEMPTS):
        value = input_stream.readline()
        if not value:
            break
        selected = aliases.get(value.strip().casefold())
        if selected is not None:
            return selected
        output_stream.write("Invalid choice. Try again.\n")
    raise OperatorAuthoringControllerError(error_code)


def _candidate_cards(value: Mapping[str, object]) -> list[Mapping[str, object]]:
    return _mapping_items(value.get("comparison_candidates"))


def _mapping_items(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _compact_display_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    terminal_safe = "".join(
        character
        for character in value
        if unicodedata.category(character) not in {"Cc", "Cf"}
        or character.isspace()
    )
    compact = " ".join(terminal_safe.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}…"


if __name__ == "__main__":
    raise SystemExit(main())
