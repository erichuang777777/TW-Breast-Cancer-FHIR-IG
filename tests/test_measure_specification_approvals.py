import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.approval_evidence import file_sha256
from scripts.audit_measure_specification_approvals import (
    APPROVAL_CONTEXT_FIELDS,
    AUDIT_COLUMNS,
    CATALOG_COLUMNS,
    CRITERIA_COLUMNS,
    approval_shape_complete,
    audit,
    canonical_sha256,
    generated_measures,
    measure_expressions,
    read_rows,
    validate_truth_table,
)


ROOT = Path(__file__).resolve().parents[1]
APPROVALS = ROOT / "mappings" / "publication" / "case-management-measure-approval-register.csv"
MEASURE_AUDIT = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
CATALOG = ROOT / "mappings" / "case-management" / "case-management-measure-catalog.csv"
CRITERIA = ROOT / "mappings" / "case-management" / "case-management-population-criteria.csv"
MEASURE_FSH = ROOT / "ig" / "input" / "fsh" / "case-management-measures.fsh"
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"
GENERATED = ROOT / "ig" / "fsh-generated" / "resources"


def approval_rows():
    with APPROVALS.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_current_measure_specification_inventory_is_exact_but_unsigned():
    report = audit(
        APPROVALS, MEASURE_AUDIT, CATALOG, CRITERIA, MEASURE_FSH, CQL, GENERATED
    )
    assert report["measure_count"] == 20
    assert report["population_criterion_count"] == 68
    assert report["measure_expression_use_count"] == 62
    assert report["approved_measure_specification_count"] == 0
    assert report["approved_truth_table_case_count"] == 0
    assert report["required_truth_assertion_count"] == 208
    assert report["measure_specification_integrity_gate"] == "pass"
    assert report["measure_specification_approval_gate"] == "block"
    assert len(report["measure_specification_fingerprints"]) == 20


def test_approval_shape_alone_does_not_prove_a_live_measure_bundle():
    row = {
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Clinical owner",
        "signer_organization_title": "Hospital / committee",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "mappings/publication/evidence/bundle.json",
        "signed_artifact_sha256": "a" * 64,
    }
    assert approval_shape_complete(row)


