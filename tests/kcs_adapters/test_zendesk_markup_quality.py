from __future__ import annotations

from kcs_adapters.zendesk_markup_quality import review_kcs_zendesk_markup_source


def _rule_ids(source_html: str) -> set[str]:
    report = review_kcs_zendesk_markup_source(source_html)
    return {finding.rule_id for finding in report.findings}


def _severity_by_rule(source_html: str) -> dict[str, str]:
    report = review_kcs_zendesk_markup_source(source_html)
    return {finding.rule_id: finding.severity for finding in report.findings}


def test_zendesk_markup_quality_blocks_vague_file_action_article() -> None:
    source = (
        "<h1>Product task fails in Plesk due to custom configuration file</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
        "<h2>Symptoms</h2><ol><li>A product task fails in Plesk.</li></ol>"
        "<h2>Cause</h2>"
        "<p>The custom configuration file /etc/product/conf.d/custom.conf "
        "overrides the product service configuration.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li>Connect to the Plesk server via SSH.</li>"
        "<li>Back up and disable /etc/product/conf.d/custom.conf.</li>"
        "<li>Run systemctl restart product-service.</li>"
        "</ol></div>"
    )

    assert {
        "resolution_missing_concrete_file_commands",
    }.issubset(_rule_ids(source))


def test_zendesk_markup_quality_blocks_technical_action_without_how() -> None:
    source = (
        "<h1>High CPU load on a Plesk server due to HTTP flood traffic</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
        "<h2>Symptoms</h2><ol><li>The server has high CPU load.</li></ol>"
        "<h2>Cause</h2><p>HTTP requests overloaded the Plesk Panel endpoint.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li><a href=\"https://support.plesk.com/hc/en-us/articles/"
        "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH\">"
        "Connect to the Plesk server via SSH.</a></li>"
        "<li>Create a custom filter at "
        "<code>/etc/fail2ban/filter.d/panel-flood.conf</code> "
        "matching repeated requests.</li>"
        "<li>Block the flood traffic on the affected port.</li>"
        "</ol></div>"
    )

    assert {
        "resolution_action_missing_implementation_detail",
    }.issubset(_rule_ids(source))


def test_zendesk_markup_quality_blocks_branching_and_command_only_steps() -> None:
    source = (
        "<h1>Product task fails in Plesk due to custom configuration file</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
        "<h2>Symptoms</h2><ol><li>A product task fails in Plesk.</li></ol>"
        "<h2>Cause</h2>"
        "<p>The custom configuration file overrides the product service.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li><a href=\"https://support.plesk.com/hc/en-us/articles/"
        "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH\">"
        "Connect to the Plesk server via SSH.</a></li>"
        "<li>If the first mitigation does not help, continue with the "
        "fallback command.</li>"
        "<li># systemctl restart product-service</li>"
        "</ol></div>"
    )

    assert {
        "resolution_main_path_has_if_then_branching",
        "optional_resolution_path_not_collapsed",
        "resolution_command_or_note_numbered_as_step",
    }.issubset(_rule_ids(source))
    severities = _severity_by_rule(source)
    assert severities["resolution_main_path_has_if_then_branching"] == "warning"
    assert severities["optional_resolution_path_not_collapsed"] == "warning"
    assert severities["resolution_command_or_note_numbered_as_step"] == "blocker"


def test_zendesk_markup_quality_accepts_golden_scr_markup_fixture() -> None:
    source = (
        "<h1>Product task fails in Plesk due to custom configuration file</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
        "<h2>Symptoms</h2><ol><li>A product task fails in Plesk.</li></ol>"
        "<h2>Cause</h2>"
        "<p>The custom configuration file /etc/product/conf.d/custom.conf "
        "overrides the product service configuration.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li><a href=\"https://support.plesk.com/hc/en-us/articles/"
        "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH\">"
        "Connect to the Plesk server via SSH.</a></li>"
        "<li>Run rpm -qf /etc/product/conf.d/custom.conf "
        "to verify that the file is not owned by any package.</li>"
        "<li>Run cat /etc/product/conf.d/custom.conf "
        "to review the file content.</li>"
        "<li>Run mkdir -p /root/kcs-case-backup to create a backup "
        "directory.</li>"
        "<li>Run cp -a /etc/product/conf.d/custom.conf "
        "/root/kcs-case-backup/ to back up the configuration file.</li>"
        "<li>Run mv /etc/product/conf.d/custom.conf "
        "/etc/product/conf.d/custom.conf.disabled to disable the configuration "
        "file.</li>"
        "<li>Run systemctl restart product-service.</li>"
        "<li>Open the affected Plesk page and confirm the task succeeds.</li>"
        "</ol></div>"
    )

    assert review_kcs_zendesk_markup_source(source).ok is True


