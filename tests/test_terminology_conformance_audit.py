import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_terminology_conformance import (
    CANONICAL,
    CLINICAL_VALUESET_IDS,
    approval_complete,
    audit,
    strip_cql_comments,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTER = (
    ROOT
    / "mappings"
    / "publication"
    / "case-management-terminology-approval-register.csv"
)
EXPANSION_REGISTER = (
    ROOT / "mappings" / "publication" / "terminology-expansion-validation-register.csv"
)
RELATIONSHIP_REGISTER = (
    ROOT / "mappings" / "publication" / "terminology-conceptmap-relationship-register.csv"
)
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"


def rows():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def register_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_register(path: Path, data):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def synthetic_resources(tmp_path: Path):
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()

    for index in range(60):
        resource_id = "qbc-workflow" if index == 59 else f"cs-{index:03d}"
        concepts = (
            [
                {"code": "P02-0"}, {"code": "P02-1"}, {"code": "P02-2"},
                {"code": "P02-3"}, {"code": "LATERALITY-L"},
                {"code": "LATERALITY-R"},
            ]
            if resource_id == "qbc-workflow"
            else [{"code": f"code-{index:03d}"}]
        )
        resource = {
            "resourceType": "CodeSystem",
            "id": resource_id,
            "url": f"{CANONICAL}CodeSystem/{resource_id}",
            "status": "draft",
            "experimental": True,
            "version": "1.0-test",
            "content": "complete",
            "concept": concepts,
        }
        (resource_dir / f"CodeSystem-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )

    for index in range(71):
        resource_id = f"vs-{index:03d}"
        resource = {
            "resourceType": "ValueSet",
            "id": resource_id,
            "url": f"{CANONICAL}ValueSet/{resource_id}",
            "status": "draft",
            "experimental": True,
            "compose": {
                "include": [{"system": f"{CANONICAL}CodeSystem/cs-000"}]
            },
        }
        (resource_dir / f"ValueSet-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )

    for resource_id in CLINICAL_VALUESET_IDS:
        resource = {
            "resourceType": "ValueSet",
            "id": resource_id,
            "url": f"{CANONICAL}ValueSet/{resource_id}",
            "status": "draft",
            "experimental": True,
        }
        (resource_dir / f"ValueSet-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )

    concept_maps = {
        "QBCGenderToFHIRAdministrativeGender": (
            "http://hl7.org/fhir/administrative-gender",
            "FHIR-R4",
            [("P02-0", "male"), ("P02-1", "female"),
             ("P02-2", "other"), ("P02-3", "unknown")],
        ),
        "QBCLateralityToSNOMEDCT": (
            "http://snomed.info/sct",
            "SNOMED-test",
            [("LATERALITY-L", "7771000"), ("LATERALITY-R", "24028007")],
        ),
    }
    for resource_id, (target_system, target_version, mappings) in concept_maps.items():
        resource = {
            "resourceType": "ConceptMap",
            "id": resource_id,
            "url": f"{CANONICAL}ConceptMap/{resource_id}",
            "status": "draft",
            "experimental": True,
            "group": [{
                "source": f"{CANONICAL}CodeSystem/qbc-workflow",
                "sourceVersion": "1.0-test",
                "target": target_system,
                "targetVersion": target_version,
                "element": [
                    {
                        "code": source_code,
                        "target": [{"code": target_code, "equivalence": "equivalent"}],
                    }
                    for source_code, target_code in mappings
                ],
            }],
        }
        (resource_dir / f"ConceptMap-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )
    return resource_dir


def test_current_register_covers_complete_inventory_and_keeps_clinical_gate_open(tmp_path):
    report = audit(
        REGISTER, EXPANSION_REGISTER, RELATIONSHIP_REGISTER, CQL,
        [synthetic_resources(tmp_path)],
    )
    assert report["terminology_integrity_gate"] == "pass"
    assert report["terminology_artifact_count"] == 152
    assert report["code_system_count"] == 60
    assert report["value_set_count"] == 90
    assert report["concept_map_count"] == 2
    assert report["empty_clinical_value_set_count"] == 19
    assert report["clinical_value_set_approval_count"] == 19
    assert report["approved_clinical_value_set_count"] == 0
    assert report["validated_clinical_value_set_expansion_count"] == 0
    assert report["concept_map_relationship_count"] == 6
    assert report["approved_concept_map_relationship_count"] == 0
    assert report["clinical_terminology_gate"] == "block"


def test_deleting_an_approval_cannot_make_the_gate_pass(tmp_path):
    altered = tmp_path / "register.csv"
    write_register(altered, rows()[:-1])
    with pytest.raises(ValueError, match="each of 19 clinical ValueSets"):
        audit(
            altered, EXPANSION_REGISTER, RELATIONSHIP_REGISTER, CQL,
            [synthetic_resources(tmp_path)],
        )


def test_empty_nonclinical_valueset_is_rejected(tmp_path):
    resource_dir = synthetic_resources(tmp_path)
    path = resource_dir / "ValueSet-vs-000.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource.pop("compose")
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected empty ValueSets"):
        audit(REGISTER, EXPANSION_REGISTER, RELATIONSHIP_REGISTER, CQL, [resource_dir])


def test_declared_cql_usage_must_match_the_library(tmp_path):
    data = rows()
    alnd = next(
        row
        for row in data
        if row["valueset_id"] == "cm-axillary-lymph-node-dissection-procedure"
    )
    alnd["cql_identifier"] = "Axillary Lymph Node Dissection"
    alnd["cql_usage_status"] = "referenced"
    altered = tmp_path / "register.csv"
    write_register(altered, data)
    with pytest.raises(ValueError, match="stale CQL declaration"):
        audit(
            altered, EXPANSION_REGISTER, RELATIONSHIP_REGISTER, CQL,
            [synthetic_resources(tmp_path)],
        )


def test_terminology_approval_requires_version_identity_date_evidence_and_hash():
    row = {
        "content_status": "approved",
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Terminology reviewer",
        "signer_organization_title": "Hospital / terminology board",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/terminology.json",
        "signed_artifact_sha256": "",
        "authoritative_source_version": "AJCC-8-and-local-catalog-2026",
    }
    assert not approval_complete(row)
    row["signed_artifact_sha256"] = "f" * 64
    assert approval_complete(row)
    row["authoritative_source_version"] = "pending-owner-confirmation"
    assert not approval_complete(row)


def test_cql_comment_stripping_preserves_urls_but_removes_fake_usage():
    source = (
        "valueset \"Example\": 'https://example.org/ValueSet/example'\n"
        "// fake use: [Observation: \"Example\"]\n"
        "define \"URL\": 'https://example.org/path' /* \"Example\" */\n"
    )
    stripped = strip_cql_comments(source)
    assert "https://example.org/ValueSet/example" in stripped
    assert "https://example.org/path" in stripped
    assert "fake use" not in stripped
    assert stripped.count('"Example"') == 1


def test_conceptmap_relationship_register_must_cover_exact_artifact_tuples(tmp_path):
    altered = tmp_path / "relationships.csv"
    write_register(altered, register_rows(RELATIONSHIP_REGISTER)[:-1])
    with pytest.raises(ValueError, match="relationship coverage mismatch"):
        audit(
            REGISTER, EXPANSION_REGISTER, altered, CQL,
            [synthetic_resources(tmp_path)],
        )


def test_validated_expansion_is_bound_to_exact_bundle_and_code_tuples(tmp_path):
    resource_dir = synthetic_resources(tmp_path)
    valueset_id = "cm-clinical-stage-group-code"
    valueset_path = resource_dir / f"ValueSet-{valueset_id}.json"
    valueset = json.loads(valueset_path.read_text(encoding="utf-8"))
    valueset["version"] = "1.0-test"
    valueset["compose"] = {
        "include": [{
            "system": f"{CANONICAL}CodeSystem/cs-000",
            "version": "1.0-test",
            "concept": [{"code": "code-000"}],
        }]
    }
    valueset_path.write_text(json.dumps(valueset), encoding="utf-8")

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    bundle_path = evidence_dir / "clinical-stage-expansion.json"
    bundle = {
        "schema_version": "1.0",
        "valueset_url": f"{CANONICAL}ValueSet/{valueset_id}",
        "valueset_version": "1.0-test",
        "expansion_identifier": "urn:uuid:test-expansion",
        "expansion_timestamp": "2026-08-21T10:00:00+08:00",
        "expansion_parameters": [],
        "terminology_service": {
            "url": "https://terminology.example.test/fhir",
            "software": "independent-test-service",
            "version": "2026.08",
        },
        "codes": [{
            "system": f"{CANONICAL}CodeSystem/cs-000",
            "version": "1.0-test",
            "code": "code-000",
            "display": "Synthetic code",
            "validation_result": True,
        }],
        "negative_tests": [{
            "system": f"{CANONICAL}CodeSystem/cs-000",
            "version": "1.0-test",
            "code": "definitely-invalid",
            "validation_result": False,
        }],
    }
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    bundle_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()

    approval_data = rows()
    approval = next(row for row in approval_data if row["valueset_id"] == valueset_id)
    approval.update({
        "authoritative_source_version": "synthetic-source-1",
        "content_status": "approved",
        "current_status": "approved",
        "decision": "approve",
        "signer_name": "Terminology reviewer",
        "signer_organization_title": "Synthetic terminology board",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/clinical-stage-expansion.json",
        "signed_artifact_sha256": bundle_hash,
    })
    approval_path = tmp_path / "approvals.csv"
    write_register(approval_path, approval_data)

    expansion_data = register_rows(EXPANSION_REGISTER)
    expansion = next(row for row in expansion_data if row["valueset_id"] == valueset_id)
    expansion.update({
        "evidence_bundle_path": "evidence/clinical-stage-expansion.json",
        "evidence_bundle_sha256": bundle_hash,
        "validation_status": "validated",
        "terminology_service": "https://terminology.example.test/fhir",
        "terminology_service_version": "2026.08",
        "validated_at": "2026-08-21T10:00:00+08:00",
        "expanded_code_count": "1",
        "resolved_code_count": "1",
        "unresolved_code_count": "0",
        "negative_test_count": "1",
        "validator_name": "Independent validator",
    })
    expansion_path = tmp_path / "expansions.csv"
    write_register(expansion_path, expansion_data)

    report = audit(
        approval_path, expansion_path, RELATIONSHIP_REGISTER, CQL, [resource_dir]
    )
    assert report["validated_clinical_value_set_expansion_count"] == 1
    assert report["validated_clinical_expansion_code_count"] == 1
    bundle["codes"][0]["code"] = "tampered"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence bundle SHA-256 mismatch"):
        audit(
            approval_path, expansion_path, RELATIONSHIP_REGISTER, CQL, [resource_dir]
        )
    tampered_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    approval["signed_artifact_sha256"] = tampered_hash
    expansion["evidence_bundle_sha256"] = tampered_hash
    write_register(approval_path, approval_data)
    write_register(expansion_path, expansion_data)
    with pytest.raises(ValueError, match="expansion omits composed code"):
        audit(
            approval_path, expansion_path, RELATIONSHIP_REGISTER, CQL, [resource_dir]
        )


def test_approved_conceptmap_relationship_is_bound_to_versions_and_artifact_hash(tmp_path):
    resource_dir = synthetic_resources(tmp_path)
    conceptmap_path = (
        resource_dir / "ConceptMap-QBCGenderToFHIRAdministrativeGender.json"
    )
    conceptmap_hash = hashlib.sha256(conceptmap_path.read_bytes()).hexdigest()
    evidence_path = tmp_path / "relationship-review.json"
    evidence_path.write_text(
        json.dumps({"decision": "approve", "relationship_id": "TERM-REL-001"}),
        encoding="utf-8",
    )
    evidence_hash = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    relationship_data = register_rows(RELATIONSHIP_REGISTER)
    relationship = next(
        row for row in relationship_data if row["relationship_id"] == "TERM-REL-001"
    )
    relationship.update({
        "source_version": "1.0-test",
        "target_version": "FHIR-R4",
        "source_resolution_status": "resolved",
        "target_resolution_status": "resolved",
        "relationship_status": "approved",
        "authoritative_source_version": "QBC-test-and-FHIR-R4",
        "decision": "approve",
        "signer_name": "Terminology reviewer",
        "signer_organization_title": "Synthetic terminology board",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "relationship-review.json",
        "evidence_sha256": evidence_hash,
        "reviewed_conceptmap_sha256": conceptmap_hash,
    })
    relationship_path = tmp_path / "relationships.csv"
    write_register(relationship_path, relationship_data)
    report = audit(
        REGISTER, EXPANSION_REGISTER, relationship_path, CQL, [resource_dir]
    )
    assert report["approved_concept_map_relationship_count"] == 1

    conceptmap = json.loads(conceptmap_path.read_text(encoding="utf-8"))
    conceptmap["group"][0]["element"][0]["target"][0]["code"] = "tampered"
    conceptmap_path.write_text(json.dumps(conceptmap), encoding="utf-8")
    with pytest.raises(ValueError, match="relationship coverage mismatch"):
        audit(
            REGISTER, EXPANSION_REGISTER, relationship_path, CQL, [resource_dir]
        )
