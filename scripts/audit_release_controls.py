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

try:
    from scripts.approval_evidence import retained_evidence_matches
except ModuleNotFoundError:  # direct execution: python scripts/audit_release_controls.py
    from approval_evidence import retained_evidence_matches


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


def qbc_approval_evidence_complete(row: dict[str, str], register_path: Path) -> bool:
    return approval_complete(row) and retained_evidence_matches(
        row,
        register_path,
        path_field="Evidence URI/path",
        hash_field="Signed artifact SHA-256",
    )


def measure_approval_evidence_complete(
    row: dict[str, str], register_path: Path
) -> bool:
    return measure_approval_complete(row) and retained_evidence_matches(
        row,
        register_path,
        path_field="evidence_uri_path",
        hash_field="signed_artifact_sha256",
    )


def scope_decision_evidence_complete(
    row: dict[str, str], register_path: Path
) -> bool:
    return scope_decision_complete(row) and retained_evidence_matches(
        row,
        register_path,
        path_field="evidence_uri_path",
        hash_field="signed_artifact_sha256",
    )


def audit(
    controls_path: Path,
    measure_audit_path: Path,
    terminology_path: Path,
    approvals_path: Path,
    measure_approvals_path: Path,
    measure_specification_audit_path: Path,
    scope_claims_path: Path,
    scope_decisions_path: Path,
    artifact_audit_path: Path,
    mapping_projection_audit_path: Path,
    terminology_audit_path: Path,
    resource_inventory_audit_path: Path,
    reference_graph_audit_path: Path,
    data_evidence_audit_path: Path,
    source_work_package_audit_path: Path,
    criterion_resolution_audit_path: Path,
    publisher_audit_path: Path,
    phi_audit_path: Path,
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
    for row in approvals:
        if row["Status"] == "approved" and row["Decision (approve/reject/revise)"] == "approve" and not qbc_approval_evidence_complete(row, approvals_path):
            raise ValueError(
                f"{approvals_path}: {row['Gate ID']} approved evidence is missing or SHA-256 mismatched"
            )
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
        if row["current_status"] == "approved" and row["decision"] == "approve" and not measure_approval_evidence_complete(row, measure_approvals_path):
            raise ValueError(
                f"{measure_approvals_path}: {row['measure_id']} approved evidence is missing or SHA-256 mismatched"
            )
    measure_specification = json.loads(
        measure_specification_audit_path.read_text(encoding="utf-8")
    )
    if measure_specification.get("gate_scope") != (
        "exact-live-measure-specification-and-truth-table-approval"
    ):
        raise ValueError(f"{measure_specification_audit_path}: invalid gate_scope")
    expected_measure_specification_counts = {
        "measure_count": 20,
        "population_criterion_count": 68,
        "measure_expression_use_count": 62,
        "required_truth_assertion_count": 208,
    }
    for field, expected in expected_measure_specification_counts.items():
        if measure_specification.get(field) != expected:
            raise ValueError(
                f"{measure_specification_audit_path}: {field} must be {expected}"
            )
    approved_measure_specifications = measure_specification.get(
        "approved_measure_specification_count"
    )
    approved_truth_cases = measure_specification.get(
        "approved_truth_table_case_count"
    )
    fingerprints = measure_specification.get("measure_specification_fingerprints")
    if (
        not isinstance(approved_measure_specifications, int)
        or not 0 <= approved_measure_specifications <= 20
        or not isinstance(approved_truth_cases, int)
        or approved_truth_cases < 0
        or not isinstance(fingerprints, dict)
        or set(fingerprints) != measure_ids
        or any(SHA256.fullmatch(str(value)) is None for value in fingerprints.values())
        or measure_specification.get("measure_specification_integrity_gate") != "pass"
    ):
        raise ValueError(f"{measure_specification_audit_path}: invalid specification evidence")
    expected_measure_specification_gate = (
        "pass" if approved_measure_specifications == 20 and approved_truth_cases >= 208
        else "block"
    )
    if measure_specification.get("measure_specification_approval_gate") != (
        expected_measure_specification_gate
    ):
        raise ValueError(f"{measure_specification_audit_path}: approval gate/count mismatch")
    retained_measure_approvals = sum(
        measure_approval_evidence_complete(row, measure_approvals_path)
        for row in measure_approvals
    )
    if retained_measure_approvals != approved_measure_specifications:
        raise ValueError(
            f"{measure_specification_audit_path}: live bundle and approval-register count mismatch"
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
        if row["current_status"] == "approved" and row["decision"] == "approve" and not scope_decision_evidence_complete(row, scope_decisions_path):
            raise ValueError(
                f"{scope_decisions_path}: {row['claim_id']} approved evidence is missing or SHA-256 mismatched"
            )
    artifact_audit = json.loads(artifact_audit_path.read_text(encoding="utf-8"))
    if artifact_audit.get("gate_scope") != "artifact-structure-example-and-exact-review-binding":
        raise ValueError(
            f"{artifact_audit_path}: invalid artifact gate_scope"
        )
    expected_artifact_counts = {
        "artifact_count": 47,
        "profile_count": 34,
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
    artifact_hash_binding_count = artifact_audit.get("artifact_hash_binding_count")
    if not isinstance(approved_artifact_count, int) or not 0 <= approved_artifact_count <= 47:
        raise ValueError(f"{artifact_audit_path}: invalid approved_artifact_count")
    if artifact_hash_binding_count != approved_artifact_count:
        raise ValueError(f"{artifact_audit_path}: artifact hash binding/count mismatch")
    expected_clinical_gate = "pass" if (
        approved_artifact_count == 47 and artifact_hash_binding_count == 47
    ) else "block"
    if artifact_audit["clinical_artifact_approval_gate"] != expected_clinical_gate:
        raise ValueError(f"{artifact_audit_path}: clinical artifact gate/count mismatch")
    mapping_projection = json.loads(
        mapping_projection_audit_path.read_text(encoding="utf-8")
    )
    if mapping_projection.get("gate_scope") != (
        "exact-common-fact-profile-and-element-projection"
    ):
        raise ValueError(f"{mapping_projection_audit_path}: invalid gate_scope")
    if (
        mapping_projection.get("mapping_fact_count") != 34
        or mapping_projection.get("target_alternative_count") != 55
        or mapping_projection.get("projection_register_integrity_gate") != "pass"
    ):
        raise ValueError(
            f"{mapping_projection_audit_path}: invalid mapping projection inventory"
        )
    resolved_projection_count = mapping_projection.get(
        "resolved_local_profile_element_count"
    )
    derived_projection_count = mapping_projection.get("declared_derived_rule_count")
    blocked_projection_count = mapping_projection.get(
        "blocked_target_alternative_count"
    )
    semantic_profile_gap_count = mapping_projection.get(
        "semantic_profile_gap_alternative_count"
    )
    semantic_profile_gap_fact_ids = mapping_projection.get(
        "semantic_profile_gap_fact_ids"
    )
    semantic_profile_gap_fact_count = mapping_projection.get(
        "semantic_profile_gap_fact_count"
    )
    unit_policy_pending_count = mapping_projection.get(
        "unit_policy_pending_alternative_count"
    )
    blocked_projection_fact_ids = mapping_projection.get(
        "blocked_projection_fact_ids"
    )
    blocked_projection_fact_count = mapping_projection.get(
        "blocked_projection_fact_count"
    )
    if (
        not all(
            isinstance(value, int) and value >= 0
            for value in (
                resolved_projection_count, derived_projection_count,
                blocked_projection_count, unit_policy_pending_count,
                blocked_projection_fact_count, semantic_profile_gap_count,
                semantic_profile_gap_fact_count,
            )
        )
        or resolved_projection_count + derived_projection_count
        + blocked_projection_count != 55
        or derived_projection_count != 1
        or unit_policy_pending_count > resolved_projection_count
        or semantic_profile_gap_count > resolved_projection_count
        or not isinstance(semantic_profile_gap_fact_ids, list)
        or len(semantic_profile_gap_fact_ids) != semantic_profile_gap_fact_count
        or len(set(semantic_profile_gap_fact_ids)) != semantic_profile_gap_fact_count
        or not set(semantic_profile_gap_fact_ids) <= set(blocked_projection_fact_ids)
        or not isinstance(blocked_projection_fact_ids, list)
        or len(blocked_projection_fact_ids) != blocked_projection_fact_count
        or len(set(blocked_projection_fact_ids)) != blocked_projection_fact_count
    ):
        raise ValueError(
            f"{mapping_projection_audit_path}: invalid mapping projection counts"
        )
    expected_projection_gate = "pass" if (
        blocked_projection_count == 0
        and semantic_profile_gap_count == 0
        and unit_policy_pending_count == 0
        and blocked_projection_fact_count == 0
    ) else "block"
    if mapping_projection.get("projection_readiness_gate") != expected_projection_gate:
        raise ValueError(
            f"{mapping_projection_audit_path}: projection readiness/count mismatch"
        )
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
        "concept_map_relationship_count": 6,
        "duplicate_code_system_code_count": 0,
    }
    for field, expected in terminology_counts.items():
        if terminology_audit.get(field) != expected:
            raise ValueError(f"{terminology_audit_path}: {field} must be {expected}")
    if terminology_audit.get("terminology_integrity_gate") != "pass":
        raise ValueError(f"{terminology_audit_path}: terminology_integrity_gate must be pass")
    empty_terminology = terminology_audit.get("empty_clinical_value_set_count")
    approved_terminology = terminology_audit.get("approved_clinical_value_set_count")
    validated_expansions = terminology_audit.get(
        "validated_clinical_value_set_expansion_count"
    )
    versionless_clinical_valuesets = terminology_audit.get(
        "versionless_clinical_value_set_count"
    )
    approved_relationships = terminology_audit.get(
        "approved_concept_map_relationship_count"
    )
    if (
        not isinstance(empty_terminology, int)
        or not 0 <= empty_terminology <= 19
        or not isinstance(approved_terminology, int)
        or not 0 <= approved_terminology <= 19
        or not isinstance(validated_expansions, int)
        or not 0 <= validated_expansions <= 19
        or not isinstance(versionless_clinical_valuesets, int)
        or not 0 <= versionless_clinical_valuesets <= 19
        or not isinstance(approved_relationships, int)
        or not 0 <= approved_relationships <= 6
    ):
        raise ValueError(f"{terminology_audit_path}: invalid clinical terminology counts")
    expected_terminology_gate = (
        "pass" if (
            empty_terminology == 0
            and approved_terminology == 19
            and validated_expansions == 19
            and versionless_clinical_valuesets == 0
            and approved_relationships == 6
        ) else "block"
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
        "resource_count": 262,
        "publication_definition_count": 225,
        "synthetic_example_count": 37,
        "canonical_resource_count": 223,
        "manual_json_resource_count": 103,
        "generated_fsh_resource_count": 159,
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
        "CV-PACKAGE-CONTEXT": 97,
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
    reference_graph = json.loads(reference_graph_audit_path.read_text(encoding="utf-8"))
    expected_reference_fields = {
        "resource_count": 262,
        "local_url_link_occurrence_count": 662,
        "unique_local_url_target_count": 198,
        "canonical_reference_occurrence_count": 269,
        "local_canonical_reference_occurrence_count": 233,
        "external_canonical_reference_occurrence_count": 36,
        "unique_external_canonical_count": 18,
        "versioned_canonical_reference_occurrence_count": 0,
        "fhir_reference_occurrence_count": 330,
        "manifest_reference_occurrence_count": 261,
        "non_manifest_reference_occurrence_count": 69,
        "total_audited_reference_edge_count": 1028,
    }
    if reference_graph.get("gate_scope") != (
        "complete-local-fhir-reference-and-canonical-graph"
    ):
        raise ValueError(f"{reference_graph_audit_path}: invalid gate_scope")
    if reference_graph.get("reference_graph_integrity_gate") != "pass":
        raise ValueError(f"{reference_graph_audit_path}: reference graph gate must pass")
    for field, expected in expected_reference_fields.items():
        if reference_graph.get(field) != expected:
            raise ValueError(f"{reference_graph_audit_path}: {field} must be {expected}")
    if reference_graph.get("local_url_link_counts") != {
        "bundle-fullUrl": 19,
        "canonical-field": 233,
        "code-system-use": 153,
        "conceptmap-code-system-use": 2,
        "extension-use-url": 240,
        "fixed-extension-url": 13,
        "naming-system-use": 2,
    }:
        raise ValueError(f"{reference_graph_audit_path}: invalid local URL link counts")
    if reference_graph.get("external_canonical_authority_counts") != {
        "fhir-r4-core-4.0.1": 34,
        "tw-core-1.0.0": 2,
    }:
        raise ValueError(
            f"{reference_graph_audit_path}: invalid external canonical authorities"
        )
    data_evidence = json.loads(data_evidence_audit_path.read_text(encoding="utf-8"))
    if data_evidence.get("gate_scope") != (
        "raw-source-independent-recalculation-and-golden-cohort"
    ):
        raise ValueError(f"{data_evidence_audit_path}: invalid gate_scope")
    expected_data_evidence = {
        "expected_fact_count": 52,
        "measure_count": 20,
        "measure_expression_count": 46,
        "measure_expression_occurrence_count": 62,
        "population_criterion_count": 68,
        "criterion_referenced_fact_count": 45,
        "source_contract_dimension_count": 19,
    }
    for field, expected in expected_data_evidence.items():
        if data_evidence.get(field) != expected:
            raise ValueError(f"{data_evidence_audit_path}: {field} must be {expected}")
    for field in (
        "source_evidence_row_count",
        "case_level_comparison_row_count",
        "complete_source_contract_count",
        "declared_derived_dependency_count",
        "approved_authoritative_or_derived_fact_count",
        "approved_independent_recalculation_count",
        "approved_golden_cohort_count",
        "secondary_reconciliation_row_count",
        "approved_secondary_reconciliation_row_count",
    ):
        value = data_evidence.get(field)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{data_evidence_audit_path}: invalid {field}")
    if data_evidence["source_evidence_row_count"] < 52:
        raise ValueError(f"{data_evidence_audit_path}: source evidence rows cannot omit facts")
    if data_evidence["source_evidence_row_count"] != (
        52 + data_evidence["secondary_reconciliation_row_count"]
    ):
        raise ValueError(f"{data_evidence_audit_path}: source/secondary row-count mismatch")
    bounded_counts = {
        "complete_source_contract_count": 52,
        "approved_authoritative_or_derived_fact_count": 52,
        "approved_independent_recalculation_count": 20,
        "approved_golden_cohort_count": 20,
        "approved_secondary_reconciliation_row_count": data_evidence[
            "secondary_reconciliation_row_count"
        ],
    }
    for field, upper in bounded_counts.items():
        if data_evidence[field] > upper:
            raise ValueError(f"{data_evidence_audit_path}: {field} exceeds {upper}")
    if data_evidence["declared_derived_dependency_count"] < 1:
        raise ValueError(
            f"{data_evidence_audit_path}: molecular subtype derivation must declare inputs"
        )
    for field in (
        "source_register_integrity_gate", "validation_register_integrity_gate",
        "case_level_comparison_integrity_gate",
    ):
        if data_evidence.get(field) != "pass":
            raise ValueError(f"{data_evidence_audit_path}: {field} must pass")
    if SHA256.fullmatch(data_evidence.get("comparison_manifest_sha256", "")) is None:
        raise ValueError(
            f"{data_evidence_audit_path}: invalid comparison_manifest_sha256"
        )
    data_gate_rules = {
        "raw_source_traceability_gate": (
            data_evidence["complete_source_contract_count"] == 52
            and
            data_evidence["approved_authoritative_or_derived_fact_count"] == 52
        ),
        "independent_recalculation_gate": (
            data_evidence["approved_independent_recalculation_count"] == 20
            and data_evidence["case_level_comparison_row_count"] > 0
        ),
        "golden_cohort_gate": (
            data_evidence["approved_golden_cohort_count"] == 20
            and data_evidence["case_level_comparison_row_count"] > 0
        ),
    }
    for field, should_pass in data_gate_rules.items():
        expected = "pass" if should_pass else "block"
        if data_evidence.get(field) != expected:
            raise ValueError(f"{data_evidence_audit_path}: {field}/count mismatch")
    source_work_packages = json.loads(
        source_work_package_audit_path.read_text(encoding="utf-8")
    )
    if source_work_packages.get("gate_scope") != (
        "all-52-source-fact-acquisition-work-packages"
    ):
        raise ValueError(f"{source_work_package_audit_path}: invalid gate_scope")
    expected_work_package_counts = {
        "fact_count": 52,
        "work_package_count": 8,
        "batch_counts": {
            "B0-result-blockers": 10,
            "B1-cohort-rate": 31,
            "B2-release-provenance": 1,
            "B3-stratifiers": 4,
            "B4-support": 6,
        },
        "work_package_fact_counts": {
            "WP-01-PATIENT-ADMIN": 3,
            "WP-02-REGISTRY-STAGING": 8,
            "WP-03-PATHOLOGY": 8,
            "WP-04-SURGERY-PROCEDURE": 5,
            "WP-05-SYSTEMIC-THERAPY": 3,
            "WP-06-RADIOTHERAPY": 3,
            "WP-07-CASE-MANAGEMENT": 19,
            "WP-08-REPORTING-PROVENANCE": 3,
        },
    }
    for field, expected in expected_work_package_counts.items():
        if source_work_packages.get(field) != expected:
            raise ValueError(f"{source_work_package_audit_path}: invalid {field}")
    confirmed_owner_count = source_work_packages.get(
        "confirmed_owner_assignment_count"
    )
    unassigned_owner_count = source_work_packages.get("unassigned_owner_count")
    if (
        not isinstance(confirmed_owner_count, int)
        or not isinstance(unassigned_owner_count, int)
        or confirmed_owner_count < 0
        or unassigned_owner_count < 0
        or confirmed_owner_count + unassigned_owner_count != 52
    ):
        raise ValueError(f"{source_work_package_audit_path}: invalid owner counts")
    if source_work_packages.get("work_package_integrity_gate") != "pass":
        raise ValueError(f"{source_work_package_audit_path}: integrity gate must pass")
    expected_owner_gate = "pass" if confirmed_owner_count == 52 else "block"
    if source_work_packages.get("owner_assignment_gate") != expected_owner_gate:
        raise ValueError(f"{source_work_package_audit_path}: owner gate/count mismatch")
    criterion_resolution = json.loads(
        criterion_resolution_audit_path.read_text(encoding="utf-8")
    )
    if criterion_resolution.get("gate_scope") != (
        "all-current-non-aligned-criterion-resolution-decisions"
    ):
        raise ValueError(f"{criterion_resolution_audit_path}: invalid gate_scope")
    expected_resolution_counts = {
        "decision_count": 18,
        "decision_group_count": 13,
        "issue_class_counts": {
            "candidate-not-approved": 1,
            "conditional-data-contract": 2,
            "definition-contradiction": 1,
            "fhir-resource-semantic-mismatch": 5,
            "implemented-variant-unresolved": 3,
            "known-not-enforced": 2,
            "task-layer-only": 4,
        },
    }
    for field, expected in expected_resolution_counts.items():
        if criterion_resolution.get(field) != expected:
            raise ValueError(f"{criterion_resolution_audit_path}: invalid {field}")
    approved_resolution_count = criterion_resolution.get("approved_decision_count")
    pending_resolution_count = criterion_resolution.get("pending_decision_count")
    non_aligned_resolution_count = criterion_resolution.get(
        "current_non_aligned_decision_count"
    )
    production_allowed_resolution_count = criterion_resolution.get(
        "production_allowed_decision_count"
    )
    if (
        not isinstance(approved_resolution_count, int)
        or not isinstance(pending_resolution_count, int)
        or not isinstance(non_aligned_resolution_count, int)
        or not isinstance(production_allowed_resolution_count, int)
        or approved_resolution_count < 0
        or pending_resolution_count < 0
        or approved_resolution_count + pending_resolution_count != 18
        or not 0 <= non_aligned_resolution_count <= 18
        or not 0 <= production_allowed_resolution_count <= 18
    ):
        raise ValueError(f"{criterion_resolution_audit_path}: invalid decision counts")
    if criterion_resolution.get("decision_register_integrity_gate") != "pass":
        raise ValueError(f"{criterion_resolution_audit_path}: integrity gate must pass")
    expected_resolution_gate = (
        "pass"
        if approved_resolution_count == 18
        and non_aligned_resolution_count == 0
        and production_allowed_resolution_count == 18
        else "block"
    )
    if criterion_resolution.get("criterion_resolution_gate") != expected_resolution_gate:
        raise ValueError(f"{criterion_resolution_audit_path}: approval gate/count mismatch")
    publisher = json.loads(publisher_audit_path.read_text(encoding="utf-8"))
    if publisher.get("gate_scope") != "publisher-qa-only":
        raise ValueError(
            f"{publisher_audit_path}: gate_scope must be publisher-qa-only"
        )
    for field in ("qa_integrity_gate", "formal_release_gate"):
        if publisher.get(field) not in {"pass", "block", "fail"}:
            raise ValueError(f"{publisher_audit_path}: invalid or missing {field}")
    phi_audit = json.loads(phi_audit_path.read_text(encoding="utf-8"))
    if phi_audit.get("gate_scope") != (
        "committable-publication-content-phi-pattern-scan"
    ):
        raise ValueError(f"{phi_audit_path}: invalid gate_scope")
    if phi_audit.get("office_open_xml_scanning") != "enabled":
        raise ValueError(f"{phi_audit_path}: Office Open XML scanning must be enabled")
    if phi_audit.get("opaque_sensitive_file_policy") != "block":
        raise ValueError(f"{phi_audit_path}: opaque sensitive file policy must block")
    candidate_file_count = phi_audit.get("candidate_file_count")
    inspected_file_count = phi_audit.get("inspected_file_count")
    scanner_exclusion_count = phi_audit.get("scanner_exclusion_count")
    if (
        not isinstance(candidate_file_count, int)
        or not isinstance(inspected_file_count, int)
        or not isinstance(scanner_exclusion_count, int)
        or candidate_file_count <= 0
        or inspected_file_count <= 0
        or scanner_exclusion_count < 0
        or inspected_file_count + scanner_exclusion_count > candidate_file_count
        or phi_audit.get("pattern_count") != 3
    ):
        raise ValueError(f"{phi_audit_path}: invalid privacy scan coverage counts")
    finding_count = phi_audit.get("finding_count")
    if not isinstance(finding_count, int) or finding_count < 0:
        raise ValueError(f"{phi_audit_path}: invalid finding_count")
    expected_phi_gate = "pass" if finding_count == 0 else "block"
    if phi_audit.get("repository_phi_pattern_scan_gate") != expected_phi_gate:
        raise ValueError(f"{phi_audit_path}: privacy scan gate/count mismatch")

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
        "RC-01": "pass" if (
            data_evidence["raw_source_traceability_gate"] == "pass"
            and all(row["raw_source_mapping"] == "pass" for row in measures)
            and source_work_packages["owner_assignment_gate"] == "pass"
            and mapping_projection["projection_readiness_gate"] == "pass"
        ) else "blocked",
        "RC-02": "pass" if (
            publisher["qa_integrity_gate"] == "pass"
            and resource_inventory["resource_inventory_gate"] == "pass"
            and reference_graph["reference_graph_integrity_gate"] == "pass"
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
        "RC-05": "pass" if (
            data_evidence["independent_recalculation_gate"] == "pass"
            and all(row["independent_recalculation"] == "pass" for row in measures)
        ) else "blocked",
        "RC-06": "pass" if (
            data_evidence["golden_cohort_gate"] == "pass"
            and all(row["golden_cohort"] == "pass" for row in measures)
        ) else "blocked",
        "RC-07": "pass" if (
            governance
            and all(qbc_approval_evidence_complete(row, approvals_path) for row in governance)
            and all(row["draft_definition_alignment"] == "approved" for row in measures)
            and all(measure_approval_evidence_complete(row, measure_approvals_path) for row in measure_approvals)
            and measure_specification["measure_specification_approval_gate"] == "pass"
            and artifact_audit["clinical_artifact_approval_gate"] == "pass"
            and criterion_resolution["criterion_resolution_gate"] == "pass"
        ) else "blocked",
        "RC-08": "pass" if (
            phi_audit["repository_phi_pattern_scan_gate"] == "pass"
            and publisher["formal_release_gate"] == "pass"
            and len(operational) == len(OPERATIONAL_APPROVALS)
            and all(qbc_approval_evidence_complete(row, approvals_path) for row in operational)
            and all(scope_decision_evidence_complete(row, scope_decisions_path) for row in scope_decisions)
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
        "approved_qbc_governance_count": sum(
            qbc_approval_evidence_complete(row, approvals_path)
            for row in governance
        ),
        "approved_operational_approval_count": sum(
            qbc_approval_evidence_complete(row, approvals_path)
            for row in operational
        ),
        "measure_approval_count": len(measure_approvals),
        "approved_measure_definition_count": sum(
            measure_approval_evidence_complete(row, measure_approvals_path)
            for row in measure_approvals
        ),
        "approved_measure_specification_count": approved_measure_specifications,
        "approved_measure_truth_table_case_count": approved_truth_cases,
        "required_measure_truth_assertion_count": 208,
        "measure_specification_approval_gate": measure_specification[
            "measure_specification_approval_gate"
        ],
        "scope_claim_count": len(scope_claims),
        "scope_decision_count": len(scope_decisions),
        "approved_scope_decision_count": sum(
            scope_decision_evidence_complete(row, scope_decisions_path)
            for row in scope_decisions
        ),
        "normative_scope_readiness": "pass" if normative_scope_ready else "block",
        "artifact_conformance_count": artifact_audit["artifact_count"],
        "approved_artifact_count": approved_artifact_count,
        "artifact_hash_binding_count": artifact_hash_binding_count,
        "clinical_artifact_approval_gate": artifact_audit[
            "clinical_artifact_approval_gate"
        ],
        "mapping_projection_fact_count": mapping_projection["mapping_fact_count"],
        "mapping_target_alternative_count": mapping_projection[
            "target_alternative_count"
        ],
        "resolved_local_profile_element_count": resolved_projection_count,
        "blocked_target_alternative_count": blocked_projection_count,
        "semantic_profile_gap_alternative_count": semantic_profile_gap_count,
        "semantic_profile_gap_fact_count": semantic_profile_gap_fact_count,
        "semantic_profile_gap_fact_ids": semantic_profile_gap_fact_ids,
        "unit_policy_pending_alternative_count": unit_policy_pending_count,
        "blocked_projection_fact_count": blocked_projection_fact_count,
        "blocked_projection_fact_ids": blocked_projection_fact_ids,
        "projection_readiness_gate": mapping_projection["projection_readiness_gate"],
        "terminology_artifact_count": terminology_audit["terminology_artifact_count"],
        "clinical_value_set_approval_count": terminology_audit[
            "clinical_value_set_approval_count"
        ],
        "approved_clinical_value_set_count": approved_terminology,
        "validated_clinical_value_set_expansion_count": validated_expansions,
        "versionless_clinical_value_set_count": versionless_clinical_valuesets,
        "concept_map_relationship_count": terminology_audit[
            "concept_map_relationship_count"
        ],
        "approved_concept_map_relationship_count": approved_relationships,
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
        "reference_graph_integrity_gate": reference_graph[
            "reference_graph_integrity_gate"
        ],
        "total_audited_reference_edge_count": reference_graph[
            "total_audited_reference_edge_count"
        ],
        "local_url_link_occurrence_count": reference_graph[
            "local_url_link_occurrence_count"
        ],
        "fhir_reference_occurrence_count": reference_graph[
            "fhir_reference_occurrence_count"
        ],
        "external_canonical_reference_occurrence_count": reference_graph[
            "external_canonical_reference_occurrence_count"
        ],
        "source_fact_count": data_evidence["expected_fact_count"],
        "measure_expression_count": data_evidence["measure_expression_count"],
        "measure_expression_occurrence_count": data_evidence[
            "measure_expression_occurrence_count"
        ],
        "case_level_comparison_row_count": data_evidence[
            "case_level_comparison_row_count"
        ],
        "source_contract_dimension_count": data_evidence[
            "source_contract_dimension_count"
        ],
        "complete_source_contract_count": data_evidence[
            "complete_source_contract_count"
        ],
        "declared_derived_dependency_count": data_evidence[
            "declared_derived_dependency_count"
        ],
        "population_criterion_count": data_evidence["population_criterion_count"],
        "criterion_referenced_fact_count": data_evidence[
            "criterion_referenced_fact_count"
        ],
        "approved_authoritative_or_derived_fact_count": data_evidence[
            "approved_authoritative_or_derived_fact_count"
        ],
        "secondary_reconciliation_row_count": data_evidence[
            "secondary_reconciliation_row_count"
        ],
        "approved_secondary_reconciliation_row_count": data_evidence[
            "approved_secondary_reconciliation_row_count"
        ],
        "approved_independent_recalculation_count": data_evidence[
            "approved_independent_recalculation_count"
        ],
        "approved_golden_cohort_count": data_evidence[
            "approved_golden_cohort_count"
        ],
        "source_acquisition_work_package_count": source_work_packages[
            "work_package_count"
        ],
        "confirmed_source_owner_assignment_count": confirmed_owner_count,
        "source_owner_assignment_gate": source_work_packages[
            "owner_assignment_gate"
        ],
        "criterion_resolution_decision_count": criterion_resolution["decision_count"],
        "approved_criterion_resolution_decision_count": approved_resolution_count,
        "non_aligned_criterion_resolution_decision_count": non_aligned_resolution_count,
        "production_allowed_criterion_resolution_decision_count": (
            production_allowed_resolution_count
        ),
        "criterion_resolution_gate": criterion_resolution["criterion_resolution_gate"],
        "control_integrity_gate": integrity,
        "data_correctness_gate": data_gate,
        "publisher_formal_qa_gate": publisher["formal_release_gate"],
        "repository_phi_pattern_scan_gate": phi_audit[
            "repository_phi_pattern_scan_gate"
        ],
        "repository_phi_pattern_finding_count": finding_count,
        "repository_phi_pattern_inspected_file_count": inspected_file_count,
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
    parser.add_argument("--measure-specification-audit", type=Path, required=True)
    parser.add_argument("--scope-claims", type=Path, required=True)
    parser.add_argument("--scope-decisions", type=Path, required=True)
    parser.add_argument("--artifact-audit", type=Path, required=True)
    parser.add_argument("--mapping-projection-audit", type=Path, required=True)
    parser.add_argument("--terminology-audit", type=Path, required=True)
    parser.add_argument("--resource-inventory-audit", type=Path, required=True)
    parser.add_argument("--reference-graph-audit", type=Path, required=True)
    parser.add_argument("--data-evidence-audit", type=Path, required=True)
    parser.add_argument("--source-work-package-audit", type=Path, required=True)
    parser.add_argument("--criterion-resolution-audit", type=Path, required=True)
    parser.add_argument("--publisher-audit", type=Path, required=True)
    parser.add_argument("--phi-audit", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--target", choices=("integrity", "data", "formal"), default="integrity"
    )
    args = parser.parse_args()
    try:
        report = audit(
            args.controls, args.measure_audit, args.terminology_fsh,
            args.approval_register, args.measure_approval_register,
            args.measure_specification_audit,
            args.scope_claims, args.scope_decisions,
            args.artifact_audit,
            args.mapping_projection_audit,
            args.terminology_audit,
            args.resource_inventory_audit,
            args.reference_graph_audit,
            args.data_evidence_audit,
            args.source_work_package_audit,
            args.criterion_resolution_audit,
            args.publisher_audit,
            args.phi_audit,
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
