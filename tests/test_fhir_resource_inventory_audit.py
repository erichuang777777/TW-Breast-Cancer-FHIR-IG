import csv
import json
from pathlib import Path

import pytest

from scripts.audit_fhir_resource_inventory import (
    CAPABILITY_DOCUMENTATION,
    CANONICAL,
    CANONICAL_TYPES,
    DEFINITION_TYPES,
    EXPECTED_CAPABILITY_PROFILES,
    PACKAGE_VERSION,
    audit,
    version_policy_approval_complete,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "fhir-resource-inventory.csv"
VERSION_POLICIES = (
    ROOT / "mappings" / "publication" / "canonical-version-policy-register.csv"
)


def rows():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_register(path: Path, data):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def version_policy_rows():
    with VERSION_POLICIES.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_version_policies(path: Path, data):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def synthetic_inventory(tmp_path: Path, *, manual_version="4.0.1"):
    generated = tmp_path / "generated"
    manual = tmp_path / "manual"
    generated.mkdir()
    manual.mkdir()
    data = rows()
    library_url = f"{CANONICAL}Library/BreastCancerCaseManagement"

    for row in data:
        resource_type = row["resource_type"]
        resource_id = row["resource_id"]
        resource = {"resourceType": resource_type, "id": resource_id}
        if resource_type in CANONICAL_TYPES:
            resource.update({
                "url": f"{CANONICAL}{resource_type}/{resource_id}",
                "status": "draft",
                "experimental": True,
            })
            if row["authoring_source"] == "manual-json":
                resource["version"] = manual_version
        if resource_type == "ImplementationGuide":
            resource.update({
                "version": PACKAGE_VERSION,
                "fhirVersion": ["4.0.1"],
                "definition": {"resource": []},
            })
        elif resource_type == "CapabilityStatement":
            resource.update({
                "version": PACKAGE_VERSION,
                "fhirVersion": "4.0.1",
                "kind": "requirements",
                "format": ["json", "xml"],
                "rest": [{
                    "mode": "server",
                    "documentation": CAPABILITY_DOCUMENTATION,
                    "resource": [
                        {
                            "type": supported_type,
                            "supportedProfile": [
                                f"{CANONICAL}StructureDefinition/{profile_id}"
                                for profile_id in profile_ids
                            ],
                        }
                        for supported_type, profile_ids
                        in EXPECTED_CAPABILITY_PROFILES.items()
                    ],
                }],
            })
        elif resource_type == "Library":
            resource.update({
                "name": "BreastCancerCaseManagement",
                "version": "1.0.0",
                "content": [{"id": "ig-loader-BreastCancerCaseManagement.cql"}],
            })
        elif resource_type == "Measure":
            resource.update({"version": PACKAGE_VERSION, "library": [library_url]})
        elif resource_type == "ConceptMap":
            resource["version"] = PACKAGE_VERSION
        elif (
            resource_type == "StructureDefinition"
            and any(
                resource_id in profile_ids
                for profile_ids in EXPECTED_CAPABILITY_PROFILES.values()
            )
        ):
            resource["type"] = next(
                supported_type
                for supported_type, profile_ids
                in EXPECTED_CAPABILITY_PROFILES.items()
                if resource_id in profile_ids
            )
        elif resource_type == "NamingSystem":
            resource.update({
                "status": "draft",
                "kind": "identifier",
                "uniqueId": [{
                    "type": "uri",
                    "value": f"{CANONICAL}sid/{resource_id}",
                    "preferred": True,
                }],
            })
        directory = generated if row["authoring_source"] == "generated-fsh" else manual
        (directory / f"{resource_type}-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )

    ig_path = generated / (
        "ImplementationGuide-io.github.erichuang777777.breast-cancer.json"
    )
    ig = json.loads(ig_path.read_text(encoding="utf-8"))
    for row in data:
        if row["resource_type"] == "ImplementationGuide":
            continue
        entry = {
            "reference": {
                "reference": f"{row['resource_type']}/{row['resource_id']}"
            }
        }
        if row["resource_type"] in DEFINITION_TYPES:
            entry["exampleBoolean"] = False
        else:
            entry["exampleBoolean"] = True
        ig["definition"]["resource"].append(entry)
    ig_path.write_text(json.dumps(ig), encoding="utf-8")

    cql = tmp_path / "library.cql"
    cql.write_text(
        "library BreastCancerCaseManagement version '1.0.0'\n", encoding="utf-8"
    )
    return generated, manual, cql


def test_exact_264_resource_inventory_and_manifest_are_locked(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    report = audit(REGISTER, VERSION_POLICIES, generated, manual, cql)
    assert report["resource_inventory_gate"] == "pass"
    assert report["resource_count"] == 264
    assert report["publication_definition_count"] == 226
    assert report["synthetic_example_count"] == 38
    assert report["canonical_resource_count"] == 224
    assert report["generated_fsh_resource_count"] == 161
    assert report["manual_json_resource_count"] == 103
    assert report["measure_count"] == 20
    assert report["capability_resource_type_count"] == 13
    assert report["capability_supported_profile_count"] == 20
    assert report["canonical_version_policy_count"] == 4
    assert report["approved_canonical_version_policy_count"] == 0
    assert report["canonical_version_policy_group_counts"] == {
        "CV-PACKAGE-EXPLICIT": 24,
        "CV-CQL-LIBRARY": 1,
        "CV-PACKAGE-CONTEXT": 98,
        "CV-TCR-MANUAL": 101,
    }
    assert report["canonical_version_policy_states"] == {
        "CV-PACKAGE-EXPLICIT": "explicit-package-version",
        "CV-CQL-LIBRARY": "cql-library-version",
        "CV-PACKAGE-CONTEXT": "package-context-policy-pending",
        "CV-TCR-MANUAL": "fhir-version-collision",
    }
    assert report["manual_canonical_versions"] == ["4.0.1"]
    assert report["business_version_provenance_gate"] == "block"


def test_deleting_a_manifest_row_cannot_make_inventory_pass(tmp_path):
    altered = tmp_path / "register.csv"
    write_register(altered, rows()[:-1])
    generated, manual, cql = synthetic_inventory(tmp_path)
    with pytest.raises(ValueError, match="exactly 264 unique resources"):
        audit(altered, VERSION_POLICIES, generated, manual, cql)


def test_replacing_a_resource_with_the_same_type_is_detected(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / "Patient-breast-cancer-patient-example.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["id"] = "replacement-patient"
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="resource inventory mismatch"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_synthetic_task_cannot_be_misclassified_as_a_definition(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    ig_path = generated / (
        "ImplementationGuide-io.github.erichuang777777.breast-cancer.json"
    )
    ig = json.loads(ig_path.read_text(encoding="utf-8"))
    entry = next(
        entry
        for entry in ig["definition"]["resource"]
        if entry["reference"]["reference"] == "Task/tcr-breast-abstraction-example"
    )
    entry["exampleBoolean"] = False
    ig_path.write_text(json.dumps(ig), encoding="utf-8")
    with pytest.raises(ValueError, match="valid example marker"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_capability_statement_supported_profile_must_resolve_and_match_type(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / (
        "CapabilityStatement-BreastCancerCommunityCapabilityStatement.json"
    )
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["rest"][0]["resource"][0]["supportedProfile"] = [
        f"{CANONICAL}StructureDefinition/not-present"
    ]
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="unresolved supportedProfile"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_capability_statement_cannot_silently_drop_a_supported_profile(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / (
        "CapabilityStatement-BreastCancerCommunityCapabilityStatement.json"
    )
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["rest"][0]["resource"][2]["supportedProfile"].pop()
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="differs from locked policy"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_capability_statement_cannot_overclaim_task_authorization(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / (
        "CapabilityStatement-BreastCancerCommunityCapabilityStatement.json"
    )
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["rest"][0]["documentation"] = "Supports every task."
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="REST claim boundary mismatch"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_library_resource_must_match_the_cql_name_and_version(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / "Library-BreastCancerCaseManagement.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["version"] = "9.9.9"
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match CQL declaration"):
        audit(REGISTER, VERSION_POLICIES, generated, manual, cql)


def test_changing_manual_version_without_policy_approval_cannot_clear_gate(tmp_path):
    generated, manual, cql = synthetic_inventory(
        tmp_path, manual_version="TCR-breast-source-2026"
    )
    policies = version_policy_rows()
    next(row for row in policies if row["policy_id"] == "CV-TCR-MANUAL")[
        "current_version_state"
    ] = "authoritative-business-version-candidate"
    altered = tmp_path / "version-policies.csv"
    write_version_policies(altered, policies)
    report = audit(REGISTER, altered, generated, manual, cql)
    assert report["business_version_provenance_gate"] == "block"
    assert report["manual_canonical_versions"] == ["TCR-breast-source-2026"]


def test_all_four_signed_version_policies_are_required_to_clear_gate(tmp_path):
    generated, manual, cql = synthetic_inventory(
        tmp_path, manual_version="TCR-breast-source-2026"
    )
    policies = version_policy_rows()
    for row in policies:
        row.update({
            "current_status": "approved",
            "decision": "approve",
            "signer_name": "Publication owner",
            "signer_organization_title": "Governance board / chair",
            "decision_date": "2026-08-21",
            "evidence_uri_path": f"evidence/{row['policy_id']}.json",
            "signed_artifact_sha256": "a" * 64,
        })
    next(row for row in policies if row["policy_id"] == "CV-PACKAGE-CONTEXT")[
        "current_version_state"
    ] = "approved-package-context-only"
    next(row for row in policies if row["policy_id"] == "CV-TCR-MANUAL")[
        "current_version_state"
    ] = "authoritative-business-version"
    approved = tmp_path / "approved-version-policies.csv"
    write_version_policies(approved, policies)
    report = audit(REGISTER, approved, generated, manual, cql)
    assert report["approved_canonical_version_policy_count"] == 4
    assert report["business_version_provenance_gate"] == "pass"


def test_version_policy_approval_requires_signed_evidence():
    row = version_policy_rows()[0]
    row.update({
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Publication owner",
        "signer_organization_title": "Governance board / chair",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/version-policy.json",
        "signed_artifact_sha256": "",
    })
    assert not version_policy_approval_complete(row)
    row["signed_artifact_sha256"] = "b" * 64
    assert version_policy_approval_complete(row)


def test_deleting_a_version_policy_cannot_make_gate_pass(tmp_path):
    altered = tmp_path / "version-policies.csv"
    write_version_policies(altered, version_policy_rows()[:-1])
    generated, manual, cql = synthetic_inventory(tmp_path)
    with pytest.raises(ValueError, match="exact four version policies"):
        audit(REGISTER, altered, generated, manual, cql)


def test_version_policy_evidence_requirement_cannot_be_weakened(tmp_path):
    policies = version_policy_rows()
    policies[0]["required_evidence"] = "none"
    altered = tmp_path / "version-policies.csv"
    write_version_policies(altered, policies)
    generated, manual, cql = synthetic_inventory(tmp_path)
    with pytest.raises(ValueError, match="does not match the locked policy"):
        audit(REGISTER, altered, generated, manual, cql)
