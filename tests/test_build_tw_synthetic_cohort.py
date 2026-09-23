import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_tw_synthetic_cohort.py"
SPEC = importlib.util.spec_from_file_location("build_tw_synthetic_cohort", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_selection_is_deterministic():
    names = [f"patient-{number}.json" for number in range(20)]
    first = MODULE.stable_selection(names, 5, "seed", "cohort")
    second = MODULE.stable_selection(reversed(names), 5, "seed", "cohort")
    assert first == second


def test_transform_preserves_fields_references_and_source_profiles():
    source = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": "urn:uuid:p1",
                "resource": {
                    "resourceType": "Patient",
                    "id": "p1",
                    "meta": {"profile": ["http://hl7.org/fhir/us/mcode/StructureDefinition/mcode-cancer-patient"]},
                    "telecom": [{"system": "phone", "value": "555-0100"}],
                },
                "request": {"method": "POST", "url": "Patient"},
            },
            {
                "fullUrl": "urn:uuid:c1",
                "resource": {
                    "resourceType": "Condition",
                    "id": "c1",
                    "meta": {"profile": ["http://hl7.org/fhir/us/mcode/StructureDefinition/mcode-primary-cancer-condition"]},
                    "subject": {"reference": "urn:uuid:p1"},
                    "note": [{"text": "retained"}],
                },
                "request": {"method": "POST", "url": "Condition"},
            },
        ],
    }
    transformed, roles = MODULE.transform_bundle(source)
    assert transformed["type"] == "transaction"
    assert transformed["entry"][0]["request"] == source["entry"][0]["request"]
    assert transformed["entry"][0]["resource"]["telecom"] == source["entry"][0]["resource"]["telecom"]
    assert transformed["entry"][1]["resource"]["subject"] == source["entry"][1]["resource"]["subject"]
    assert transformed["entry"][1]["resource"]["note"] == source["entry"][1]["resource"]["note"]
    assert roles == {"Patient": 1, "PrimaryCancerCondition": 1}
    assert len(transformed["entry"][1]["resource"]["meta"]["profile"]) == 2
    assert len(source["entry"][1]["resource"]["meta"]["profile"]) == 1


def test_source_archives_contain_enough_patient_bundles():
    for _, archive_path, required in MODULE.SOURCES:
        assert archive_path.exists()
        with zipfile.ZipFile(archive_path) as archive:
            members = MODULE.json_members(archive)
            assert len(members) >= required
            sample = json.loads(archive.read(members[0]))
            assert sample["resourceType"] == "Bundle"


def test_unresolved_reference_audit_groups_paths():
    bundle = {
        "resourceType": "Bundle",
        "entry": [
            {"fullUrl": "urn:uuid:p1", "resource": {"resourceType": "Patient", "id": "p1"}},
            {
                "fullUrl": "urn:uuid:prov1",
                "resource": {
                    "resourceType": "Provenance",
                    "target": [
                        {"reference": "urn:uuid:p1"},
                        {"reference": "urn:uuid:external"},
                    ],
                },
            },
        ],
    }
    assert MODULE.unresolved_urn_references(bundle) == {
        ".entry[].resource.target[].reference": 1
    }
