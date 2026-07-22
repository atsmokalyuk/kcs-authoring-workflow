from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLICE_PLANS = ROOT / "docs" / "internal" / "engineering-process" / "slice-plans"

RETAINED_KCS14_5_DOCS = {
    "kcs-14-5-contract-consolidation.md",
    "kcs-14-5-decision-log.md",
    "kcs-14-5-local-langfuse-observability.md",
    "kcs-14-5-multi-issue-component-forensic-audit.md",
    "kcs-14-5-semantic-stabilization-aggregate-attempt-review.md",
}


def test_kcs14_5_release_keeps_only_authoritative_closeout_docs() -> None:
    actual = {path.name for path in SLICE_PLANS.glob("kcs-14-5-*.md")}

    assert actual == RETAINED_KCS14_5_DOCS


def test_kcs14_5_status_records_failed_strict_stability_target() -> None:
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    aggregate = " ".join(
        (SLICE_PLANS / "kcs-14-5-semantic-stabilization-aggregate-attempt-review.md")
        .read_text(encoding="utf-8")
        .split()
    )
    consolidation = " ".join(
        (SLICE_PLANS / "kcs-14-5-contract-consolidation.md")
        .read_text(encoding="utf-8")
        .split()
    )

    assert "strict multi-issue stability target" in readme
    assert "did not establish stable candidate identity" in aggregate
    assert "strict semantic-stability target is now closed" in consolidation
    assert "semantic-review fallback has been stabilized" not in readme


def test_kcs14_5_decision_log_points_only_to_retained_local_evidence() -> None:
    decision_log = (
        SLICE_PLANS / "kcs-14-5-decision-log.md"
    ).read_text(encoding="utf-8")

    for name in RETAINED_KCS14_5_DOCS - {"kcs-14-5-decision-log.md"}:
        assert f"`{name}`" in decision_log
        assert (SLICE_PLANS / name).is_file()

    assert "feature/PAUX-7103-kcs-14.5-contract-consolidation" in decision_log
    assert "kcs-14-review-notes.md" not in decision_log
