from __future__ import annotations

import json
from pathlib import Path

from kcs_core.models import KcsReviewerPacket

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_fixtures_load_as_contract_packets() -> None:
    fixture_paths = sorted(FIXTURE_DIR.glob("*.json"))

    assert fixture_paths
    for fixture_path in fixture_paths:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        packet = KcsReviewerPacket.from_json_dict(payload)

        assert packet.schema_version == KcsReviewerPacket.SCHEMA_VERSION
        assert packet.case_ref.startswith("CASE-SYNTH-")
        assert packet.auto_publish_allowed is False
        assert packet.to_json_dict() == payload