def test_zendesk_markup_quality_flags_style_guide_markup_issues() -> None:
    source = (
        "<h1>Plesk issue</h1>"
        "<h2>Applicable to</h2><ul><li>All supported versions</li></ul>"
        "<h2>Symptoms</h2><ol><li>Plesk Firewall shows an error.</li></ol>"
        "<h2>Cause</h2><p>The cause is not clear at the moment.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li>Log in to Plesk.</li>"
        "<li>Go to Tools &amp; Settings &gt; Firewall.</li>"
        "<li>PLESK_INFO: 500 Internal Server Error</li>"
        "</ol></div>"
        "<h2>Related articles</h2><p>See more articles.</p>"
    )

    assert {
        "source_title_missing_error_or_issue_detail",
        "environment_scope_too_broad",
        "resolution_plesk_login_howto_link_missing",
        "resolution_reusable_howto_missing_link",
        "plesk_info_used_for_error_message",
        "gui_path_not_bold",
        "related_articles_section_present",
        "language_confidence_weak",
    }.issubset(_rule_ids(source))


def test_zendesk_markup_quality_flags_language_style_issues() -> None:
    source = (
        "<h1>Unable to open Plesk: 500 Internal Server Error</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Linux</li></ul>"
        "<h2>Symptoms</h2><ol><li>Plesk shows "
        "<strong>500 Internal Server Error</strong>.</li></ol>"
        "<h2>Cause</h2><p>The issue probably happens because a service is hanged.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li><a href=\"https://support.plesk.com/hc/en-us/articles/"
        "12377512781975-How-to-connect-to-a-Plesk-server-via-SSH\">"
        "Connect to the Plesk server via SSH.</a></li>"
        "<li>Run the following command in order to restart the service: "
        "<p><code># systemctl restart product-service</code></p></li>"
        "<li>We confirm that the service starts.</li>"
        "</ol></div>"
    )

    assert {
        "language_confidence_weak",
        "language_personal_pronoun_present",
        "language_diminishing_product_wording",
        "language_resolution_step_wordy",
    }.issubset(_rule_ids(source))


def test_zendesk_markup_quality_flags_style_guide_html_shapes() -> None:
    source = (
        "<h1>Unable to run task in Plesk: PowerShell command fails</h1>"
        "<h2>Applicable to</h2><ul><li>Plesk for Windows</li></ul>"
        "<h2>Symptoms</h2><ol><li>PowerShell command fails in Plesk.</li></ol>"
        "<h2>Cause</h2><p>A custom Windows path is used.</p>"
        "<h2>Resolution</h2><div class=\"resolution\"><ol>"
        "<li>Run PowerShell Get-Service PleskControlPanel.</li>"
        "<li>Edit C:\\Program Files\\Plesk\\admin\\conf\\panel.ini.</li>"
        "</ol></div>"
        "<p><img src=\"https://support.plesk.com/example/image.png\" alt=\"State\"></p>"
        "<div class=\"accordion-custom\">Optional details.</div>"
        "<table><tbody><tr><td>Value</td></tr></tbody></table>"
        "<p><a href=\"https://support.plesk.com/example/file.txt\">"
        "download file</a></p>"
    )

    assert {
        "powershell_trigger_missing",
        "windows_plesk_path_placeholder_missing",
        "article_media_image_not_resizable",
        "accordion_markup_unknown_shape",
        "table_markup_wrapper_missing",
        "attachment_archive_format_missing",
    }.issubset(_rule_ids(source))
