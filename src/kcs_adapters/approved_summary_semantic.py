"""Local semantic extraction from explicit approved sanitized summaries."""

from __future__ import annotations

import re

from kcs_core.json_payload import JsonDict
from kcs_core.models import ArticleType
from kcs_core.sanitizer import ensure_safe_sanitized_payload
from kcs_core.semantic_extraction import (
    CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
    KcsItemStatus,
    ProductRelation,
    Supportability,
    SupportabilityBasis,
    VisibilityHint,
)

_ITEM_HEADING_RE = re.compile(r"(?im)^\s*Item\s+\d+\s*:\s*(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.*\S)\s*$")
_TRANSCRIPT_PLACEHOLDER_RE = re.compile(
    r"\{\{[A-Z_]+_\d+\}\}|(?:PERSON_NAME|SHELL_USERHOST|EMAIL|IP_ADDRESS)_\d+",
    re.I,
)
_CONFIG_PATH_RE = re.compile(r"(/etc/[A-Za-z0-9_./-]+\.conf)\b")
_DATADIR_PATH_RE = re.compile(r'DataDir\s+"([^"]+)"', re.I)
_DIAGNOSTIC_TRANSCRIPT_RE = re.compile(
    r"(?:"
    r"\bAvatar\b|"
    r"\bAssign\b|"
    r"\bInternal\b|"
    r"\bShow more\b|"
    r"\bTo:\s*Team\b|"
    r"\bTechnical Support Engineer\b|"
    r"\bTeam\s*•\b|"
    r"\bFriday\b|"
    r"\bSaturday\b|"
    r"\blogger=|"
    r"\blevel=|"
    r"\bmsg=|"
    r"plugin process exited|"
    r"Plugin validation failed|"
    r"Skipping loading plugin|"
    r"proc_close\(\)|"
    r"filemng failed|"
    r"exit status|"
    r"\bdrwx|"
    r"\buid=\d+|"
    r"\bgid=\d+|"
    r"\bcat\s+/|"
    r"\bgrep\s+|"
    r"\bcurl\s+|"
    r"\bls\s+-|"
    r"\bstat\s+-c\b|"
    r"\bgetenforce\b|"
    r"\bps\s+aux\b|"
    r"\[.*?\]\#|"
    r"\btest server\b|"
    r"\bclient server\b"
    r")",
    re.I,
)
_INTERIM_INVESTIGATION_RE = re.compile(
    r"(?:"
    r"sorry reply|"
    r"i am reviewing|"
    r"investigation continues|"
    r"waiting for grafana|"
    r"not sure|"
    r"should those be|"
    r"main issue appears|"
    r"some sort of backend|"
    r"plugin path is okay|"
    r"with grafana debug enabled|"
    r"we manually corrected|"
    r"we have un-installed|"
    r"we have uninstalled|"
    r"attempted these fixes"
    r")",
    re.I,
)
_NON_ARTICLE_HEADING_TEXT = frozenset(
    {
        "customer ticket content",
        "customer ticket",
        "ticket content",
        "approved summary",
        "summary",
    }
)
_LONG_TRANSCRIPT_MIN_CHARS = 10_000
_EXPLICIT_ARTICLE_LABEL_RE = re.compile(
    r"(?im)^\s*(?:Title|Symptoms|Cause|Root cause|Resolution steps?|Solution)\s*:"
)
_FINAL_EVIDENCE_RE = re.compile(
    r"(?is)\broot cause\s*:.{0,2500}\b(?:resolution|resolved|i found|"
    r"i backed up|i disabled|i created|i enabled)\b"
)
_WINDOWS_PLATFORM_RE = re.compile(
    r"(?i)\b(?:plesk\s+for\s+windows|windows\s+server|via\s+rdp|rdp\s+access)\b"
)


def semantic_extraction_from_approved_summary_text(
    text: str,
    *,
    approved_clean_ticket: bool = False,
) -> JsonDict | None:
    """Build semantic candidates from explicit approved sanitized summary text."""

    if not approved_clean_ticket:
        ensure_safe_sanitized_payload(text)
    sections = _approved_summary_item_sections(text)
    items = []
    for index, section in enumerate(sections, start=1):
        item = _semantic_item_from_approved_summary_section(section, index)
        if item is not None:
            items.append(item)
    if not items:
        return None
    return {
        "case_ref": "approved-summary-case-001",
        "extraction_source_ref": "approved-summary-local-extraction-001",
        "items": items,
        "schema_version": CANDIDATE_SEMANTIC_EXTRACTION_SCHEMA_VERSION,
        "source_refs": ["approved-summary-source-001"],
    }


