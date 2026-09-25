#!/usr/bin/env python3
"""Build and audit role-based work packages for acquiring all 52 raw facts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


COLUMNS = [
    "fact_id",
    "acquisition_batch",
    "batch_rank",
    "work_package_id",
    "proposed_primary_owner_role",
    "required_co_reviewer_roles",
    "priority",
    "fact_name",
    "indicator_family",
    "affected_measure_ids",
    "affected_criterion_ids",
    "fhir_target",
    "acquisition_question",
    "required_source_artifacts",
    "acceptance_evidence",
    "assignment_status",
    "confirmed_owner_name",
    "confirmed_owner_organization_title",
    "assignment_date",
    "assignment_evidence_uri_path",
    "signed_assignment_sha256",
    "notes",
]

SHA256 = re.compile(r"[0-9a-fA-F]{64}")

BATCHES = {
    "B0-result-blockers": ("0", "P0 facts already classified as blocking-data-gap"),
    "B1-cohort-rate": ("1", "remaining P0 facts that determine cohort or rate"),
    "B2-release-provenance": ("2", "P0 release provenance not tied to one criterion"),
    "B3-stratifiers": ("3", "P1 distribution and stratifier facts"),
    "B4-support": ("4", "P2 output support or currently unused candidates"),
}

PACKAGE_DEFINITIONS = {
    "WP-01-PATIENT-ADMIN": {
        "facts": {"CM-BC-001", "CM-BC-030", "CM-BC-036"},
        "owner": "patient administration / health-information-management source owner",
        "reviewers": "case-management owner; privacy/data-governance reviewer",
        "artifacts": "MPI/ADT schema or API specification; birth sex and death field dictionary; patient merge and identifier rule; event timezone; extract query and version",
    },
    "WP-02-REGISTRY-STAGING": {
        "facts": {
            "CM-BC-002", "CM-BC-003", "CM-BC-004", "CM-BC-005",
            "CM-BC-006", "CM-BC-007", "CM-BC-033", "CM-BC-038",
        },
        "owner": "cancer-registry / staging source owner",
        "reviewers": "oncology clinical owner; pathology reviewer; terminology reviewer",
        "artifacts": "registry and staging schema; case-entry and diagnosis fields; AJCC edition and method; case and episode identity rules; prior-year cohort query; late-update duplicate and null rules; source version",
    },
    "WP-03-PATHOLOGY": {
        "facts": {
            "CM-BC-008", "CM-BC-009", "CM-BC-010", "CM-BC-011",
            "CM-BC-012", "CM-BC-013", "CM-BC-019", "CM-BC-032",
        },
        "owner": "pathology / laboratory-information-system source owner",
        "reviewers": "pathology clinical owner; cancer-registry owner; terminology reviewer",
        "artifacts": "LIS/pathology schema; accession specimen and report linkage; effective final and corrected timestamps; ER PR HER2 Ki-67 and histology code dictionaries; pending null correction and derivation rules; source version",
    },
    "WP-04-SURGERY-PROCEDURE": {
        "facts": {
            "CM-BC-014", "CM-BC-015", "CM-BC-016", "CM-BC-017", "CM-BC-018",
        },
        "owner": "surgery / procedure-record source owner",
        "reviewers": "breast-surgery clinical owner; pathology reviewer; coding/terminology reviewer",
        "artifacts": "OR and procedure schema; surgery axillary-procedure and biopsy code lists; performed start/end semantics; cancelled and not-done rules; laterality and encounter linkage; source version",
    },
    "WP-05-SYSTEMIC-THERAPY": {
        "facts": {"CM-BC-020", "CM-BC-021", "CM-BC-022"},
        "owner": "oncology medication / pharmacy source owner",
        "reviewers": "medical-oncology owner; pharmacy reviewer; terminology reviewer",
        "artifacts": "medication order and administration schema; drug and regimen code systems; intent authored administration and completion timestamps; status cancellation and external-treatment rules; source version",
    },
    "WP-06-RADIOTHERAPY": {
        "facts": {"CM-BC-023", "CM-BC-024", "CM-BC-025"},
        "owner": "radiation-oncology information-system source owner",
        "reviewers": "radiation-oncology clinical owner; medical-physics reviewer; FHIR/terminology reviewer",
        "artifacts": "OIS/RIS schema; course fraction target-volume and delivered-dose fields; UCUM and cGy conversion; performer location and external-site rules; completion status and source version",
    },
    "WP-07-CASE-MANAGEMENT": {
        "facts": {
            "CM-BC-031", "CM-BC-034", "CM-BC-035", "CM-BC-037",
            "CM-TASK-001", "CM-TASK-002", "CM-TASK-003", "CM-TASK-004",
            "CM-TASK-005", "CM-TASK-006", "CM-TASK-007", "CM-TASK-010",
            "CM-TASK-011", "CM-TASK-012", "CM-TASK-013", "CM-TASK-014",
            "CM-TASK-015", "CM-TASK-016", "CM-TASK-023",
        },
        "owner": "case-management / quality-program source owner",
        "reviewers": "indicator clinical owner; quality-committee owner; data-governance reviewer",
        "artifacts": "case-management form and database schema; complete code lists; original and adjusted result model; decision reason approver and audit timestamps; contact transfer treatment-state and closure semantics; source version",
    },
    "WP-08-REPORTING-PROVENANCE": {
        "facts": {"CM-TASK-020", "CM-TASK-021", "CM-TASK-022"},
        "owner": "reporting-platform / data-engineering owner",
        "reviewers": "quality-program owner; source-system owners; security/data-governance reviewer",
        "artifacts": "reporting-period and benchmark specification; extraction and job configuration; raw-file and run hashes; execution timestamp timezone and software version; Provenance retention and access policy",
    },
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    return rows


def package_by_fact() -> dict[str, tuple[str, dict[str, object]]]:
    result: dict[str, tuple[str, dict[str, object]]] = {}
    for package_id, package in PACKAGE_DEFINITIONS.items():
        for fact_id in package["facts"]:
            if fact_id in result:
                raise ValueError(f"{fact_id}: assigned to multiple work packages")
            result[fact_id] = (package_id, package)
    return result


def batch_for(row: dict[str, str]) -> str:
    if row["priority"] == "P0" and row["mapping_review_status"] == "blocking-data-gap":
        return "B0-result-blockers"
    if row["priority"] == "P0" and row["affected_criterion_ids"]:
        return "B1-cohort-rate"
    if row["priority"] == "P0":
        return "B2-release-provenance"
    if row["priority"] == "P1":
        return "B3-stratifiers"
    if row["priority"] == "P2":
        return "B4-support"
    raise ValueError(f"{row['fact_id']}: unsupported priority {row['priority']}")


def derive(priority_path: Path) -> list[dict[str, str]]:
    priority_rows = read_rows(priority_path)
    if len(priority_rows) != 52 or len({row["fact_id"] for row in priority_rows}) != 52:
        raise ValueError(f"{priority_path}: expected exactly 52 unique facts")
    packages = package_by_fact()
    fact_ids = {row["fact_id"] for row in priority_rows}
    if set(packages) != fact_ids:
        raise ValueError(
            f"work-package coverage differs; missing={sorted(fact_ids - set(packages))}, "
            f"extra={sorted(set(packages) - fact_ids)}"
        )

    expected: list[dict[str, str]] = []
    for source in priority_rows:
        fact_id = source["fact_id"]
        package_id, package = packages[fact_id]
        batch = batch_for(source)
        expected.append({
            "fact_id": fact_id,
            "acquisition_batch": batch,
            "batch_rank": BATCHES[batch][0],
            "work_package_id": package_id,
            "proposed_primary_owner_role": str(package["owner"]),
            "required_co_reviewer_roles": str(package["reviewers"]),
            "priority": source["priority"],
            "fact_name": source["fact_name"],
            "indicator_family": source["indicator_family"],
            "affected_measure_ids": source["criterion_owner_ids"],
            "affected_criterion_ids": source["affected_criterion_ids"],
            "fhir_target": source["fhir_target"],
            "acquisition_question": source["acquisition_question"],
            "required_source_artifacts": str(package["artifacts"]),
            "acceptance_evidence": source["acceptance_evidence"],
            "assignment_status": "unassigned",
            "confirmed_owner_name": "",
            "confirmed_owner_organization_title": "",
            "assignment_date": "",
            "assignment_evidence_uri_path": "",
            "signed_assignment_sha256": "",
            "notes": "",
        })
    return expected


def assignment_complete(row: dict[str, str]) -> bool:
    if row["assignment_status"] != "confirmed":
        return False
    required = (
        "confirmed_owner_name",
        "confirmed_owner_organization_title",
        "assignment_date",
        "assignment_evidence_uri_path",
        "signed_assignment_sha256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["assignment_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_assignment_sha256"].strip()) is not None


def audit(register_path: Path, expected: list[dict[str, str]]) -> dict[str, object]:
    actual = read_rows(register_path)
    if list(actual[0]) != COLUMNS:
        raise ValueError(f"{register_path}: columns must exactly match the locked schema")
    if len(actual) != 52 or len({row["fact_id"] for row in actual}) != 52:
        raise ValueError(f"{register_path}: expected exactly one row for each of 52 facts")
    expected_by_id = {row["fact_id"]: row for row in expected}
    actual_by_id = {row["fact_id"]: row for row in actual}
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError(f"{register_path}: fact set differs from source priority register")

    assignment_fields = {
        "assignment_status", "confirmed_owner_name",
        "confirmed_owner_organization_title", "assignment_date",
        "assignment_evidence_uri_path", "signed_assignment_sha256", "notes",
    }
    for fact_id, expected_row in expected_by_id.items():
        row = actual_by_id[fact_id]
        stale = [
            field for field in COLUMNS
            if field not in assignment_fields and row[field] != expected_row[field]
        ]
        if stale:
            raise ValueError(f"{register_path}: stale derived fields for {fact_id}: {stale}")
        if row["assignment_status"] not in {"unassigned", "confirmed"}:
            raise ValueError(f"{register_path}: {fact_id} has invalid assignment_status")
        if row["assignment_status"] == "unassigned" and any(
            row[field].strip() for field in assignment_fields - {"assignment_status", "notes"}
        ):
            raise ValueError(f"{register_path}: {fact_id} unassigned row contains assignment evidence")
        if row["assignment_status"] == "confirmed" and not assignment_complete(row):
            raise ValueError(f"{register_path}: {fact_id} confirmed assignment lacks signed evidence")

    batch_counts = {
        batch: sum(row["acquisition_batch"] == batch for row in actual)
        for batch in BATCHES
    }
    package_counts = {
        package_id: sum(row["work_package_id"] == package_id for row in actual)
        for package_id in PACKAGE_DEFINITIONS
    }
    confirmed = sum(assignment_complete(row) for row in actual)
    return {
        "gate_scope": "all-52-source-fact-acquisition-work-packages",
        "fact_count": 52,
        "work_package_count": len(PACKAGE_DEFINITIONS),
        "batch_counts": batch_counts,
        "work_package_fact_counts": package_counts,
        "confirmed_owner_assignment_count": confirmed,
        "unassigned_owner_count": 52 - confirmed,
        "work_package_integrity_gate": "pass",
        "owner_assignment_gate": "pass" if confirmed == 52 else "block",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--priority-register", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "assignment"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(args.register, derive(args.priority_register))
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Source-acquisition work-package audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Source acquisition work packages: {report['work_package_count']} packages, "
        f"owners confirmed={report['confirmed_owner_assignment_count']}/52"
    )
    selected = "work_package_integrity_gate" if args.target == "integrity" else "owner_assignment_gate"
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
