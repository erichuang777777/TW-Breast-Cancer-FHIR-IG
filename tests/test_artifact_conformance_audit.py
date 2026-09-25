import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_artifact_conformance import approval_complete, audit


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "artifact-conformance-register.csv"
SCOPES = ROOT / "mappings" / "publication" / "ig-scope-claim-register.csv"
CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/"


def rows():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_register(path: Path, data):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def synthetic_resources(tmp_path: Path, data):
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    child_by_base = {
        row["expected_base_definition"]: CANONICAL + row["artifact_id"]
        for row in data
    }
    examples = {}
    for row in data:
        artifact = {
            "resourceType": "StructureDefinition",
            "id": row["artifact_id"],
            "url": CANONICAL + row["artifact_id"],
            "name": row["artifact_name"],
            "type": row["expected_type"],
            "kind": row["expected_kind"],
            "baseDefinition": row["expected_base_definition"],
            "derivation": "constraint",
            "status": "draft",
            "experimental": True,
        }
        (resource_dir / f"StructureDefinition-{row['artifact_id']}.json").write_text(
            json.dumps(artifact), encoding="utf-8"
        )
        example = examples.setdefault(
            row["example_resource_id"],
            {"resourceType": row["expected_type"], "id": row["example_resource_id"]},
        )
        if row["evidence_mode"] == "direct-profile":
            example["resourceType"] = row["expected_type"]
            example.setdefault("meta", {}).setdefault("profile", []).append(
                CANONICAL + row["artifact_id"]
            )
        elif row["evidence_mode"] == "derived-profile":
            example["resourceType"] = row["expected_type"]
            example.setdefault("meta", {}).setdefault("profile", []).append(
                child_by_base[CANONICAL + row["artifact_id"]]
            )
        else:
            example.setdefault("extension", []).append({
                "url": CANONICAL + row["artifact_id"], "valueString": "synthetic"
            })
    for resource_id, resource in examples.items():
        (resource_dir / f"Example-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )
    return resource_dir


def test_current_register_covers_all_48_artifacts_and_keeps_human_review_open(tmp_path):
    data = rows()
    resource_dir = synthetic_resources(tmp_path, data)
    report = audit(REGISTER, SCOPES, [resource_dir])
    assert report["artifact_integrity_gate"] == "pass"
    assert report["artifact_count"] == 48
    assert report["profile_count"] == 35
    assert report["extension_count"] == 13
    assert report["approved_artifact_count"] == 0
    assert report["clinical_artifact_approval_gate"] == "block"
    assert all(row["clinical_review_status"] == "pending-human-signoff" for row in data)


def test_deleting_an_artifact_cannot_make_the_gate_pass(tmp_path):
    data = rows()[:-1]
    altered = tmp_path / "register.csv"
    write_register(altered, data)
    resource_dir = synthetic_resources(tmp_path, data)
    with pytest.raises(ValueError, match="exactly 48 unique artifacts"):
        audit(altered, SCOPES, [resource_dir])


def test_stale_parent_is_rejected_against_generated_structure_definition(tmp_path):
    data = rows()
    resource_dir = synthetic_resources(tmp_path, data)
    data[0]["expected_base_definition"] = "http://hl7.org/fhir/StructureDefinition/Observation"
    altered = tmp_path / "register.csv"
    write_register(altered, data)
    with pytest.raises(ValueError, match="generated baseDefinition"):
        audit(altered, SCOPES, [resource_dir])


def test_example_must_actually_assert_the_profile_or_extension(tmp_path):
    data = rows()
    resource_dir = synthetic_resources(tmp_path, data)
    example = resource_dir / "Example-QBCWorkflowEpisodeExample.json"
    payload = json.loads(example.read_text(encoding="utf-8"))
    payload["extension"] = []
    example.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="does not prove extension-use"):
        audit(REGISTER, SCOPES, [resource_dir])


def test_artifact_approval_requires_identity_date_evidence_and_hash():
    row = {
        "clinical_review_status": "approved", "decision": "approve",
        "signer_name": "Clinical reviewer",
        "signer_organization_title": "Hospital / governance board",
        "decision_date": "2026-08-21", "evidence_uri_path": "evidence/profile.json",
        "signed_artifact_sha256": "",
    }
    assert not approval_complete(row)
    row["signed_artifact_sha256"] = "f" * 64
    assert approval_complete(row)


def test_artifact_approval_is_bound_to_exact_generated_structure_definition(tmp_path):
    data = rows()
    resource_dir = synthetic_resources(tmp_path, data)
    artifact = data[0]
    artifact_path = resource_dir / f"StructureDefinition-{artifact['artifact_id']}.json"
    artifact.update({
        "clinical_review_status": "approved",
        "decision": "approve",
        "signer_name": "Clinical reviewer",
        "signer_organization_title": "Hospital / governance board",
        "decision_date": "2026-08-21",
        "evidence_uri_path": f"resources/{artifact_path.name}",
        "signed_artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
    })
    altered = tmp_path / "register.csv"
    write_register(altered, data)
    report = audit(altered, SCOPES, [resource_dir])
    assert report["approved_artifact_count"] == 1
    assert report["artifact_hash_binding_count"] == 1

    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    payload["description"] = "changed after review"
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="not bound to the exact generated"):
        audit(altered, SCOPES, [resource_dir])
