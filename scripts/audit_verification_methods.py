#!/usr/bin/env python3
"""Lock the exact eight verification methods to the derived release controls."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


REQUIRED_COLUMNS = {
    "method_id", "release_control_id", "method_class", "method_name",
    "verification_unit", "locked_scope", "pass_threshold", "required_evidence",
    "independence_rule", "owner",
}
EXPECTED = {
    "VM-01": {
        "release_control_id": "RC-01",
        "method_class": "data-correctness",
        "method_name": "raw-source-field-traceability",
        "locked_scope": (
            "52 source facts; 52 accountable owner assignments; "
            "19 source-contract dimensions per fact"
        ),
        "threshold_markers": (
            "52/52", "19 dimensions", "authoritative", "valid and acyclic",
            "reports remain secondary",
        ),
        "evidence_markers": (
            "source schema", "source-traceability-register.csv",
            "signed source contracts", "hashes",
        ),
        "independence_markers": (
            "original source data", "cannot satisfy", "unexplained not-applicable",
        ),
    },
    "VM-02": {
        "release_control_id": "RC-02",
        "method_class": "data-correctness",
        "method_name": "FHIR-structure-and-reference-conformance",
        "locked_scope": (
            "262 FHIR resources; 225 publication definitions; 37 synthetic examples; "
            "1028 reference edges; 47 StructureDefinitions"
        ),
        "threshold_markers": ("262/262", "1028/1028", "0 errors", "0 broken links"),
        "evidence_markers": ("Publisher qa.html", "fhir-resource-inventory-audit.json", "fhir-reference-graph-audit.json"),
        "independence_markers": ("separate from clinical correctness", "cannot substitute"),
    },
    "VM-03": {
        "release_control_id": "RC-03",
        "method_class": "data-correctness",
        "method_name": "terminology-resolution-and-clinical-review",
        "locked_scope": (
            "152 terminology artifacts: 60 CodeSystems; 90 ValueSets; 2 ConceptMaps; "
            "19 clinical ValueSets"
        ),
        "threshold_markers": ("152/152", "19/19", "every used code resolves", "0 candidate-unverified"),
        "evidence_markers": ("terminology-conformance-audit.json", "versioned expansions", "signatures"),
        "independence_markers": ("authorized reviewer", "cannot be inferred"),
    },
    "VM-04": {
        "release_control_id": "RC-04",
        "method_class": "data-correctness",
        "method_name": "executable-rule-and-boundary-testing",
        "locked_scope": "20 Measures; 46 population or stratifier expressions; 68 criteria",
        "threshold_markers": ("20/20", "46/46", "68/68", "boundary", "all enumerated strata"),
        "evidence_markers": ("CQL-to-ELM log", "asserted case-level results", "MeasureReport fixtures"),
        "independence_markers": ("independently of runtime output", "does not prove real-data correctness"),
    },
    "VM-05": {
        "release_control_id": "RC-05",
        "method_class": "data-correctness",
        "method_name": "independent-case-level-recalculation",
        "locked_scope": (
            "20 Measures; every in-scope case; all 62 Measure-expression uses "
            "across 46 unique CQL expressions"
        ),
        "threshold_markers": ("20/20", "exact case-by-declared-expression tuple set", "does not reuse CQL logic", "0 total final differences"),
        "evidence_markers": ("independent implementation hash", "truth-set hash", "case-level-comparison-register.csv", "manifest hash"),
        "independence_markers": ("independent of the CQL implementation", "partial expression sample are insufficient"),
    },
    "VM-06": {
        "release_control_id": "RC-06",
        "method_class": "data-correctness",
        "method_name": "end-to-end-original-data-golden-cohort",
        "locked_scope": (
            "20 Measures; one complete reporting period; every in-scope case; "
            "every required source fact and complete MeasureReport"
        ),
        "threshold_markers": ("20/20", "100%", "exact case-by-expression", "case-by-source-fact", "0 total final differences"),
        "evidence_markers": ("original extract hash", "FHIR Bundle hash", "case-level truth set", "case-level-comparison-register.csv", "manifest hash"),
        "independence_markers": ("independently", "comparison copies only"),
    },
    "VM-07": {
        "release_control_id": "RC-07",
        "method_class": "release-acceptance",
        "method_name": "clinical-specification-and-governance-approval",
        "locked_scope": (
            "14 QBC gates; 20 Measure definitions; 47 StructureDefinitions; "
            "12 non-aligned criterion decisions"
        ),
        "threshold_markers": ("14/14", "20/20", "47/47", "12/12", "live non-aligned criterion count is 0", "SHA-256"),
        "evidence_markers": ("approval registers", "signed decisions", "artifact hashes"),
        "independence_markers": ("cannot overwrite", "live implementation contradiction"),
    },
    "VM-08": {
        "release_control_id": "RC-08",
        "method_class": "release-acceptance",
        "method_name": "privacy-operational-version-and-publication-acceptance",
        "locked_scope": (
            "repository publication content; 3 operational approvals; 10 scope decisions; "
            "4 canonical version-policy groups"
        ),
        "threshold_markers": ("findings are 0", "3/3", "10/10", "4/4", "formal-release-ready"),
        "evidence_markers": ("repository-phi-pattern-scan-audit.json", "receiver receipt", "immutable release manifest"),
        "independence_markers": ("never substitutes", "formal privacy/security review"),
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = set(rows[0]) if rows else set()
    if not rows or actual != REQUIRED_COLUMNS:
        raise ValueError(f"{path}: expected exact columns {sorted(REQUIRED_COLUMNS)}")
    return rows


def audit(register_path: Path, controls_path: Path, release_audit_path: Path) -> dict[str, object]:
    rows = read_csv(register_path)
    by_id = {row["method_id"]: row for row in rows}
    if len(rows) != 8 or set(by_id) != set(EXPECTED):
        raise ValueError(f"{register_path}: method_id must be exactly VM-01 through VM-08")
    if len({row["release_control_id"] for row in rows}) != 8:
        raise ValueError(f"{register_path}: each release control must map to exactly one method")

    for method_id, expected in EXPECTED.items():
        row = by_id[method_id]
        for field in (
            "release_control_id", "method_class", "method_name", "locked_scope"
        ):
            if row[field] != expected[field]:
                raise ValueError(f"{register_path}: {method_id} invalid {field}")
        for field in ("verification_unit", "pass_threshold", "required_evidence", "independence_rule", "owner"):
            if not row[field].strip():
                raise ValueError(f"{register_path}: {method_id} empty {field}")
        for marker in expected["threshold_markers"]:
            if marker not in row["pass_threshold"]:
                raise ValueError(f"{register_path}: {method_id} pass threshold lost marker {marker!r}")
        for marker in expected["evidence_markers"]:
            if marker not in row["required_evidence"]:
                raise ValueError(f"{register_path}: {method_id} evidence lost marker {marker!r}")
        for marker in expected["independence_markers"]:
            if marker not in row["independence_rule"]:
                raise ValueError(f"{register_path}: {method_id} independence rule lost marker {marker!r}")

    controls = read_csv_with_required(
        controls_path, {"control_id", "current_status"}
    )
    declared = {row["control_id"]: row["current_status"] for row in controls}
    if len(controls) != 8 or set(declared) != {f"RC-{number:02d}" for number in range(1, 9)}:
        raise ValueError(f"{controls_path}: expected exact RC-01 through RC-08")

    release = json.loads(release_audit_path.read_text(encoding="utf-8"))
    if release.get("control_count") != 8 or release.get("data_correctness_control_count") != 6:
        raise ValueError(f"{release_audit_path}: invalid release-control counts")
    derived = release.get("derived_status")
    if not isinstance(derived, dict) or set(derived) != set(declared):
        raise ValueError(f"{release_audit_path}: invalid derived_status set")
    if any(status not in {"pass", "blocked"} for status in derived.values()):
        raise ValueError(f"{release_audit_path}: invalid derived status")
    if declared != derived or release.get("control_integrity_gate") != "pass":
        raise ValueError(f"{release_audit_path}: declared and derived controls are not identical")

    method_status = {
        method_id: derived[EXPECTED[method_id]["release_control_id"]]
        for method_id in sorted(EXPECTED)
    }
    passed = [method_id for method_id, status in method_status.items() if status == "pass"]
    blocked = [method_id for method_id, status in method_status.items() if status == "blocked"]
    expected_data_gate = "pass" if all(
        method_status[f"VM-{number:02d}"] == "pass" for number in range(1, 7)
    ) else "block"
    if release.get("data_correctness_gate") != expected_data_gate:
        raise ValueError(f"{release_audit_path}: data gate does not match VM-01 through VM-06")
    expected_formal_gate = "pass" if not blocked else "block"
    if release.get("formal_release_gate") != expected_formal_gate:
        raise ValueError(f"{release_audit_path}: formal gate does not match VM-01 through VM-08")

    return {
        "register": str(register_path),
        "gate_scope": "exact-eight-method-publication-verification-coverage",
        "method_count": 8,
        "data_correctness_method_count": 6,
        "release_acceptance_method_count": 2,
        "method_status": method_status,
        "passed_methods": passed,
        "blocked_methods": blocked,
        "verification_catalog_integrity_gate": "pass",
        "data_correctness_gate": expected_data_gate,
        "formal_release_gate": expected_formal_gate,
        "maximum_supported_claim": release.get("maximum_supported_claim"),
    }


def read_csv_with_required(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = set(rows[0]) if rows else set()
    if not rows or not required <= actual:
        raise ValueError(f"{path}: missing columns {sorted(required - actual)}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--controls", type=Path, required=True)
    parser.add_argument("--release-audit", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "data", "formal"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(args.register, args.controls, args.release_audit)
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Verification-method audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Verification methods: {len(report['passed_methods'])}/8 pass; "
        f"blocked={','.join(report['blocked_methods']) or 'none'}"
    )
    print(f"Data correctness gate: {report['data_correctness_gate']}")
    print(f"Formal release gate: {report['formal_release_gate']}")
    selected = {
        "integrity": "verification_catalog_integrity_gate",
        "data": "data_correctness_gate",
        "formal": "formal_release_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