def _approved_summary_item_sections(text: str) -> list[str]:
    matches = list(_ITEM_HEADING_RE.finditer(text))
    if len(matches) < 2:
        return [text]
    sections: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append(text[match.start() : end].strip())
    return sections


def _semantic_item_from_approved_summary_section(
    section: str,
    index: int,
) -> JsonDict | None:
    if _requires_more_explicit_semantic_evidence(section):
        return None
    title = _summary_title(section)
    symptoms = _section_lines(section, "Symptoms") or _symptoms_from_text(
        section,
        title,
    )
    cause = _section_value(section, ("Cause", "Root cause")) or _cause_from_text(
        section
    )
    if cause:
        cause = _augment_cause_with_config_path(cause, section)
    if title and cause:
        title = _specific_title_from_cause(title, cause)
    resolution = _section_value(
        section,
        ("Resolution", "Resolution summary", "Solution"),
    )
    resolution_steps = _section_lines(section, "Resolution steps")
    if not resolution_steps and resolution:
        resolution_steps = _resolution_steps_from_text(resolution)
    if not resolution_steps:
        resolution_steps = _resolution_steps_from_text(section)
    if not title or not symptoms or not cause or not resolution_steps:
        return None
    platform = _platform_from_text(section)
    item: JsonDict = {
        "article_type_hint": ArticleType.TECHNICAL_SCR.value,
        "candidate_id": f"candidate-{index:03d}",
        "confirmed_facts": _confirmed_facts(section, title),
        "environment": {
            "applicable_to": [platform],
            "platform": platform,
        },
        "kcs_item_status": KcsItemStatus.CANDIDATE_ALLOWED.value,
        "product_relation": ProductRelation.PLESK_OWNED.value,
        "resolution_steps": resolution_steps,
        "source_refs": [f"approved-summary-source-item-{index:03d}"],
        "summary": title,
        "supportability": Supportability.SUPPORTED.value,
        "supportability_basis": SupportabilityBasis.EXPLICIT_INPUT_MENTION.value,
        "supported_cause": cause,
        "supported_resolution_or_workaround": _supported_resolution(resolution_steps),
        "symptoms": symptoms,
        "visibility_hint": VisibilityHint.PUBLIC_CUSTOMER_SAFE.value,
    }
    ensure_safe_sanitized_payload(item)
    return item


def _summary_title(section: str) -> str | None:
    explicit = _section_value(section, ("Title", "Item 1", "Item 2"))
    if explicit:
        return _clean_sentence(explicit)
    for sentence in _sentences(section):
        title = _title_from_symptom(sentence)
        if title:
            return title
    for line in section.splitlines():
        cleaned = _clean_sentence(line)
        if (
            cleaned
            and not cleaned.endswith(":")
            and cleaned.casefold() not in _NON_ARTICLE_HEADING_TEXT
        ):
            return cleaned
    return None


