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
    "draft_definition_alignment",
}
QBC_APPROVAL_IDS = {
    "QBC-TM02-SURGERY-POSTOP-REQUIRED",
    "QBC-DIAGTYPE3-RECURRENCE-REQUIRED",
    "QBC-XML-TABLE1-CLOSING-TAGS",
    "QBC-FAQ-PREOP-HORMONE-3D-DIRECT-SURGERY",
    "FHIR-MCODE-SCOPE",
    "FHIR-EXTENSIONS",
    "TERM-PR",
    "TERM-HER2-FISH",
    "TERM-PDL1",
    "GOV-AJCC",
    "GOV-SNOMED-DRUG",
    "SEC-PRIVACY",
    "UAT-VPN",
    "PUB-RELEASE",
}
OPERATIONAL_APPROVALS = {"SEC-PRIVACY", "UAT-VPN", "PUB-RELEASE"}
REQUIRED_MEASURE_APPROVAL_COLUMNS = {
    "approval_id", "measure_id", "indicator_family", "decision_scope",
    "known_issue", "current_status", "required_signer", "acceptance_evidence",
    "decision", "signer_name", "signer_organization_title", "decision_date",
    "evidence_uri_path", "signed_artifact_sha256", "notes",
}
REQUIRED_SCOPE_CLAIM_COLUMNS = {
    "claim_id", "scope", "authority", "version", "relationship",
    "evidence_status", "allowed_claim", "prohibited_claim", "blocking_evidence",
}
REQUIRED_SCOPE_DECISION_COLUMNS = {
    "decision_id", "claim_id", "scope", "proposed_role",
    "claim_evidence_status", "allowed_claim", "prohibited_claim",
    "blocking_evidence", "current_status", "required_signer",
    "acceptance_evidence", "decision", "approved_role", "signer_name",
    "signer_organization_title", "decision_date", "evidence_uri_path",
    "signed_artifact_sha256", "notes",
}
SCOPE_ROLES = {
    "IG-CORE": "normative",
    "IG-TWCORE": "informative",
    "IG-MCODE": "informative",
    "IG-ICHOM": "informative",
    "TASK-CAREPLAN": "informative",
    "TASK-QBC": "normative",
    "TASK-TWPAS": "informative",
    "TASK-CASE-MGMT": "normative",
    "TASK-TCR": "informative",
    "TASK-FUTURE": "excluded",
}
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


