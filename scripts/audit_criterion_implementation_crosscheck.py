#!/usr/bin/env python3
"""Build and audit the 68-row criterion-to-implementation crosscheck.

This register deliberately separates executable coverage from correctness.
An ELM/runtime pass proves that an expression runs; it does not approve the
clinical definition, the source semantics, or the resulting case membership.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


COLUMNS = [
    "criterion_id",
    "measure_id",
    "indicator_family",
    "population_type",
    "variant",
    "normative_rule",
    "cql_evidence",
    "cql_alignment",
    "legacy_python_status",
    "source_approval",
    "workflow_contract",
    "difference_classes",
    "known_difference",
    "publication_disposition",
    "required_resolution",
]


def _evidence_map() -> dict[str, str]:
    result: dict[str, str] = {}

    def add(evidence: str, *criterion_ids: str) -> None:
        for criterion_id in criterion_ids:
            if criterion_id in result:
                raise ValueError(f"duplicate CQL evidence mapping for {criterion_id}")
            result[criterion_id] = evidence

    add("task-layer-only", "IP-CLASS", "X1-TEAM", "X5-TEAM", "N5-ADH-RULE")
    add("Reporting Episode|Initial Population", "IP-QUARTER")
    add("Denominator 1", "D1-STAGE")
    add("Denominator 1 Exclusion", "D1-ER", "X1-ER-LOW")
    add("Numerator 1", "N1-HT")
    add("Denominator 2", "D2-STAGE", "D2-NODE", "D2-SURGERY-FIRST")
    add("Numerator 2", "N2-SLNB")
    add("Denominator 3", "D3-NODE", "D3-MASTECTOMY", "D3-STAGE")
    add("Denominator 3 Exclusion", "X3-STAGE4")
    add("Numerator 3", "N3-RT")
    add("Total Radiotherapy Dose cGy", "N3-DOSE")
    add("Denominator 4", "D4-SURGERY", "D4-HER2", "D4-NODE")
    add("Denominator 4 Exclusion", "X4-STAGE4")
    add("Numerator 4", "N4-ANTIHER2")
    add("Denominator 5", "D5-SURGERY", "D5-STAGE")
    add("Denominator 5 Exclusion", "X5-INSITU-STAGE4")
    add("Numerator 5|Earliest Histologic Diagnosis Date", "N5-BIOPSY-BEFORE")
    add("Denominator 6", "D6-SURGERY-BCT", "D6-INVASIVE")
    add("Denominator 6 Exclusion", "X6-STAGE4")
    add("Denominator 6 Exclusion|Definition Age Node Exclusion", "X6-AGE-NODE-DEF")
    add("Denominator 6 Exclusion|Practice Age Node Exclusion", "X6-AGE-PRACTICE", "X6-NODE-PRACTICE")
    add("Numerator 6", "N6-RT")

    add("Quarterly Caseload", "IP-CASELOAD")
    add("New Diagnosis Case", "IP-NEWDX")
    add("Denominator QR1", "D1-BASE")
    add("Denominator QR1 Exclusion", "X1-STAGING", "X1-STAGING-DEATH", "X1-CONSIDERING")
    add("Numerator QR1", "N1-STAY")
    add("Numerator QR1 Exclusion", "X1-NOSTAY-TRANSFER", "X1-NOSTAY-REFUSE")
    add("Denominator QR2", "D2-BASE")
    add("Numerator QR2", "N2-STAY-INSYS")
    add("Denominator QR3", "D3-BASE")
    add("Denominator QR3 Exclusion", "X3-STAGING", "X3-ONGOING", "X3-TX-EVENT", "X3-NONCURATIVE")
    add("Numerator QR3", "N3-COMPLETE")
    add("Numerator QR3 Exclusion", "X3-INCOMPLETE")
    add("Prior Year And Current New Diagnosis Cohort|Denominator QR4", "D4-COHORT")
    add("Last Contact Date|Numerator QR4", "N4-LOST")
    add("Denominator QR5", "D5-QUIT")
    add("Interruption Date|Numerator QR5", "N5-RETURN")
    add("Case Entry Category", "S10-IDENTITY")
    add("Case Entry Month", "S11-MONTH")
    add("Case Status Reported", "S12-DYNAMIC")
    add("Closure Reason", "S13-CLOSURE")
    add("Administrative Sex", "S14-SEX")
    add("Age Band At Case Entry", "S14-AGEBAND")
    add("Registry Case Class Reported", "S15-CLASS")
    add("Is Registry Class 3", "S15-CLASS3")
    add("Reported Stage Group", "S16-STAGE")
    add("Histology Group", "S17-HISTOLOGY")
    add("HR HER2 Subtype", "S18-SUBTYPE")
    return result


SPECIAL = {
    "IP-CLASS": (
        "task-layer-only",
        "Class 1/2 and breast-cancer membership are assumed when the evaluation Group is assembled; this repository has no executable Group-assembly rule.",
        "Implement and test the Group-assembly contract, then obtain cohort-owner approval.",
    ),
    "X1-TEAM": (
        "task-layer-only",
        "The multidisciplinary exclusion is intentionally absent from CQL and must be applied as a reasoned case-level decision.",
        "Define the Task/MeasureReport override contract and reconcile every excluded case.",
    ),
    "N3-DOSE": (
        "known-not-enforced",
        "Total Radiotherapy Dose cGy is a null placeholder and Numerator 3 does not enforce the required >=4000 cGy threshold; the result is only an upper bound.",
        "Add an approved delivered-dose source/profile, enforce the unit-normalized threshold, and rerun truth cases.",
    ),
    "X5-TEAM": (
        "task-layer-only",
        "The multidisciplinary exclusion is intentionally absent from CQL and must be applied as a reasoned case-level decision.",
        "Define the Task/MeasureReport override contract and reconcile every excluded case.",
    ),
    "N5-ADH-RULE": (
        "task-layer-only",
        "The ADH committee add-back is intentionally absent from CQL and has no executable per-case override contract in this IG.",
        "Define the governed add-back input/output and test the original value, reason, decision, and approver trail.",
    ),
    "X6-AGE-NODE-DEF": (
        "implemented-variant-unresolved",
        "The written AND rule is implemented, but the caller may instead choose the historical practice variant; the authoritative reading is not approved.",
        "Obtain cancer-committee approval of one variant and lock the production parameter value.",
    ),
    "X6-AGE-PRACTICE": (
        "implemented-variant-unresolved",
        "The historical age-only exclusion is implemented, but it conflicts with the written AND rule.",
        "Obtain cancer-committee approval of one variant and lock the production parameter value.",
    ),
    "X6-NODE-PRACTICE": (
        "implemented-variant-unresolved",
        "The historical node-only exclusion is implemented, but it conflicts with the written AND rule.",
        "Obtain cancer-committee approval of one variant and lock the production parameter value.",
    ),
    "D4-COHORT": (
        "conditional-data-contract",
        "The expression returns false unless the caller asserts that the full prior-year plus current cohort was loaded; the current single-period export cannot prove that assertion.",
        "Approve and load the complete cohort contract, then reconcile all denominator members.",
    ),
    "N4-LOST": (
        "conditional-data-contract",
        "The one-year calculation executes only inside the unavailable complete cohort and still requires governed manual loss-to-follow-up adjudication.",
        "Load longitudinal contact history and the complete cohort, then reconcile case-level adjudications.",
    ),
    "N5-RETURN": (
        "candidate-not-approved",
        "The interruption-date and subsequent-treatment expression is a candidate rule; the source does not currently record an approved interruption date.",
        "Approve the event semantics and compare the candidate against a case-manager truth set.",
    ),
    "S17-HISTOLOGY": (
        "definition-contradiction",
        "CQL implements ten histology groups while the source documentation says eleven; the unidentified group must not be invented.",
        "Pathology and case-management owners must identify and approve the exact group set and terminology.",
    ),
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        result = list(csv.DictReader(handle))
    if not result:
        raise ValueError(f"{path}: empty CSV")
    return result


def cql_symbols(cql_text: str) -> set[str]:
    return set(re.findall(r'^define(?: function)? "([^"]+)"', cql_text, re.MULTILINE))


def derive(
    criteria_path: Path,
    source_register_path: Path,
    task_mapping_path: Path,
    cql_path: Path,
    fsh_directory: Path,
) -> list[dict[str, str]]:
    criteria = read_rows(criteria_path)
    sources = read_rows(source_register_path)
    task_fields = {row["field_id"]: row for row in read_rows(task_mapping_path)}
    if len(criteria) != 68 or len({row["criterion_id"] for row in criteria}) != 68:
        raise ValueError("expected exactly 68 unique criteria")

    evidence = _evidence_map()
    criterion_ids = {row["criterion_id"] for row in criteria}
    if set(evidence) != criterion_ids:
        missing = sorted(criterion_ids - set(evidence))
        extra = sorted(set(evidence) - criterion_ids)
        raise ValueError(f"CQL evidence coverage differs; missing={missing}, extra={extra}")

    cql_text = cql_path.read_text(encoding="utf-8")
    symbols = cql_symbols(cql_text)
    for criterion_id, value in evidence.items():
        if value == "task-layer-only":
            continue
        unknown = [symbol for symbol in value.split("|") if symbol not in symbols]
        if unknown:
            raise ValueError(f"{criterion_id}: unknown CQL symbols {unknown}")

    source_by_fact: dict[str, list[dict[str, str]]] = {}
    for source in sources:
        if source["source_role"] == "secondary-reconciliation":
            continue
        source_by_fact.setdefault(source["fact_id"], []).append(source)
    duplicate_sources = [fact for fact, rows in source_by_fact.items() if len(rows) != 1]
    if duplicate_sources:
        raise ValueError(f"expected one primary source row for {duplicate_sources}")

    fsh_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(fsh_directory.glob("*.fsh"))
    )
    profile_blocks = re.findall(
        r"(?ms)^Profile:\s+\S+.*?(?=^(?:Profile|Instance|Extension|Logical):|\Z)",
        fsh_text,
    )
    dedicated_task_profile = any(
        re.search(r"(?m)^Parent:\s+Task\s*$", block)
        and ("cm-task-input-type" in block or "CMTaskInputType" in block)
        for block in profile_blocks
    )

    result: list[dict[str, str]] = []
    for criterion in criteria:
        criterion_id = criterion["criterion_id"]
        dependencies = criterion["depends_on_mapping"].split()
        missing_source_rows = [fact for fact in dependencies if fact not in source_by_fact]
        if missing_source_rows:
            raise ValueError(f"{criterion_id}: facts missing from source register {missing_source_rows}")
        approved = sum(
            source_by_fact[fact][0]["review_status"] == "approved" for fact in dependencies
        )

        task_targets = [
            task_fields[fact]["fhir_representation"]
            for fact in dependencies
            if fact in task_fields and "Task" in task_fields[fact]["fhir_representation"]
        ]
        if not task_targets:
            workflow_contract = "not-applicable"
        elif dedicated_task_profile:
            workflow_contract = "dedicated-task-profile-present-pending-approval"
        else:
            workflow_contract = "missing-dedicated-task-profile"

        if criterion_id in SPECIAL:
            alignment, special_difference, special_resolution = SPECIAL[criterion_id]
        else:
            alignment = "aligned-to-current-draft"
            special_difference = ""
            special_resolution = ""

        classes: list[str] = []
        if alignment != "aligned-to-current-draft":
            classes.append(alignment)
        if criterion["proxy_removed_by_fhir"] in {"yes", "partial", "partly"}:
            classes.append("source-proxy-replacement")
        if criterion["python_status"] in {
            "not-implemented", "divergent", "not-evaluable", "manual-override", "task-layer"
        }:
            classes.append(f"legacy-{criterion['python_status']}")
        if criterion["review_status"] in {"blocking-data-gap", "open-question", "proxy-in-use"}:
            classes.append(criterion["review_status"])
        if workflow_contract == "missing-dedicated-task-profile":
            classes.append("workflow-profile-gap")
        if not classes:
            classes.append("none-known-against-current-draft")

        details = [special_difference]
        if criterion["current_proxy"] and criterion["current_proxy"] != "none":
            details.append(f"Current source/report proxy: {criterion['current_proxy']}")
        if criterion["python_divergence"]:
            details.append(f"Legacy Python result impact: {criterion['python_divergence']}")
        if workflow_contract == "missing-dedicated-task-profile":
            details.append(
                "Task elements are queried through a generic Task contract; no dedicated local case-management Task profile constrains subject, slices, cardinalities, or bindings."
            )
        details = [detail for detail in details if detail]
        if not details:
            details = [
                "No implementation difference identified against the current draft; clinical meaning and real-data correctness remain unapproved."
            ]

        resolutions = [
            "Approve every dependent source fact and its null, time, unit, transformation, and provenance semantics.",
            "Obtain criterion owner sign-off and pass independent recalculation plus end-to-end golden-cohort reconciliation.",
        ]
        if special_resolution:
            resolutions.insert(0, special_resolution)
        if workflow_contract == "missing-dedicated-task-profile":
            resolutions.insert(
                0,
                "Add a dedicated case-management Task profile or approve an equally testable generic-Task contract.",
            )

        result.append({
            "criterion_id": criterion_id,
            "measure_id": criterion["measure_id"],
            "indicator_family": criterion["indicator_family"],
            "population_type": criterion["population_type"],
            "variant": criterion["variant"],
            "normative_rule": criterion["criterion_zh"],
            "cql_evidence": evidence[criterion_id],
            "cql_alignment": alignment,
            "legacy_python_status": criterion["python_status"],
            "source_approval": f"{approved}/{len(dependencies)}-facts-approved",
            "workflow_contract": workflow_contract,
            "difference_classes": "; ".join(sorted(set(classes))),
            "known_difference": " | ".join(details),
            "publication_disposition": "blocked-for-production-publication",
            "required_resolution": " | ".join(resolutions),
        })
    return result


def audit(register_path: Path, expected: list[dict[str, str]]) -> dict[str, object]:
    actual = read_rows(register_path)
    if list(actual[0]) != COLUMNS:
        raise ValueError(f"{register_path}: expected exact columns {COLUMNS}")
    if len(actual) != 68 or len({row["criterion_id"] for row in actual}) != 68:
        raise ValueError(f"{register_path}: expected exactly 68 unique criterion rows")
    expected_by_id = {row["criterion_id"]: row for row in expected}
    actual_by_id = {row["criterion_id"]: row for row in actual}
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError(f"{register_path}: criterion set differs from criteria source")
    for criterion_id, expected_row in expected_by_id.items():
        if actual_by_id[criterion_id] != expected_row:
            stale = [
                column for column in COLUMNS
                if actual_by_id[criterion_id].get(column) != expected_row[column]
            ]
            raise ValueError(f"{register_path}: stale fields for {criterion_id}: {stale}")

    alignment_counts: dict[str, int] = {}
    for row in expected:
        alignment_counts[row["cql_alignment"]] = alignment_counts.get(row["cql_alignment"], 0) + 1
    return {
        "gate_scope": "criterion-to-implementation-crosscheck-integrity",
        "criterion_count": len(expected),
        "alignment_counts": dict(sorted(alignment_counts.items())),
        "source_fully_approved_count": sum(row["source_approval"].split("/", 1)[0] == row["source_approval"].split("/", 1)[1].split("-", 1)[0] for row in expected),
        "production_publication_allowed_count": sum(row["publication_disposition"] == "production-publication-allowed" for row in expected),
        "workflow_profile_gap_count": sum(row["workflow_contract"] == "missing-dedicated-task-profile" for row in expected),
        "integrity_gate": "pass",
    }


def write_register(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, required=True)
    parser.add_argument("--source-register", type=Path, required=True)
    parser.add_argument("--task-mapping", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--fsh-directory", type=Path, required=True)
    parser.add_argument("--write-register", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        expected = derive(
            args.criteria,
            args.source_register,
            args.task_mapping,
            args.cql,
            args.fsh_directory,
        )
        if args.write_register:
            write_register(args.register, expected)
        report = audit(args.register, expected)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Criterion implementation crosscheck failed: {exc}", file=sys.stderr)
        return 1
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
