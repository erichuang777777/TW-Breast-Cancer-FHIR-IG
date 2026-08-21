import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_release_controls import approval_complete, measure_approval_complete


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_release_controls.py"
CONTROLS = ROOT / "mappings" / "publication" / "release-control-register.csv"
MEASURES = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
TERMINOLOGY = ROOT / "ig" / "input" / "fsh" / "case-management-terminology.fsh"
APPROVALS = ROOT / "outputs" / "qbc_ig_mapping" / "qbc_mapping_approval_register.csv"
MEASURE_APPROVALS = (
    ROOT / "mappings" / "publication" / "case-management-measure-approval-register.csv"
)


def run_audit(
    tmp_path: Path,
    *,
    controls: Path = CONTROLS,
    measures: Path = MEASURES,
    approvals: Path = APPROVALS,
    measure_approvals: Path = MEASURE_APPROVALS,
    target: str = "integrity",
):
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
            "--measure-audit", str(measures),
            "--terminology-fsh", str(TERMINOLOGY),
            "--approval-register", str(approvals),
            "--measure-approval-register", str(measure_approvals),
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
    assert report["qbc_approval_count"] == 14
    assert report["measure_approval_count"] == 20
    assert report["approved_measure_definition_count"] == 0
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


def test_measure_approval_requires_decision_identity_date_evidence_and_hash():
    row = {
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Clinical owner",
        "signer_organization_title": "Hospital / committee chair",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/bc-qi-01.json",
        "signed_artifact_sha256": "",
    }
    assert not measure_approval_complete(row)
    row["signed_artifact_sha256"] = "b" * 64
    assert measure_approval_complete(row)


def test_deleting_a_required_qbc_gate_is_rejected(tmp_path):
    with APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    altered = tmp_path / "approvals.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows[:-1])
    completed, report = run_audit(tmp_path, approvals=altered)
    assert completed.returncode == 2
    assert report is None
    assert "exact 14 required gates" in completed.stderr


def test_deleting_a_measure_approval_is_rejected(tmp_path):
    with MEASURE_APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    altered = tmp_path / "measure-approvals.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows[:-1])
    completed, report = run_audit(tmp_path, measure_approvals=altered)
    assert completed.returncode == 2
    assert report is None
    assert "exactly one unique approval for each Measure" in completed.stderr


def test_signed_approvals_cannot_hide_unresolved_measure_definitions(tmp_path):
    with APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        qbc_rows = list(csv.DictReader(handle))
        qbc_fields = list(qbc_rows[0])
    for row in qbc_rows:
        row.update({
            "Status": "approved",
            "Decision (approve/reject/revise)": "approve",
            "Signer name": "Authorized owner",
            "Signer organization/title": "Hospital / authorized committee",
            "Decision date": "2026-08-21",
            "Evidence URI/path": f"evidence/{row['Gate ID']}.json",
            "Signed artifact SHA-256": "a" * 64,
        })
    qbc_signed = tmp_path / "qbc-signed.csv"
    with qbc_signed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=qbc_fields)
        writer.writeheader()
        writer.writerows(qbc_rows)

    with MEASURE_APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        measure_rows = list(csv.DictReader(handle))
        measure_fields = list(measure_rows[0])
    for row in measure_rows:
        row.update({
            "current_status": "approved",
            "decision": "approve",
            "signer_name": "Authorized clinical owner",
            "signer_organization_title": "Hospital / cancer committee",
            "decision_date": "2026-08-21",
            "evidence_uri_path": f"evidence/{row['measure_id']}.json",
            "signed_artifact_sha256": "b" * 64,
        })
    measures_signed = tmp_path / "measures-signed.csv"
    with measures_signed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=measure_fields)
        writer.writeheader()
        writer.writerows(measure_rows)

    completed, report = run_audit(
        tmp_path, approvals=qbc_signed, measure_approvals=measures_signed
    )
    assert completed.returncode == 1  # signed operational gates make declared RC-08 stale
    assert report["approved_measure_definition_count"] == 20
    assert report["derived_status"]["RC-07"] == "blocked"
    assert report["status_mismatches"] == [
        {"control_id": "RC-08", "declared": "blocked", "derived": "pass"}
    ]


def test_rc07_requires_both_complete_signatures_and_approved_alignment(tmp_path):
    with MEASURES.open(encoding="utf-8-sig", newline="") as handle:
        measure_audit_rows = list(csv.DictReader(handle))
        measure_audit_fields = list(measure_audit_rows[0])
    for row in measure_audit_rows:
        row["draft_definition_alignment"] = "approved"
    approved_audit = tmp_path / "measure-audit-approved.csv"
    with approved_audit.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=measure_audit_fields)
        writer.writeheader()
        writer.writerows(measure_audit_rows)

    with APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        qbc_rows = list(csv.DictReader(handle))
        qbc_fields = list(qbc_rows[0])
    for row in qbc_rows:
        row.update({
            "Status": "approved", "Decision (approve/reject/revise)": "approve",
            "Signer name": "Owner", "Signer organization/title": "Hospital / owner",
            "Decision date": "2026-08-21", "Evidence URI/path": "evidence/qbc.json",
            "Signed artifact SHA-256": "c" * 64,
        })
    qbc_signed = tmp_path / "qbc-all-signed.csv"
    with qbc_signed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=qbc_fields)
        writer.writeheader()
        writer.writerows(qbc_rows)

    with MEASURE_APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        measure_rows = list(csv.DictReader(handle))
        measure_fields = list(measure_rows[0])
    for row in measure_rows:
        row.update({
            "current_status": "approved", "decision": "approve",
            "signer_name": "Clinical owner",
            "signer_organization_title": "Hospital / cancer committee",
            "decision_date": "2026-08-21",
            "evidence_uri_path": "evidence/measures.json",
            "signed_artifact_sha256": "d" * 64,
        })
    measures_signed = tmp_path / "measures-all-signed.csv"
    with measures_signed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=measure_fields)
        writer.writeheader()
        writer.writerows(measure_rows)

    completed, report = run_audit(
        tmp_path,
        measures=approved_audit,
        approvals=qbc_signed,
        measure_approvals=measures_signed,
    )
    assert completed.returncode == 1  # declared RC-07 is still blocked in the real register
    assert report["derived_status"]["RC-07"] == "pass"
    assert report["status_mismatches"] == [
        {"control_id": "RC-07", "declared": "blocked", "derived": "pass"},
        {"control_id": "RC-08", "declared": "blocked", "derived": "pass"},
    ]
