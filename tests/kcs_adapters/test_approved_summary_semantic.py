from __future__ import annotations

import pytest

from kcs_adapters.approved_summary_semantic import (
    semantic_extraction_from_approved_summary_text,
)
from kcs_core.models import ArticleType
from kcs_core.semantic_extraction import validate_candidate_semantic_extraction


def test_approved_summary_semantic_extracts_explicit_labeled_item() -> None:
    extraction = semantic_extraction_from_approved_summary_text(
        "Title: Monitoring graphs show no data in Plesk\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Confirmed facts:\n"
        "- The collectd config points to a non-standard metric path.\n"
        "Cause: The collectd configuration points metric data to a path that "
        "the Monitoring backend does not query.\n"
        "Resolution steps:\n"
        "- Back up and disable the custom collectd configuration.\n"
        "- Restart sw-collectd.\n"
        "- Confirm Monitoring graphs show new data.\n"
    )

    assert extraction is not None
    validation = validate_candidate_semantic_extraction(extraction)
    assert validation.ok is True
    assert extraction["items"][0]["article_type_hint"] == (
        ArticleType.TECHNICAL_SCR.value
    )
    assert extraction["items"][0]["environment"]["applicable_to"] == [
        "Plesk for Linux"
    ]


def test_approved_summary_semantic_splits_explicit_items() -> None:
    extraction = semantic_extraction_from_approved_summary_text(
        "Item 1: Monitoring graphs show no data in Plesk\n"
        "Symptoms:\n"
        "- Monitoring graphs show no data.\n"
        "Cause: The collectd configuration points metrics to an unsupported "
        "path.\n"
        "Resolution steps:\n"
        "- Back up and disable the custom collectd configuration.\n"
        "- Restart sw-collectd.\n"
        "\n"
        "Item 2: Monitoring extension post-install fails\n"
        "Symptoms:\n"
        "- Monitoring extension post-install fails.\n"
        "Cause: The module directory has incorrect ownership.\n"
        "Resolution steps:\n"
        "- Verify the module directory ownership.\n"
        "- Reinstall the Monitoring extension.\n"
    )

    assert extraction is not None
    assert [item["candidate_id"] for item in extraction["items"]] == [
        "candidate-001",
        "candidate-002",
    ]
    assert validate_candidate_semantic_extraction(extraction).ok is True


def test_approved_summary_semantic_rejects_long_transcript_without_evidence() -> None:
    noisy_investigation = "\n".join(
        [
            "Avatar",
            "{{PERSON_NAME_002}}",
            "To: Client",
            "Show more",
            "I am logged in and checking the issue.",
            "Internal",
            "[{{SHELL_USERHOST_001}} ~]# ps aux",
            "many sw-engine-fpm workers are running",
            "I found that the panel was receiving many external requests.",
            "I created and tested a dedicated Fail2Ban rule for this traffic:",
            "fail2ban-regex /var/log/plesk/httpsd_access_log "
            "/etc/fail2ban/filter.d/plesk-panel-flood.conf",
            "systemctl reload fail2ban",
            "systemctl restart sw-engine sw-cp-server",
            "Later the customer asked about SSH connectivity and blocked IPs.",
            "As per the SSH access, Plesk does not manage it.",
        ]
        * 55
    )

    extraction = semantic_extraction_from_approved_summary_text(
        "# Customer Ticket Content\n\n"
        "I think my server is on attack, I blocked some IP but I think I have "
        "another thing.\n"
        f"{noisy_investigation}\n"
    )

    assert extraction is None


def test_approved_summary_semantic_returns_none_without_required_facts() -> None:
    assert (
        semantic_extraction_from_approved_summary_text(
            "Approved sanitized summary: Monitoring graphs show no data."
        )
        is None
    )


def test_approved_summary_semantic_skips_transcript_placeholders() -> None:
    extraction = semantic_extraction_from_approved_summary_text(
        "# Customer Ticket Content\n\n"
        "PERSON_NAME_1 reported from IP_ADDRESS_1.\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data.\n"
        "The issue is caused by /etc/sw-collectd/conf.d/"
        "02rrdtool-monitoring.conf pointing metric data to a path that the "
        "Monitoring backend does not query.\n"
        "Resolution: Back up and remove /etc/sw-collectd/conf.d/"
        "02rrdtool-monitoring.conf. Restart sw-collectd. Confirm Monitoring "
        "graphs start displaying data again.\n"
        "Do not include SHELL_USERHOST_1 in the article.\n"
    )

    assert extraction is not None
    assert validate_candidate_semantic_extraction(extraction).ok is True
    item_text = repr(extraction["items"][0])
    assert "PERSON_NAME_1" not in item_text
    assert "IP_ADDRESS_1" not in item_text
    assert "SHELL_USERHOST_1" not in item_text
    assert extraction["items"][0]["summary"] != "Customer Ticket Content"


