#!/usr/bin/env python3
"""Derive and audit the acquisition order for every mapped source fact.

P0/P1/P2 is an acquisition sequence, not an optionality scale.  Every row is
required before a production publication claim.  Priority is computed from the
criterion graph so a hand-edited spreadsheet cannot quietly downgrade a fact.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


PRIORITY_COLUMNS = [
    "fact_id",
    "priority",
    "fact_name",
    "indicator_family",
    "source_owner",
    "affected_criterion_ids",
    "criterion_owner_ids",
    "population_roles",
    "mapping_review_status",
    "priority_basis",
    "fhir_target",
    "acquisition_question",
    "acceptance_evidence",
    "release_requirement",
]

RATE_ROLES = {
    "initial-population",
    "denominator",
    "denominator-exclusion",
    "numerator",
    "numerator-exclusion",
}

ACCEPTANCE = {
    "P0": (
        "approved source contract; source-to-FHIR case trace; explicit null/time/unit "
        "rules; independent recalculation and golden-cohort comparison"
    ),
    "P1": (
        "approved source contract; source-to-FHIR case trace; bucket-level "
        "golden-cohort distribution comparison"
    ),
    "P2": (
        "approved source/output contract; provenance or report-reconciliation evidence"
    ),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    return rows


def family_set(value: str) -> set[str]:
    if value == "both":
        return {"quality", "quarterly"}
    if value in {"quality", "quarterly"}:
        return {value}
    raise ValueError(f"invalid indicator family {value!r}")


def derive(
    common_mapping_path: Path,
    task_mapping_path: Path,
    population_criteria_path: Path,
    source_register_path: Path,
) -> list[dict[str, str]]:
    common = read_rows(common_mapping_path)
    task = read_rows(task_mapping_path)
    criteria = read_rows(population_criteria_path)
    sources = read_rows(source_register_path)

    if len(common) != 34 or len(task) != 18:
        raise ValueError("expected exactly 34 common and 18 task-only facts")
    if len(criteria) != 68 or len({row["criterion_id"] for row in criteria}) != 68:
        raise ValueError("expected exactly 68 unique population criteria")

    facts: dict[str, dict[str, str]] = {}
    for row in common:
        facts[row["mapping_id"]] = {
            "fact_name": row["common_concept"],
            "indicator_family": row["used_by_indicator_family"],
            "mapping_review_status": row["review_status"],
            "field_group": "clinical-common",
            "fhir_target": (
                f"{row['source_profile_or_resource']}::{row['target_path']}"
            ),
            "acquisition_detail": row["gap_if_absent"],
        }
    for row in task:
        fact_id = row["field_id"]
        if fact_id in facts:
            raise ValueError(f"duplicate fact ID {fact_id}")
        facts[fact_id] = {
            "fact_name": row["field_zh"],
            "indicator_family": row["used_by_indicator_family"],
            "mapping_review_status": row["review_status"],
            "field_group": row["field_group"],
            "fhir_target": row["fhir_representation"],
            "acquisition_detail": row["required_behavior"],
        }

    source_owner: dict[str, str] = {}
    for row in sources:
        if row["source_role"] == "secondary-reconciliation":
            continue
        fact_id = row["fact_id"]
        if fact_id in source_owner:
            raise ValueError(f"{source_register_path}: multiple primary rows for {fact_id}")
        source_owner[fact_id] = row["source_owner"]
    if set(source_owner) != set(facts):
        raise ValueError(f"{source_register_path}: primary fact coverage differs from mappings")

    dependencies: dict[str, list[dict[str, str]]] = defaultdict(list)
    for criterion in criteria:
        for fact_id in criterion["depends_on_mapping"].split():
            if fact_id not in facts:
                raise ValueError(
                    f"{population_criteria_path}: {criterion['criterion_id']} uses unknown {fact_id}"
                )
            if criterion["indicator_family"] not in family_set(
                facts[fact_id]["indicator_family"]
            ):
                raise ValueError(
                    f"{fact_id} is declared {facts[fact_id]['indicator_family']} but "
                    f"{criterion['criterion_id']} uses it for {criterion['indicator_family']}"
                )
            dependencies[fact_id].append(criterion)

    expected: list[dict[str, str]] = []
    for fact_id in sorted(facts):
        fact = facts[fact_id]
        uses = dependencies[fact_id]
        roles = sorted({row["population_type"] for row in uses})
        bases: list[str] = []
        if fact["mapping_review_status"] == "blocking-data-gap":
            bases.append("blocking-data-gap")
        if RATE_ROLES.intersection(roles):
            bases.append("cohort-or-rate-calculation")
        if fact["field_group"] == "provenance":
            bases.append("release-provenance")
        if not RATE_ROLES.intersection(roles) and uses:
            bases.append("distribution-stratifier")
        if not uses and fact["field_group"] != "provenance":
            bases.append("report-support-or-unused-candidate")

        if (
            "blocking-data-gap" in bases
            or "cohort-or-rate-calculation" in bases
            or "release-provenance" in bases
        ):
            priority = "P0"
        elif uses:
            priority = "P1"
        else:
            priority = "P2"

        expected.append({
            "fact_id": fact_id,
            "priority": priority,
            "fact_name": fact["fact_name"],
            "indicator_family": fact["indicator_family"],
            "source_owner": source_owner[fact_id],
            "affected_criterion_ids": " ".join(sorted({r["criterion_id"] for r in uses})),
            "criterion_owner_ids": " ".join(sorted({r["measure_id"] for r in uses})),
            "population_roles": " ".join(roles),
            "mapping_review_status": fact["mapping_review_status"],
            "priority_basis": "; ".join(bases),
            "fhir_target": fact["fhir_target"],
            "acquisition_question": (
                f"Identify the authoritative system/artifact/element and version for "
                f"{fact['fact_name']}; resolve: {fact['acquisition_detail']}"
            ),
            "acceptance_evidence": ACCEPTANCE[priority],
            "release_requirement": "required-before-production-publication",
        })
    return expected


def audit(register_path: Path, expected: list[dict[str, str]]) -> dict[str, object]:
    actual = read_rows(register_path)
    if list(actual[0]) != PRIORITY_COLUMNS:
        raise ValueError(f"{register_path}: expected exact columns {PRIORITY_COLUMNS}")
    if len(actual) != 52 or len({row["fact_id"] for row in actual}) != 52:
        raise ValueError(f"{register_path}: expected exactly one row for each of 52 facts")
    expected_by_id = {row["fact_id"]: row for row in expected}
    actual_by_id = {row["fact_id"]: row for row in actual}
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError(f"{register_path}: fact set differs from the mappings")
    for fact_id, expected_row in expected_by_id.items():
        if actual_by_id[fact_id] != expected_row:
            stale = [
                field for field in PRIORITY_COLUMNS
                if actual_by_id[fact_id].get(field) != expected_row[field]
            ]
            raise ValueError(f"{register_path}: stale derived fields for {fact_id}: {stale}")

    counts = {
        priority: sum(row["priority"] == priority for row in expected)
        for priority in ("P0", "P1", "P2")
    }
    return {
        "gate_scope": "source-acquisition-priority-integrity",
        "fact_count": len(expected),
        "priority_counts": counts,
        "criterion_referenced_fact_count": sum(
            bool(row["affected_criterion_ids"]) for row in expected
        ),
        "priority_register_integrity_gate": "pass",
        "priority_is_sequence_not_optionality": True,
    }


def write_register(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRIORITY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--common-mapping", type=Path, required=True)
    parser.add_argument("--task-mapping", type=Path, required=True)
    parser.add_argument("--population-criteria", type=Path, required=True)
    parser.add_argument("--source-register", type=Path, required=True)
    parser.add_argument("--write-register", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        expected = derive(
            args.common_mapping,
            args.task_mapping,
            args.population_criteria,
            args.source_register,
        )
        if args.write_register:
            write_register(args.register, expected)
        report = audit(args.register, expected)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Source acquisition priority audit failed: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    counts = report["priority_counts"]
    print(
        f"Source acquisition priority: P0={counts['P0']}; "
        f"P1={counts['P1']}; P2={counts['P2']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
