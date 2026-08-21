import csv
import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_release_controls import (
    approval_complete,
    measure_approval_complete,
    scope_decision_complete,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_release_controls.py"
CONTROLS = ROOT / "mappings" / "publication" / "release-control-register.csv"
MEASURES = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
TERMINOLOGY = ROOT / "ig" / "input" / "fsh" / "case-management-terminology.fsh"
APPROVALS = ROOT / "outputs" / "qbc_ig_mapping" / "qbc_mapping_approval_register.csv"
MEASURE_APPROVALS = (
    ROOT / "mappings" / "publication" / "case-management-measure-approval-register.csv"
)
SCOPE_CLAIMS = ROOT / "mappings" / "publication" / "ig-scope-claim-register.csv"
SCOPE_DECISIONS = (
    ROOT / "mappings" / "publication" / "publication-scope-decision-register.csv"
)


def run_audit(
    tmp_path: Path,
    *,
    controls: Path = CONTROLS,
    measures: Path = MEASURES,
    approvals: Path = APPROVALS,
    measure_approvals: Path = MEASURE_APPROVALS,
    scope_claims: Path = SCOPE_CLAIMS,
    scope_decisions: Path = SCOPE_DECISIONS,
    artifact_approved: bool = False,
    terminology_overrides: dict | None = None,
    inventory_overrides: dict | None = None,
    reference_overrides: dict | None = None,
    data_evidence_overrides: dict | None = None,
    criterion_resolution_approved: bool = False,
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
    artifact_audit = tmp_path / "artifact-audit.json"
    artifact_audit.write_text(
        json.dumps({
            "gate_scope": "artifact-structure-and-example-only",
            "artifact_integrity_gate": "pass",
            "artifact_count": 47,
            "profile_count": 34,
            "extension_count": 13,
            "approved_artifact_count": 47 if artifact_approved else 0,
            "clinical_artifact_approval_gate": "pass" if artifact_approved else "block",
        }),
        encoding="utf-8",
    )
    terminology_audit = tmp_path / "terminology-audit.json"
    terminology_report = {
        "gate_scope": "complete-local-terminology-technical-and-clinical",
        "terminology_integrity_gate": "pass",
        "terminology_artifact_count": 152,
        "code_system_count": 60,
        "value_set_count": 90,
        "concept_map_count": 2,
        "empty_clinical_value_set_count": 19,
        "clinical_value_set_approval_count": 19,
        "approved_clinical_value_set_count": 0,
        "clinical_terminology_gate": "block",
    }
    terminology_report.update(terminology_overrides or {})
    terminology_audit.write_text(json.dumps(terminology_report), encoding="utf-8")
    inventory_audit = tmp_path / "inventory-audit.json"
    inventory_report = {
        "gate_scope": "exact-complete-fhir-resource-inventory-and-ig-manifest",
        "resource_inventory_gate": "pass",
        "resource_count": 262,
        "publication_definition_count": 225,
        "synthetic_example_count": 37,
        "canonical_resource_count": 223,
        "manual_json_resource_count": 103,
        "generated_fsh_resource_count": 159,
        "measure_count": 20,
        "canonical_version_policy_count": 4,
        "approved_canonical_version_policy_count": 0,
        "canonical_version_policy_group_counts": {
            "CV-PACKAGE-EXPLICIT": 24,
            "CV-CQL-LIBRARY": 1,
            "CV-PACKAGE-CONTEXT": 97,
            "CV-TCR-MANUAL": 101,
        },
        "canonical_version_policy_states": {
            "CV-PACKAGE-EXPLICIT": "explicit-package-version",
            "CV-CQL-LIBRARY": "cql-library-version",
            "CV-PACKAGE-CONTEXT": "package-context-policy-pending",
            "CV-TCR-MANUAL": "fhir-version-collision",
        },
        "manual_canonical_versions": ["4.0.1"],
        "business_version_provenance_gate": "block",
    }
    inventory_report.update(inventory_overrides or {})
    inventory_audit.write_text(json.dumps(inventory_report), encoding="utf-8")
    reference_graph_audit = tmp_path / "reference-graph-audit.json"
    reference_report = {
        "gate_scope": "complete-local-fhir-reference-and-canonical-graph",
        "reference_graph_integrity_gate": "pass",
        "resource_count": 262,
        "local_url_link_occurrence_count": 662,
        "local_url_link_counts": {
            "bundle-fullUrl": 19,
            "canonical-field": 233,
            "code-system-use": 153,
            "conceptmap-code-system-use": 2,
            "extension-use-url": 240,
            "fixed-extension-url": 13,
            "naming-system-use": 2,
        },
        "unique_local_url_target_count": 198,
        "canonical_reference_occurrence_count": 269,
        "local_canonical_reference_occurrence_count": 233,
        "external_canonical_reference_occurrence_count": 36,
        "unique_external_canonical_count": 18,
        "external_canonical_authority_counts": {
            "fhir-r4-core-4.0.1": 34,
            "tw-core-1.0.0": 2,
        },
        "versioned_canonical_reference_occurrence_count": 0,
        "fhir_reference_occurrence_count": 330,
        "manifest_reference_occurrence_count": 261,
        "non_manifest_reference_occurrence_count": 69,
        "total_audited_reference_edge_count": 1028,
    }
    reference_report.update(reference_overrides or {})
    reference_graph_audit.write_text(
        json.dumps(reference_report),
        encoding="utf-8",
    )
    data_evidence_audit = tmp_path / "data-evidence-audit.json"
    data_evidence_report = {
        "gate_scope": "raw-source-independent-recalculation-and-golden-cohort",
        "expected_fact_count": 52,
        "source_evidence_row_count": 52,
        "secondary_reconciliation_row_count": 0,
        "approved_secondary_reconciliation_row_count": 0,
        "approved_authoritative_or_derived_fact_count": 0,
        "measure_count": 20,
        "population_criterion_count": 68,
        "criterion_referenced_fact_count": 45,
        "approved_independent_recalculation_count": 0,
        "approved_golden_cohort_count": 0,
        "source_register_integrity_gate": "pass",
        "validation_register_integrity_gate": "pass",
        "raw_source_traceability_gate": "block",
        "independent_recalculation_gate": "block",
        "golden_cohort_gate": "block",
    }
    data_evidence_report.update(data_evidence_overrides or {})
    data_evidence_audit.write_text(
        json.dumps(data_evidence_report), encoding="utf-8"
    )
    criterion_resolution_audit = tmp_path / "criterion-resolution-audit.json"
    approved_resolution_count = 12 if criterion_resolution_approved else 0
    criterion_resolution_audit.write_text(
        json.dumps({
            "gate_scope": "all-current-non-aligned-criterion-resolution-decisions",
            "decision_count": 12,
            "decision_group_count": 8,
            "issue_class_counts": {
                "candidate-not-approved": 1,
                "conditional-data-contract": 2,
                "definition-contradiction": 1,
                "implemented-variant-unresolved": 3,
                "known-not-enforced": 1,
                "task-layer-only": 4,
            },
            "approved_decision_count": approved_resolution_count,
            "pending_decision_count": 12 - approved_resolution_count,
            "current_non_aligned_decision_count": (
                0 if criterion_resolution_approved else 12
            ),
            "production_allowed_decision_count": (
                12 if criterion_resolution_approved else 0
            ),
            "decision_register_integrity_gate": "pass",
            "criterion_resolution_gate": (
                "pass" if criterion_resolution_approved else "block"
            ),
        }),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--controls", str(controls),
            "--measure-audit", str(measures),
            "--terminology-fsh", str(TERMINOLOGY),
            "--approval-register", str(approvals),
            "--measure-approval-register", str(measure_approvals),
            "--scope-claims", str(scope_claims),
            "--scope-decisions", str(scope_decisions),
            "--artifact-audit", str(artifact_audit),
            "--terminology-audit", str(terminology_audit),
            "--resource-inventory-audit", str(inventory_audit),
            "--reference-graph-audit", str(reference_graph_audit),
            "--data-evidence-audit", str(data_evidence_audit),
            "--criterion-resolution-audit", str(criterion_resolution_audit),
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
    assert report["scope_claim_count"] == 10
    assert report["scope_decision_count"] == 10
    assert report["approved_scope_decision_count"] == 0
    assert report["normative_scope_readiness"] == "block"
    assert report["artifact_conformance_count"] == 47
    assert report["approved_artifact_count"] == 0
    assert report["clinical_artifact_approval_gate"] == "block"
    assert report["terminology_artifact_count"] == 152
    assert report["clinical_value_set_approval_count"] == 19
    assert report["approved_clinical_value_set_count"] == 0
    assert report["clinical_terminology_gate"] == "block"
    assert report["fhir_resource_count"] == 262
    assert report["publication_definition_count"] == 225
    assert report["synthetic_example_count"] == 37
    assert report["canonical_resource_count"] == 223
    assert report["canonical_version_policy_count"] == 4
    assert report["approved_canonical_version_policy_count"] == 0
    assert report["canonical_version_policy_group_counts"]["CV-TCR-MANUAL"] == 101
    assert report["canonical_version_policy_states"]["CV-TCR-MANUAL"] == (
        "fhir-version-collision"
    )
    assert report["manual_canonical_versions"] == ["4.0.1"]
    assert report["business_version_provenance_gate"] == "block"
    assert report["reference_graph_integrity_gate"] == "pass"
    assert report["total_audited_reference_edge_count"] == 1028
    assert report["local_url_link_occurrence_count"] == 662
    assert report["fhir_reference_occurrence_count"] == 330
    assert report["external_canonical_reference_occurrence_count"] == 36
    assert report["source_fact_count"] == 52
    assert report["approved_authoritative_or_derived_fact_count"] == 0
    assert report["approved_independent_recalculation_count"] == 0
    assert report["approved_golden_cohort_count"] == 0
    assert report["criterion_resolution_decision_count"] == 12
    assert report["approved_criterion_resolution_decision_count"] == 0
    assert report["non_aligned_criterion_resolution_decision_count"] == 12
    assert report["production_allowed_criterion_resolution_decision_count"] == 0
    assert report["criterion_resolution_gate"] == "block"
    assert report["data_correctness_gate"] == "block"
    assert report["formal_release_gate"] == "block"
    assert report["maximum_supported_claim"] == "technical-draft-only"


def test_zero_publisher_warnings_cannot_bypass_clinical_release_controls(tmp_path):
    completed, report = run_audit(tmp_path, target="formal")
    assert completed.returncode == 1
    assert report["publisher_formal_qa_gate"] == "pass"
    assert report["formal_release_gate"] == "block"


def test_terminology_inventory_count_cannot_be_reduced(tmp_path):
    completed, report = run_audit(
        tmp_path, terminology_overrides={"terminology_artifact_count": 151}
    )
    assert completed.returncode == 2
    assert report is None
    assert "terminology_artifact_count must be 152" in completed.stderr


def test_terminology_gate_cannot_contradict_empty_or_unsigned_counts(tmp_path):
    completed, report = run_audit(
        tmp_path, terminology_overrides={"clinical_terminology_gate": "pass"}
    )
    assert completed.returncode == 2
    assert report is None
    assert "clinical terminology gate/count mismatch" in completed.stderr


def test_fhir_resource_inventory_count_cannot_be_reduced(tmp_path):
    completed, report = run_audit(
        tmp_path, inventory_overrides={"resource_count": 261}
    )
    assert completed.returncode == 2
    assert report is None
    assert "resource_count must be 262" in completed.stderr


def test_reference_graph_count_cannot_be_reduced(tmp_path):
    completed, report = run_audit(
        tmp_path, reference_overrides={"total_audited_reference_edge_count": 1027}
    )
    assert completed.returncode == 2
    assert report is None
    assert "total_audited_reference_edge_count must be 1028" in completed.stderr


def test_measure_summary_cannot_fake_source_independent_or_golden_evidence(tmp_path):
    with MEASURES.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    for row in rows:
        row["raw_source_mapping"] = "pass"
        row["independent_recalculation"] = "pass"
        row["golden_cohort"] = "pass"
    altered = tmp_path / "measures.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    completed, report = run_audit(tmp_path, measures=altered)
    assert completed.returncode == 0
    assert report["derived_status"]["RC-01"] == "blocked"
    assert report["derived_status"]["RC-05"] == "blocked"
    assert report["derived_status"]["RC-06"] == "blocked"


def test_business_version_gate_cannot_contradict_policy_approval_state(tmp_path):
    completed, report = run_audit(
        tmp_path, inventory_overrides={"business_version_provenance_gate": "pass"}
    )
    assert completed.returncode == 2
    assert report is None
    assert "business-version policy gate/count mismatch" in completed.stderr


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


def test_scope_decision_requires_matching_role_identity_date_evidence_and_hash():
    row = {
        "current_status": "approved",
        "decision": "approve",
        "proposed_role": "normative",
        "approved_role": "normative",
        "signer_name": "Publisher",
        "signer_organization_title": "Governance board / chair",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/scope.json",
        "signed_artifact_sha256": "",
    }
    assert not scope_decision_complete(row)
    row["signed_artifact_sha256"] = "e" * 64
    assert scope_decision_complete(row)
    row["approved_role"] = "informative"
    assert not scope_decision_complete(row)


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


def test_deleting_a_scope_decision_is_rejected(tmp_path):
    with SCOPE_DECISIONS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    altered = tmp_path / "scope-decisions.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows[:-1])
    completed, report = run_audit(tmp_path, scope_decisions=altered)
    assert completed.returncode == 2
    assert report is None
    assert "exactly one unique decision for each scope claim" in completed.stderr


def test_scope_role_cannot_be_downgraded_to_bypass_normative_evidence(tmp_path):
    with SCOPE_DECISIONS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0])
    next(row for row in rows if row["claim_id"] == "TASK-QBC")["proposed_role"] = "informative"
    altered = tmp_path / "scope-decisions.csv"
    with altered.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    completed, report = run_audit(tmp_path, scope_decisions=altered)
    assert completed.returncode == 2
    assert report is None
    assert "proposed_role does not match locked policy" in completed.stderr


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
    assert completed.returncode == 0
    assert report["approved_measure_definition_count"] == 20
    assert report["derived_status"]["RC-07"] == "blocked"
    assert report["derived_status"]["RC-08"] == "blocked"
    assert report["status_mismatches"] == []


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
        artifact_approved=True,
        criterion_resolution_approved=True,
    )
    assert completed.returncode == 1  # declared RC-07 is still blocked in the real register
    assert report["derived_status"]["RC-07"] == "pass"
    assert report["status_mismatches"] == [
        {"control_id": "RC-07", "declared": "blocked", "derived": "pass"},
    ]


