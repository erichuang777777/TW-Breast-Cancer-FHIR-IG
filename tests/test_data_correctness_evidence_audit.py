import csv
from pathlib import Path

import pytest

from scripts.audit_data_correctness_evidence import audit


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTER = ROOT / "mappings" / "publication" / "source-traceability-register.csv"
VALIDATION_REGISTER = (
    ROOT / "mappings" / "publication" / "measure-validation-evidence-register.csv"
)
COMMON_MAPPING = (
    ROOT / "mappings" / "case-management" / "breast-common-to-case-management.csv"
)
TASK_MAPPING = (
    ROOT / "mappings" / "case-management" / "case-management-task-only-fields.csv"
)
MEASURE_CATALOG = (
    ROOT / "mappings" / "case-management" / "case-management-measure-catalog.csv"
)
POPULATION_CRITERIA = (
    ROOT / "mappings" / "case-management" / "case-management-population-criteria.csv"
)


def run(source: Path = SOURCE_REGISTER, validation: Path = VALIDATION_REGISTER):
    return audit(
        source, validation, COMMON_MAPPING, TASK_MAPPING, MEASURE_CATALOG,
        POPULATION_CRITERIA,
    )


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_current_evidence_registers_are_complete_templates_but_not_release_evidence():
    report = run()
    assert report["source_register_integrity_gate"] == "pass"
    assert report["validation_register_integrity_gate"] == "pass"
    assert report["expected_fact_count"] == 52
    assert report["source_evidence_row_count"] == 52
    assert report["approved_authoritative_or_derived_fact_count"] == 0
    assert report["measure_count"] == 20
    assert report["population_criterion_count"] == 68
    assert report["criterion_referenced_fact_count"] == 37
    assert report["approved_independent_recalculation_count"] == 0
    assert report["approved_golden_cohort_count"] == 0
    assert report["raw_source_traceability_gate"] == "block"
    assert report["independent_recalculation_gate"] == "block"
    assert report["golden_cohort_gate"] == "block"


def test_secondary_report_row_cannot_replace_the_required_source_row(tmp_path):
    rows = read_rows(SOURCE_REGISTER)
    rows[0]["source_role"] = "secondary-reconciliation"
    altered = tmp_path / "source.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="exactly one primary/derived/pending row"):
        run(source=altered)


def test_an_approved_source_without_evidence_is_rejected(tmp_path):
    rows = read_rows(SOURCE_REGISTER)
    rows[0]["source_role"] = "authoritative-primary"
    rows[0]["review_status"] = "approved"
    altered = tmp_path / "source.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete approved source"):
        run(source=altered)


def test_an_approved_independent_result_without_case_diff_evidence_is_rejected(tmp_path):
    rows = read_rows(VALIDATION_REGISTER)
    rows[0]["independent_status"] = "approved"
    altered = tmp_path / "validation.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete independent approval"):
        run(validation=altered)


def test_an_approved_golden_result_without_complete_period_evidence_is_rejected(tmp_path):
    rows = read_rows(VALIDATION_REGISTER)
    rows[0]["golden_cohort_status"] = "approved"
    altered = tmp_path / "validation.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete golden approval"):
        run(validation=altered)


def test_complete_signed_case_level_evidence_can_pass_all_three_data_gates(tmp_path):
    digest = "a" * 64
    source_rows = read_rows(SOURCE_REGISTER)
    for row in source_rows:
        if row["source_role"] != "derived":
            row.update({
                "source_role": "authoritative-primary",
                "source_system": "synthetic-source-system",
                "source_artifact": "schema.table",
                "source_element": row["fact_id"],
                "source_version": "2026-01",
                "data_type": "documented-type",
                "transformation_rule": "identity-or-versioned-transform",
            })
        row.update({
            "time_semantics": "event-time-or-explicit-not-applicable",
            "null_policy": "explicit-null-and-absent-reason-policy",
            "provenance_rule": "retain source identity value time and adapter hash",
            "review_status": "approved",
            "reviewer_name": "Synthetic Reviewer",
            "reviewer_organization_title": "Test Data Governance",
            "review_date": "2026-08-21",
            "evidence_uri_path": "test://signed-source-contract",
            "signed_artifact_sha256": digest,
        })
    source_path = tmp_path / "source.csv"
    write_rows(source_path, source_rows)

    validation_rows = read_rows(VALIDATION_REGISTER)
    for row in validation_rows:
        row.update({
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "cohort_completeness": "all-in-scope-cases",
            "source_extract_sha256": digest,
            "fhir_bundle_sha256": digest,
            "cql_artifact_sha256": digest,
            "independent_implementation_sha256": digest,
            "truth_set_sha256": digest,
            "case_count": "10",
            "case_population_comparison_count": "40",
            "source_fact_comparison_count": "100",
            "manual_override_comparison_count": "0",
            "unexplained_difference_count": "0",
            "independent_method": "independent-no-shared-cql-logic",
            "independent_status": "approved",
            "golden_cohort_status": "approved",
            "reviewer_name": "Synthetic Reviewer",
            "reviewer_organization_title": "Test Clinical Validation",
            "review_date": "2026-08-21",
            "evidence_uri_path": "test://case-level-diff",
        })
    validation_path = tmp_path / "validation.csv"
    write_rows(validation_path, validation_rows)

    report = run(source=source_path, validation=validation_path)
    assert report["approved_authoritative_or_derived_fact_count"] == 52
    assert report["approved_independent_recalculation_count"] == 20
    assert report["approved_golden_cohort_count"] == 20
    assert report["raw_source_traceability_gate"] == "pass"
    assert report["independent_recalculation_gate"] == "pass"
    assert report["golden_cohort_gate"] == "pass"


def test_secondary_report_evidence_is_counted_but_never_used_as_primary(tmp_path):
    rows = read_rows(SOURCE_REGISTER)
    secondary = rows[0].copy()
    secondary.update({
        "evidence_id": "REPORT-CM-BC-001",
        "source_role": "secondary-reconciliation",
        "source_system": "exported-report",
        "source_artifact": "quarterly-report.xlsx",
        "source_element": "年齡",
    })
    rows.append(secondary)
    altered = tmp_path / "source.csv"
    write_rows(altered, rows)
    report = run(source=altered)
    assert report["source_evidence_row_count"] == 53
    assert report["secondary_reconciliation_row_count"] == 1
    assert report["approved_secondary_reconciliation_row_count"] == 0
    assert report["approved_authoritative_or_derived_fact_count"] == 0
    assert report["raw_source_traceability_gate"] == "block"
