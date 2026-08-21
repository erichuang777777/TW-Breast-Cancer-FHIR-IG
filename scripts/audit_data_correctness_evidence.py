#!/usr/bin/env python3
"""Audit raw-source traceability and real-data validation evidence.

This gate deliberately treats exported reports as secondary reconciliation
evidence.  They can help explain a result, but cannot satisfy the requirement
for an authoritative source element used to create a FHIR fact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
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
    "source_version", "data_type", "record_grain", "business_key",
    "join_rule", "source_cardinality", "allowed_value_domain",
    "time_semantics", "event_timezone", "precision_tolerance", "unit_policy",
    "null_policy", "duplicate_resolution_rule", "late_arriving_update_rule",
    "invalid_value_policy", "extraction_filter", "transformation_rule",
    "fhir_absence_representation", "provenance_rule",
    "derivation_input_fact_ids", "source_owner",
    "review_status", "reviewer_name", "reviewer_organization_title",
    "review_date", "evidence_uri_path", "signed_artifact_sha256", "notes",
}
SOURCE_LOCATOR_FIELDS = (
    "source_system", "source_artifact", "source_element", "source_version",
)
SOURCE_CONTRACT_FIELDS = (
    "data_type", "record_grain", "business_key", "join_rule",
    "source_cardinality", "allowed_value_domain", "time_semantics",
    "event_timezone", "precision_tolerance", "unit_policy", "null_policy",
    "duplicate_resolution_rule", "late_arriving_update_rule",
    "invalid_value_policy", "extraction_filter", "transformation_rule",
    "fhir_absence_representation", "provenance_rule",
    "derivation_input_fact_ids",
)
PLACEHOLDER_VALUES = {
    "-", "?", "na", "n/a", "none", "null", "tbd", "todo", "unknown",
    "not applicable", "not-applicable", "pending", "待確認", "待補",
}
PLACEHOLDER_PREFIXES = (
    "pending", "tbd", "todo", "unknown", "待確認", "待補",
)
VALIDATION_COLUMNS = {
    "measure_id", "indicator_family", "reporting_period_start",
    "reporting_period_end", "cohort_completeness", "source_extract_sha256",
    "fhir_bundle_sha256", "cql_artifact_sha256",
    "independent_implementation_sha256", "truth_set_sha256", "case_count",
    "case_population_comparison_count", "source_fact_comparison_count",
    "manual_override_comparison_count", "unexplained_difference_count",
    "comparison_manifest_sha256", "independent_manifest_row_count",
    "golden_manifest_row_count", "independent_difference_count",
    "golden_difference_count", "comparison_normalizer_sha256",
    "independent_method", "independent_status", "golden_cohort_status",
    "reviewer_name", "reviewer_organization_title", "review_date",
    "evidence_uri_path", "notes",
}
COMPARISON_COLUMNS = {
    "comparison_id", "verification_method", "measure_id", "case_token",
    "comparison_unit_type", "comparison_unit_id", "normalization_rule_id",
    "expected_value_sha256",
    "actual_value_sha256", "comparison_status", "notes",
}
MANUAL_OVERRIDE_FACT_IDS = {
    "CM-TASK-010", "CM-TASK-013", "CM-TASK-014", "CM-TASK-015",
}


def read_csv(
    path: Path, columns: set[str], *, allow_empty: bool = False,
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if set(fieldnames) != columns or len(fieldnames) != len(columns):
        raise ValueError(f"{path}: expected exact columns {sorted(columns)}")
    if not rows and not allow_empty:
        raise ValueError(f"{path}: expected at least one data row")
    if any(
        None in row or any(value is None for value in row.values())
        for row in rows
    ):
        raise ValueError(f"{path}: malformed row width")
    return rows


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def explicit_contract_value(value: str | None) -> bool:
    """Require a real rule or an explained not-applicable declaration."""
    normalized = (value or "").strip()
    if not normalized or normalized.casefold() in PLACEHOLDER_VALUES:
        return False
    lowered = normalized.casefold()
    if any(
        lowered == prefix
        or lowered.startswith(prefix + " ")
        or lowered.startswith(prefix + ":")
        or lowered.startswith(prefix + "-")
        for prefix in PLACEHOLDER_PREFIXES
    ):
        return False
    prefix = "not-applicable:"
    if lowered.startswith(prefix):
        return len(normalized[len(prefix):].strip()) >= 8
    return True


def source_contract_complete(row: dict[str, str]) -> bool:
    role = row["source_role"]
    if role not in {
        "authoritative-primary", "authoritative-external", "derived",
        "secondary-reconciliation",
    }:
        return False
    if not all(explicit_contract_value(row[field]) for field in (
        "fact_name", "fhir_target", "source_owner", *SOURCE_LOCATOR_FIELDS,
        *SOURCE_CONTRACT_FIELDS,
    )):
        return False
    dependencies = row["derivation_input_fact_ids"].strip()
    if role == "derived":
        return not dependencies.casefold().startswith("not-applicable:")
    return dependencies.casefold().startswith("not-applicable:")


def source_complete(row: dict[str, str]) -> bool:
    return (
        row["source_role"] in {
            "authoritative-primary", "authoritative-external", "derived",
        }
        and reviewed(row)
        and source_contract_complete(row)
    )


def secondary_complete(row: dict[str, str]) -> bool:
    return (
        row["source_role"] == "secondary-reconciliation"
        and reviewed(row)
        and source_contract_complete(row)
    )


def validate_derivation_dependencies(
    primary_rows: dict[str, list[dict[str, str]]],
) -> int:
    """Validate declared derived-fact inputs and reject self/cyclic derivations."""
    fact_ids = set(primary_rows)
    graph: dict[str, set[str]] = {}
    declared = 0
    for fact_id, rows in primary_rows.items():
        row = rows[0]
        raw = row["derivation_input_fact_ids"].strip()
        if row["source_role"] != "derived":
            continue
        if not raw:
            continue
        dependencies = raw.split()
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"duplicate derivation dependency for {fact_id}")
        unknown = sorted(set(dependencies) - fact_ids)
        if unknown:
            raise ValueError(f"unknown derivation dependencies for {fact_id}: {unknown}")
        if fact_id in dependencies:
            raise ValueError(f"self derivation dependency for {fact_id}")
        graph[fact_id] = set(dependencies)
        declared += 1

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(fact_id: str) -> None:
        if fact_id in visiting:
            raise ValueError(f"cyclic derivation dependency involving {fact_id}")
        if fact_id in visited:
            return
        visiting.add(fact_id)
        for dependency in graph.get(fact_id, set()):
            if dependency in graph:
                visit(dependency)
        visiting.remove(fact_id)
        visited.add(fact_id)

    for fact_id in graph:
        visit(fact_id)
    return declared


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


def independent_complete(
    row: dict[str, str], coverage: dict[str, object], manifest_sha256: str,
) -> bool:
    comparisons = parse_nonnegative_int(row, "case_population_comparison_count")
    differences = parse_nonnegative_int(row, "unexplained_difference_count")
    total_differences = parse_nonnegative_int(row, "independent_difference_count")
    manifest_rows = parse_nonnegative_int(row, "independent_manifest_row_count")
    return (
        row["independent_status"] == "approved"
        and row["independent_method"] == "independent-no-shared-cql-logic"
        and comparisons is not None and comparisons > 0
        and comparisons == coverage["expression_comparison_count"]
        and manifest_rows == coverage["independent_row_count"]
        and coverage["independent_complete"] is True
        and coverage["independent_difference_count"] == 0
        and total_differences == 0
        and differences == 0
        and row["comparison_manifest_sha256"] == manifest_sha256
        and validation_reviewed(row)
        and all(valid_sha(row[field]) for field in (
            "cql_artifact_sha256", "independent_implementation_sha256",
            "comparison_normalizer_sha256",
            "truth_set_sha256",
        ))
    )


def golden_complete(
    row: dict[str, str], coverage: dict[str, object], manifest_sha256: str,
) -> bool:
    cases = parse_nonnegative_int(row, "case_count")
    populations = parse_nonnegative_int(row, "case_population_comparison_count")
    facts = parse_nonnegative_int(row, "source_fact_comparison_count")
    overrides = parse_nonnegative_int(row, "manual_override_comparison_count")
    differences = parse_nonnegative_int(row, "unexplained_difference_count")
    total_differences = parse_nonnegative_int(row, "golden_difference_count")
    manifest_rows = parse_nonnegative_int(row, "golden_manifest_row_count")
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
        and populations == coverage["expression_comparison_count"]
        and facts == coverage["source_fact_comparison_count"]
        and overrides == coverage["manual_override_comparison_count"]
        and manifest_rows == coverage["golden_row_count"]
        and coverage["golden_complete"] is True
        and coverage["golden_difference_count"] == 0
        and total_differences == 0
        and differences == 0
        and row["comparison_manifest_sha256"] == manifest_sha256
        and validation_reviewed(row)
        and all(valid_sha(row[field]) for field in (
            "source_extract_sha256", "fhir_bundle_sha256", "cql_artifact_sha256",
            "comparison_normalizer_sha256",
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


def expected_measure_expressions(measure_fsh_path: Path) -> dict[str, set[str]]:
    text = measure_fsh_path.read_text(encoding="utf-8")
    expressions: dict[str, set[str]] = {}
    for block in text.split("\nInstance: ")[1:]:
        if "InstanceOf: Measure" not in block:
            continue
        measure_match = re.search(r'\* id = "(bc-q[ir]-\d+)"', block)
        if not measure_match:
            raise ValueError(f"{measure_fsh_path}: Measure without bc-qi/bc-qr id")
        measure_id = measure_match.group(1)
        values = re.findall(r'criteria\.expression = "([^"]+)"', block)
        if not values or len(values) != len(set(values)):
            raise ValueError(
                f"{measure_fsh_path}: missing or duplicate expressions for {measure_id}"
            )
        expressions[measure_id] = set(values)
    unique_expressions = set().union(*expressions.values()) if expressions else set()
    if (
        len(expressions) != 20
        or sum(map(len, expressions.values())) != 62
        or len(unique_expressions) != 46
    ):
        raise ValueError(
            f"{measure_fsh_path}: expected 20 Measures, 62 expression uses, "
            "and 46 unique expressions"
        )
    return expressions


def expected_measure_facts(
    criteria: list[dict[str, str]], measures: dict[str, str],
) -> dict[str, set[str]]:
    shared = {
        "quality": "bc-qi-00",
        "quarterly": "bc-qr-00",
    }
    result: dict[str, set[str]] = {}
    for measure_id, family in measures.items():
        included_measure_ids = {measure_id, shared[family]}
        result[measure_id] = {
            fact_id
            for row in criteria
            if row["measure_id"] in included_measure_ids
            for fact_id in row["depends_on_mapping"].split()
        }
        if not result[measure_id]:
            raise ValueError(f"no source facts resolve for {measure_id}")
    return result


def validate_case_comparisons(
    path: Path,
    rows: list[dict[str, str]],
    measures: dict[str, str],
    expressions: dict[str, set[str]],
    facts: dict[str, set[str]],
) -> dict[str, dict[str, object]]:
    if len({row["comparison_id"] for row in rows}) != len(rows):
        raise ValueError(f"{path}: comparison_id must be unique")
    seen: set[tuple[str, str, str, str, str]] = set()
    by_measure: dict[str, dict[str, object]] = {
        measure_id: {
            "VM-05": [], "VM-06": [],
            "VM-05-differences": 0, "VM-06-differences": 0,
        }
        for measure_id in measures
    }
    for row in rows:
        if not row["comparison_id"].strip():
            raise ValueError(f"{path}: comparison_id cannot be blank")
        method = row["verification_method"]
        measure_id = row["measure_id"]
        unit_type = row["comparison_unit_type"]
        unit_id = row["comparison_unit_id"]
        case_token = row["case_token"]
        if method not in {"VM-05", "VM-06"}:
            raise ValueError(f"{path}: invalid verification_method")
        if measure_id not in measures:
            raise ValueError(f"{path}: unknown measure_id {measure_id}")
        allowed_types = (
            {"expression"}
            if method == "VM-05"
            else {"expression", "source-fact", "manual-override", "report-resource"}
        )
        if unit_type not in allowed_types:
            raise ValueError(f"{path}: invalid {method} comparison_unit_type")
        if unit_type == "report-resource":
            if case_token != "aggregate" or unit_id != "MeasureReport":
                raise ValueError(f"{path}: invalid report-resource comparison")
        elif not valid_sha(case_token):
            raise ValueError(f"{path}: case_token must be an HMAC-SHA256 token")
        if unit_type == "expression" and unit_id not in expressions[measure_id]:
            raise ValueError(f"{path}: unknown expression {measure_id}/{unit_id}")
        if unit_type in {"source-fact", "manual-override"}:
            if unit_id not in facts[measure_id]:
                raise ValueError(f"{path}: unrelated source fact {measure_id}/{unit_id}")
            expected_type = (
                "manual-override"
                if unit_id in MANUAL_OVERRIDE_FACT_IDS
                else "source-fact"
            )
            if unit_type != expected_type:
                raise ValueError(f"{path}: incorrect comparison type for {unit_id}")
        expected_normalization = (
            "FHIR-MR-1" if unit_type == "report-resource" else "CV-1"
        )
        if row["normalization_rule_id"] != expected_normalization:
            raise ValueError(f"{path}: invalid normalization rule for {unit_type}")
        expected_hash = row["expected_value_sha256"]
        actual_hash = row["actual_value_sha256"]
        if not valid_sha(expected_hash) or not valid_sha(actual_hash):
            raise ValueError(f"{path}: comparison values must be SHA-256 digests")
        status = row["comparison_status"]
        expected_status = "match" if expected_hash == actual_hash else "difference"
        if status != expected_status:
            raise ValueError(f"{path}: comparison_status/hash mismatch")
        key = (method, measure_id, case_token, unit_type, unit_id)
        if key in seen:
            raise ValueError(f"{path}: duplicate comparison unit {key}")
        seen.add(key)
        by_measure[measure_id][method].append(row)
        by_measure[measure_id][f"{method}-differences"] += status == "difference"
    return by_measure


def exact_case_coverage(
    row: dict[str, str],
    comparison_rows: dict[str, object],
    expressions: set[str],
    facts: set[str],
) -> dict[str, object]:
    case_count = parse_nonnegative_int(row, "case_count")
    vm05 = comparison_rows["VM-05"]
    vm06 = comparison_rows["VM-06"]
    independent_tokens = {
        item["case_token"] for item in vm05 if item["comparison_unit_type"] != "report-resource"
    }
    golden_tokens = {
        item["case_token"] for item in vm06 if item["comparison_unit_type"] != "report-resource"
    }
    expected_independent = {
        (token, "expression", expression)
        for token in independent_tokens
        for expression in expressions
    }
    expected_golden_expressions = {
        (token, "expression", expression)
        for token in golden_tokens
        for expression in expressions
    }
    expected_golden = expected_golden_expressions | {
        (
            token,
            "manual-override" if fact_id in MANUAL_OVERRIDE_FACT_IDS else "source-fact",
            fact_id,
        )
        for token in golden_tokens
        for fact_id in facts
    } | {("aggregate", "report-resource", "MeasureReport")}
    actual_independent = {
        (item["case_token"], item["comparison_unit_type"], item["comparison_unit_id"])
        for item in vm05
    }
    actual_golden = {
        (item["case_token"], item["comparison_unit_type"], item["comparison_unit_id"])
        for item in vm06
    }
    manual_count = sum(
        item["comparison_unit_type"] == "manual-override" for item in vm06
    )
    source_fact_count = sum(
        item["comparison_unit_type"] in {"source-fact", "manual-override"}
        for item in vm06
    )
    return {
        "case_count": case_count,
        "independent_row_count": len(vm05),
        "golden_row_count": len(vm06),
        "expression_comparison_count": (
            (case_count or 0) * len(expressions)
        ),
        "source_fact_comparison_count": source_fact_count,
        "manual_override_comparison_count": manual_count,
        "independent_difference_count": comparison_rows["VM-05-differences"],
        "golden_difference_count": comparison_rows["VM-06-differences"],
        "independent_complete": (
            case_count is not None and case_count > 0
            and len(independent_tokens) == case_count
            and actual_independent == expected_independent
        ),
        "golden_complete": (
            case_count is not None and case_count > 0
            and len(golden_tokens) == case_count
            and actual_golden == expected_golden
        ),
        "cohort_tokens_aligned": independent_tokens == golden_tokens,
    }


def audit(
    source_register_path: Path,
    validation_register_path: Path,
    common_mapping_path: Path,
    task_mapping_path: Path,
    measure_catalog_path: Path,
    population_criteria_path: Path,
    measure_fsh_path: Path,
    case_comparison_register_path: Path,
) -> dict[str, object]:
    sources = read_csv(source_register_path, SOURCE_COLUMNS)
    validations = read_csv(validation_register_path, VALIDATION_COLUMNS)
    comparisons = read_csv(
        case_comparison_register_path, COMPARISON_COLUMNS, allow_empty=True,
    )
    comparison_manifest_sha256 = file_sha256(case_comparison_register_path)
    facts = expected_facts(common_mapping_path, task_mapping_path)
    measures = expected_measures(measure_catalog_path)
    measure_expressions = expected_measure_expressions(measure_fsh_path)
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
    if set(measure_expressions) != set(measures):
        raise ValueError(f"{measure_fsh_path}: Measure set differs from catalog")
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
    measure_facts = expected_measure_facts(criteria, measures)
    comparison_rows = validate_case_comparisons(
        case_comparison_register_path, comparisons, measures,
        measure_expressions, measure_facts,
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
    declared_derived_dependencies = validate_derivation_dependencies(primary_rows)

    if len(validations) != len(measures) or len({row["measure_id"] for row in validations}) != len(measures):
        raise ValueError(f"{validation_register_path}: expected one row per Measure")
    if {row["measure_id"] for row in validations} != set(measures):
        raise ValueError(f"{validation_register_path}: Measure set differs from catalog")
    for row in validations:
        if row["indicator_family"] != measures[row["measure_id"]]:
            raise ValueError(f"{validation_register_path}: stale indicator_family for {row['measure_id']}")
        if row["independent_status"] not in {"pending", "approved"} or row["golden_cohort_status"] not in {"pending", "approved"}:
            raise ValueError(f"{validation_register_path}: invalid status for {row['measure_id']}")
        coverage = exact_case_coverage(
            row, comparison_rows[row["measure_id"]],
            measure_expressions[row["measure_id"]], measure_facts[row["measure_id"]],
        )
        declared_counts = {
            "independent_manifest_row_count": coverage["independent_row_count"],
            "golden_manifest_row_count": coverage["golden_row_count"],
            "independent_difference_count": coverage["independent_difference_count"],
            "golden_difference_count": coverage["golden_difference_count"],
        }
        for field, expected in declared_counts.items():
            if row[field].strip():
                value = parse_nonnegative_int(row, field)
                if value != expected:
                    raise ValueError(
                        f"{validation_register_path}: {field}/manifest mismatch "
                        f"for {row['measure_id']}"
                    )
        if row["comparison_manifest_sha256"].strip() and (
            row["comparison_manifest_sha256"] != comparison_manifest_sha256
        ):
            raise ValueError(
                f"{validation_register_path}: comparison manifest hash mismatch "
                f"for {row['measure_id']}"
            )
        if row["independent_status"] == "approved" and not independent_complete(
            row, coverage, comparison_manifest_sha256,
        ):
            raise ValueError(f"{validation_register_path}: incomplete independent approval for {row['measure_id']}")
        if row["golden_cohort_status"] == "approved" and not golden_complete(
            row, coverage, comparison_manifest_sha256,
        ):
            raise ValueError(f"{validation_register_path}: incomplete golden approval for {row['measure_id']}")
        if (
            row["independent_status"] == "approved"
            and row["golden_cohort_status"] == "approved"
            and coverage["cohort_tokens_aligned"] is not True
        ):
            raise ValueError(
                f"{validation_register_path}: VM-05/VM-06 cohort tokens differ "
                f"for {row['measure_id']}"
            )
        row["_coverage"] = coverage

    complete_contracts = sum(
        source_contract_complete(rows[0]) for rows in primary_rows.values()
    )
    approved_sources = sum(source_complete(rows[0]) for rows in primary_rows.values())
    independent_count = sum(
        independent_complete(row, row["_coverage"], comparison_manifest_sha256)
        for row in validations
    )
    golden_count = sum(
        golden_complete(row, row["_coverage"], comparison_manifest_sha256)
        for row in validations
    )
    return {
        "gate_scope": "raw-source-independent-recalculation-and-golden-cohort",
        "expected_fact_count": len(facts),
        "source_evidence_row_count": len(sources),
        "secondary_reconciliation_row_count": secondary_count,
        "approved_secondary_reconciliation_row_count": approved_secondary_count,
        "source_contract_dimension_count": len(SOURCE_CONTRACT_FIELDS),
        "complete_source_contract_count": complete_contracts,
        "declared_derived_dependency_count": declared_derived_dependencies,
        "approved_authoritative_or_derived_fact_count": approved_sources,
        "measure_count": len(measures),
        "measure_expression_count": len(set().union(*measure_expressions.values())),
        "measure_expression_occurrence_count": sum(
            map(len, measure_expressions.values())
        ),
        "case_level_comparison_row_count": len(comparisons),
        "comparison_manifest_sha256": comparison_manifest_sha256,
        "population_criterion_count": len(criteria),
        "criterion_referenced_fact_count": len(criterion_fact_ids),
        "approved_independent_recalculation_count": independent_count,
        "approved_golden_cohort_count": golden_count,
        "source_register_integrity_gate": "pass",
        "validation_register_integrity_gate": "pass",
        "case_level_comparison_integrity_gate": "pass",
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
    parser.add_argument("--measure-fsh", type=Path, required=True)
    parser.add_argument("--case-comparison-register", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "data"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(
            args.source_register, args.validation_register, args.common_mapping,
            args.task_mapping, args.measure_catalog,
            args.population_criteria,
            args.measure_fsh, args.case_comparison_register,
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
