import csv
import json
from pathlib import Path

import pytest

from scripts.audit_profile_constraints import (
    BASELINE_COLUMNS,
    CANONICAL_ROOT,
    audit,
    live_rows,
    load_structures,
    write_baseline,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "mappings" / "publication" / "profile-constraint-baseline.csv"
RESOURCE_DIRS = [
    ROOT / "ig" / "fsh-generated" / "resources",
    ROOT / "ig" / "input" / "resources",
]


def make_profile(path: Path) -> None:
    payload = {
        "resourceType": "StructureDefinition",
        "id": "test-profile",
        "url": CANONICAL_ROOT + "test-profile",
        "name": "TestProfile",
        "status": "draft",
        "experimental": True,
        "kind": "resource",
        "type": "Observation",
        "baseDefinition": "http://hl7.org/fhir/StructureDefinition/Observation",
        "derivation": "constraint",
        "differential": {
            "element": [
                {
                    "id": "Observation.subject",
                    "path": "Observation.subject",
                    "min": 1,
                    "mustSupport": True,
                    "type": [{
                        "code": "Reference",
                        "targetProfile": [
                            "http://hl7.org/fhir/StructureDefinition/Patient"
                        ],
                    }],
                },
                {
                    "id": "Observation.code",
                    "path": "Observation.code",
                    "binding": {
                        "strength": "required",
                        "valueSet": "http://example.org/ValueSet/test",
                    },
                },
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_current_baseline_locks_all_48_profiles_and_222_elements():
    report = audit(BASELINE, RESOURCE_DIRS)
    assert report["constraint_baseline_gate"] == "pass"
    assert report["structure_definition_count"] == 48
    assert report["differential_element_count"] == 222
    assert report["facet_counts"] == {
        "cardinality": 77,
        "must-support": 106,
        "binding": 19,
        "type": 55,
        "fixed-or-pattern": 29,
        "slicing": 2,
        "invariant": 0,
        "declaration-or-narrative": 18,
    }
    assert len(report["constraint_manifest_sha256"]) == 64
    assert report["clinical_correctness_gate"] == (
        "not-assessed-requires-exact-artifact-approval"
    )


def test_cardinality_change_after_baseline_is_rejected(tmp_path):
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    profile_path = resource_dir / "StructureDefinition-test-profile.json"
    make_profile(profile_path)
    baseline = tmp_path / "baseline.csv"
    write_baseline(baseline, live_rows(load_structures([resource_dir])))
    assert audit(baseline, [resource_dir])["differential_element_count"] == 2

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload["differential"]["element"][0]["min"] = 0
    profile_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="profile constraint drift"):
        audit(baseline, [resource_dir])


def test_added_or_removed_differential_element_is_rejected(tmp_path):
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    profile_path = resource_dir / "StructureDefinition-test-profile.json"
    make_profile(profile_path)
    baseline = tmp_path / "baseline.csv"
    write_baseline(baseline, live_rows(load_structures([resource_dir])))

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload["differential"]["element"].pop()
    profile_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="constraint set drift"):
        audit(baseline, [resource_dir])


def test_differential_element_order_is_part_of_the_baseline(tmp_path):
    resource_dir = tmp_path / "resources"
    resource_dir.mkdir()
    profile_path = resource_dir / "StructureDefinition-test-profile.json"
    make_profile(profile_path)
    baseline = tmp_path / "baseline.csv"
    write_baseline(baseline, live_rows(load_structures([resource_dir])))

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    payload["differential"]["element"].reverse()
    profile_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="differential order drift"):
        audit(baseline, [resource_dir])


def test_baseline_columns_are_exact_and_human_readable():
    with BASELINE.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert tuple(reader.fieldnames or ()) == BASELINE_COLUMNS
    task_for = next(
        row for row in rows
        if row["artifact_id"] == "breast-cancer-case-management-task"
        and row["element_id"] == "Task.for"
    )
    assert task_for["cardinality"] == "1.."
    assert "type" in task_for["facets"]
    assert "breast-cancer-patient" in task_for["type_constraints_json"]
    assert len(task_for["constraint_sha256"]) == 64
