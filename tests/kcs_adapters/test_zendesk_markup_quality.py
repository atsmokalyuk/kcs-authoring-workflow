from __future__ import annotations

from kcs_adapters.zendesk_markup_quality import review_kcs_zendesk_markup_source


def _rule_ids(source_html: str) -> set[str]:
    report = review_kcs_zendesk_markup_source(source_html)
    return {finding.rule_id for finding in report.findings}


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
