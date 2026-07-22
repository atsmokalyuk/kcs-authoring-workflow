"""Private submit-validation helpers for Desktop semantic review."""

from __future__ import annotations

import json
import re
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    CandidateSemanticExtraction,
)

SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES = 4000
SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES = 64_000

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
_SUBMIT_CONFIG_COMMENT_PATH_RE = re.compile(
    r"^\s*#{1,6}\s+/[A-Za-z0-9_./:-]+", re.M
)
_SUBMIT_SHELL_PROMPT_COMMAND_RE = re.compile(
    r"^\s*#\s+[a-z0-9_./-]+(?:\s|$)", re.M
)
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
_SUBMIT_PLAIN_STRING_ARRAY_FIELDS = frozenset(
    {
        "confirmed_facts",
        "open_questions",
        "resolution_steps",
        "source_refs",
        "symptoms",
    }
)
_SUBMIT_ALLOWED_PLATFORM_VALUES = frozenset(
    {
        "Linux",
        "Plesk for Linux",
        "Plesk for Windows",
        "Windows",
    }
)
_SUBMIT_ALLOWED_PRODUCT_VALUES = frozenset({"Plesk"})
_SUBMIT_ALLOWED_APPLICABLE_TO_VALUES = frozenset(
    {
        "Plesk for Linux",
        "Plesk for Windows",
    }
)
_SEMANTIC_CONTRACT_DEBUG_CODE_RULES = (
    ("unsupported semantic article_type_hint", "semantic_review_article_type_invalid"),
    (
        "unsupported semantic product_relation",
        "semantic_review_product_relation_invalid",
    ),
    (
        "semantic extraction product relation invalid",
        "semantic_review_product_relation_invalid",
    ),
    (
        "unsupported semantic supportability_basis",
        "semantic_review_supportability_basis_invalid",
    ),
    ("unsupported semantic supportability", "semantic_review_supportability_invalid"),
    ("unsupported semantic kcs_item_status", "semantic_review_item_status_invalid"),
    ("unsupported semantic visibility_hint", "semantic_review_visibility_hint_invalid"),
    ("unsupported semantic eol_role", "semantic_review_eol_role_invalid"),
    ("semantic item environment invalid", "semantic_review_environment_invalid"),
    ("semantic extraction requires items", "semantic_review_items_missing"),
    (
        "semantic extraction source refs invalid",
        "semantic_review_top_level_source_refs_missing",
    ),
    ("source_refs", "semantic_review_source_refs_invalid"),
)


class SemanticReviewSubmissionError(ValueError):
    """Private value-safe semantic-review submit validation error."""

    def __init__(self, debug_code: str) -> None:
        super().__init__("semantic review submission unavailable")
        self.debug_code = debug_code


def validated_semantic_review_submission(
    *,
    candidate_semantic_extraction: object,
    expected_case_ref: object,
    allowed_source_refs: set[str],
    max_candidates: int,
) -> CandidateSemanticExtraction:
    """Validate submitted candidate extraction against a prepared review packet."""

    _ensure_bounded_submit_payload(candidate_semantic_extraction)
    _ensure_plain_string_submit_arrays(candidate_semantic_extraction)
    _ensure_no_forbidden_submit_values(candidate_semantic_extraction)
    shape_debug_code = _semantic_extraction_shape_debug_code(
        candidate_semantic_extraction
    )
    if shape_debug_code is not None:
        raise SemanticReviewSubmissionError(shape_debug_code)
    ensure_safe_sanitized_payload(candidate_semantic_extraction)
    try:
        extraction = (
            candidate_semantic_extraction
            if isinstance(candidate_semantic_extraction, CandidateSemanticExtraction)
            else CandidateSemanticExtraction.from_json_dict(
                candidate_semantic_extraction
            )
        )
    except ContractValidationError as exc:
        raise SemanticReviewSubmissionError(
            _semantic_contract_debug_code(str(exc))
        ) from exc
    if extraction.case_ref != expected_case_ref:
        raise SemanticReviewSubmissionError("semantic_review_case_ref_invalid")
    _ensure_submit_environment_values(extraction)
    _ensure_submit_candidate_count(extraction, max_candidates=max_candidates)
    _ensure_submit_source_refs(
        extraction,
        allowed_source_refs=allowed_source_refs,
    )
    _ensure_submit_excerpt_coverage(
        extraction,
        required_source_refs=allowed_source_refs,
    )
    _ensure_bounded_submit_text(extraction.to_json_dict())
    return extraction


