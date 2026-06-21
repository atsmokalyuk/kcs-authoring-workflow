"""KCS Zendesk markup pattern snippets for optional HTML/source drafting."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

KCS_MARKUP_PATTERN_SCHEMA_VERSION = "kcs-markup-pattern-v1"
DEFAULT_KCS_MARKUP_PATTERN_SET = (
    Path(__file__).resolve().parents[2] / "evals/kcs_markup_patterns_v1.jsonl"
)

_FORBIDDEN_FRAGMENTS = (
    "ticket.txt",
    "ticket.redacted.md",
    "ticket.final.clean.md",
    ".private/",
    "/users/",
    "/home/customer",
    "authorization: bearer",
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.IGNORECASE)
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)


@dataclass(frozen=True)
class KcsMarkupPattern:
    """One allowed KCS markup pattern."""

    pattern_id: str
    use_when: str
    output_mode: str
    snippet: str
    guidance: tuple[str, ...]
    avoid_when: tuple[str, ...]

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> "KcsMarkupPattern":
        if payload.get("schema_version") != KCS_MARKUP_PATTERN_SCHEMA_VERSION:
            raise ValueError("Unsupported KCS markup pattern schema version.")
        return cls(
            pattern_id=_required_string(payload, "pattern_id"),
            use_when=_required_string(payload, "use_when"),
            output_mode=_required_string(payload, "output_mode"),
            snippet=_required_string(payload, "snippet"),
            guidance=_required_string_tuple(payload, "guidance"),
            avoid_when=_required_string_tuple(payload, "avoid_when"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": KCS_MARKUP_PATTERN_SCHEMA_VERSION,
            "pattern_id": self.pattern_id,
            "use_when": self.use_when,
            "output_mode": self.output_mode,
            "snippet": self.snippet,
            "guidance": list(self.guidance),
            "avoid_when": list(self.avoid_when),
        }


def load_kcs_markup_patterns(
    pattern_set: Path = DEFAULT_KCS_MARKUP_PATTERN_SET,
) -> tuple[KcsMarkupPattern, ...]:
    """Load allowed KCS markup patterns."""

    text = pattern_set.read_text(encoding="utf-8")
    _assert_safe_text(text)
    patterns: list[KcsMarkupPattern] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("Each KCS markup pattern line must be an object.")
        pattern = KcsMarkupPattern.from_json_dict(payload)
        _assert_safe_pattern(pattern)
        patterns.append(pattern)
    if not patterns:
        raise ValueError("KCS markup pattern set is empty.")
    if len({pattern.pattern_id for pattern in patterns}) != len(patterns):
        raise ValueError("KCS markup pattern IDs must be unique.")
    return tuple(patterns)


def select_kcs_markup_patterns(
    *,
    max_patterns: int = 8,
    output_modes: tuple[str, ...] = ("zendesk_html", "zendesk_trigger_text"),
    pattern_set: Path = DEFAULT_KCS_MARKUP_PATTERN_SET,
) -> tuple[KcsMarkupPattern, ...]:
    """Select a bounded set of markup patterns for an explicit HTML/source prompt."""

    allowed_modes = set(output_modes)
    patterns = [
        pattern
        for pattern in load_kcs_markup_patterns(pattern_set)
        if pattern.output_mode in allowed_modes
    ]
    return tuple(patterns[: max(0, max_patterns)])


def render_kcs_markup_patterns_for_prompt(
    patterns: tuple[KcsMarkupPattern, ...],
) -> str:
    """Render markup patterns for optional Zendesk HTML/source prompts."""

    if not patterns:
        return ""
    lines = [
        "Zendesk/KCS markup patterns:",
        "",
        "Use these snippets only when the requested output is Zendesk HTML/editor "
        "source. For plain Markdown drafts, follow the semantic rules and do not "
        "force HTML containers.",
        "",
    ]
    for index, pattern in enumerate(patterns, 1):
        lines.append(f"{index}. `{pattern.pattern_id}`")
        lines.append(f"   Use when: {pattern.use_when}")
        lines.append(f"   Output mode: {pattern.output_mode}")
        lines.append("   Snippet:")
        lines.append("   ```html")
        for snippet_line in pattern.snippet.splitlines():
            lines.append(f"   {snippet_line}")
        lines.append("   ```")
        if pattern.guidance:
            lines.append(f"   Guidance: {'; '.join(pattern.guidance)}")
        if pattern.avoid_when:
            lines.append(f"   Avoid when: {'; '.join(pattern.avoid_when)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _required_string(payload: dict[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _required_string_tuple(
    payload: dict[str, object],
    field_name: str,
) -> tuple[str, ...]:
    value = payload.get(field_name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings.")
    return tuple(item for item in value if item)


def _assert_safe_text(text: str) -> None:
    lower = text.casefold()
    if any(fragment in lower for fragment in _FORBIDDEN_FRAGMENTS):
        raise ValueError(
            "KCS markup pattern set contains a forbidden private fragment."
        )
    if _EMAIL_RE.search(text):
        raise ValueError("KCS markup pattern set must not contain email identifiers.")
    for match in _IPV4_RE.finditer(text):
        value = match.group(0)
        if not value.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
            raise ValueError(
                "KCS markup pattern set must not contain private IPv4 values."
            )


def _assert_safe_pattern(pattern: KcsMarkupPattern) -> None:
    if not re.fullmatch(r"[a-z0-9_]+", pattern.pattern_id):
        raise ValueError("KCS markup pattern ID must be lowercase snake_case.")
    if pattern.output_mode not in {"zendesk_html", "zendesk_trigger_text", "markdown"}:
        raise ValueError("KCS markup pattern output_mode is unsupported.")