def test_rc08_requires_signed_scope_roles_and_formal_ready_normative_claims(tmp_path):
    with APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        approval_rows = list(csv.DictReader(handle))
        approval_fields = list(approval_rows[0])
    for row in approval_rows:
        if row["Gate ID"] in {"SEC-PRIVACY", "UAT-VPN", "PUB-RELEASE"}:
            row.update({
                "Status": "approved", "Decision (approve/reject/revise)": "approve",
                "Signer name": "Operational owner",
                "Signer organization/title": "Hospital / owner",
                "Decision date": "2026-08-21",
                "Evidence URI/path": "evidence/operations.json",
                "Signed artifact SHA-256": "a" * 64,
            })
    signed_operations = tmp_path / "operations.csv"
    with signed_operations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=approval_fields)
        writer.writeheader()
        writer.writerows(approval_rows)

    with SCOPE_DECISIONS.open(encoding="utf-8-sig", newline="") as handle:
        decision_rows = list(csv.DictReader(handle))
        decision_fields = list(decision_rows[0])
    for row in decision_rows:
        row.update({
            "current_status": "approved", "decision": "approve",
            "approved_role": row["proposed_role"], "signer_name": "Scope owner",
            "signer_organization_title": "Governance board / chair",
            "decision_date": "2026-08-21",
            "evidence_uri_path": f"evidence/{row['claim_id']}.json",
            "signed_artifact_sha256": "b" * 64,
        })
    signed_scopes = tmp_path / "signed-scopes.csv"
    with signed_scopes.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decision_rows)

    completed, report = run_audit(
        tmp_path,
        approvals=signed_operations,
        scope_decisions=signed_scopes,
        inventory_overrides={
            "approved_canonical_version_policy_count": 4,
            "canonical_version_policy_states": {
                "CV-PACKAGE-EXPLICIT": "explicit-package-version",
                "CV-CQL-LIBRARY": "cql-library-version",
                "CV-PACKAGE-CONTEXT": "approved-package-context-only",
                "CV-TCR-MANUAL": "authoritative-business-version",
            },
            "manual_canonical_versions": ["TCR-breast-source-2026"],
            "business_version_provenance_gate": "pass",
        },
    )
    assert completed.returncode == 0
    assert report["approved_scope_decision_count"] == 10
    assert report["normative_scope_readiness"] == "block"
    assert report["derived_status"]["RC-08"] == "blocked"

    with SCOPE_CLAIMS.open(encoding="utf-8-sig", newline="") as handle:
        claim_rows = list(csv.DictReader(handle))
        claim_fields = list(claim_rows[0])
    for row in claim_rows:
        if row["claim_id"] in {"TASK-QBC", "TASK-CASE-MGMT"}:
            row["evidence_status"] = "formal-release-ready"
    ready_claims = tmp_path / "ready-claims.csv"
    with ready_claims.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=claim_fields)
        writer.writeheader()
        writer.writerows(claim_rows)
    for row in decision_rows:
        if row["claim_id"] in {"TASK-QBC", "TASK-CASE-MGMT"}:
            row["claim_evidence_status"] = "formal-release-ready"
    ready_decisions = tmp_path / "ready-decisions.csv"
    with ready_decisions.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decision_rows)

    completed, report = run_audit(
        tmp_path,
        approvals=signed_operations,
        scope_claims=ready_claims,
        scope_decisions=ready_decisions,
        inventory_overrides={
            "approved_canonical_version_policy_count": 4,
            "canonical_version_policy_states": {
                "CV-PACKAGE-EXPLICIT": "explicit-package-version",
                "CV-CQL-LIBRARY": "cql-library-version",
                "CV-PACKAGE-CONTEXT": "approved-package-context-only",
                "CV-TCR-MANUAL": "authoritative-business-version",
            },
            "manual_canonical_versions": ["TCR-breast-source-2026"],
            "business_version_provenance_gate": "pass",
        },
    )
    assert completed.returncode == 1  # real register truthfully declares RC-08 blocked
    assert report["normative_scope_readiness"] == "pass"
    assert report["derived_status"]["RC-08"] == "pass"
    assert report["status_mismatches"] == [
        {"control_id": "RC-08", "declared": "blocked", "derived": "pass"}
    ]
