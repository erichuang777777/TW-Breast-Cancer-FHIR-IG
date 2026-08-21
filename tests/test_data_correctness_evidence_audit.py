import csv
import hashlib
from pathlib import Path

import pytest

from scripts.audit_data_correctness_evidence import (
    MANUAL_OVERRIDE_FACT_IDS,
    SOURCE_CONTRACT_FIELDS,
    audit,
    expected_measure_expressions,
    expected_measure_facts,
    expected_measures,
)


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
MEASURE_FSH = ROOT / "ig" / "input" / "fsh" / "case-management-measures.fsh"
CASE_COMPARISONS = (
    ROOT / "mappings" / "publication" / "case-level-comparison-register.csv"
)


def run(
    source: Path = SOURCE_REGISTER,
    validation: Path = VALIDATION_REGISTER,
    comparisons: Path = CASE_COMPARISONS,
):
    return audit(
        source, validation, COMMON_MAPPING, TASK_MAPPING, MEASURE_CATALOG,
        POPULATION_CRITERIA, MEASURE_FSH, comparisons,
    )


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def approved_source_rows() -> list[dict[str, str]]:
    digest = "a" * 64
    rows = read_rows(SOURCE_REGISTER)
    for row in rows:
        role = row["source_role"]
        row.update({
            "source_role": role if role == "derived" else "authoritative-primary",
            "source_system": "synthetic-source-system",
            "source_artifact": "schema.table-or-versioned-derivation",
            "source_element": row["fact_id"],
            "source_version": "2026-01",
            "data_type": "documented-type",
            "record_grain": "one row per patient case event",
            "business_key": "facility-id plus case-id plus event-id",
            "join_rule": "versioned deterministic patient-case-event join",
            "source_cardinality": "zero-to-many events per case; latest valid event selected",
            "allowed_value_domain": "versioned enumerated domain or documented scalar range",
            "time_semantics": "event-time-or-explicit-not-applicable",
            "event_timezone": "Asia/Taipei with ISO-8601 offset retained",
            "precision_tolerance": "exact for codes; documented precision for quantities",
            "unit_policy": "UCUM unit or not-applicable with governed reason",
            "null_policy": "explicit null and missing reason policy",
            "duplicate_resolution_rule": "stable key then latest corrected timestamp",
            "late_arriving_update_rule": "restate open period and version closed-period correction",
            "invalid_value_policy": "reject and quarantine outside governed domain",
            "extraction_filter": "versioned in-scope facility period and case predicate",
            "transformation_rule": "identity or versioned deterministic transform",
            "fhir_absence_representation": "dataAbsentReason or omitted optional element by profile rule",
            "provenance_rule": "retain source identity value time and adapter hash",
            "derivation_input_fact_ids": (
                row["derivation_input_fact_ids"]
                if role == "derived"
                else "not-applicable: authoritative source fact"
            ),
            "source_owner": "Synthetic accountable source-system owner",
            "review_status": "approved",
            "reviewer_name": "Synthetic Reviewer",
            "reviewer_organization_title": "Test Data Governance",
            "review_date": "2026-08-21",
            "evidence_uri_path": "test://signed-source-contract",
            "signed_artifact_sha256": digest,
        })
    return rows


def complete_comparison_manifest(tmp_path: Path, case_count: int = 10):
    measures = expected_measures(MEASURE_CATALOG)
    expressions = expected_measure_expressions(MEASURE_FSH)
    facts = expected_measure_facts(read_rows(POPULATION_CRITERIA), measures)
    case_tokens = [f"{index + 1:064x}" for index in range(case_count)]
    rows: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {}
    digest = "b" * 64

    def add(method, measure_id, token, unit_type, unit_id):
        rows.append({
            "comparison_id": f"CMP-{len(rows) + 1:07d}",
            "verification_method": method,
            "measure_id": measure_id,
            "case_token": token,
            "comparison_unit_type": unit_type,
            "comparison_unit_id": unit_id,
            "normalization_rule_id": (
                "FHIR-MR-1" if unit_type == "report-resource" else "CV-1"
            ),
            "expected_value_sha256": digest,
            "actual_value_sha256": digest,
            "comparison_status": "match",
            "notes": "synthetic complete-coverage manifest",
        })

    for measure_id in measures:
        independent_rows = 0
        golden_rows = 1
        manual_rows = 0
        for token in case_tokens:
            for expression in sorted(expressions[measure_id]):
                add("VM-05", measure_id, token, "expression", expression)
                add("VM-06", measure_id, token, "expression", expression)
                independent_rows += 1
                golden_rows += 1
            for fact_id in sorted(facts[measure_id]):
                unit_type = (
                    "manual-override"
                    if fact_id in MANUAL_OVERRIDE_FACT_IDS
                    else "source-fact"
                )
                add("VM-06", measure_id, token, unit_type, fact_id)
                golden_rows += 1
                manual_rows += unit_type == "manual-override"
        add("VM-06", measure_id, "aggregate", "report-resource", "MeasureReport")
        counts[measure_id] = {
            "independent": independent_rows,
            "golden": golden_rows,
            "facts": case_count * len(facts[measure_id]),
            "manual": manual_rows,
        }
    path = tmp_path / "case-comparisons.csv"
    write_rows(path, rows)
    manifest_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return path, counts, manifest_hash


def test_current_evidence_registers_are_complete_templates_but_not_release_evidence():
    report = run()
    assert report["source_register_integrity_gate"] == "pass"
    assert report["validation_register_integrity_gate"] == "pass"
    assert report["expected_fact_count"] == 52
    assert report["source_evidence_row_count"] == 52
    assert report["source_contract_dimension_count"] == 19
    assert report["complete_source_contract_count"] == 0
    assert report["declared_derived_dependency_count"] == 1
    assert report["approved_authoritative_or_derived_fact_count"] == 0
    assert report["measure_count"] == 20
    assert report["measure_expression_count"] == 46
    assert report["measure_expression_occurrence_count"] == 62
    assert report["case_level_comparison_row_count"] == 0
    assert report["case_level_comparison_integrity_gate"] == "pass"
    assert report["population_criterion_count"] == 68
    assert report["criterion_referenced_fact_count"] == 45
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


