import json
from pathlib import Path

import pytest

from scripts.audit_fhir_reference_graph import GraphExpectations, audit


ROOT = Path(__file__).resolve().parents[1]
SUSHI_CONFIG = ROOT / "ig" / "sushi-config.yaml"
CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
FHIR_PATIENT = "http://hl7.org/fhir/StructureDefinition/Patient"
FHIR_EXTENSION = "http://hl7.org/fhir/StructureDefinition/Extension"

SYNTHETIC_EXPECTATIONS = GraphExpectations(
    resource_count=12,
    local_link_counts={
        "bundle-fullUrl": 1,
        "canonical-field": 4,
        "code-system-use": 1,
        "extension-use-url": 2,
        "naming-system-use": 2,
    },
    unique_local_target_count=7,
    external_canonical_occurrence_count=2,
    external_canonicals=frozenset({FHIR_PATIENT, FHIR_EXTENSION}),
    external_authority_counts={"fhir-r4-core-4.0.1": 2, "tw-core-1.0.0": 0},
    versioned_canonical_reference_count=0,
    fhir_reference_count=2,
    manifest_reference_count=1,
)


def write_resource(directory: Path, resource: dict):
    path = directory / f"{resource['resourceType']}-{resource['id']}.json"
    path.write_text(json.dumps(resource), encoding="utf-8")


def synthetic_resources(tmp_path: Path):
    generated = tmp_path / "generated"
    manual = tmp_path / "manual"
    generated.mkdir()
    manual.mkdir()

    profile_url = f"{CANONICAL}StructureDefinition/patient-profile"
    extension_url = f"{CANONICAL}StructureDefinition/local-extension"
    code_system_url = f"{CANONICAL}CodeSystem/local-codes"
    value_set_url = f"{CANONICAL}ValueSet/local-values"
    naming_uri = f"{CANONICAL}sid/local-patient-id"
    library_url = f"{CANONICAL}Library/local-library"
    patient = {
        "resourceType": "Patient",
        "id": "patient-example",
        "meta": {"profile": [profile_url]},
        "identifier": [{"system": naming_uri, "value": "synthetic"}],
        "extension": [{"url": extension_url, "valueBoolean": True}],
    }
    resources = [
        {
            "resourceType": "StructureDefinition", "id": "patient-profile",
            "url": profile_url, "type": "Patient", "baseDefinition": FHIR_PATIENT,
        },
        {
            "resourceType": "StructureDefinition", "id": "local-extension",
            "url": extension_url, "type": "Extension", "baseDefinition": FHIR_EXTENSION,
        },
        {"resourceType": "CodeSystem", "id": "local-codes", "url": code_system_url},
        {
            "resourceType": "ValueSet", "id": "local-values", "url": value_set_url,
            "compose": {"include": [{"system": code_system_url}]},
        },
        {
            "resourceType": "NamingSystem", "id": "local-patient-id",
            "uniqueId": [{"type": "uri", "value": naming_uri}],
        },
        {"resourceType": "Library", "id": "local-library", "url": library_url},
        {
            "resourceType": "Measure", "id": "local-measure",
            "url": f"{CANONICAL}Measure/local-measure", "library": [library_url],
        },
        patient,
        {
            "resourceType": "Questionnaire", "id": "local-questionnaire",
            "url": f"{CANONICAL}Questionnaire/local-questionnaire",
            "item": [{"linkId": "coded", "type": "choice", "answerValueSet": value_set_url}],
        },
        {
            "resourceType": "Bundle", "id": "local-bundle", "type": "collection",
            "entry": [{
                "fullUrl": f"{CANONICAL}Patient/patient-example",
                "resource": patient,
            }],
        },
        {
            "resourceType": "CarePlan", "id": "local-care-plan",
            "subject": {"reference": "Patient/patient-example"},
        },
        {
            "resourceType": "ImplementationGuide", "id": "local-ig",
            "url": f"{CANONICAL}ImplementationGuide/local-ig",
            "definition": {"resource": [{
                "reference": {"reference": "Patient/patient-example"},
                "exampleBoolean": True,
            }]},
        },
    ]
    for resource in resources:
        write_resource(generated, resource)
    return generated, manual


def rewrite(path: Path, change):
    resource = json.loads(path.read_text(encoding="utf-8"))
    change(resource)
    path.write_text(json.dumps(resource), encoding="utf-8")


def run_synthetic(generated: Path, manual: Path):
    return audit(
        generated,
        manual,
        SUSHI_CONFIG,
        expectations=SYNTHETIC_EXPECTATIONS,
    )


def test_reference_graph_logic_is_exact_and_resolved_without_generated_build(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    report = run_synthetic(generated, manual)
    assert report["reference_graph_integrity_gate"] == "pass"
    assert report["resource_count"] == 12
    assert report["local_url_link_occurrence_count"] == 10
    assert report["unique_local_url_target_count"] == 7
    assert report["canonical_reference_occurrence_count"] == 6
    assert report["external_canonical_reference_occurrence_count"] == 2
    assert report["unique_external_canonical_count"] == 2
    assert report["fhir_reference_occurrence_count"] == 2
    assert report["manifest_reference_occurrence_count"] == 1
    assert report["non_manifest_reference_occurrence_count"] == 1
    assert report["total_audited_reference_edge_count"] == 14


def test_unresolved_local_valueset_reference_is_rejected(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "Questionnaire-local-questionnaire.json"
    rewrite(path, lambda resource: resource["item"][0].update({
        "answerValueSet": f"{CANONICAL}ValueSet/not-present"
    }))
    with pytest.raises(ValueError, match="unresolved local URL"):
        run_synthetic(generated, manual)


def test_local_canonical_target_type_mismatch_is_rejected(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "Patient-patient-example.json"
    rewrite(path, lambda resource: resource["meta"].update({
        "profile": [f"{CANONICAL}ValueSet/local-values"]
    }))
    with pytest.raises(ValueError, match="expected StructureDefinition, resolved ValueSet"):
        run_synthetic(generated, manual)


def test_unresolved_fhir_reference_is_rejected(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "CarePlan-local-care-plan.json"
    rewrite(path, lambda resource: resource["subject"].update({
        "reference": "Patient/not-present"
    }))
    with pytest.raises(ValueError, match="unresolved FHIR reference"):
        run_synthetic(generated, manual)


def test_unreviewed_external_canonical_is_rejected(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "StructureDefinition-patient-profile.json"
    rewrite(path, lambda resource: resource.update({
        "baseDefinition": "https://unreviewed.example/StructureDefinition/base"
    }))
    with pytest.raises(ValueError, match="external canonical graph changed"):
        run_synthetic(generated, manual)


def test_external_canonical_target_type_mismatch_is_rejected(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "Patient-patient-example.json"
    rewrite(path, lambda resource: resource["meta"].update({
        "profile": ["http://hl7.org/fhir/ValueSet/administrative-gender"]
    }))
    with pytest.raises(ValueError, match="does not identify a StructureDefinition"):
        run_synthetic(generated, manual)


def test_bundle_fullurl_must_match_embedded_resource_identity(tmp_path):
    generated, manual = synthetic_resources(tmp_path)
    path = generated / "Bundle-local-bundle.json"
    rewrite(path, lambda resource: resource["entry"][0].update({
        "fullUrl": f"{CANONICAL}Patient/not-present"
    }))
    with pytest.raises(ValueError, match="fullUrl/resource identity mismatch"):
        run_synthetic(generated, manual)
