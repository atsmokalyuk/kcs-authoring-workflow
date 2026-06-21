"""Approved-summary payload normalization for Desktop authoring."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from kcs_core.errors import ContractValidationError
from kcs_core.evidence_builder import APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION
from kcs_core.json_payload import JsonDict, require_json_object
from kcs_core.models import ArticleType
from kcs_core.safety import EvidenceVisibility, InputClass
from kcs_core.sanitizer import ensure_safe_sanitized_payload

RESOLUTION_EXECUTABLE_DETAIL_RE = re.compile(
    r"(?:"
    r"https?://|"
    r"/[A-Za-z0-9._~:/%+\-]+|"
    r"\b(?:"
    r"awk|cat|chmod|chown|cp|curl|find|grep|head|journalctl|"
    r"fail2ban-client|firewall-cmd|iptables|ls|mkdir|mv|nft|plesk|"
    r"rm|rpm|sed|service|stat|systemctl|tail|test|ufw"
    r")\b(?:\s+[A-Za-z0-9_./:+%=-]+)+|"
    r"\b(?:click|open|select|browse|navigate)\b.*\b(?:menu|page|screen|tab|ui)\b|"
    r"\b(?:connect|log in|login)\b.*\b(?:plesk|rdp|server|ssh)\b|"
    r"\b(?:block|allow|drop)\b.*\b(?:port|tcp|udp|traffic)\b.*\b\d{2,5}\b|"
    r"\b(?:reload|restart)\b.*\b(?:daemon|fail2ban|firewall|service)\b|"
    r"\b(?:check|confirm|verify)\b.*\b(?:"
    r"data|directory|graphs?|log|metrics?|ownership|path|permissions?|"
    r"service|status"
    r")\b"
    r")",
    re.I,
)
RESOLUTION_INFORMATIONAL_DETAIL_RE = re.compile(
    r"\b(?:advise|inform|note|warn)\b|"
    r"\b(?:historical|older|previous)\s+data\b|"
    r"\b(?:will|may)\s+not\s+(?:appear|backfill|be\s+visible)\b|"
    r"\b(?:repopulate|populate)\s+gradually\b",
    re.I,
)
RESOLUTION_DESTRUCTIVE_STEP_RE = re.compile(
    r"\brm\s+(?:-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*|"
    r"-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*|-[A-Za-z]*r[A-Za-z]*\s+-[A-Za-z]*f[A-Za-z]*)\s+/",
    re.I,
)
SUPPORTED_CAUSE_UNCERTAIN_RE = re.compile(
    r"\b(?:appears?|likely|maybe|possibly|probably|seems?|suspected|unclear|unknown)\b",
    re.I,
)
TOOL_ARGUMENT_ARTIFACT_RE = re.compile(
    r"</?\s*(?:function|parameter|tool_call)\b|<\s*parameter\s+name\s*=",
    re.I,
)

APPROVED_SUMMARY_FALSE_ONLY_ARGS = frozenset(
    {
        "auto_publish_allowed",
        "customer_replies",
        "network_calls",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "ready_for_real_ticket_use",
        "writes_files",
    }
)
APPROVED_SUMMARY_PIPELINE_ARGS = frozenset(
    {
        "applicable_to",
        "approved_summary_text",
        "article_type",
        "article_title",
        "auto_publish_allowed",
        "candidate_id",
        "cause",
        "case_ref",
        "commands",
        "confirmed_facts",
        "customer_replies",
        "debug",
        "diagnosis",
        "environment",
        "evidence",
        "facts",
        "fix",
        "item",
        "log_evidence",
        "logs",
        "notes",
        "open_questions",
        "problem",
        "problem_statement",
        "provider_calls",
        "public_output_approved",
        "publishes",
        "question",
        "ready_for_real_ticket_use",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "reference_article",
        "reference_article_text",
        "reference_article_html",
        "resolution",
        "resolution_procedure",
        "root_cause",
        "root_cause_analysis",
        "resolution_steps",
        "resolution_summary",
        "secondary_finding",
        "secondary_findings",
        "secondary_issue",
        "secondary_issues",
        "solution",
        "summary",
        "steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptom",
        "symptoms",
        "title",
        "network_calls",
        "writes_files",
    }
)
APPROVED_SUMMARY_ITEM_FIELDS = frozenset(
    {
        "answer_steps",
        "applicable_to",
        "article_type",
        "article_title",
        "candidate_id",
        "cause",
        "commands",
        "confirmed_facts",
        "diagnosis",
        "environment",
        "evidence",
        "facts",
        "fix",
        "log_evidence",
        "logs",
        "notes",
        "open_questions",
        "problem",
        "problem_statement",
        "question",
        "reuse_search_checked",
        "reuse_search_run_ref",
        "resolution",
        "resolution_procedure",
        "resolution_steps",
        "resolution_summary",
        "root_cause",
        "root_cause_analysis",
        "secondary_finding",
        "secondary_findings",
        "secondary_issue",
        "secondary_issues",
        "solution",
        "summary",
        "steps",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
        "symptom",
        "symptoms",
        "title",
    }
)
APPROVED_SUMMARY_ENVIRONMENT_FIELDS = frozenset(
    {
        "applicable_to",
        "component",
        "components",
        "extension",
        "operating_system",
        "os",
        "platform",
        "product",
        "version",
    }
)
APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS = frozenset(
    {"component", "platform", "product", "version"}
)
APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS = frozenset(
    APPROVED_SUMMARY_PIPELINE_ARGS
    - {
        "approved_summary_text",
        "case_ref",
        "debug",
        "item",
        *APPROVED_SUMMARY_FALSE_ONLY_ARGS,
        "reference_article",
        "reference_article_html",
        "reference_article_text",
    }
)


class ApprovedSummaryInputError(ContractValidationError):
    """Value-safe approved summary input error with a compact debug code."""

    def __init__(self, debug_code: str) -> None:
        super().__init__("approved summary input invalid")
        self.debug_code = debug_code


class ApprovedSummaryPayloadArgumentError(ValueError):
    """Approved-summary argument shape error."""


def approved_summary_pipeline_payload(arguments: Mapping[str, Any]) -> JsonDict:
    """Normalize approved-summary authoring arguments into evidence export."""

    require_approved_summary_args(arguments)
    approved_summary_text = approved_summary_text_argument(arguments)
    item = approved_summary_checked_item(arguments, approved_summary_text)
    article_type = approved_summary_checked_article_type(item)
    candidate_id = approved_summary_checked_item_ref(arguments)
    environment = approved_summary_checked_environment(item)
    resolution_steps = approved_summary_optional_string_list(
        item, "resolution_steps"
    )
    require_approved_summary_authoring_fields(
        article_type=article_type,
        environment=environment,
        item=item,
        resolution_steps=resolution_steps,
    )
    candidate: JsonDict = {
        "article_type": article_type,
        "atomic": True,
        "candidate_id": candidate_id,
        "confirmed_facts": approved_summary_required_string_list(
            item, "confirmed_facts"
        ),
        "customer_reported": True,
        "kcs_applicable": True,
        "public_solution_safe": True,
        "resolution_state": "solved",
        "resolution_steps": resolution_steps,
        "source_refs": [f"approved-summary-source-{candidate_id}"],
        "summary": approved_summary_required_string(item, "summary"),
        "symptoms": approved_summary_required_string_list(item, "symptoms"),
        "title": approved_summary_required_string(item, "title"),
    }
    optional_string_fields = (
        "question",
        "supported_answer",
        "supported_cause",
        "supported_resolution_or_workaround",
    )
    for field_name in optional_string_fields:
        value = approved_summary_optional_string(item, field_name)
        if value is not None:
            candidate[field_name] = value
    optional_list_fields = ("answer_steps", "applicable_to", "open_questions")
    for field_name in optional_list_fields:
        values = approved_summary_optional_string_list(item, field_name)
        if values:
            candidate[field_name] = values
    if environment:
        candidate["environment"] = environment
    return {
        "confirmed_facts": candidate["confirmed_facts"],
        "environment": environment,
        "input_class": InputClass.OPERATOR_SANITIZED_SUMMARY.value,
        "issue_candidates": [candidate],
        "open_questions": approved_summary_optional_string_list(
            item, "open_questions"
        ),
        "sanitizer_report": {},
        "schema_version": APPROVED_EVIDENCE_EXPORT_SCHEMA_VERSION,
        "source_refs": ["approved-summary-source-001"],
        "supported_cause": candidate.get("supported_cause"),
        "supported_resolution_or_workaround": candidate.get(
            "supported_resolution_or_workaround"
        )
        or candidate.get("supported_answer"),
        "symptoms": candidate["symptoms"],
        "visibility_summary": {
            "classes": [EvidenceVisibility.PUBLIC_CUSTOMER_SAFE.value]
        },
    }


def require_approved_summary_args(arguments: Mapping[str, Any]) -> None:
    try:
        require_known_args(arguments, APPROVED_SUMMARY_PIPELINE_ARGS)
        require_approved_summary_false_only_args(arguments)
    except ApprovedSummaryPayloadArgumentError:
        raise ApprovedSummaryInputError("approved_summary_args_invalid") from None


def require_known_args(
    arguments: Mapping[str, Any],
    allowed: frozenset[str],
) -> None:
    if any(key not in allowed for key in arguments):
        raise ApprovedSummaryPayloadArgumentError("Unexpected approved summary field.")


def require_approved_summary_false_only_args(arguments: Mapping[str, Any]) -> None:
    for key in APPROVED_SUMMARY_FALSE_ONLY_ARGS:
        if key in arguments and arguments[key] is not False:
            raise ApprovedSummaryInputError("approved_summary_policy_flag_invalid")


def approved_summary_text_argument(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("approved_summary_text")
    if isinstance(value, str) and value.strip():
        try:
            ensure_safe_sanitized_payload(value)
        except ContractValidationError:
            raise ApprovedSummaryInputError(
                "approved_summary_text_invalid"
            ) from None
        if TOOL_ARGUMENT_ARTIFACT_RE.search(value):
            raise ApprovedSummaryInputError(
                "approved_summary_text_invalid"
            ) from None
        return value.strip()
    if value is not None:
        raise ApprovedSummaryInputError("approved_summary_text_invalid") from None
    text = approved_summary_text_from_structured_arguments(arguments)
    if text:
        return text
    raise ApprovedSummaryInputError("approved_summary_text_invalid") from None


def approved_summary_checked_item(
    arguments: Mapping[str, Any],
    approved_summary_text: str,
) -> JsonDict:
    try:
        return approved_summary_item(arguments, approved_summary_text)
    except ApprovedSummaryPayloadArgumentError:
        raise
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_item_invalid") from None


def approved_summary_checked_article_type(item: Mapping[str, Any]) -> str:
    try:
        return approved_summary_article_type(item)
    except ContractValidationError:
        raise ApprovedSummaryInputError(
            "approved_summary_article_type_invalid"
        ) from None


def approved_summary_checked_item_ref(arguments: Mapping[str, Any]) -> str:
    try:
        return approved_summary_item_ref(arguments)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_item_ref_invalid") from None


def approved_summary_checked_environment(item: Mapping[str, Any]) -> JsonDict:
    try:
        return approved_summary_environment(item)
    except ApprovedSummaryPayloadArgumentError:
        raise
    except ContractValidationError:
        raise ApprovedSummaryInputError(
            "approved_summary_environment_invalid"
        ) from None


def approved_summary_optional_item_object(
    arguments: Mapping[str, Any],
) -> JsonDict | None:
    if "item" not in arguments:
        return None
    return require_json_object(arguments["item"])


def approved_summary_case_ref(arguments: Mapping[str, Any]) -> str:
    value = arguments.get("case_ref")
    if isinstance(value, str) and value.strip():
        try:
            ensure_safe_sanitized_payload(value)
        except ContractValidationError:
            raise ApprovedSummaryInputError(
                "approved_summary_case_ref_invalid"
            ) from None
        return opaque_approved_summary_case_ref(value)
    return "approved-summary-case-001"


def opaque_approved_summary_case_ref(value: str) -> str:
    digest = sha256(value.strip().encode("utf-8")).hexdigest()[:12]
    return f"approved-summary-case-{digest}"


def approved_summary_item_ref(arguments: Mapping[str, Any]) -> str:
    item = approved_summary_item(
        arguments,
        approved_summary_text_argument(arguments),
    )
    value = item.get("candidate_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "item-001"


def approved_summary_title(arguments: Mapping[str, Any]) -> str:
    item = approved_summary_item(
        arguments,
        approved_summary_text_argument(arguments),
    )
    return required_string(item, "title")


def approved_summary_short_summary(arguments: Mapping[str, Any]) -> str:
    item = approved_summary_item(
        arguments,
        approved_summary_text_argument(arguments),
    )
    return required_string(item, "summary")


def approved_summary_item(
    arguments: Mapping[str, Any],
    approved_summary_text: str,
) -> JsonDict:
    if "item" in arguments:
        item = require_json_object(arguments["item"])
        if any(key not in APPROVED_SUMMARY_ITEM_FIELDS for key in item):
            raise ApprovedSummaryPayloadArgumentError(
                "Unexpected approved summary item field."
            )
        ensure_safe_sanitized_payload(item)
        return apply_approved_summary_item_defaults(
            normalize_approved_summary_item(dict(item)),
            approved_summary_text,
        )

    item: JsonDict = {}
    for key in sorted(APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS):
        if key in arguments:
            item[key] = arguments[key]
    item = normalize_approved_summary_item(item)
    return apply_approved_summary_item_defaults(item, approved_summary_text)


def apply_approved_summary_item_defaults(
    item: JsonDict,
    approved_summary_text: str,
) -> JsonDict:
    summary = approved_summary_snippet(approved_summary_text, max_length=500)
    item.setdefault("article_type", ArticleType.TECHNICAL_SCR.value)
    item.setdefault("summary", summary)
    if "environment" not in item and "applicable_to" in item:
        item["environment"] = item["applicable_to"]
    item.setdefault(
        "applicable_to",
        approved_summary_applicable_to_from_environment(item.get("environment"))
        or ["Approved sanitized support context"],
    )
    item["applicable_to"] = approved_summary_canonical_applicable_to(
        item.get("applicable_to"),
        item.get("environment"),
    )
    promote_resolution_steps_to_supported_resolution(item)
    ensure_safe_sanitized_payload(item)
    return item


def promote_resolution_steps_to_supported_resolution(item: JsonDict) -> None:
    if "supported_resolution_or_workaround" in item or "supported_answer" in item:
        return
    resolution_steps = optional_string_list(item, "resolution_steps")
    if resolution_steps:
        item["supported_resolution_or_workaround"] = " ".join(resolution_steps)


def normalize_approved_summary_item(item: JsonDict) -> JsonDict:
    move_item_alias(item, "article_title", "title")
    move_item_alias(item, "symptom", "symptoms")
    move_item_alias(item, "problem", "symptoms")
    move_item_alias(item, "problem_statement", "symptoms")
    move_item_alias(item, "evidence", "confirmed_facts")
    move_item_alias(item, "facts", "confirmed_facts")
    move_item_alias(item, "log_evidence", "confirmed_facts")
    move_item_alias(item, "logs", "confirmed_facts")
    move_item_alias(item, "notes", "confirmed_facts")
    move_item_alias(item, "secondary_finding", "confirmed_facts")
    move_item_alias(item, "secondary_findings", "confirmed_facts")
    move_item_alias(item, "secondary_issue", "confirmed_facts")
    move_item_alias(item, "secondary_issues", "confirmed_facts")
    move_item_alias(item, "root_cause", "supported_cause")
    move_item_alias(item, "root_cause_analysis", "supported_cause")
    move_item_alias(item, "cause", "supported_cause")
    move_item_alias(item, "diagnosis", "supported_cause")
    move_item_alias(item, "resolution_summary", "supported_resolution_or_workaround")
    move_item_alias(item, "resolution", "supported_resolution_or_workaround")
    move_item_alias(item, "resolution_procedure", "supported_resolution_or_workaround")
    move_item_alias(item, "solution", "supported_resolution_or_workaround")
    move_item_alias(item, "fix", "supported_resolution_or_workaround")
    move_item_alias(item, "steps", "resolution_steps")
    move_item_alias(item, "commands", "resolution_steps")
    return item


def move_item_alias(item: JsonDict, alias: str, canonical: str) -> None:
    value = item.pop(alias, None)
    if value is not None and canonical not in item:
        item[canonical] = value


def approved_summary_text_from_structured_arguments(
    arguments: Mapping[str, Any],
) -> str:
    item = approved_summary_structured_item_for_text(arguments)
    if not item:
        return ""
    fragments: list[str] = []
    for key in (
        "title",
        "symptoms",
        "confirmed_facts",
        "supported_cause",
        "supported_resolution_or_workaround",
        "resolution_steps",
        "environment",
        "applicable_to",
    ):
        fragments.extend(approved_summary_text_fragments(item.get(key)))
    text = " ".join(fragment for fragment in fragments if fragment).strip()
    ensure_safe_sanitized_payload(text)
    return approved_summary_snippet(text, max_length=900) if text else ""


def approved_summary_structured_item_for_text(
    arguments: Mapping[str, Any],
) -> JsonDict:
    if "item" in arguments:
        item = require_json_object(arguments["item"])
        if any(key not in APPROVED_SUMMARY_ITEM_FIELDS for key in item):
            raise ApprovedSummaryInputError("approved_summary_item_invalid")
        return normalize_approved_summary_item(dict(item))
    item: JsonDict = {}
    for key in sorted(APPROVED_SUMMARY_TOP_LEVEL_ITEM_FIELDS):
        if key in arguments:
            item[key] = arguments[key]
    return normalize_approved_summary_item(item)


def approved_summary_text_fragments(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        fragments: list[str] = []
        for item in value.values():
            fragments.extend(approved_summary_text_fragments(item))
        return fragments
    if isinstance(value, list | tuple):
        fragments: list[str] = []
        for item in value:
            fragments.extend(approved_summary_text_fragments(item))
        return fragments
    return []


def approved_summary_article_type(item: Mapping[str, Any]) -> str:
    value = required_string(item, "article_type")
    try:
        article_type = ArticleType(value)
    except ValueError:
        raise ContractValidationError("approved summary article_type invalid") from None
    if article_type == ArticleType.NONE:
        raise ContractValidationError("approved summary article_type invalid")
    return article_type.value


def approved_summary_environment(item: Mapping[str, Any]) -> JsonDict:
    value = item.get("environment")
    if value is None:
        return {}
    if isinstance(value, str):
        ensure_safe_sanitized_payload(value)
        return {"platform": approved_summary_snippet(value, max_length=180)}
    if isinstance(value, list | tuple):
        return approved_summary_environment_from_labels(value)
    environment = require_json_object(value)
    if any(key not in APPROVED_SUMMARY_ENVIRONMENT_FIELDS for key in environment):
        raise ApprovedSummaryPayloadArgumentError(
            "Unexpected approved summary environment field."
        )
    ensure_safe_sanitized_payload(environment)
    return normalized_approved_summary_environment(dict(environment))


def normalized_approved_summary_environment(environment: JsonDict) -> JsonDict:
    normalized = dict(environment)
    component_values = approved_summary_environment_values(
        normalized.pop("component", None)
    )
    component_values.extend(
        approved_summary_environment_values(normalized.pop("components", None))
    )
    component_values.extend(
        approved_summary_environment_values(normalized.pop("extension", None))
    )
    applicable_to_values = approved_summary_environment_values(
        normalized.pop("applicable_to", None)
    )
    if component_values:
        normalized["component"] = " / ".join(component_values)
    platform_alias = normalized.pop("os", None) or normalized.pop(
        "operating_system", None
    )
    if platform_alias is not None and "platform" not in normalized:
        normalized["platform"] = platform_alias
    if applicable_to_values and "platform" not in normalized:
        normalized["platform"] = " / ".join(applicable_to_values)
    return {
        key: value
        for key, value in normalized.items()
        if key in APPROVED_SUMMARY_NORMALIZED_ENVIRONMENT_FIELDS
    }


def approved_summary_environment_from_labels(value: object) -> JsonDict:
    labels = approved_summary_environment_label_values(value)
    if not labels:
        raise ApprovedSummaryPayloadArgumentError(
            "Unexpected approved summary environment field."
        )
    return {"platform": approved_summary_snippet(" / ".join(labels), max_length=180)}


def require_approved_summary_authoring_fields(
    *,
    article_type: str,
    environment: Mapping[str, Any],
    item: Mapping[str, Any],
    resolution_steps: list[str],
) -> None:
    if not environment:
        raise ApprovedSummaryInputError("approved_summary_environment_required")
    if article_type == ArticleType.TECHNICAL_SCR.value and not resolution_steps:
        raise ApprovedSummaryInputError("approved_summary_resolution_steps_required")
    if article_type == ArticleType.TECHNICAL_SCR.value:
        require_supported_cause_not_speculative(item)
        require_non_destructive_resolution_steps(resolution_steps)
        require_executable_resolution_steps(resolution_steps)


def require_supported_cause_not_speculative(item: Mapping[str, Any]) -> None:
    cause = optional_string(item, "supported_cause")
    if cause is None:
        return
    if SUPPORTED_CAUSE_UNCERTAIN_RE.search(cause):
        raise ApprovedSummaryInputError("approved_summary_supported_cause_uncertain")


def require_non_destructive_resolution_steps(resolution_steps: list[str]) -> None:
    if any(RESOLUTION_DESTRUCTIVE_STEP_RE.search(step) for step in resolution_steps):
        raise ApprovedSummaryInputError("approved_summary_resolution_step_destructive")


def require_executable_resolution_steps(resolution_steps: list[str]) -> None:
    executable_steps = sum(
        1 for step in resolution_steps if RESOLUTION_EXECUTABLE_DETAIL_RE.search(step)
    )
    detailed_steps = sum(
        1 for step in resolution_steps if resolution_step_has_executable_detail(step)
    )
    if len(resolution_steps) <= 2:
        minimum_detailed_steps = len(resolution_steps)
    else:
        minimum_detailed_steps = max(2, (len(resolution_steps) + 1) // 2)
    if executable_steps < 1 or detailed_steps < minimum_detailed_steps:
        raise ApprovedSummaryInputError("approved_summary_resolution_steps_incomplete")


def resolution_step_has_executable_detail(step: str) -> bool:
    return bool(
        RESOLUTION_EXECUTABLE_DETAIL_RE.search(step)
        or RESOLUTION_INFORMATIONAL_DETAIL_RE.search(step)
    )


def approved_summary_applicable_to_from_environment(value: object) -> list[str]:
    values = approved_summary_environment_label_values(value)
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        label = approved_summary_snippet(item, max_length=120)
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(label)
    return result[:8]


def approved_summary_canonical_applicable_to(
    value: object,
    environment: object,
) -> list[str]:
    values = approved_summary_applicable_to_from_environment(value)
    text = " ".join(
        [
            *values,
            *approved_summary_environment_label_values(environment),
        ]
    ).casefold()
    if "plesk" in text:
        if "windows" in text or "rdp" in text or "iis" in text:
            return ["Plesk for Windows"]
        if (
            "linux" in text
            or "rpm" in text
            or "sw-collectd" in text
            or "grafana" in text
            or "plesk for linux" in text
        ):
            return ["Plesk for Linux"]
    return values


def approved_summary_environment_label_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        ensure_safe_sanitized_payload(value)
        return split_approved_summary_environment_text(value)
    if isinstance(value, Mapping):
        labels: list[str] = []
        for key in (
            "product",
            "component",
            "components",
            "extension",
            "applicable_to",
            "platform",
            "os",
            "operating_system",
            "version",
        ):
            labels.extend(approved_summary_environment_label_values(value.get(key)))
        return labels
    if isinstance(value, list | tuple):
        labels: list[str] = []
        for item in value:
            labels.extend(approved_summary_environment_label_values(item))
        return labels
    return []


def split_approved_summary_environment_text(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[;,]", value) if part.strip()]
    return parts or [value.strip()]


def approved_summary_environment_values(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            raise ApprovedSummaryPayloadArgumentError(
                "Unexpected approved summary environment field."
            )
        ensure_safe_sanitized_payload(value)
        return [value.strip()]
    if not isinstance(value, list):
        raise ApprovedSummaryPayloadArgumentError(
            "Unexpected approved summary environment field."
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ApprovedSummaryPayloadArgumentError(
                "Unexpected approved summary environment field."
            )
        ensure_safe_sanitized_payload(item)
        result.append(item.strip())
    return result


def approved_summary_default_title(summary: str) -> str:
    sentence = summary.split(".", 1)[0].strip()
    if not sentence:
        sentence = "Approved sanitized KCS candidate"
    return approved_summary_snippet(sentence, max_length=140)


def approved_summary_snippet(value: str, *, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 1].rstrip(" ,.;:") + "."


def approved_summary_required_string(item: Mapping[str, Any], key: str) -> str:
    try:
        return required_string(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def approved_summary_optional_string(
    item: Mapping[str, Any], key: str
) -> str | None:
    try:
        return optional_string(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def approved_summary_required_string_list(
    item: Mapping[str, Any], key: str
) -> list[str]:
    try:
        return required_string_list(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def approved_summary_optional_string_list(
    item: Mapping[str, Any], key: str
) -> list[str]:
    try:
        return optional_string_list(item, key)
    except ContractValidationError:
        raise ApprovedSummaryInputError("approved_summary_content_invalid") from None


def required_string(item: Mapping[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary field invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def required_argument_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary argument invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def optional_string(item: Mapping[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError("approved summary field invalid")
    ensure_safe_sanitized_payload(value)
    return value.strip()


def required_string_list(item: Mapping[str, Any], key: str) -> list[str]:
    values = optional_string_list(item, key)
    if not values:
        raise ContractValidationError("approved summary field invalid")
    return values


def optional_string_list(item: Mapping[str, Any], key: str) -> list[str]:
    value = item.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        return string_list_from_scalar(value)
    if not isinstance(value, list):
        raise ContractValidationError("approved summary field invalid")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ContractValidationError("approved summary field invalid")
        ensure_safe_sanitized_payload(entry)
        result.append(entry.strip())
    return result


def string_list_from_scalar(value: str) -> list[str]:
    if not value.strip():
        raise ContractValidationError("approved summary field invalid")
    values = string_or_json_string_list(value)
    for entry in values:
        ensure_safe_sanitized_payload(entry)
    return values


def string_or_json_string_list(value: str) -> list[str]:
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            parsed = json.loads(stripped)
        except ValueError:
            parsed = None
        if isinstance(parsed, list) and all(
            isinstance(entry, str) and entry.strip() for entry in parsed
        ):
            return [entry.strip() for entry in parsed]
    return [stripped]
