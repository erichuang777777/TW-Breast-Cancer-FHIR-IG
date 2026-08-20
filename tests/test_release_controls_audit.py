import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_release_controls import approval_complete


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_release_controls.py"
CONTROLS = ROOT / "mappings" / "publication" / "release-control-register.csv"
MEASURES = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
TERMINOLOGY = ROOT / "ig" / "input" / "fsh" / "case-management-terminology.fsh"
APPROVALS = ROOT / "outputs" / "qbc_ig_mapping" / "qbc_mapping_approval_register.csv"


def run_audit(tmp_path: Path, *, controls: Path = CONTROLS, target: str = "integrity"):
    publisher = tmp_path / "publisher.json"
    publisher.write_text(
        json.dumps({
            "gate_scope": "publisher-qa-only",
            "qa_integrity_gate": "pass",
            "formal_release_gate": "pass",
        }),
        encoding="utf-8",
    )
    output = tmp_path / "release.json"
    completed = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--controls", str(controls),
            "--measure-audit", str(MEASURES),
            "--terminology-fsh", str(TERMINOLOGY),
            "--approval-register", str(APPROVALS),
            "--publisher-audit", str(publisher),
            "--json-out", str(output),
            "--target", target,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    return completed, report


def test_current_register_is_truthful_and_only_two_of_eight_controls_pass(tmp_path):
    completed, report = run_audit(tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert report["control_integrity_gate"] == "pass"
    assert report["passed_controls"] == ["RC-02", "RC-04"]
    assert report["blocked_controls"] == [
        "RC-01", "RC-03", "RC-05", "RC-06", "RC-07", "RC-08"
    ]
    assert report["clinical_valuesets"] == 19
    assert report["empty_clinical_valuesets"] == 19
    assert report["data_correctness_gate"] == "block"
    assert report["formal_release_gate"] == "block"
    assert report["maximum_supported_claim"] == "technical-draft-only"


def test_zero_publisher_warnings_cannot_bypass_clinical_release_controls(tmp_path):
    completed, report = run_audit(tmp_path, target="formal")
    assert completed.returncode == 1
    assert report["publisher_formal_qa_gate"] == "pass"
    assert report["formal_release_gate"] == "block"


def test_declared_control_status_must_match_derived_evidence(tmp_path):
    with CONTROLS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    rows[0]["current_status"] = "pass"
    altered = tmp_path / "controls.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    completed, report = run_audit(tmp_path, controls=altered)
    assert completed.returncode == 1
    assert report["control_integrity_gate"] == "fail"
    assert report["status_mismatches"] == [
        {"control_id": "RC-01", "declared": "pass", "derived": "blocked"}
    ]


def test_approval_status_alone_cannot_fake_a_signed_release_decision():
    row = {
        "Status": "approved",
        "Decision (approve/reject/revise)": "approve",
        "Signer name": "Reviewer",
        "Signer organization/title": "Hospital / owner",
        "Decision date": "2026-08-21",
        "Evidence URI/path": "evidence/review.json",
        "Signed artifact SHA-256": "",
    }
    assert not approval_complete(row)
    row["Signed artifact SHA-256"] = "a" * 64
    assert approval_complete(row)
