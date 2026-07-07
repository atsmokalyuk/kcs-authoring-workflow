from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "measure_complexity.py"


def test_complexity_measurement_outputs_advisory_snapshot() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--extra",
            "dev",
            "python",
            str(SCRIPT.relative_to(ROOT)),
            "--paths",
            "scripts/measure_complexity.py",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    snapshot = json.loads(result.stdout)

    assert snapshot["schema_version"] == "kcs_complexity_snapshot_v1"
    assert snapshot["threshold"] == 7
    assert snapshot["summary"]["files_scanned"] == 1
    assert "cc_average" in snapshot["summary"]
    assert "import_edges" in snapshot["summary"]
    assert "public_defs" in snapshot["summary"]
    assert "scripts" in snapshot["groups"]


def test_complexity_measurement_compares_to_baseline() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--extra",
            "dev",
            "python",
            str(SCRIPT.relative_to(ROOT)),
            "--baseline",
            "docs/internal/engineering-process/kcs-14-complexity-baseline.json",
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    snapshot = json.loads(result.stdout)

    assert "delta_from_baseline" in snapshot
    assert "max_cc" in snapshot["delta_from_baseline"]
