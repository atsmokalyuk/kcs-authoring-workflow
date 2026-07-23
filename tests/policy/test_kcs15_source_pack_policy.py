from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "docs" / "internal" / "kcs-sources"
MATRIX_PATH = ROOT / "docs" / "internal" / "kcs-15-style-parity-matrix.md"

SNAPSHOT_PROVENANCE = {
    "kcs-style-guide-plesk.md": (
        "https://webpros.atlassian.net/wiki/spaces/SOLUS/pages/3649045319/"
        "KCS+Style+Guide",
        "cc940c94a94d7a6c18561eb36ba4e9af4e0cebd186d8acd5f30e12b8d774bbb4",
    ),
    "kcs-style-guide-webpros.md": (
        "https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902448/"
        "KCS+Style+Guide",
        "5a7f03e288a6f0699bdb6d0429f614629f9c94aa2247fd2df04447bbcf0acc6a",
    ),
    "article-quality-criteria.md": (
        "https://webpros.atlassian.net/wiki/spaces/CX/pages/5422743564/"
        "KCS+Article+Quality+Criteria",
        "9955dfdec1727d6747a98df24f8f9b0f39718f652fb07b86ece14c28424f1bf6",
    ),
    "kcs-content-standard-checklist.md": (
        "https://webpros.atlassian.net/wiki/spaces/CX/pages/5375295653/"
        "The+KCS+Content+Standard+Checklist",
        "2a4372d1cc5168d24695f25e22472817ad08bc5177c203d3dd8687c4da528886",
    ),
    "article-simplification-guide.md": (
        "https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902677/"
        "Article+simplification+guide",
        "a854af6d7e86c04562f4702add55be38a29a64da2d5bb4ad8b33d9e26a190baa",
    ),
    "kcs-style-triggers.md": (
        "https://support.plesk.com/hc/en-us/articles/"
        "12378148057495-KCS-Style-triggers",
        "450cd5038c51d969ecf1639187f55fe89ae20bac5955fb4f31944062bbf696fd",
    ),
    "kb-articles-best-practices-examples.md": (
        "https://webpros.atlassian.net/wiki/spaces/CX/pages/3156902730/"
        "Article+Quality+criteria#Examples",
        "e7ab27b5fe047089e654a04acc2d28189294012577d6a07d376054af4f4e108d",
    ),
}

FORBIDDEN_SOURCE_SUFFIXES = {
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".webp",
}

EVIDENCE_STATES = ("confirmed", "provisional", "unknown", "rejected")
GATE_CLASSES = ("deterministic", "bounded-model-trial", "named-human-review")


def test_kcs15_source_pack_has_all_approved_sources_and_snapshots() -> None:
    manifest = (SOURCE_DIR / "README.md").read_text(encoding="utf-8")

    for filename, (url, _) in SNAPSHOT_PROVENANCE.items():
        path = SOURCE_DIR / filename
        assert path.is_file(), filename
        assert f"docs/internal/kcs-sources/{filename}" in manifest
        assert url in manifest


def test_kcs15_snapshots_record_reviewable_provenance() -> None:
    for filename, (url, expected_hash) in SNAPSHOT_PROVENANCE.items():
        text = (SOURCE_DIR / filename).read_text(encoding="utf-8")
        normalized = " ".join(text.lower().split())
        assert "source of truth" in normalized, filename
        assert url in text, filename
        assert re.search(r"Captured: \d{4}-\d{2}-\d{2}\b", text), filename
        assert "Export filename:" in text, filename
        hashes = re.findall(r"`([a-f0-9]{64})`", text)
        assert hashes == [expected_hash], filename


def test_kcs15_source_pack_excludes_binary_exports_and_local_download_paths() -> None:
    violations: list[str] = []

    for path in SOURCE_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SOURCE_SUFFIXES:
            violations.append(str(path.relative_to(ROOT)))
        text = path.read_text(encoding="utf-8")
        if (
            "/Users/" in text
            or "Downloads/" in text
            or "yourpleskhost.ru" in text
            or re.search(r"^\s*!\[", text, re.M)
        ):
            violations.append(str(path.relative_to(ROOT)))

    assert not violations, "\n".join(violations)