def test_approved_summary_semantic_does_not_infer_windows_from_common_word() -> None:
    extraction = semantic_extraction_from_approved_summary_text(
        "Title: Plesk panel service requires restart\n"
        "Applicable To: Plesk for Linux\n"
        "Symptoms:\n"
        "- The Plesk panel does not respond.\n"
        "Cause: The service workers are overloaded.\n"
        "Resolution steps:\n"
        "- Close extra terminal windows.\n"
        "- Restart sw-engine.\n"
    )

    assert extraction is not None
    assert extraction["items"][0]["environment"]["applicable_to"] == [
        "Plesk for Linux"
    ]


def test_approved_summary_semantic_extracts_final_fix_from_ticket_transcript() -> None:
    extraction = semantic_extraction_from_approved_summary_text(
        "# Customer Ticket Content\n\n"
        "When loading the monitoring module in Plesk, none of the graphs show "
        "any data.\n"
        "We have un-installed and re-installed within the extentions section, "
        "and it still fails to give any data.\n"
        "logger=example t=2026-06-12 level=error msg=\"plugin process exited\" "
        "plugin=/var/lib/grafana/plugins/plesk-json-backend-datasource/dist/bin "
        "error=\"signal: terminated\"\n"
        "Server\n"
        "[root@server modules]# ls -ld /var/lib/grafana/\n"
        "drwxrwxr-x 3 root root 18 Jun 17 2021 "
        "plesk-json-backend-datasource grafana:grafana 750 Disabled\n"
        "Test server\n"
        "[root@10-66-95-94 monitoring]# stat -c '%U:%G %a' "
        "/var/lib/grafana/plugins/\n"
        "Saturday 11:16\n"
        "[{{SHELL_USERHOST_001}} ~]# rpm -qf "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf\n"
        "cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf\n"
        "file /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf is not owned "
        "by any package\n"
        "<Plugin rrdtool>\n"
        "    DataDir \"/usr/local/psa/var/modules/monitoring/rrd\"\n"
        "</Plugin>\n"
        "Root cause: leftover/custom unowned collectd override caused RRD files "
        "to be written to a path that Monitoring backend does not query "
        "correctly.\n"
        "[{{SHELL_USERHOST_001}} ~]# mkdir -p /root/monitoring-case-backup\n"
        "cp -a /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
        "/root/monitoring-case-backup/\n"
        "mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
        "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled\n"
        "systemctl restart sw-collectd\n"
        "I found that the Monitoring data collector was writing RRD metric "
        "files to a non-standard path due to a leftover custom/unowned collectd "
        "configuration file: /etc/sw-collectd/conf.d/"
        "02rrdtool-monitoring.conf. Because of this path mismatch, "
        "Grafana/Monitoring could list the metric names, but queries for graph "
        "datapoints returned no data. I backed up and disabled the incorrect "
        "configuration file, restarted the statistics collector, and confirmed "
        "that new metric data is now being written to the expected location. "
        "The Monitoring graphs have started displaying data again.\n"
    )

    assert extraction is not None
    assert validate_candidate_semantic_extraction(extraction).ok is True
    item = extraction["items"][0]
    item_text = repr(item)
    assert item["summary"] == (
        "Monitoring graphs show no data in Plesk due to custom unowned collectd "
        "configuration file"
    )
    assert item["symptoms"] == [
        "Plesk Monitoring graphs show no data.",
        (
            "Monitoring/Grafana can list metric names, but graph datapoint "
            "queries return no data."
        ),
    ]
    assert "02rrdtool-monitoring.conf" in item["supported_cause"]
    assert "plugin process exited" not in item_text
    assert "drwxrwxr-x" not in item_text
    assert "Test server" not in item_text
    assert item["resolution_steps"] == [
        (
            "Run rpm -qf /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to verify that the file is not owned by any package."
        ),
        (
            "Run cat /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "to review the DataDir setting."
        ),
        "Run mkdir -p /root/monitoring-case-backup to create a backup directory.",
        (
            "Run cp -a /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "/root/monitoring-case-backup/ to back up the configuration file."
        ),
        (
            "Run mv /etc/sw-collectd/conf.d/02rrdtool-monitoring.conf "
            "/etc/sw-collectd/conf.d/02rrdtool-monitoring.conf.disabled "
            "to disable the configuration file."
        ),
        "Run systemctl restart sw-collectd.",
        (
            "Open the Monitoring page in Plesk and confirm graphs start "
            "displaying data."
        ),
        (
            "Wait for graphs to repopulate with newly collected metrics; "
            "historical data from before the correction may not be visible."
        ),
    ]


def test_approved_summary_semantic_rejects_unsafe_summary() -> None:
    with pytest.raises(Exception):
        semantic_extraction_from_approved_summary_text("api_key=secret-value")