def _section_value(section: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        pattern = re.compile(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$")
        match = pattern.search(section)
        if match:
            return _clean_sentence(match.group(1))
    return None


def _section_lines(section: str, label: str) -> list[str]:
    lines = section.splitlines()
    result: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(rf"{re.escape(label)}\s*:", stripped, flags=re.I):
            collecting = True
            continue
        if collecting and re.fullmatch(r"[A-Za-z][A-Za-z ]{1,40}:", stripped):
            break
        if collecting:
            bullet = _BULLET_RE.match(line)
            value = bullet.group(1) if bullet else stripped
            cleaned = _clean_sentence(value)
            if cleaned:
                result.append(cleaned)
    return result


def _symptoms_from_text(section: str, title: str | None) -> list[str]:
    normalized = _monitoring_symptoms_from_text(section)
    if normalized:
        return normalized
    markers = (
        " does not ",
        " do not ",
        " fails",
        " failure",
        " no data",
        " not visible",
        " unable ",
    )
    symptoms = [
        sentence
        for sentence in _sentences(section)
        if _is_public_article_sentence(sentence)
        if not _INTERIM_INVESTIGATION_RE.search(sentence)
        if any(marker in f" {sentence.casefold()} " for marker in markers)
    ]
    if symptoms:
        return symptoms[:3]
    return [title] if title else []


def _cause_from_text(section: str) -> str | None:
    for sentence in _sentences(section):
        lowered = sentence.casefold()
        if "root cause" in lowered or "caused" in lowered or "because" in lowered:
            return _augment_cause_with_config_path(sentence, section)
    return None


def _resolution_steps_from_text(text: str) -> list[str]:
    structured_steps = _structured_resolution_steps_from_text(text)
    if structured_steps:
        return structured_steps
    markers = ("back", "disable", "restart", "reinstall", "verify", "confirm")
    steps = [
        sentence
        for sentence in _sentences(text)
        if _is_public_article_sentence(sentence)
        if not _INTERIM_INVESTIGATION_RE.search(sentence)
        if any(marker in sentence.casefold() for marker in markers)
    ]
    return steps[:6]


def _confirmed_facts(section: str, title: str) -> list[str]:
    facts = _section_lines(section, "Confirmed facts")
    return facts[:6] if facts else [title]


def _supported_resolution(resolution_steps: list[str]) -> str:
    return " ".join(resolution_steps[:2])


def _title_from_symptom(sentence: str) -> str | None:
    lowered = sentence.casefold()
    if "monitoring" in lowered and "graph" in lowered and "no data" in lowered:
        return "Monitoring graphs show no data in Plesk"
    if (
        "monitoring" in lowered
        and "graph" in lowered
        and "none of the graphs show any data" in lowered
    ):
        return "Monitoring graphs show no data in Plesk"
    return None


def _specific_title_from_cause(title: str, cause: str) -> str:
    if " due to " in title.casefold():
        return title
    hint = _cause_title_hint(cause)
    if hint and hint.casefold() not in title.casefold():
        return f"{title} due to {hint}"
    return title


def _cause_title_hint(cause: str) -> str:
    cleaned = re.sub(r"\s+", " ", cause).strip().rstrip(".")
    cleaned = re.sub(r"(?i)^the\s+", "", cleaned)
    cleaned = re.sub(r"/[A-Za-z0-9_./%:+-]+", "", cleaned)
    cleaned = re.split(
        r"(?i)\b(?:configured|caused|pointed|redirected|resulted|which|that)\b",
        cleaned,
        maxsplit=1,
    )[0]
    words = [word.strip(" ,;:-") for word in cleaned.split()]
    words = [word for word in words if word]
    if len(words) < 2:
        return ""
    return " ".join(words[:8])


def _monitoring_symptoms_from_text(text: str) -> list[str]:
    lowered = text.casefold()
    symptoms: list[str] = []
    if "monitoring" in lowered and "graph" in lowered and (
        "no data" in lowered or "none of the graphs show any data" in lowered
    ):
        symptoms.append("Plesk Monitoring graphs show no data.")
    if (
        ("metric names" in lowered or "metrics" in lowered or "datapoint" in lowered)
        and "no data" in lowered
        and ("query" in lowered or "queries" in lowered or "datapoint" in lowered)
    ):
        symptoms.append(
            "Monitoring/Grafana can list metric names, but graph datapoint "
            "queries return no data."
        )
    return _unique_public_sentences(symptoms)[:3]


def _augment_cause_with_config_path(cause: str, text: str) -> str:
    lowered = cause.casefold()
    config_path = _preferred_config_path(text)
    datadir = _datadir_path(text)
    if "collectd" not in lowered or not config_path:
        return _sentence_case(cause)
    if datadir:
        return (
            f"The custom unowned collectd configuration file {config_path} "
            f"configured collectd to write RRD metric files to {datadir}, "
            "which Plesk Monitoring did not query for graph datapoints."
        )
    return (
        f"The custom unowned collectd configuration file {config_path} "
        "caused RRD metric files to be written to a path that Plesk Monitoring "
        "did not query for graph datapoints."
    )


def _structured_resolution_steps_from_text(text: str) -> list[str]:
    lowered = text.casefold()
    config_path = _preferred_config_path(text)
    steps: list[str] = []
    if config_path:
        steps.extend(_config_file_resolution_steps(config_path, text, lowered))
    return _unique_public_sentences(steps, allow_command_steps=True)


def _config_file_resolution_steps(
    config_path: str,
    original_text: str,
    lowered_text: str,
) -> list[str]:
    steps: list[str] = []
    if _mentions_unowned_package_check(lowered_text):
        steps.append(
            f"Run rpm -qf {config_path} to verify that the file is not owned "
            "by any package."
        )
    if _mentions_config_content_review(config_path, lowered_text):
        detail = "DataDir setting" if "datadir" in lowered_text else "file content"
        steps.append(f"Run cat {config_path} to review the {detail}.")
    if _mentions_config_backup_or_disable(config_path, lowered_text):
        backup_dir = _backup_dir_from_text(original_text) or "/root/kcs-case-backup"
        steps.extend(
            [
                f"Run mkdir -p {backup_dir} to create a backup directory.",
                (
                    f"Run cp -a {config_path} {backup_dir}/ to back up the "
                    "configuration file."
                ),
                (
                    f"Run mv {config_path} {config_path}.disabled to disable "
                    "the configuration file."
                ),
            ]
        )
    service_name = _restarted_service_from_text(original_text)
    if service_name:
        steps.append(f"Run systemctl restart {service_name}.")
    if _mentions_graphs_displaying_data(lowered_text):
        steps.append(
            "Open the Monitoring page in Plesk and confirm graphs start "
            "displaying data."
        )
    if _mentions_repopulate_context(lowered_text) or steps:
        steps.append(
            "Wait for graphs to repopulate with newly collected metrics; "
            "historical data from before the correction may not be visible."
        )
    return steps


def _mentions_unowned_package_check(lowered_text: str) -> bool:
    return "not owned by any package" in lowered_text or "rpm -qf" in lowered_text


def _mentions_config_content_review(config_path: str, lowered_text: str) -> bool:
    return "datadir" in lowered_text or f"cat {config_path}".casefold() in lowered_text


def _mentions_config_backup_or_disable(config_path: str, lowered_text: str) -> bool:
    markers = (
        "backed up and disabled",
        "backed up and removed",
        "backed up",
        "backup",
        "back up",
        "config file was backed up",
        f"cp -a {config_path}".casefold(),
        f"mv {config_path}".casefold(),
    )
    return any(marker in lowered_text for marker in markers)


def _mentions_graphs_displaying_data(lowered_text: str) -> bool:
    return (
        "graphs have started displaying data" in lowered_text
        or "graphs started displaying data" in lowered_text
        or (
            "confirm" in lowered_text
            and "graphs" in lowered_text
            and "data" in lowered_text
        )
    )


def _mentions_repopulate_context(lowered_text: str) -> bool:
    return (
        "historical" in lowered_text
        or "before the fix" in lowered_text
        or "repopulate" in lowered_text
    )


def _backup_dir_from_text(text: str) -> str:
    match = re.search(r"\bmkdir\s+-p\s+(/[A-Za-z0-9_./%:+-]+)", text, re.I)
    return match.group(1).rstrip("/") if match else ""


def _restarted_service_from_text(text: str) -> str:
    explicit = re.search(r"\bsystemctl\s+restart\s+([A-Za-z0-9_.@-]+)", text, re.I)
    if explicit:
        return explicit.group(1).rstrip(".")
    passive = re.search(
        r"\b([A-Za-z][A-Za-z0-9_.@-]+)\s+service\s+was\s+restarted\b",
        text,
        re.I,
    )
    if passive:
        return passive.group(1)
    return ""


def _preferred_config_path(text: str) -> str:
    paths = _CONFIG_PATH_RE.findall(text)
    if not paths:
        return ""
    for path in paths:
        if "02rrdtool-monitoring.conf" in path:
            return path
    return paths[0]


def _datadir_path(text: str) -> str:
    match = _DATADIR_PATH_RE.search(text)
    return match.group(1) if match else ""


def _unique_public_sentences(
    values: list[str],
    *,
    allow_command_steps: bool = False,
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_sentence(value)
        if not cleaned or not _is_public_article_sentence(
            cleaned,
            allow_command_steps=allow_command_steps,
        ):
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _is_public_article_sentence(
    value: str,
    *,
    allow_command_steps: bool = False,
) -> bool:
    if not value or _TRANSCRIPT_PLACEHOLDER_RE.search(value):
        return False
    if _DIAGNOSTIC_TRANSCRIPT_RE.search(value) and not allow_command_steps:
        return False
    if len(value) > 360:
        return False
    return True


def _sentence_case(value: str) -> str:
    if not value:
        return value
    first = value[0]
    if first.isalpha() and first.islower():
        return first.upper() + value[1:]
    return value


def _platform_from_text(text: str) -> str:
    if _WINDOWS_PLATFORM_RE.search(text):
        return "Plesk for Windows"
    return "Plesk for Linux"


def _requires_more_explicit_semantic_evidence(section: str) -> bool:
    if len(section) < _LONG_TRANSCRIPT_MIN_CHARS:
        return False
    if not _DIAGNOSTIC_TRANSCRIPT_RE.search(section):
        return False
    label_count = len(_EXPLICIT_ARTICLE_LABEL_RE.findall(section))
    if label_count >= 3:
        return False
    return not _FINAL_EVIDENCE_RE.search(section)


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [cleaned for part in parts if (cleaned := _clean_sentence(part))]


def _clean_sentence(value: str) -> str:
    cleaned = value.strip().strip("-*# \t")
    if _TRANSCRIPT_PLACEHOLDER_RE.search(cleaned):
        return ""
    return _sentence_case(cleaned[:280].strip())
