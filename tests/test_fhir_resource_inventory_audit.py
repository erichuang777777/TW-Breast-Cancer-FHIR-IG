import csv
import json
from pathlib import Path

import pytest

from scripts.audit_fhir_resource_inventory import (
    CANONICAL,
    CANONICAL_TYPES,
    DEFINITION_TYPES,
    PACKAGE_VERSION,
    audit,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "fhir-resource-inventory.csv"


def rows():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_register(path: Path, data):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def synthetic_inventory(tmp_path: Path, *, questionnaire_version="4.0.1"):
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
                "rest": [],
            })
        elif resource_type == "Library":
            resource.update({
                "name": "BreastCancerCaseManagement",
                "version": "1.0.0",
                "content": [{"id": "ig-loader-BreastCancerCaseManagement.cql"}],
            })
        elif resource_type == "Measure":
            resource.update({"version": PACKAGE_VERSION, "library": [library_url]})
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
        elif resource_type == "Questionnaire":
            resource["version"] = questionnaire_version

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


def test_exact_260_resource_inventory_and_manifest_are_locked(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    report = audit(REGISTER, generated, manual, cql)
    assert report["resource_inventory_gate"] == "pass"
    assert report["resource_count"] == 260
    assert report["publication_definition_count"] == 224
    assert report["synthetic_example_count"] == 36
    assert report["canonical_resource_count"] == 222
    assert report["generated_fsh_resource_count"] == 157
    assert report["manual_json_resource_count"] == 103
    assert report["measure_count"] == 20
    assert report["business_version_provenance_gate"] == "block"
    assert report["ambiguous_business_version_artifacts"] == [
        "Questionnaire/tcr-breast-longform"
    ]


def test_deleting_a_manifest_row_cannot_make_inventory_pass(tmp_path):
    altered = tmp_path / "register.csv"
    write_register(altered, rows()[:-1])
    generated, manual, cql = synthetic_inventory(tmp_path)
    with pytest.raises(ValueError, match="exactly 260 unique resources"):
        audit(altered, generated, manual, cql)


def test_replacing_a_resource_with_the_same_type_is_detected(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / "Patient-breast-cancer-patient-example.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["id"] = "replacement-patient"
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="resource inventory mismatch"):
        audit(REGISTER, generated, manual, cql)


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
        audit(REGISTER, generated, manual, cql)


def test_capability_statement_supported_profile_must_resolve_and_match_type(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / (
        "CapabilityStatement-BreastCancerCommunityCapabilityStatement.json"
    )
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["rest"] = [{
        "resource": [{
            "type": "Patient",
            "supportedProfile": [f"{CANONICAL}StructureDefinition/not-present"],
        }]
    }]
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="unresolved supportedProfile"):
        audit(REGISTER, generated, manual, cql)


def test_library_resource_must_match_the_cql_name_and_version(tmp_path):
    generated, manual, cql = synthetic_inventory(tmp_path)
    path = generated / "Library-BreastCancerCaseManagement.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource["version"] = "9.9.9"
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match CQL declaration"):
        audit(REGISTER, generated, manual, cql)


def test_authoritative_questionnaire_business_version_can_clear_version_gate(tmp_path):
    generated, manual, cql = synthetic_inventory(
        tmp_path, questionnaire_version="TCR-breast-source-2026"
    )
    report = audit(REGISTER, generated, manual, cql)
    assert report["business_version_provenance_gate"] == "pass"
    assert report["ambiguous_business_version_artifacts"] == []
