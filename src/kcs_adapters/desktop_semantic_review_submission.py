"""Value-safe string guards shared by semantic and operator submissions."""

from __future__ import annotations

import re
from collections.abc import Mapping

from kcs_core.semantic_extraction import (
    SemanticIssueProposal,
    SemanticIssueProposalPacket,
    SemanticObservation,
)

_EXTRACTIVE_OBSERVATION_SEQUENCE_FIELDS = (
    "symptoms",
    "error_evidence",
    "cause_evidence",
    "resolution_evidence",
    "verification_evidence",
    "answer_evidence",
    "context_evidence",
)
_EXTRACTIVE_OBSERVATION_FIELDS = frozenset(
    (*_EXTRACTIVE_OBSERVATION_SEQUENCE_FIELDS, "question")
)

_SUBMIT_FORBIDDEN_TEXT_RE = re.compile(r"```", re.I | re.M)
_SUBMIT_FORBIDDEN_HTML_TAG_RE = re.compile(
    r"</?\s*(?:"
    r"a|blockquote|body|br|code|div|em|h[1-6]|html|iframe|img|li|ol|p|pre|"
    r"script|span|strong|style|table|tbody|td|th|thead|tr|ul"
    r")(?:\s|/?>)",
    re.I | re.M,
)
_SUBMIT_MARKDOWN_BLOCKQUOTE_RE = re.compile(r"^\s*>\s+\S.*$", re.M)
_SUBMIT_MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S.*$", re.M)
_SUBMIT_CONFIG_TEXT_RE = re.compile(r"\bCONFIG_TEXT:", re.I)
_SUBMIT_CONFIG_COMMENT_PATH_RE = re.compile(r"^\s*#{1,6}\s+/[A-Za-z0-9_./:-]+", re.M)
_SUBMIT_SHELL_PROMPT_COMMAND_RE = re.compile(r"^\s*#\s+[a-z0-9_./-]+(?:\s|$)", re.M)
_SAFE_CONFIG_PLACEHOLDER_RE = re.compile(
    r"<(?:"
    r"DOMAIN|EMAIL|HOST|HOSTNAME|IP|IPV4|IPV6|PERSON_NAME|SERVER|URL|USER|"
    r"domain|email|host|hostname|ip|ipv4|ipv6|server|url|user"
    r")>",
    re.I,
)
_SUBMIT_FORBIDDEN_LOCAL_PATH_RE = re.compile(
    r"(?:file://|~[/\\]|(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\[^\\\s]+\\[^\\\s]+|"
    r"(?<![A-Za-z0-9])/(?:Users|private|tmp)(?:/[A-Za-z0-9._~+-]+)*|"
    r"(?<![A-Za-z0-9])local-data/(?:approved-summaries|reviewer-bundles)"
    r"(?:/[A-Za-z0-9._~+-]+)*)",
    re.I,
)
_SUBMIT_FORBIDDEN_COMPACT_KEYS = frozenset(
    {
        "autopublishallowed",
        "candidateextraction",
        "file",
        "filepath",
        "item",
        "itemcandidates",
        "localpath",
        "path",
        "publicoutputapproved",
        "recommendedaction",
        "revieweronlyhtml",
    }
)


class SemanticReviewSubmissionError(ValueError):
    """Value-safe semantic submission validation error."""

    def __init__(
        self,
        debug_code: str,
        *,
        field_paths: tuple[str, ...] = (),
    ) -> None:
        super().__init__("semantic review submission unavailable")
        self.debug_code = debug_code
        self.field_paths = field_paths


def ensure_no_forbidden_submit_values(value: object) -> None:
    """Reject article/control surfaces and workstation-local references."""

    if isinstance(value, dict):
        _ensure_no_forbidden_submit_mapping(value)
        return
    if isinstance(value, list):
        for item in value:
            ensure_no_forbidden_submit_values(item)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_submit_string(value)


def ensure_no_forbidden_semantic_submit_values(value: object) -> None:
    """Reject unsafe surfaces while preserving exact source headings."""

    _ensure_no_forbidden_semantic_submit_values(value, field_path=())


def ensure_extractively_grounded_observations(
    proposal: SemanticIssueProposalPacket,
    excerpt_text_by_ref: Mapping[str, str],
) -> None:
    """Require evidence observations to preserve original excerpt wording."""

    normalized_excerpts = {
        source_ref: _normalized_grounding_text(text)
        for source_ref, text in excerpt_text_by_ref.items()
    }
    invalid: list[str] = []
    for index, issue in enumerate(proposal.issues):
        invalid.extend(
            _non_extractive_issue_field_paths(index, issue, normalized_excerpts)
        )
    if invalid:
        raise SemanticReviewSubmissionError(
            "semantic_observation_text_not_extractive",
            field_paths=tuple(invalid),
        )