def ensure_no_forbidden_submit_values(value: object) -> None:
    """Validate submitted strings without exposing the full submit pipeline."""

    _ensure_no_forbidden_submit_values(value)


def _semantic_contract_debug_code(message: str) -> str:
    normalized = message.casefold()
    for needle, debug_code in _SEMANTIC_CONTRACT_DEBUG_CODE_RULES:
        if needle in normalized:
            return debug_code
    return "semantic_review_submission_invalid"


def _semantic_extraction_shape_debug_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return "semantic_review_submit_payload_not_object"
    debug_code = _semantic_extraction_top_level_debug_code(value)
    if debug_code is not None:
        return debug_code
    items = value["items"]
    if not isinstance(items, list) or not items:
        return "semantic_review_items_missing"
    for item in items:
        item_debug_code = _semantic_item_shape_debug_code(item)
        if item_debug_code is not None:
            return item_debug_code
    return None


def _semantic_extraction_top_level_debug_code(
    value: dict[object, object],
) -> str | None:
    allowed_top_level = {
        "case_ref",
        "extraction_source_ref",
        "items",
        "schema_version",
        "source_refs",
    }
    if not set(value).issubset(allowed_top_level):
        return "semantic_review_forbidden_field"
    if value.get("schema_version") != CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION:
        return "semantic_review_schema_version_invalid"
    if not isinstance(value.get("case_ref"), str):
        return "semantic_review_case_ref_missing"
    if not isinstance(value.get("extraction_source_ref"), str):
        return "semantic_review_extraction_source_ref_missing"
    if not _is_plain_string_list(value.get("source_refs")):
        return "semantic_review_top_level_source_refs_missing"
    return None


def _semantic_item_shape_debug_code(value: object) -> str | None:
    if not isinstance(value, dict):
        return "semantic_review_item_invalid"
    allowed_item = {
        "article_type_hint",
        "answer_steps",
        "candidate_id",
        "confirmed_facts",
        "eol_role",
        "environment",
        "item_type_hint",
        "kcs_item_status",
        "open_questions",
        "product_relation",
        "question",
        "resolution_steps",
        "source_refs",
        "summary",
        "supportability",
        "supportability_basis",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptoms",
        "visibility_hint",
    }
    if not set(value).issubset(allowed_item):
        return "semantic_review_forbidden_field"
    required_strings = (
        "candidate_id",
        "kcs_item_status",
        "product_relation",
        "summary",
        "supportability",
    )
    if any(not isinstance(value.get(field), str) for field in required_strings):
        return "semantic_review_item_required_field_missing"
    if not _is_plain_string_list(value.get("source_refs")):
        return "semantic_review_item_source_refs_missing"
    return None


def _is_plain_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) for item in value
    )


def _ensure_no_forbidden_submit_values(value: object) -> None:
    if isinstance(value, dict):
        _ensure_no_forbidden_submit_mapping(value)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_no_forbidden_submit_values(item)
        return
    if isinstance(value, str):
        _ensure_no_forbidden_submit_string(value)


