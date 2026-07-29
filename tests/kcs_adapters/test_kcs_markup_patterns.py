from __future__ import annotations

from kcs_adapters.kcs_markup_patterns import (
    KCS_MARKUP_PATTERN_SCHEMA_VERSION,
    load_kcs_markup_patterns,
    render_kcs_markup_patterns_for_prompt,
    select_kcs_markup_patterns,
)


def test_markup_patterns_are_safe_bounded_source_of_truth_snippets() -> None:
    patterns = load_kcs_markup_patterns()

    assert tuple(pattern.pattern_id for pattern in patterns) == (
        "resolution_container",
        "technical_symptoms_numbered_list",
        "gui_cli_tabs",
        "advanced_accordion",
        "internaldata_note",
        "linux_shell_trigger",
        "windows_command_trigger",
        "config_text_trigger",
        "warning_and_note_triggers",
        "powershell_trigger",
        "resizable_image",
        "style_guide_tabs",
        "style_guide_accordion",
        "style_guide_table",
    )
    assert len({pattern.pattern_id for pattern in patterns}) == len(patterns)
    for pattern in patterns:
        serialized = str(pattern.to_json_dict()).casefold()
        assert (
            pattern.to_json_dict()["schema_version"]
            == KCS_MARKUP_PATTERN_SCHEMA_VERSION
        )
        assert pattern.output_mode in {
            "zendesk_html",
            "zendesk_trigger_text",
            "markdown",
        }
        assert len(pattern.snippet.splitlines()) <= 12
        assert "ticket.final.clean.md" not in serialized
        assert ".private/" not in serialized
        assert "authorization: bearer" not in serialized

    config_text = next(
        pattern for pattern in patterns if pattern.pattern_id == "config_text_trigger"
    )
    assert any(
        "PLESK_INFO for white/gray Plesk errors and messages" in item
        for item in config_text.guidance
    )
    assert any(
        "do not infer the Plesk presentation trigger" in item
        for item in config_text.guidance
    )


def test_markup_pattern_prompt_is_html_specific_and_bounded() -> None:
    patterns = select_kcs_markup_patterns(max_patterns=2)

    rendered = render_kcs_markup_patterns_for_prompt(patterns)

    assert "Zendesk/KCS markup patterns" in rendered
    assert "Zendesk HTML/editor source" in rendered
    assert '<div class="resolution">' in rendered
    assert "<h2>Symptoms</h2>" in rendered
    assert "For plain Markdown drafts" in rendered
    assert "## Resolution" not in rendered