def ensure_issue_entry_speaker_compatibility(
    proposal: SemanticIssueProposalPacket,
    excerpt_text_by_ref: Mapping[str, str],
    excerpt_speaker_by_ref: Mapping[str, str],
) -> None:
    """Reject issue-entry evidence grounded only in explicit support turns."""

    normalized_excerpts = {
        source_ref: _normalized_grounding_text(text)
        for source_ref, text in excerpt_text_by_ref.items()
    }
    for issue in proposal.issues:
        observations = list(issue.symptoms)
        if issue.question is not None:
            observations.append(issue.question)
        for observation in observations:
            grounded_speakers = {
                excerpt_speaker_by_ref.get(source_ref, "unknown")
                for source_ref in observation.source_refs
                if _normalized_grounding_text(observation.text)
                in normalized_excerpts.get(source_ref, "")
            }
            if grounded_speakers == {"support"}:
                raise SemanticReviewSubmissionError(
                    "semantic_issue_entry_speaker_incompatible"
                )


def _non_extractive_issue_field_paths(
    index: int,
    issue: SemanticIssueProposal,
    normalized_excerpts: Mapping[str, str],
) -> list[str]:
    invalid: list[str] = []
    question = getattr(issue, "question")
    if question is not None and not _observation_is_extractive(
        question, normalized_excerpts
    ):
        invalid.append(f"issues[{index}].question")
    invalid.extend(
        f"issues[{index}].{field_name}"
        for field_name in _EXTRACTIVE_OBSERVATION_SEQUENCE_FIELDS
        if any(
            not _observation_is_extractive(observation, normalized_excerpts)
            for observation in getattr(issue, field_name)
        )
    )
    return invalid


def _observation_is_extractive(
    observation: SemanticObservation,
    normalized_excerpts: Mapping[str, str],
) -> bool:
    normalized_observation = _normalized_grounding_text(observation.text)
    return any(
        normalized_observation in normalized_excerpts.get(source_ref, "")
        for source_ref in observation.source_refs
    )


def _normalized_grounding_text(value: str) -> str:
    return " ".join(value.split())


def _ensure_no_forbidden_submit_mapping(value: dict[object, object]) -> None:
    for key, item in value.items():
        if isinstance(key, str):
            _ensure_submit_key_allowed(key)
        ensure_no_forbidden_submit_values(item)


def _ensure_no_forbidden_semantic_submit_values(
    value: object,
    *,
    field_path: tuple[str, ...],
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                _ensure_submit_key_allowed(key)
                _ensure_no_forbidden_semantic_submit_values(
                    item,
                    field_path=(*field_path, key),
                )
            else:
                _ensure_no_forbidden_semantic_submit_values(
                    item,
                    field_path=field_path,
                )
        return
    if isinstance(value, list):
        for item in value:
            _ensure_no_forbidden_semantic_submit_values(
                item,
                field_path=field_path,
            )
        return
    if isinstance(value, str):
        _ensure_no_forbidden_submit_string(
            value,
            allow_source_heading=_is_source_observation_text(field_path),
        )


def _ensure_submit_key_allowed(key: str) -> None:
    compact_key = key.replace("_", "").replace("-", "").casefold()
    if compact_key in _SUBMIT_FORBIDDEN_COMPACT_KEYS:
        raise SemanticReviewSubmissionError("semantic_review_forbidden_field")


def _is_source_observation_text(field_path: tuple[str, ...]) -> bool:
    return (
        len(field_path) >= 2
        and field_path[-1] == "text"
        and field_path[-2] in _EXTRACTIVE_OBSERVATION_FIELDS
    )


def _ensure_no_forbidden_submit_string(
    value: str,
    *,
    allow_source_heading: bool = False,
) -> None:
    html_checked_value = _SAFE_CONFIG_PLACEHOLDER_RE.sub("", value)
    if _SUBMIT_FORBIDDEN_TEXT_RE.search(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _SUBMIT_FORBIDDEN_HTML_TAG_RE.search(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if not allow_source_heading and _submit_markdown_heading_forbidden(
        html_checked_value
    ):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _SUBMIT_MARKDOWN_BLOCKQUOTE_RE.search(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _SUBMIT_FORBIDDEN_LOCAL_PATH_RE.search(value):
        raise SemanticReviewSubmissionError("semantic_review_local_ref_blocked")


def _submit_markdown_heading_forbidden(value: str) -> bool:
    matches = list(_SUBMIT_MARKDOWN_HEADING_RE.finditer(value))
    if not matches:
        return False
    if not _SUBMIT_CONFIG_TEXT_RE.search(value):
        return any(
            _SUBMIT_SHELL_PROMPT_COMMAND_RE.fullmatch(match.group(0)) is None
            for match in matches
        )
    return any(
        _SUBMIT_CONFIG_COMMENT_PATH_RE.fullmatch(match.group(0)) is None
        and _SUBMIT_SHELL_PROMPT_COMMAND_RE.fullmatch(match.group(0)) is None
        for match in matches
    )


__all__ = [
    "SemanticReviewSubmissionError",
    "ensure_extractively_grounded_observations",
    "ensure_issue_entry_speaker_compatibility",
    "ensure_no_forbidden_semantic_submit_values",
    "ensure_no_forbidden_submit_values",
]
