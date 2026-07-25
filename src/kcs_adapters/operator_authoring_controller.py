"""Direct controller for operator-confirmed reuse comparison."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from kcs_adapters import desktop_tool_results as _desktop_tool_results
from kcs_adapters.desktop_mcp_adapter import McpToolResult
from kcs_adapters.desktop_reuse_comparison import REUSE_COMPARISON_OUTCOMES
from kcs_adapters.desktop_tool_names import (
    TOOL_CONFIRM_REUSE_COMPARISON,
)
from kcs_adapters.desktop_tool_schemas import tool_output_schema
from kcs_core.errors import ContractValidationError
from kcs_core.json_payload import JsonDict


class OperatorAuthoringControllerError(RuntimeError):
    """Fail-closed controller error with a value-safe code."""


class ToolCaller(Protocol):
    """Small adapter seam used by the controller and deterministic tests."""

    @property
    def reuse_comparison_enabled(self) -> bool: ...

    def call_tool(
        self,
        name: str,
        arguments: Mapping[str, object] | None = None,
    ) -> McpToolResult: ...

    def begin_operator_reuse_comparison(
        self,
        ticket_ref: str,
    ) -> McpToolResult: ...


@dataclass
class OperatorAuthoringController:
    """Enter the comparison gate directly and retain one adapter process."""

    adapter: ToolCaller
    _comparison_ref: str | None = field(init=False, default=None)
    _candidate_refs: frozenset[str] = field(
        init=False,
        default_factory=frozenset,
    )

    def begin(self, ticket_ref: str) -> JsonDict:
        """Start from an existing ticket ref and accept no pre-comparison draft."""

        if self._comparison_ref is not None:
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_session_active"
            )
        if not self.adapter.reuse_comparison_enabled:
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_gate_unavailable"
            )
        result = self.adapter.begin_operator_reuse_comparison(ticket_ref)
        structured = _required_result(result)
        _require_safe_first_result(structured)
        if structured["result_kind"] == "reuse_comparison_required":
            self._retain_comparison_session(structured)
        return structured

    def confirm(
        self,
        *,
        comparison_ref: str,
        outcome: str,
        candidate_ref: str | None = None,
    ) -> JsonDict:
        """Submit one closed-enum operator choice to the same adapter process."""

        self._require_confirmation_matches_session(
            comparison_ref=comparison_ref,
            outcome=outcome,
            candidate_ref=candidate_ref,
        )
        self._clear_comparison_session()
        arguments: JsonDict = {
            "comparison_ref": comparison_ref,
            "outcome": outcome,
        }
        if candidate_ref is not None:
            arguments["candidate_ref"] = candidate_ref
        structured = _required_result(
            self.adapter.call_tool(TOOL_CONFIRM_REUSE_COMPARISON, arguments)
        )
        _require_safe_confirm_result(structured, outcome=outcome)
        return structured

    def _retain_comparison_session(self, result: Mapping[str, object]) -> None:
        comparison_ref = result.get("comparison_ref")
        outcomes = result.get("comparison_outcomes")
        candidate_refs = _displayed_candidate_refs(result)
        if (
            not isinstance(comparison_ref, str)
            or not comparison_ref
            or outcomes != list(REUSE_COMPARISON_OUTCOMES)
            or not candidate_refs
        ):
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_invariant_violated"
            )
        self._comparison_ref = comparison_ref
        self._candidate_refs = candidate_refs

    def _require_confirmation_matches_session(
        self,
        *,
        comparison_ref: str,
        outcome: str,
        candidate_ref: str | None,
    ) -> None:
        expected_ref = self._comparison_ref
        if expected_ref is None:
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_session_unavailable"
            )
        if outcome not in REUSE_COMPARISON_OUTCOMES:
            self._clear_comparison_session()
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_outcome_invalid"
            )
        valid = comparison_ref == expected_ref and _candidate_ref_matches_outcome(
            outcome=outcome,
            candidate_ref=candidate_ref,
            displayed_candidate_refs=self._candidate_refs,
        )
        if not valid:
            self._clear_comparison_session()
            raise OperatorAuthoringControllerError(
                "operator_entrypoint_confirmation_invalid"
            )

    def _clear_comparison_session(self) -> None:
        self._comparison_ref = None
        self._candidate_refs = frozenset()


def _required_result(result: McpToolResult) -> JsonDict:
    if not result.ok or result.result is None:
        raise OperatorAuthoringControllerError(
            result.error_code or "operator_entrypoint_tool_failed"
        )
    try:
        _desktop_tool_results.validate_tool_structured_content(
            result.result,
            tool_output_schema(),
        )
    except ContractValidationError as exc:
        raise OperatorAuthoringControllerError(
            "operator_entrypoint_result_invalid"
        ) from exc
    return result.result


def _require_safe_first_result(result: Mapping[str, object]) -> None:
    if (
        result.get("draft_generated") is not False
        or result.get("reviewer_bundle_written") is not False
        or result.get("writes_files") is not False
        or result.get("result_kind")
        not in {"reuse_comparison_required", "reuse_comparison_blocked"}
    ):
        raise OperatorAuthoringControllerError(
            "operator_entrypoint_invariant_violated"
        )


def _require_safe_confirm_result(
    result: Mapping[str, object],
    *,
    outcome: str,
) -> None:
    valid = (
        _is_safe_none_fit_result(result)
        if outcome == "none_fit"
        else _is_safe_terminal_result(result, outcome=outcome)
    )
    if valid:
        return
    raise OperatorAuthoringControllerError(
        "operator_entrypoint_confirmation_failed"
    )


def _is_safe_terminal_result(
    result: Mapping[str, object],
    *,
    outcome: str,
) -> bool:
    return all(
        (
            result.get("result_kind") == "reuse_comparison_completed",
            result.get("comparison_outcome") == outcome,
            result.get("draft_generated") is False,
            result.get("reviewer_bundle_written") is False,
            result.get("writes_files") is False,
        )
    )


def _is_safe_none_fit_result(result: Mapping[str, object]) -> bool:
    return all(
        (
            result.get("result_kind") == "approved_summary_authoring",
            result.get("auto_publish_allowed") is False,
            result.get("public_output_approved") is False,
            result.get("ready_for_real_ticket_use") is False,
            _has_none_fit_ledger(result.get("comparison_sequence_outcomes")),
        )
    )


def _has_none_fit_ledger(value: object) -> bool:
    if not isinstance(value, list):
        return False
    return any(
        isinstance(item, Mapping)
        and item.get("comparison_outcome") == "none_fit"
        for item in value
    )


def _displayed_candidate_refs(
    result: Mapping[str, object],
) -> frozenset[str]:
    candidates = result.get("comparison_candidates")
    if not isinstance(candidates, list):
        return frozenset()
    return frozenset(
        candidate_ref
        for candidate in candidates
        if isinstance(candidate, Mapping)
        and isinstance((candidate_ref := candidate.get("candidate_ref")), str)
        and candidate_ref
    )


def _candidate_ref_matches_outcome(
    *,
    outcome: str,
    candidate_ref: str | None,
    displayed_candidate_refs: frozenset[str],
) -> bool:
    if outcome in {"reuse", "update"}:
        return candidate_ref in displayed_candidate_refs
    return candidate_ref is None


__all__ = [
    "OperatorAuthoringController",
    "OperatorAuthoringControllerError",
]