@pytest.mark.parametrize("field", SOURCE_CONTRACT_FIELDS)
def test_every_source_contract_dimension_is_mandatory_for_approval(tmp_path, field):
    rows = approved_source_rows()
    target = next(row for row in rows if row["source_role"] != "derived")
    target[field] = ""
    altered = tmp_path / f"source-missing-{field}.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete approved source"):
        run(source=altered)


def test_unexplained_not_applicable_placeholder_is_rejected(tmp_path):
    rows = approved_source_rows()
    rows[0]["unit_policy"] = "not-applicable"
    altered = tmp_path / "source-placeholder.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete approved source"):
        run(source=altered)


def test_pending_owner_placeholder_cannot_pass_as_accountable_owner(tmp_path):
    rows = approved_source_rows()
    rows[0]["source_owner"] = "pending source-system owner"
    altered = tmp_path / "source-pending-owner.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="incomplete approved source"):
        run(source=altered)


def test_unknown_derived_input_is_rejected_even_before_approval(tmp_path):
    rows = read_rows(SOURCE_REGISTER)
    derived = next(row for row in rows if row["source_role"] == "derived")
    derived["derivation_input_fact_ids"] = "CM-BC-999"
    altered = tmp_path / "source-unknown-derived-input.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="unknown derivation dependencies"):
        run(source=altered)


def test_cyclic_derived_inputs_are_rejected_even_before_approval(tmp_path):
    rows = read_rows(SOURCE_REGISTER)
    first, second = rows[0], rows[1]
    first["source_role"] = "derived"
    first["derivation_input_fact_ids"] = second["fact_id"]
    second["source_role"] = "derived"
    second["derivation_input_fact_ids"] = first["fact_id"]
    altered = tmp_path / "source-cyclic-derived-input.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="cyclic derivation dependency"):
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


def test_approved_independent_manifest_cannot_omit_one_case_expression(tmp_path):
    comparison_path, counts, _ = complete_comparison_manifest(tmp_path)
    comparison_rows = read_rows(comparison_path)
    omitted = next(
        index for index, row in enumerate(comparison_rows)
        if row["verification_method"] == "VM-05"
        and row["measure_id"] == "bc-qi-01"
    )
    comparison_rows.pop(omitted)
    write_rows(comparison_path, comparison_rows)
    manifest_hash = hashlib.sha256(comparison_path.read_bytes()).hexdigest()

    rows = read_rows(VALIDATION_REGISTER)
    row = next(item for item in rows if item["measure_id"] == "bc-qi-01")
    digest = "a" * 64
    row.update({
        "case_count": "10",
        "case_population_comparison_count": str(counts["bc-qi-01"]["independent"] - 1),
        "unexplained_difference_count": "0",
        "comparison_manifest_sha256": manifest_hash,
        "independent_manifest_row_count": str(counts["bc-qi-01"]["independent"] - 1),
        "independent_difference_count": "0",
        "cql_artifact_sha256": digest,
        "independent_implementation_sha256": digest,
        "truth_set_sha256": digest,
        "independent_method": "independent-no-shared-cql-logic",
        "independent_status": "approved",
        "reviewer_name": "Synthetic Reviewer",
        "reviewer_organization_title": "Test Clinical Validation",
        "review_date": "2026-08-21",
        "evidence_uri_path": "test://truncated-case-level-diff",
    })
    validation_path = tmp_path / "validation-truncated.csv"
    write_rows(validation_path, rows)
    with pytest.raises(ValueError, match="incomplete independent approval"):
        run(validation=validation_path, comparisons=comparison_path)


def test_complete_signed_case_level_evidence_can_pass_all_three_data_gates(tmp_path):
    digest = "a" * 64
    source_rows = approved_source_rows()
    source_path = tmp_path / "source.csv"
    write_rows(source_path, source_rows)

    comparison_path, comparison_counts, manifest_hash = (
        complete_comparison_manifest(tmp_path)
    )

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
            "comparison_manifest_sha256": manifest_hash,
            "independent_manifest_row_count": str(
                comparison_counts[row["measure_id"]]["independent"]
            ),
            "golden_manifest_row_count": str(
                comparison_counts[row["measure_id"]]["golden"]
            ),
            "independent_difference_count": "0",
            "golden_difference_count": "0",
            "comparison_normalizer_sha256": digest,
            "independent_method": "independent-no-shared-cql-logic",
            "independent_status": "approved",
            "golden_cohort_status": "approved",
            "reviewer_name": "Synthetic Reviewer",
            "reviewer_organization_title": "Test Clinical Validation",
            "review_date": "2026-08-21",
            "evidence_uri_path": "test://case-level-diff",
        })
        row["case_population_comparison_count"] = str(
            comparison_counts[row["measure_id"]]["independent"]
        )
        row["source_fact_comparison_count"] = str(
            comparison_counts[row["measure_id"]]["facts"]
        )
        row["manual_override_comparison_count"] = str(
            comparison_counts[row["measure_id"]]["manual"]
        )
    validation_path = tmp_path / "validation.csv"
    write_rows(validation_path, validation_rows)

    report = run(
        source=source_path, validation=validation_path,
        comparisons=comparison_path,
    )
    assert report["approved_authoritative_or_derived_fact_count"] == 52
    assert report["complete_source_contract_count"] == 52
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
