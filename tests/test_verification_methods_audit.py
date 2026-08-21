import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_verification_methods.py"
REGISTER = ROOT / "mappings" / "publication" / "verification-method-register.csv"
CONTROLS = ROOT / "mappings" / "publication" / "release-control-register.csv"


def release_report() -> dict:
    return {
        "control_count": 8,
        "data_correctness_control_count": 6,
        "derived_status": {
            "RC-01": "blocked",
            "RC-02": "pass",
            "RC-03": "blocked",
            "RC-04": "pass",
            "RC-05": "blocked",
            "RC-06": "blocked",
            "RC-07": "blocked",
            "RC-08": "blocked",
        },
        "control_integrity_gate": "pass",
        "data_correctness_gate": "block",
        "formal_release_gate": "block",
        "maximum_supported_claim": "technical-draft-only",
    }


def run_audit(tmp_path: Path, *, register: Path = REGISTER, release: dict | None = None, target: str = "integrity"):
    release_path = tmp_path / "release.json"
    release_path.write_text(json.dumps(release or release_report()), encoding="utf-8")
    output = tmp_path / "verification.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--register", str(register),
            "--controls", str(CONTROLS),
            "--release-audit", str(release_path),
            "--json-out", str(output),
            "--target", target,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    return completed, report


def test_exact_eight_methods_map_one_to_one_to_release_controls(tmp_path):
    completed, report = run_audit(tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert report["method_count"] == 8
    assert report["data_correctness_method_count"] == 6
    assert report["release_acceptance_method_count"] == 2
    assert report["passed_methods"] == ["VM-02", "VM-04"]
    assert report["blocked_methods"] == [
        "VM-01", "VM-03", "VM-05", "VM-06", "VM-07", "VM-08"
    ]
    assert report["verification_catalog_integrity_gate"] == "pass"
    assert report["formal_release_gate"] == "block"


def test_lowering_zero_difference_threshold_is_rejected(tmp_path):
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[4]["pass_threshold"] = rows[4]["pass_threshold"].replace(
        "0 unexplained", "review unexplained"
    )
    altered = tmp_path / "methods.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    completed, report = run_audit(tmp_path, register=altered)
    assert completed.returncode == 2
    assert report is None
    assert "pass threshold lost marker '0 unexplained'" in completed.stderr


def test_release_status_cannot_disagree_with_declared_controls(tmp_path):
    release = release_report()
    release["derived_status"]["RC-01"] = "pass"
    completed, report = run_audit(tmp_path, release=release)
    assert completed.returncode == 2
    assert report is None
    assert "declared and derived controls are not identical" in completed.stderr


def test_integrity_pass_does_not_mean_data_or_formal_release_pass(tmp_path):
    completed, report = run_audit(tmp_path, target="data")
    assert completed.returncode == 1
    assert report["verification_catalog_integrity_gate"] == "pass"
    assert report["data_correctness_gate"] == "block"
    completed, report = run_audit(tmp_path, target="formal")
    assert completed.returncode == 1
    assert report["formal_release_gate"] == "block"
