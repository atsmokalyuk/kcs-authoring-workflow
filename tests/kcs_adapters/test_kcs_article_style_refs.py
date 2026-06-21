from __future__ import annotations

from kcs_adapters.kcs_article_style_refs import (
    KCS_ARTICLE_STYLE_REF_SCHEMA_VERSION,
    load_kcs_article_style_references,
    render_kcs_style_references_for_prompt,
    select_kcs_article_style_references,
)


def test_style_refs_are_metadata_only_safe_public_refs() -> None:
    refs = load_kcs_article_style_references()

    assert len(refs) >= 8
    assert len({ref.ref_id for ref in refs}) == len(refs)
    for ref in refs:
        serialized = str(ref.to_json_dict()).casefold()
        assert (
            ref.to_json_dict()["schema_version"]
            == KCS_ARTICLE_STYLE_REF_SCHEMA_VERSION
        )
        assert ref.public_url.startswith("https://support.plesk.com/")
        assert ref.article_type in {"technical_scr", "howto_qa"}
        assert ref.keywords
        assert ref.style_hints
        assert "ticket.final.clean.md" not in serialized
        assert ".private/" not in serialized
        assert "snippet body" not in serialized


def test_style_refs_select_by_metadata_without_article_body() -> None:
    refs = select_kcs_article_style_references(
        query_text="How to add custom PHP version in Plesk on Ubuntu Debian",
        expected_article_type="howto_qa",
        max_refs=2,
    )

    rendered = render_kcs_style_references_for_prompt(refs)

    assert refs
    assert refs[0].ref_id == "KCS-STYLE-HOWTO-CUSTOM-PHP"
    assert "Style references" in rendered
    assert "Do not copy article bodies" in rendered
    assert "## Symptoms" not in rendered
    assert "## Resolution" not in rendered