def _ensure_plain_string_submit_arrays(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _SUBMIT_PLAIN_STRING_ARRAY_FIELDS and isinstance(item, list):
                if any(not isinstance(member, str) for member in item):
                    raise SemanticReviewSubmissionError(
                        "semantic_review_plain_string_arrays_required"
                    )
            _ensure_plain_string_submit_arrays(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_plain_string_submit_arrays(item)


def _ensure_no_forbidden_submit_mapping(value: dict[object, object]) -> None:
    for key, item in value.items():
        if isinstance(key, str):
            compact_key = key.replace("_", "").replace("-", "").casefold()
            if compact_key in _SUBMIT_FORBIDDEN_COMPACT_KEYS:
                raise SemanticReviewSubmissionError("semantic_review_forbidden_field")
        _ensure_no_forbidden_submit_values(item)


def _ensure_no_forbidden_submit_string(value: str) -> None:
    html_checked_value = _SAFE_CONFIG_PLACEHOLDER_RE.sub("", value)
    if _SUBMIT_FORBIDDEN_TEXT_RE.search(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _SUBMIT_FORBIDDEN_HTML_TAG_RE.search(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _submit_markdown_heading_forbidden(html_checked_value):
        raise SemanticReviewSubmissionError(
            "semantic_review_forbidden_html_or_markdown"
        )
    if _submit_markdown_blockquote_forbidden(html_checked_value):
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


def _submit_markdown_blockquote_forbidden(value: str) -> bool:
    """Reject Markdown blockquotes without blocking GUI breadcrumbs."""

    return bool(_SUBMIT_MARKDOWN_BLOCKQUOTE_RE.search(value))


def _ensure_submit_candidate_count(
    extraction: CandidateSemanticExtraction,
    *,
    max_candidates: int,
) -> None:
    if len(extraction.items) > max_candidates:
        raise SemanticReviewSubmissionError("semantic_review_too_many_candidates")


def _ensure_submit_environment_values(
    extraction: CandidateSemanticExtraction,
) -> None:
    for item in extraction.items:
        environment = item.environment
        if not environment:
            continue
        if not isinstance(environment, dict):
            raise SemanticReviewSubmissionError("semantic_review_environment_invalid")
        _ensure_optional_allowed_environment_text(
            environment.get("platform"),
            allowed_values=_SUBMIT_ALLOWED_PLATFORM_VALUES,
        )
        _ensure_optional_allowed_environment_text(
            environment.get("product"),
            allowed_values=_SUBMIT_ALLOWED_PRODUCT_VALUES,
        )
        applicable_to = environment.get("applicable_to")
        if applicable_to is None:
            continue
        values = [applicable_to] if isinstance(applicable_to, str) else applicable_to
        if not isinstance(values, list) or not values:
            raise SemanticReviewSubmissionError("semantic_review_environment_invalid")
        for value in values:
            _ensure_optional_allowed_environment_text(
                value,
                allowed_values=_SUBMIT_ALLOWED_APPLICABLE_TO_VALUES,
            )


def _ensure_optional_allowed_environment_text(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> None:
    if value is None:
        return
    if not isinstance(value, str) or value not in allowed_values:
        raise SemanticReviewSubmissionError("semantic_review_environment_invalid")


def _ensure_submit_source_refs(
    extraction: CandidateSemanticExtraction,
    *,
    allowed_source_refs: set[str],
) -> None:
    if not set(extraction.source_refs).issubset(allowed_source_refs):
        raise SemanticReviewSubmissionError("semantic_review_source_refs_invalid")
    for item in extraction.items:
        if not item.source_refs:
            raise SemanticReviewSubmissionError("semantic_review_source_refs_invalid")
        if not set(item.source_refs).issubset(allowed_source_refs):
            raise SemanticReviewSubmissionError("semantic_review_source_refs_invalid")


def _ensure_submit_excerpt_coverage(
    extraction: CandidateSemanticExtraction,
    *,
    required_source_refs: set[str],
) -> None:
    covered_source_refs: set[str] = set()
    for item in extraction.items:
        covered_source_refs.update(item.source_refs)
    if not required_source_refs.issubset(covered_source_refs):
        raise SemanticReviewSubmissionError(
            "semantic_review_excerpt_coverage_incomplete"
        )


def _ensure_bounded_submit_text(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _ensure_bounded_submit_text(item)
        return
    if isinstance(value, list):
        for item in value:
            _ensure_bounded_submit_text(item)
        return
    if (
        isinstance(value, str)
        and len(value.encode("utf-8")) > SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES
    ):
        raise SemanticReviewSubmissionError("semantic_review_submission_too_large")


def _ensure_bounded_submit_payload(value: object) -> None:
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise SemanticReviewSubmissionError(
            "semantic_review_submission_invalid"
        ) from exc
    if len(payload.encode("utf-8")) > SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES:
        raise SemanticReviewSubmissionError("semantic_review_submission_too_large")


__all__ = [
    "SEMANTIC_REVIEW_SUBMIT_MAX_TEXT_BYTES",
    "SEMANTIC_REVIEW_SUBMIT_MAX_TOTAL_BYTES",
    "SemanticReviewSubmissionError",
    "ensure_no_forbidden_submit_values",
    "validated_semantic_review_submission",
]