def test_kcs15_source_precedence_records_operator_decisions() -> None:
    manifest = (SOURCE_DIR / "README.md").read_text(encoding="utf-8")
    practices = (SOURCE_DIR / "operator-kcs-practices.md").read_text(
        encoding="utf-8"
    )
    authority_ids = (
        "AUTH-MANDATORY",
        "AUTH-OPERATOR",
        "AUTH-PLESK-STYLE",
        "AUTH-AQ",
        "AUTH-WEBPROS",
        "AUTH-SIMPLIFICATION",
        "AUTH-EXAMPLES",
    )
    positions = [manifest.index(authority_id) for authority_id in authority_ids]

    assert positions == sorted(positions)
    for decision_id in (
        "OP-SOURCE-001",
        "OP-SOURCE-002",
        "OP-SOURCE-003",
        "OP-RAG-001",
        "OP-AUTH-001",
    ):
        assert decision_id in practices


def test_kcs15_parity_rows_use_evidence_states_and_gate_classes() -> None:
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    rows = [
        line
        for line in matrix.splitlines()
        if re.match(r"^\| `[A-Z]+-\d+` ", line)
    ]

    assert len(rows) >= 30
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 7, row
        assert cells[3] in EVIDENCE_STATES, row
        assert any(gate in cells[6] for gate in GATE_CLASSES), row


def test_kcs15_example_deck_is_supporting_and_superseded_advice_is_explicit() -> None:
    text = (SOURCE_DIR / "kb-articles-best-practices-examples.md").read_text(
        encoding="utf-8"
    )
    assert "Authority ID: `AUTH-EXAMPLES`" in text
    assert "Lifecycle in source: `beta`" in text
    assert "`AUTH-AQ` source-control rule" in text


def test_kcs15_tracking_separates_rag_enabling_from_parent_delivery() -> None:
    internal = ROOT / "docs" / "internal"
    process = internal / "engineering-process"
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    roadmap = (process / "engineering-roadmap.md").read_text(encoding="utf-8")
    adapter_plan = (
        process / "slice-plans/rag-1-local-public-adapter.md"
    ).read_text(encoding="utf-8")
    kcs15_1_plan = (
        process / "slice-plans/kcs-15-1-plesk-info-trigger-parity.md"
    ).read_text(encoding="utf-8")
    registry = (process / "engineering-rule-portability.md").read_text(
        encoding="utf-8"
    )
    practices = (SOURCE_DIR / "operator-kcs-practices.md").read_text(
        encoding="utf-8"
    )

    assert "Completed KCS-15 enabling slice: KCS-15.2a" in roadmap
    assert "Completed KCS-15 enabling slice: KCS-15.2b1" in roadmap
    assert "Authorized KCS-15.2b2 phase: Phase A" in roadmap
    assert "KCS-15.2b2 Phase B Delivery state: locked" in roadmap
    assert "target UX selection is not authorization" in roadmap
    assert "`KCS-15.3`" in matrix
    assert "`KCS-15.4`" in matrix
    assert "Status: completed" in adapter_plan
    assert "Outcome agreement: agreed" in adapter_plan
    assert "Design selection: open" in adapter_plan
    assert "Delivery authorization: locked" in adapter_plan
    assert "Status: completed" in kcs15_1_plan
    assert "ENG-PORT-DES-007" in registry
    assert "ENG-PORT-DES-008" in registry
    assert "ENG-PORT-DEL-008" in registry
    assert "KCS-14.5 is closed" in practices


def test_kcs15_explicit_article_priority_requires_helpful_ticket_evidence() -> None:
    internal = ROOT / "docs" / "internal"
    process = internal / "engineering-process"
    anchors = (
        (
            internal / "kcs-core-pipeline-architecture-and-contracts.md",
            "The caller may populate the priority-bearing "
            "`explicit_article` field only",
            "URL presence, a neutral mention",
        ),
        (
            internal / "kcs-core-pipeline-technical-design.md",
            "accepted, source-grounded ticket evidence says the article helped",
            "A URL-only, merely mentioned, unconfirmed, or confirmed-not-helpful",
        ),
        (
            internal / "kcs-authoring-mvp-data-handling-baseline.md",
            "accepted source-grounded ticket evidence says the article helped",
            "A URL-only, merely mentioned, unconfirmed, or confirmed-not-helpful",
        ),
        (
            process
            / "slice-plans/kcs-15-2b2-operator-confirmed-comparison-workflow.md",
            "`confirmed_partially_helpful`",
            "URL-only priority or partial match: rejected",
        ),
    )

    for path, helpful_anchor, rejection_anchor in anchors:
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert helpful_anchor in text, path.name
        assert rejection_anchor in text, path.name
