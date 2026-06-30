"""Metadata-only KCS article style references for draft prompts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

KCS_ARTICLE_STYLE_REF_SCHEMA_VERSION = "kcs-article-style-ref-v1"
DEFAULT_KCS_ARTICLE_STYLE_REF_SET = (
    Path(__file__).resolve().parents[2] / "evals/kcs_article_style_refs_v1.jsonl"
)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,63}\b", re.IGNORECASE)
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
_FORBIDDEN_FRAGMENTS = (
    "ticket.txt",
    "ticket.redacted.md",
    "ticket.final.clean.md",
    ".private/",
    "/users/",
    "/home/customer",
    "authorization: bearer",
    "raw query text",
    "snippet body",
    "chunk body",
    "vector values",
)
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class KcsArticleStyleReference:
    """One public metadata-only style reference."""

    ref_id: str
    public_url: str
    title: str
    article_type: str
    keywords: tuple[str, ...]
    coverage_tags: tuple[str, ...]
    style_hints: tuple[str, ...]
    cautions: tuple[str, ...]

    @classmethod
    def from_json_dict(cls, payload: dict[str, object]) -> "KcsArticleStyleReference":
        if payload.get("schema_version") != KCS_ARTICLE_STYLE_REF_SCHEMA_VERSION:
            raise ValueError("Unsupported KCS article style ref schema version.")
        return cls(
            ref_id=_required_string(payload, "ref_id"),
            public_url=_required_string(payload, "public_url"),
            title=_required_string(payload, "title"),
            article_type=_required_string(payload, "article_type"),
            keywords=_required_string_tuple(payload, "keywords"),
            coverage_tags=_required_string_tuple(payload, "coverage_tags"),
            style_hints=_required_string_tuple(payload, "style_hints"),
            cautions=_required_string_tuple(payload, "cautions"),
        )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": KCS_ARTICLE_STYLE_REF_SCHEMA_VERSION,
            "ref_id": self.ref_id,
            "public_url": self.public_url,
            "title": self.title,
            "article_type": self.article_type,
            "keywords": list(self.keywords),
            "coverage_tags": list(self.coverage_tags),
            "style_hints": list(self.style_hints),
            "cautions": list(self.cautions),
        }


def load_kcs_article_style_references(
    ref_set: Path = DEFAULT_KCS_ARTICLE_STYLE_REF_SET,
) -> tuple[KcsArticleStyleReference, ...]:
    """Load metadata-only public style references."""

    text = ref_set.read_text(encoding="utf-8")
    _assert_safe_text(text)
    refs: list[KcsArticleStyleReference] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("Each KCS article style ref line must be an object.")
        ref = KcsArticleStyleReference.from_json_dict(payload)
        _assert_safe_ref(ref)
        refs.append(ref)
    if not refs:
        raise ValueError("KCS article style reference set is empty.")
    if len({ref.ref_id for ref in refs}) != len(refs):
        raise ValueError("KCS article style reference IDs must be unique.")
    return tuple(refs)


def select_kcs_article_style_references(
    *,
    query_text: str,
    expected_article_type: str | None,
    max_refs: int = 3,
    ref_set: Path = DEFAULT_KCS_ARTICLE_STYLE_REF_SET,
) -> tuple[KcsArticleStyleReference, ...]:
    """Select a small set of style references by metadata overlap."""

    refs = load_kcs_article_style_references(ref_set)
    query_tokens = _tokens(query_text)
    scored: list[tuple[int, str, KcsArticleStyleReference]] = []
    for ref in refs:
        score = _score_ref(ref, query_tokens, expected_article_type)
        if score > 0:
            scored.append((score, ref.ref_id, ref))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in scored[:max(0, max_refs)])


def render_kcs_style_references_for_prompt(
    refs: tuple[KcsArticleStyleReference, ...],
) -> str:
    """Render safe style references for an agent prompt."""

    if not refs:
        return ""
    lines = [
        "Style references:",
        "",
        "Use these public articles only as metadata-level style references. Do not "
        "copy article bodies, steps, or claims unless they are independently "
        "supported by the investigation notes.",
        "",
    ]
    for index, ref in enumerate(refs, 1):
        lines.append(f"{index}. {ref.title}")
        lines.append(f"   URL: {ref.public_url}")
        lines.append(f"   Type: {ref.article_type}")
        if ref.coverage_tags:
            lines.append(f"   Coverage: {', '.join(ref.coverage_tags)}")
        if ref.style_hints:
            lines.append(f"   Style hints: {'; '.join(ref.style_hints)}")
        if ref.cautions:
            lines.append(f"   Cautions: {'; '.join(ref.cautions)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _score_ref(
    ref: KcsArticleStyleReference,
    query_tokens: set[str],
    expected_article_type: str | None,
) -> int:
    ref_tokens = _tokens(
        " ".join((ref.title, " ".join(ref.keywords), " ".join(ref.coverage_tags)))
    )
    score = len(query_tokens & ref_tokens)
    if expected_article_type and ref.article_type == expected_article_type:
        score += 3
    return score


def _tokens(text: str) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_RE.findall(text)
        if token.casefold() not in _STOP_WORDS
    }


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
            "KCS article style ref set contains a forbidden private fragment."
        )
    if _EMAIL_RE.search(text):
        raise ValueError(
            "KCS article style ref set must not contain email identifiers."
        )
    for match in _IPV4_RE.finditer(text):
        value = match.group(0)
        if not value.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
            raise ValueError(
                "KCS article style ref set must not contain private IPv4 values."
            )


def _assert_safe_ref(ref: KcsArticleStyleReference) -> None:
    if not re.fullmatch(r"[A-Z0-9_-]+", ref.ref_id):
        raise ValueError("KCS article style ref ID must be uppercase slug format.")
    if not ref.public_url.startswith("https://support.plesk.com/"):
        raise ValueError(
            "KCS article style ref URL must be an approved public Plesk Support URL."
        )