def test_exact_bundle_truth_table_and_live_component_binding(tmp_path):
    measure_id = "bc-qi-01"
    approvals = approval_rows()
    approval = next(row for row in approvals if row["measure_id"] == measure_id)
    audits = {row["measure_id"]: row for row in read_rows(MEASURE_AUDIT, AUDIT_COLUMNS)}
    catalogs = {row["measure_id"]: row for row in read_rows(CATALOG, CATALOG_COLUMNS)}
    criteria = read_rows(CRITERIA, CRITERIA_COLUMNS)
    criterion_rows = sorted(
        [
            row for row in criteria
            if row["measure_id"] in {measure_id, "bc-qi-00"}
        ],
        key=lambda row: row["criterion_id"],
    )
    criterion_ids = sorted(row["criterion_id"] for row in criterion_rows)
    generated = generated_measures(GENERATED)
    expressions = measure_expressions(MEASURE_FSH)[measure_id]
    cql_copy = tmp_path / "BreastCancerCaseManagement.cql"
    cql_copy.write_text(CQL.read_text(encoding="utf-8"), encoding="utf-8")

    approval.update({
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Clinical owner",
        "signer_organization_title": "Hospital / cancer committee",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "measure-bundle.json",
    })
    components = {
        "measure_fsh_sha256": file_sha256(MEASURE_FSH),
        "cql_sha256": file_sha256(cql_copy),
        "generated_measure_sha256": canonical_sha256(generated[measure_id]),
        "catalog_row_sha256": canonical_sha256(catalogs[measure_id]),
        "population_criteria_sha256": canonical_sha256(criterion_rows),
        "measure_audit_row_sha256": canonical_sha256(audits[measure_id]),
        "approval_context_sha256": canonical_sha256(
            {field: approval[field] for field in APPROVAL_CONTEXT_FIELDS}
        ),
    }
    truth_path = tmp_path / "measure-truth-table.json"
    truth = {
        "schema_version": "1.0",
        "measure_id": measure_id,
        "cases": [
            {
                "case_id": f"{criterion_id}-{'positive' if expected else 'negative'}",
                "criterion_id": criterion_id,
                "expected_result": expected,
                "boundary_class": "positive-control" if expected else "negative-control",
                "rationale": "Synthetic clinical specification assertion",
            }
            for criterion_id in criterion_ids
            for expected in (False, True)
        ],
    }
    truth_path.write_text(json.dumps(truth), encoding="utf-8")
    issues = [item.strip() for item in approval["known_issue"].split(";") if item.strip()]
    bundle_path = tmp_path / "measure-bundle.json"
    bundle = {
        "schema_version": "1.0",
        "measure_id": measure_id,
        "specification_fingerprint": canonical_sha256(components),
        "component_hashes": components,
        "reviewed_expression_ids": expressions,
        "reviewed_criterion_ids": criterion_ids,
        "known_issue_resolutions": [
            {
                "issue": issue,
                "resolution": "Resolved by the signed specification decision",
                "evidence": f"decision-item-{index + 1}",
            }
            for index, issue in enumerate(issues)
        ],
        "unresolved_issue_count": 0,
        "truth_table_path": "measure-truth-table.json",
        "truth_table_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
        "reviewer_name": approval["signer_name"],
        "reviewer_organization_title": approval["signer_organization_title"],
        "reviewed_at": "2026-08-21T10:00:00+08:00",
    }
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    approval["signed_artifact_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    approval_path = tmp_path / "approvals.csv"
    write_rows(approval_path, approvals)

    report = audit(
        approval_path, MEASURE_AUDIT, CATALOG, CRITERIA,
        MEASURE_FSH, cql_copy, GENERATED,
    )
    assert report["approved_measure_specification_count"] == 1
    assert report["approved_truth_table_case_count"] == len(criterion_ids) * 2

    bundle["known_issue_resolutions"].append(
        dict(bundle["known_issue_resolutions"][0])
    )
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    approval["signed_artifact_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    write_rows(approval_path, approvals)
    with pytest.raises(ValueError, match="known-issue resolution coverage mismatch"):
        audit(
            approval_path, MEASURE_AUDIT, CATALOG, CRITERIA,
            MEASURE_FSH, cql_copy, GENERATED,
        )

    bundle["known_issue_resolutions"].pop()
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    approval["signed_artifact_sha256"] = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    write_rows(approval_path, approvals)
    cql_copy.write_text(cql_copy.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale against live specification"):
        audit(
            approval_path, MEASURE_AUDIT, CATALOG, CRITERIA,
            MEASURE_FSH, cql_copy, GENERATED,
        )


def test_truth_table_requires_positive_and_negative_assertions_for_every_criterion(tmp_path):
    register = tmp_path / "approvals.csv"
    register.write_text("header\n", encoding="utf-8")
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text("{}\n", encoding="utf-8")
    truth_path = tmp_path / "truth.json"
    truth = {
        "schema_version": "1.0",
        "measure_id": "bc-qi-01",
        "cases": [
            {
                "case_id": f"A-{expected}",
                "criterion_id": "A",
                "expected_result": expected,
                "boundary_class": "control",
                "rationale": "assertion",
            }
            for expected in (False, True)
        ],
    }
    truth_path.write_text(json.dumps(truth), encoding="utf-8")
    bundle = {
        "truth_table_path": "truth.json",
        "truth_table_sha256": hashlib.sha256(truth_path.read_bytes()).hexdigest(),
    }
    with pytest.raises(ValueError, match="exact positive/negative criterion coverage"):
        validate_truth_table(
            bundle, bundle_path, register, "bc-qi-01", {"A", "B"}, "test"
        )


def test_approval_context_must_match_live_measure_audit(tmp_path):
    approvals = approval_rows()
    approvals[0]["known_issue"] += "; omitted live issue"
    approval_path = tmp_path / "approvals.csv"
    write_rows(approval_path, approvals)

    with pytest.raises(ValueError, match="omits or changes live blocking issues"):
        audit(
            approval_path, MEASURE_AUDIT, CATALOG, CRITERIA,
            MEASURE_FSH, CQL, GENERATED,
        )
