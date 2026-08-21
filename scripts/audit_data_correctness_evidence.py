#!/usr/bin/env python3
"""Audit raw-source traceability and real-data validation evidence.

This gate deliberately treats exported reports as secondary reconciliation
evidence.  They can help explain a result, but cannot satisfy the requirement
for an authoritative source element used to create a FHIR fact.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


SHA256 = re.compile(r"[0-9a-fA-F]{64}")
PRIMARY_ROLES = {
    "authoritative-primary",
    "authoritative-external",
    "derived",
    "pending-source-discovery",
}
ALL_ROLES = PRIMARY_ROLES | {"secondary-reconciliation"}
SOURCE_COLUMNS = {
    "evidence_id", "fact_id", "indicator_family", "fact_name", "fhir_target",
    "source_role", "source_system", "source_artifact", "source_element",
    "source_version", "data_type", "time_semantics", "unit_policy",
    "null_policy", "transformation_rule", "provenance_rule", "source_owner",
    "review_status", "reviewer_name", "reviewer_organization_title",
    "review_date", "evidence_uri_path", "signed_artifact_sha256", "notes",
}
VALIDATION_COLUMNS = {
    "measure_id", "indicator_family", "reporting_period_start",
    "reporting_period_end", "cohort_completeness", "source_extract_sha256",
    "fhir_bundle_sha256", "cql_artifact_sha256",
    "independent_implementation_sha256", "truth_set_sha256", "case_count",
    "case_population_comparison_count", "source_fact_comparison_count",
    "manual_override_comparison_count", "unexplained_difference_count",
    "independent_method", "independent_status", "golden_cohort_status",
    "reviewer_name", "reviewer_organization_title", "review_date",
    "evidence_uri_path", "notes",
}


def read_csv(path: Path, columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = set(rows[0]) if rows else set()
    if not rows or actual != columns:
        raise ValueError(f"{path}: expected exact columns {sorted(columns)}")
    return rows


def valid_sha(value: str) -> bool:
    return SHA256.fullmatch(value.strip()) is not None


def valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def reviewed(row: dict[str, str]) -> bool:
    return (
        row["review_status"] == "approved"
        and all(row[field].strip() for field in (
            "reviewer_name", "reviewer_organization_title", "review_date",
            "evidence_uri_path", "signed_artifact_sha256",
        ))
        and valid_date(row["review_date"])
        and valid_sha(row["signed_artifact_sha256"])
    )


def source_complete(row: dict[str, str]) -> bool:
    if not reviewed(row):
        return False
    role = row["source_role"]
    common = (
        "fact_name", "fhir_target", "source_owner", "time_semantics",
        "null_policy", "transformation_rule", "provenance_rule",
    )
    if not all(row[field].strip() for field in common):
        return False
    if role == "derived":
        return True
    if role not in {"authoritative-primary", "authoritative-external"}:
        return False
    return all(row[field].strip() for field in (
        "source_system", "source_artifact", "source_element", "source_version",
        "data_type",
    ))


def secondary_complete(row: dict[str, str]) -> bool:
    return (
        row["source_role"] == "secondary-reconciliation"
        and reviewed(row)
        and all(row[field].strip() for field in (
            "source_system", "source_artifact", "source_element", "source_version",
            "source_owner", "time_semantics", "null_policy", "provenance_rule",
        ))
    )


def parse_nonnegative_int(row: dict[str, str], field: str) -> int | None:
    try:
        value = int(row[field])
    except ValueError:
        return None
    return value if value >= 0 else None


def validation_reviewed(row: dict[str, str]) -> bool:
    return (
        all(row[field].strip() for field in (
            "reviewer_name", "reviewer_organization_title", "review_date",
            "evidence_uri_path",
        ))
        and valid_date(row["review_date"])
    )


def independent_complete(row: dict[str, str]) -> bool:
    comparisons = parse_nonnegative_int(row, "case_population_comparison_count")
    differences = parse_nonnegative_int(row, "unexplained_difference_count")
    return (
        row["independent_status"] == "approved"
        and row["independent_method"] == "independent-no-shared-cql-logic"
        and comparisons is not None and comparisons > 0
        and differences == 0
        and validation_reviewed(row)
        and all(valid_sha(row[field]) for field in (
            "cql_artifact_sha256", "independent_implementation_sha256",
            "truth_set_sha256",
        ))
    )


def golden_complete(row: dict[str, str]) -> bool:
    cases = parse_nonnegative_int(row, "case_count")
    populations = parse_nonnegative_int(row, "case_population_comparison_count")
    facts = parse_nonnegative_int(row, "source_fact_comparison_count")
    overrides = parse_nonnegative_int(row, "manual_override_comparison_count")
    differences = parse_nonnegative_int(row, "unexplained_difference_count")
    try:
        period_start = date.fromisoformat(row["reporting_period_start"])
        period_end = date.fromisoformat(row["reporting_period_end"])
    except ValueError:
        return False
    return (
        row["golden_cohort_status"] == "approved"
        and row["cohort_completeness"] == "all-in-scope-cases"
        and period_start <= period_end
        and cases is not None and cases > 0
        and populations is not None and populations >= cases
        and facts is not None and facts >= cases
        and overrides is not None
        and differences == 0
        and validation_reviewed(row)
        and all(valid_sha(row[field]) for field in (
            "source_extract_sha256", "fhir_bundle_sha256", "cql_artifact_sha256",
            "truth_set_sha256",
        ))
    )


def expected_facts(common_path: Path, task_path: Path) -> dict[str, dict[str, str]]:
    with common_path.open(encoding="utf-8-sig", newline="") as handle:
        common = list(csv.DictReader(handle))
    with task_path.open(encoding="utf-8-sig", newline="") as handle:
        task = list(csv.DictReader(handle))
    facts: dict[str, dict[str, str]] = {}
    for row in common:
        facts[row["mapping_id"]] = {
            "indicator_family": row["used_by_indicator_family"],
            "fact_name": row["common_concept"],
        }
    for row in task:
        if row["field_id"] in facts:
            raise ValueError(f"duplicate mapped fact {row['field_id']}")
        facts[row["field_id"]] = {
            "indicator_family": row["used_by_indicator_family"],
            "fact_name": row["field_zh"],
        }
    return facts


def expected_measures(catalog_path: Path) -> dict[str, str]:
    with catalog_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["measure_id"]: row["indicator_family"] for row in rows}


def audit(
    source_register_path: Path,
    validation_register_path: Path,
    common_mapping_path: Path,
    task_mapping_path: Path,
    measure_catalog_path: Path,
    population_criteria_path: Path,
) -> dict[str, object]:
    sources = read_csv(source_register_path, SOURCE_COLUMNS)
    validations = read_csv(validation_register_path, VALIDATION_COLUMNS)
    facts = expected_facts(common_mapping_path, task_mapping_path)
    measures = expected_measures(measure_catalog_path)
    with population_criteria_path.open(encoding="utf-8-sig", newline="") as handle:
        criteria = list(csv.DictReader(handle))
    if len(facts) != 52:
        raise ValueError(f"{common_mapping_path}/{task_mapping_path}: expected 52 facts")
    if len(measures) != 20:
        raise ValueError(f"{measure_catalog_path}: expected 20 Measures")
    if (
        len(criteria) != 68
        or len({row["criterion_id"] for row in criteria}) != 68
        or {row["measure_id"] for row in criteria}
        != set(measures) | {"bc-qi-00", "bc-qr-00"}
    ):
        raise ValueError(
            f"{population_criteria_path}: expected 68 unique criteria covering "
            "all 20 Measures and the bc-qi-00/bc-qr-00 common cohorts"
        )
    criterion_fact_ids = {
        fact_id
        for row in criteria
        for fact_id in row["depends_on_mapping"].split()
    }
    unknown_dependencies = sorted(criterion_fact_ids - set(facts))
    if unknown_dependencies:
        raise ValueError(
            f"{population_criteria_path}: unknown mapping dependencies {unknown_dependencies}"
        )
    if len({row["evidence_id"] for row in sources}) != len(sources):
        raise ValueError(f"{source_register_path}: evidence_id must be unique")
    unknown_facts = sorted({row["fact_id"] for row in sources} - set(facts))
    if unknown_facts:
        raise ValueError(f"{source_register_path}: unknown fact IDs {unknown_facts}")
    primary_rows: dict[str, list[dict[str, str]]] = {fact_id: [] for fact_id in facts}
    secondary_count = 0
    approved_secondary_count = 0
    for row in sources:
        if row["source_role"] not in ALL_ROLES:
            raise ValueError(f"{source_register_path}: invalid source_role for {row['evidence_id']}")
        expected = facts[row["fact_id"]]
        for field in ("indicator_family", "fact_name"):
            if row[field] != expected[field]:
                raise ValueError(f"{source_register_path}: stale {field} for {row['fact_id']}")
        if row["review_status"] not in {"pending", "approved"}:
            raise ValueError(f"{source_register_path}: invalid review_status")
        if row["review_status"] == "approved":
            complete = (
                secondary_complete(row)
                if row["source_role"] == "secondary-reconciliation"
                else source_complete(row)
            )
            if not complete:
                raise ValueError(f"{source_register_path}: incomplete approved source {row['evidence_id']}")
        if row["source_role"] == "secondary-reconciliation":
            secondary_count += 1
            approved_secondary_count += secondary_complete(row)
        else:
            primary_rows[row["fact_id"]].append(row)
    bad_coverage = sorted(fact_id for fact_id, rows in primary_rows.items() if len(rows) != 1)
    if bad_coverage:
        raise ValueError(
            f"{source_register_path}: each fact needs exactly one primary/derived/pending row; bad={bad_coverage}"
        )

    if len(validations) != len(measures) or len({row["measure_id"] for row in validations}) != len(measures):
        raise ValueError(f"{validation_register_path}: expected one row per Measure")
    if {row["measure_id"] for row in validations} != set(measures):
        raise ValueError(f"{validation_register_path}: Measure set differs from catalog")
    for row in validations:
        if row["indicator_family"] != measures[row["measure_id"]]:
            raise ValueError(f"{validation_register_path}: stale indicator_family for {row['measure_id']}")
        if row["independent_status"] not in {"pending", "approved"} or row["golden_cohort_status"] not in {"pending", "approved"}:
            raise ValueError(f"{validation_register_path}: invalid status for {row['measure_id']}")
        if row["independent_status"] == "approved" and not independent_complete(row):
            raise ValueError(f"{validation_register_path}: incomplete independent approval for {row['measure_id']}")
        if row["golden_cohort_status"] == "approved" and not golden_complete(row):
            raise ValueError(f"{validation_register_path}: incomplete golden approval for {row['measure_id']}")

    approved_sources = sum(source_complete(rows[0]) for rows in primary_rows.values())
    independent_count = sum(independent_complete(row) for row in validations)
    golden_count = sum(golden_complete(row) for row in validations)
    return {
        "gate_scope": "raw-source-independent-recalculation-and-golden-cohort",
        "expected_fact_count": len(facts),
        "source_evidence_row_count": len(sources),
        "secondary_reconciliation_row_count": secondary_count,
        "approved_secondary_reconciliation_row_count": approved_secondary_count,
        "approved_authoritative_or_derived_fact_count": approved_sources,
        "measure_count": len(measures),
        "population_criterion_count": len(criteria),
        "criterion_referenced_fact_count": len(criterion_fact_ids),
        "approved_independent_recalculation_count": independent_count,
        "approved_golden_cohort_count": golden_count,
        "source_register_integrity_gate": "pass",
        "validation_register_integrity_gate": "pass",
        "raw_source_traceability_gate": "pass" if approved_sources == len(facts) else "block",
        "independent_recalculation_gate": "pass" if independent_count == len(measures) else "block",
        "golden_cohort_gate": "pass" if golden_count == len(measures) else "block",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-register", type=Path, required=True)
    parser.add_argument("--validation-register", type=Path, required=True)
    parser.add_argument("--common-mapping", type=Path, required=True)
    parser.add_argument("--task-mapping", type=Path, required=True)
    parser.add_argument("--measure-catalog", type=Path, required=True)
    parser.add_argument("--population-criteria", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "data"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(
            args.source_register, args.validation_register, args.common_mapping,
            args.task_mapping, args.measure_catalog,
            args.population_criteria,
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Data-correctness evidence audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "Data evidence: "
        f"source={report['approved_authoritative_or_derived_fact_count']}/{report['expected_fact_count']}; "
        f"independent={report['approved_independent_recalculation_count']}/{report['measure_count']}; "
        f"golden={report['approved_golden_cohort_count']}/{report['measure_count']}"
    )
    integrity = (
        report["source_register_integrity_gate"] == "pass"
        and report["validation_register_integrity_gate"] == "pass"
    )
    data = all(report[field] == "pass" for field in (
        "raw_source_traceability_gate", "independent_recalculation_gate", "golden_cohort_gate"
    ))
    return 0 if (integrity if args.target == "integrity" else data) else 1


if __name__ == "__main__":
    raise SystemExit(main())
