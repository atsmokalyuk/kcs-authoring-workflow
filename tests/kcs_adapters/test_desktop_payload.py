from __future__ import annotations

import pytest

from kcs_adapters.desktop_payload import (
    ApprovedSummaryInputError,
    ApprovedSummaryPayloadArgumentError,
    approved_summary_pipeline_payload,
)
from kcs_core.models import ArticleType
from kcs_core.safety import InputClass


def _payload_args() -> dict[str, object]:
    return {
        "approved_summary_text": (
            "Approved sanitized summary: Monitoring graphs show no data."
        ),
        "item": {
            "article_type": ArticleType.TECHNICAL_SCR.value,
            "environment": {
                "applicable_to": ["Plesk for Linux"],
            },
            "evidence": "The sanitized summary confirms the config override.",
            "resolution_steps": [
                (
                    "Confirm the file contains a <Plugin rrdtool> block setting "
                    "DataDir to a non-default path."
                ),
                "Run systemctl restart sw-collectd.",
            ],
            "root_cause": "A leftover collector config redirects metric data.",
            "solution": "Disable the override and restart the collector.",
            "symptom": "Monitoring graphs show no data.",
            "title": "Monitoring graphs show no data",
        },
        "reuse_search_checked": True,
        "reuse_search_run_ref": "reuse-search-001",
    }


def test_desktop_payload_normalizes_aliases_and_applicable_to() -> None:
    payload = approved_summary_pipeline_payload(_payload_args())

    candidate = payload["issue_candidates"][0]
    assert payload["input_class"] == InputClass.OPERATOR_SANITIZED_SUMMARY.value
    assert candidate["article_type"] == ArticleType.TECHNICAL_SCR.value
    assert candidate["applicable_to"] == ["Plesk for Linux"]
    assert candidate["confirmed_facts"] == [
        "The sanitized summary confirms the config override."
    ]
    assert candidate["environment"] == {"platform": "Plesk for Linux"}
    assert candidate["supported_cause"] == (
        "A leftover collector config redirects metric data."
    )
    assert candidate["supported_resolution_or_workaround"] == (
        "Disable the override and restart the collector."
    )
    assert candidate["symptoms"] == ["Monitoring graphs show no data."]


def test_desktop_payload_rejects_unknown_item_field_as_argument_shape() -> None:
    arguments = _payload_args()
    assert isinstance(arguments["item"], dict)
    arguments["item"]["unexpected"] = "safe-looking value"

    with pytest.raises(ApprovedSummaryPayloadArgumentError):
        approved_summary_pipeline_payload(arguments)


def test_desktop_payload_keeps_existing_content_debug_codes() -> None:
    arguments = _payload_args()
    assert isinstance(arguments["item"], dict)
    arguments["item"].pop("resolution_steps")

    with pytest.raises(ApprovedSummaryInputError) as exc_info:
        approved_summary_pipeline_payload(arguments)

    assert exc_info.value.debug_code == "approved_summary_resolution_steps_required"