def measure_approval_complete(row: dict[str, str]) -> bool:
    if row["current_status"] != "approved" or row["decision"] != "approve":
        return False
    required = (
        "signer_name", "signer_organization_title", "decision_date",
        "evidence_uri_path", "signed_artifact_sha256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["decision_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_artifact_sha256"].strip()) is not None


def scope_decision_complete(row: dict[str, str]) -> bool:
    if (
        row["current_status"] != "approved"
        or row["decision"] != "approve"
        or row["approved_role"] != row["proposed_role"]
    ):
        return False
    required = (
        "signer_name", "signer_organization_title", "decision_date",
        "evidence_uri_path", "signed_artifact_sha256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["decision_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_artifact_sha256"].strip()) is not None


def audit(
    controls_path: Path,
    measure_audit_path: Path,
    terminology_path: Path,
    approvals_path: Path,
    measure_approvals_path: Path,
    scope_claims_path: Path,
    scope_decisions_path: Path,
    artifact_audit_path: Path,
    terminology_audit_path: Path,
    resource_inventory_audit_path: Path,
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
    if len(approvals) != len(QBC_APPROVAL_IDS) or approval_ids != QBC_APPROVAL_IDS:
        raise ValueError(f"{approvals_path}: Gate ID set must be the exact 14 required gates")
    measure_approvals = read_csv(
        measure_approvals_path, REQUIRED_MEASURE_APPROVAL_COLUMNS, exact_columns=True
    )
    measure_ids = {row["measure_id"] for row in measures}
    if (
        len(measure_approvals) != len(measures)
        or {row["measure_id"] for row in measure_approvals} != measure_ids
        or len({row["approval_id"] for row in measure_approvals}) != len(measures)
    ):
        raise ValueError(
            f"{measure_approvals_path}: expected exactly one unique approval for each Measure"
        )
    for row in measure_approvals:
        for field in (
            "approval_id", "indicator_family", "decision_scope", "known_issue",
            "current_status", "required_signer", "acceptance_evidence",
        ):
            if not row[field].strip():
                raise ValueError(
                    f"{measure_approvals_path}: {row['measure_id']} has empty {field}"
                )
    scope_claims = read_csv(
        scope_claims_path, REQUIRED_SCOPE_CLAIM_COLUMNS, exact_columns=True
    )
    if (
        len(scope_claims) != len(SCOPE_ROLES)
        or {row["claim_id"] for row in scope_claims} != set(SCOPE_ROLES)
    ):
        raise ValueError(
            f"{scope_claims_path}: claim_id set must be the exact 10 required scopes"
        )
    scope_decisions = read_csv(
        scope_decisions_path, REQUIRED_SCOPE_DECISION_COLUMNS, exact_columns=True
    )
    if (
        len(scope_decisions) != len(scope_claims)
        or {row["claim_id"] for row in scope_decisions} != set(SCOPE_ROLES)
        or len({row["decision_id"] for row in scope_decisions}) != len(scope_claims)
    ):
        raise ValueError(
            f"{scope_decisions_path}: expected exactly one unique decision for each scope claim"
        )
    claims_by_id = {row["claim_id"]: row for row in scope_claims}
    for row in scope_decisions:
        claim = claims_by_id[row["claim_id"]]
        if row["proposed_role"] != SCOPE_ROLES[row["claim_id"]]:
            raise ValueError(
                f"{scope_decisions_path}: {row['claim_id']} proposed_role does not match locked policy"
            )
        copied_context = {
            "scope": "scope",
            "claim_evidence_status": "evidence_status",
            "allowed_claim": "allowed_claim",
            "prohibited_claim": "prohibited_claim",
            "blocking_evidence": "blocking_evidence",
        }
        for decision_field, claim_field in copied_context.items():
            if row[decision_field] != claim[claim_field]:
                raise ValueError(
                    f"{scope_decisions_path}: {row['claim_id']} stale {decision_field}"
                )
        for field in (
            "decision_id", "scope", "claim_evidence_status", "allowed_claim",
            "prohibited_claim", "blocking_evidence", "current_status",
            "required_signer", "acceptance_evidence",
        ):
            if not row[field].strip():
                raise ValueError(
                    f"{scope_decisions_path}: {row['claim_id']} has empty {field}"
                )
    artifact_audit = json.loads(artifact_audit_path.read_text(encoding="utf-8"))
    if artifact_audit.get("gate_scope") != "artifact-structure-and-example-only":
        raise ValueError(
            f"{artifact_audit_path}: gate_scope must be artifact-structure-and-example-only"
        )
    expected_artifact_counts = {
        "artifact_count": 46,
        "profile_count": 33,
        "extension_count": 13,
    }
    for field, expected in expected_artifact_counts.items():
        if artifact_audit.get(field) != expected:
            raise ValueError(f"{artifact_audit_path}: {field} must be {expected}")
    if artifact_audit.get("artifact_integrity_gate") != "pass":
        raise ValueError(f"{artifact_audit_path}: artifact_integrity_gate must be pass")
    if artifact_audit.get("clinical_artifact_approval_gate") not in {"pass", "block"}:
        raise ValueError(f"{artifact_audit_path}: invalid clinical_artifact_approval_gate")
    approved_artifact_count = artifact_audit.get("approved_artifact_count")
    if not isinstance(approved_artifact_count, int) or not 0 <= approved_artifact_count <= 46:
        raise ValueError(f"{artifact_audit_path}: invalid approved_artifact_count")
    expected_clinical_gate = "pass" if approved_artifact_count == 46 else "block"
    if artifact_audit["clinical_artifact_approval_gate"] != expected_clinical_gate:
        raise ValueError(f"{artifact_audit_path}: clinical artifact gate/count mismatch")
    terminology_audit = json.loads(terminology_audit_path.read_text(encoding="utf-8"))
    if terminology_audit.get("gate_scope") != "complete-local-terminology-technical-and-clinical":
        raise ValueError(
            f"{terminology_audit_path}: invalid terminology gate_scope"
        )
    terminology_counts = {
        "terminology_artifact_count": 152,
        "code_system_count": 60,
        "value_set_count": 90,
        "concept_map_count": 2,
        "clinical_value_set_approval_count": 19,
    }
    for field, expected in terminology_counts.items():
        if terminology_audit.get(field) != expected:
            raise ValueError(f"{terminology_audit_path}: {field} must be {expected}")
    if terminology_audit.get("terminology_integrity_gate") != "pass":
        raise ValueError(f"{terminology_audit_path}: terminology_integrity_gate must be pass")
    empty_terminology = terminology_audit.get("empty_clinical_value_set_count")
    approved_terminology = terminology_audit.get("approved_clinical_value_set_count")
    if (
        not isinstance(empty_terminology, int)
        or not 0 <= empty_terminology <= 19
        or not isinstance(approved_terminology, int)
        or not 0 <= approved_terminology <= 19
    ):
        raise ValueError(f"{terminology_audit_path}: invalid clinical terminology counts")
    expected_terminology_gate = (
        "pass" if empty_terminology == 0 and approved_terminology == 19 else "block"
    )
    if terminology_audit.get("clinical_terminology_gate") != expected_terminology_gate:
        raise ValueError(f"{terminology_audit_path}: clinical terminology gate/count mismatch")
    resource_inventory = json.loads(
        resource_inventory_audit_path.read_text(encoding="utf-8")
    )
    if resource_inventory.get("gate_scope") != (
        "exact-complete-fhir-resource-inventory-and-ig-manifest"
    ):
        raise ValueError(f"{resource_inventory_audit_path}: invalid gate_scope")
    inventory_counts = {
        "resource_count": 260,
        "publication_definition_count": 224,
        "synthetic_example_count": 36,
        "canonical_resource_count": 222,
        "manual_json_resource_count": 103,
        "generated_fsh_resource_count": 157,
        "measure_count": 20,
    }
    for field, expected in inventory_counts.items():
        if resource_inventory.get(field) != expected:
            raise ValueError(
                f"{resource_inventory_audit_path}: {field} must be {expected}"
            )
    if resource_inventory.get("resource_inventory_gate") != "pass":
        raise ValueError(f"{resource_inventory_audit_path}: inventory gate must pass")
    version_policy_count = resource_inventory.get("canonical_version_policy_count")
    approved_version_policy_count = resource_inventory.get(
        "approved_canonical_version_policy_count"
    )
    version_group_counts = resource_inventory.get(
        "canonical_version_policy_group_counts"
    )
    expected_version_group_counts = {
        "CV-PACKAGE-EXPLICIT": 24,
        "CV-CQL-LIBRARY": 1,
        "CV-PACKAGE-CONTEXT": 96,
        "CV-TCR-MANUAL": 101,
    }
    if version_policy_count != 4:
        raise ValueError(
            f"{resource_inventory_audit_path}: canonical_version_policy_count must be 4"
        )
    if (
        not isinstance(approved_version_policy_count, int)
        or not 0 <= approved_version_policy_count <= 4
    ):
        raise ValueError(
            f"{resource_inventory_audit_path}: invalid approved version-policy count"
        )
    if version_group_counts != expected_version_group_counts:
        raise ValueError(
            f"{resource_inventory_audit_path}: invalid canonical version-policy groups"
        )
    version_states = resource_inventory.get("canonical_version_policy_states")
    if not isinstance(version_states, dict) or set(version_states) != set(
        expected_version_group_counts
    ):
        raise ValueError(
            f"{resource_inventory_audit_path}: invalid canonical version-policy states"
        )
    if version_states["CV-PACKAGE-EXPLICIT"] != "explicit-package-version":
        raise ValueError(f"{resource_inventory_audit_path}: invalid explicit-version state")
    if version_states["CV-CQL-LIBRARY"] != "cql-library-version":
        raise ValueError(f"{resource_inventory_audit_path}: invalid CQL-version state")
    if version_states["CV-PACKAGE-CONTEXT"] not in {
        "package-context-policy-pending", "approved-package-context-only",
    }:
        raise ValueError(f"{resource_inventory_audit_path}: invalid package-context state")
    if version_states["CV-TCR-MANUAL"] not in {
        "missing-business-version", "fhir-version-collision",
        "mixed-business-versions", "authoritative-business-version-candidate",
        "authoritative-business-version",
    }:
        raise ValueError(f"{resource_inventory_audit_path}: invalid manual-version state")
    manual_versions = resource_inventory.get("manual_canonical_versions")
    if not isinstance(manual_versions, list) or any(
        not isinstance(item, str) for item in manual_versions
    ):
        raise ValueError(
            f"{resource_inventory_audit_path}: invalid manual canonical-version list"
        )
    expected_version_gate = (
        "pass"
        if approved_version_policy_count == 4
        and version_states["CV-PACKAGE-CONTEXT"] == "approved-package-context-only"
        and version_states["CV-TCR-MANUAL"] == "authoritative-business-version"
        else "block"
    )
    if resource_inventory.get("business_version_provenance_gate") != expected_version_gate:
        raise ValueError(
            f"{resource_inventory_audit_path}: business-version policy gate/count mismatch"
        )
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
    normative_scope_ready = all(
        row["claim_id"] == "IG-CORE"
        or row["claim_evidence_status"] == "formal-release-ready"
        for row in scope_decisions
        if row["proposed_role"] == "normative"
    )
    derived = {
        "RC-01": "pass" if all(row["raw_source_mapping"] == "pass" for row in measures) else "blocked",
        "RC-02": "pass" if (
            publisher["qa_integrity_gate"] == "pass"
            and resource_inventory["resource_inventory_gate"] == "pass"
        ) else "blocked",
        "RC-03": "pass" if (
            clinical_count > 0
            and empty_clinical_count == 0
            and terminology_audit["clinical_terminology_gate"] == "pass"
            and all(row["terminology_evidence"] in {"verified", "not-applicable"} for row in measures)
        ) else "blocked",
        "RC-04": "pass" if all(
            row["fhir_conformance"] == "pass"
            and row["cql_execution"].startswith("pass-synthetic")
            for row in measures
        ) else "blocked",
        "RC-05": "pass" if all(row["independent_recalculation"] == "pass" for row in measures) else "blocked",
        "RC-06": "pass" if all(row["golden_cohort"] == "pass" for row in measures) else "blocked",
        "RC-07": "pass" if (
            governance
            and all(approval_complete(row) for row in governance)
            and all(row["draft_definition_alignment"] == "approved" for row in measures)
            and all(measure_approval_complete(row) for row in measure_approvals)
            and artifact_audit["clinical_artifact_approval_gate"] == "pass"
        ) else "blocked",
        "RC-08": "pass" if (
            len(operational) == len(OPERATIONAL_APPROVALS)
            and all(approval_complete(row) for row in operational)
            and all(scope_decision_complete(row) for row in scope_decisions)
            and normative_scope_ready
            and resource_inventory["business_version_provenance_gate"] == "pass"
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
        "qbc_approval_count": len(approvals),
        "measure_approval_count": len(measure_approvals),
        "approved_measure_definition_count": sum(
            measure_approval_complete(row) for row in measure_approvals
        ),
        "scope_claim_count": len(scope_claims),
        "scope_decision_count": len(scope_decisions),
        "approved_scope_decision_count": sum(
            scope_decision_complete(row) for row in scope_decisions
        ),
        "normative_scope_readiness": "pass" if normative_scope_ready else "block",
        "artifact_conformance_count": artifact_audit["artifact_count"],
        "approved_artifact_count": approved_artifact_count,
        "clinical_artifact_approval_gate": artifact_audit[
            "clinical_artifact_approval_gate"
        ],
        "terminology_artifact_count": terminology_audit["terminology_artifact_count"],
        "clinical_value_set_approval_count": terminology_audit[
            "clinical_value_set_approval_count"
        ],
        "approved_clinical_value_set_count": approved_terminology,
        "clinical_terminology_gate": terminology_audit["clinical_terminology_gate"],
        "fhir_resource_count": resource_inventory["resource_count"],
        "publication_definition_count": resource_inventory[
            "publication_definition_count"
        ],
        "synthetic_example_count": resource_inventory["synthetic_example_count"],
        "canonical_resource_count": resource_inventory["canonical_resource_count"],
        "business_version_provenance_gate": resource_inventory[
            "business_version_provenance_gate"
        ],
        "canonical_version_policy_count": version_policy_count,
        "approved_canonical_version_policy_count": approved_version_policy_count,
        "canonical_version_policy_group_counts": version_group_counts,
        "canonical_version_policy_states": version_states,
        "manual_canonical_versions": manual_versions,
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
    parser.add_argument("--measure-approval-register", type=Path, required=True)
    parser.add_argument("--scope-claims", type=Path, required=True)
    parser.add_argument("--scope-decisions", type=Path, required=True)
    parser.add_argument("--artifact-audit", type=Path, required=True)
    parser.add_argument("--terminology-audit", type=Path, required=True)
    parser.add_argument("--resource-inventory-audit", type=Path, required=True)
    parser.add_argument("--publisher-audit", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--target", choices=("integrity", "data", "formal"), default="integrity"
    )
    args = parser.parse_args()
    try:
        report = audit(
            args.controls, args.measure_audit, args.terminology_fsh,
            args.approval_register, args.measure_approval_register,
            args.scope_claims, args.scope_decisions,
            args.artifact_audit,
            args.terminology_audit,
            args.resource_inventory_audit,
            args.publisher_audit,
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
