#!/usr/bin/env python3
"""Audit the complete data-correctness and formal-release controls.

Publisher QA is necessary but deliberately insufficient: this gate also checks
source traceability, terminology, independent calculation, golden-cohort and
human/operational approvals before it can report a formal release pass.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


CONTROL_IDS = {f"RC-{number:02d}" for number in range(1, 9)}
REQUIRED_CONTROL_COLUMNS = {
    "control_id", "control_name", "scope", "current_status", "evidence",
    "owner", "exit_criteria",
}
REQUIRED_MEASURE_COLUMNS = {
    "measure_id", "fhir_conformance", "cql_execution", "terminology_evidence",
    "raw_source_mapping", "independent_recalculation", "golden_cohort",
}
OPERATIONAL_APPROVALS = {"SEC-PRIVACY", "UAT-VPN", "PUB-RELEASE"}
SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def read_csv(
    path: Path, required: set[str], *, exact_columns: bool = False
) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = set(rows[0]) if rows else set()
    if not rows or (actual != required if exact_columns else not required <= actual):
        raise ValueError(f"{path}: expected columns {sorted(required)}")
    return rows


def clinical_valueset_count_and_empty_count(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    marker = "// 個管作業分類：院內行政代碼"
    if marker not in text:
        raise ValueError(f"{path}: clinical/admin terminology boundary is missing")
    blocks = text.split(marker, 1)[0].split("ValueSet: ")[1:]
    return len(blocks), sum("* include" not in block for block in blocks)


def approval_complete(row: dict[str, str]) -> bool:
    if row["Status"] != "approved" or row["Decision (approve/reject/revise)"] != "approve":
        return False
    required = (
        "Signer name", "Signer organization/title", "Decision date",
        "Evidence URI/path", "Signed artifact SHA-256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["Decision date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["Signed artifact SHA-256"].strip()) is not None


def audit(
    controls_path: Path,
    measure_audit_path: Path,
    terminology_path: Path,
    approvals_path: Path,
    publisher_audit_path: Path,
) -> dict[str, object]:
    controls = read_csv(controls_path, REQUIRED_CONTROL_COLUMNS, exact_columns=True)
    if {row["control_id"] for row in controls} != CONTROL_IDS or len(controls) != 8:
        raise ValueError(f"{controls_path}: control_id must be exactly RC-01 through RC-08")
    if any(row["current_status"] not in {"pass", "blocked"} for row in controls):
        raise ValueError(f"{controls_path}: current_status must be pass or blocked")
    for row in controls:
        for field in ("control_name", "scope", "evidence", "owner", "exit_criteria"):
            if not row[field].strip():
                raise ValueError(f"{controls_path}: {row['control_id']} has empty {field}")

    measures = read_csv(measure_audit_path, REQUIRED_MEASURE_COLUMNS)
    if len(measures) != 20 or len({row["measure_id"] for row in measures}) != 20:
        raise ValueError(f"{measure_audit_path}: expected exactly 20 unique Measures")
    approvals = read_csv(
        approvals_path,
        {
            "Gate ID", "Category", "Proposed decision", "Required signer", "Status",
            "Acceptance evidence", "Decision (approve/reject/revise)", "Signer name",
            "Signer organization/title", "Decision date", "Evidence URI/path",
            "Signed artifact SHA-256", "Notes",
        },
    )
    approval_ids = {row["Gate ID"] for row in approvals}
    if not OPERATIONAL_APPROVALS <= approval_ids:
        raise ValueError(f"{approvals_path}: missing operational approval gates")
    publisher = json.loads(publisher_audit_path.read_text(encoding="utf-8"))
    if publisher.get("gate_scope") != "publisher-qa-only":
        raise ValueError(
            f"{publisher_audit_path}: gate_scope must be publisher-qa-only"
        )
    for field in ("qa_integrity_gate", "formal_release_gate"):
        if publisher.get(field) not in {"pass", "block", "fail"}:
            raise ValueError(f"{publisher_audit_path}: invalid or missing {field}")

    clinical_count, empty_clinical_count = clinical_valueset_count_and_empty_count(
        terminology_path
    )
    governance = [row for row in approvals if row["Gate ID"] not in OPERATIONAL_APPROVALS]
    operational = [row for row in approvals if row["Gate ID"] in OPERATIONAL_APPROVALS]
    derived = {
        "RC-01": "pass" if all(row["raw_source_mapping"] == "pass" for row in measures) else "blocked",
        "RC-02": "pass" if publisher["qa_integrity_gate"] == "pass" else "blocked",
        "RC-03": "pass" if (
            clinical_count > 0
            and empty_clinical_count == 0
            and all(row["terminology_evidence"] in {"verified", "not-applicable"} for row in measures)
        ) else "blocked",
        "RC-04": "pass" if all(
            row["fhir_conformance"] == "pass"
            and row["cql_execution"].startswith("pass-synthetic")
            for row in measures
        ) else "blocked",
        "RC-05": "pass" if all(row["independent_recalculation"] == "pass" for row in measures) else "blocked",
        "RC-06": "pass" if all(row["golden_cohort"] == "pass" for row in measures) else "blocked",
        "RC-07": "pass" if governance and all(approval_complete(row) for row in governance) else "blocked",
        "RC-08": "pass" if len(operational) == len(OPERATIONAL_APPROVALS) and all(
            approval_complete(row) for row in operational
        ) else "blocked",
    }
    declared = {row["control_id"]: row["current_status"] for row in controls}
    mismatches = [
        {"control_id": control_id, "declared": declared[control_id], "derived": status}
        for control_id, status in derived.items()
        if declared[control_id] != status
    ]
    passed = sorted(control_id for control_id, status in derived.items() if status == "pass")
    blocked = sorted(control_id for control_id, status in derived.items() if status == "blocked")
    integrity = "pass" if not mismatches else "fail"
    data_gate = "pass" if integrity == "pass" and all(
        derived[f"RC-{number:02d}"] == "pass" for number in range(1, 7)
    ) else "block"
    formal_gate = "pass" if (
        integrity == "pass"
        and not blocked
        and publisher["formal_release_gate"] == "pass"
    ) else "block"
    return {
        "register": str(controls_path),
        "control_count": 8,
        "data_correctness_control_count": 6,
        "derived_status": derived,
        "passed_controls": passed,
        "blocked_controls": blocked,
        "status_mismatches": mismatches,
        "clinical_valuesets": clinical_count,
        "empty_clinical_valuesets": empty_clinical_count,
        "control_integrity_gate": integrity,
        "data_correctness_gate": data_gate,
        "publisher_formal_qa_gate": publisher["formal_release_gate"],
        "formal_release_gate": formal_gate,
        "maximum_supported_claim": (
            "technical-draft-only" if integrity == "pass" and derived["RC-02"] == "pass"
            and derived["RC-04"] == "pass" else "not-technically-ready"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--measure-audit", type=Path, required=True)
    parser.add_argument("--terminology-fsh", type=Path, required=True)
    parser.add_argument("--approval-register", type=Path, required=True)
    parser.add_argument("--publisher-audit", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--target", choices=("integrity", "data", "formal"), default="integrity"
    )
    args = parser.parse_args()
    try:
        report = audit(
            args.controls, args.measure_audit, args.terminology_fsh,
            args.approval_register, args.publisher_audit,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Release-control audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Release controls: {len(report['passed_controls'])}/8 pass; "
        f"blocked={','.join(report['blocked_controls']) or 'none'}"
    )
    print(f"Control integrity gate: {report['control_integrity_gate']}")
    print(f"Data correctness gate: {report['data_correctness_gate']}")
    print(f"Formal release gate: {report['formal_release_gate']}")
    print(f"Maximum supported claim: {report['maximum_supported_claim']}")
    selected = {
        "integrity": "control_integrity_gate",
        "data": "data_correctness_gate",
        "formal": "formal_release_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
