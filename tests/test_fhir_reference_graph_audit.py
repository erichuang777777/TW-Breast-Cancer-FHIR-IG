import json
import shutil
from pathlib import Path

import pytest

from scripts.audit_fhir_reference_graph import audit


ROOT = Path(__file__).resolve().parents[1]
GENERATED = ROOT / "ig" / "fsh-generated" / "resources"
MANUAL = ROOT / "ig" / "input" / "resources"
SUSHI_CONFIG = ROOT / "ig" / "sushi-config.yaml"


def copied_resources(tmp_path: Path):
    generated = tmp_path / "generated"
    manual = tmp_path / "manual"
    shutil.copytree(GENERATED, generated)
    shutil.copytree(MANUAL, manual)
    return generated, manual


def rewrite(path: Path, change):
    resource = json.loads(path.read_text(encoding="utf-8-sig"))
    change(resource)
    path.write_text(json.dumps(resource), encoding="utf-8")


def test_complete_reference_graph_is_exact_and_resolved():
    report = audit(GENERATED, MANUAL, SUSHI_CONFIG)
    assert report["reference_graph_integrity_gate"] == "pass"
    assert report["resource_count"] == 260
    assert report["local_url_link_occurrence_count"] == 633
    assert report["local_url_link_counts"] == {
        "bundle-fullUrl": 19,
        "canonical-field": 219,
        "code-system-use": 138,
        "conceptmap-code-system-use": 2,
        "extension-use-url": 240,
        "fixed-extension-url": 13,
        "naming-system-use": 2,
    }
    assert report["unique_local_url_target_count"] == 190
    assert report["canonical_reference_occurrence_count"] == 254
    assert report["external_canonical_reference_occurrence_count"] == 35
    assert report["unique_external_canonical_count"] == 18
    assert report["external_canonical_authority_counts"] == {
        "fhir-r4-core-4.0.1": 33,
        "tw-core-1.0.0": 2,
    }
    assert report["versioned_canonical_reference_occurrence_count"] == 0
    assert report["fhir_reference_occurrence_count"] == 326
    assert report["manifest_reference_occurrence_count"] == 259
    assert report["non_manifest_reference_occurrence_count"] == 67
    assert report["total_audited_reference_edge_count"] == 994


def test_unresolved_local_valueset_reference_is_rejected(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = manual / "Questionnaire-tcr-breast-longform.json"
    rewrite(
        path,
        lambda resource: resource["item"][0]["item"][0].update({
            "answerValueSet": (
                "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
                "ValueSet/not-present"
            )
        }),
    )
    with pytest.raises(ValueError, match="unresolved local URL"):
        audit(generated, manual, SUSHI_CONFIG)


def test_local_canonical_target_type_mismatch_is_rejected(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = generated / "Bundle-breast-cancer-synthetic-scenario.json"
    rewrite(
        path,
        lambda resource: resource["meta"].update({
            "profile": [
                "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
                "ValueSet/qbc-field"
            ]
        }),
    )
    with pytest.raises(ValueError, match="expected StructureDefinition, resolved ValueSet"):
        audit(generated, manual, SUSHI_CONFIG)


def test_unresolved_fhir_reference_is_rejected(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = generated / "CarePlan-cancer-care-plan-example.json"
    rewrite(
        path,
        lambda resource: resource["subject"].update({
            "reference": "Patient/not-present"
        }),
    )
    with pytest.raises(ValueError, match="unresolved FHIR reference"):
        audit(generated, manual, SUSHI_CONFIG)


def test_unreviewed_external_canonical_is_rejected(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = generated / "StructureDefinition-breast-cancer-case-management-report.json"
    rewrite(
        path,
        lambda resource: resource.update({
            "baseDefinition": "https://unreviewed.example/StructureDefinition/base"
        }),
    )
    with pytest.raises(ValueError, match="external canonical graph changed"):
        audit(generated, manual, SUSHI_CONFIG)


def test_external_canonical_target_type_mismatch_is_rejected(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = generated / "Bundle-breast-cancer-synthetic-scenario.json"
    rewrite(
        path,
        lambda resource: resource["meta"].update({
            "profile": ["http://hl7.org/fhir/ValueSet/administrative-gender"]
        }),
    )
    with pytest.raises(ValueError, match="does not identify a StructureDefinition"):
        audit(generated, manual, SUSHI_CONFIG)


def test_bundle_fullurl_must_match_embedded_resource_identity(tmp_path):
    generated, manual = copied_resources(tmp_path)
    path = generated / "Bundle-breast-cancer-synthetic-scenario.json"
    rewrite(
        path,
        lambda resource: resource["entry"][0].update({
            "fullUrl": (
                "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
                "Patient/not-present"
            )
        }),
    )
    with pytest.raises(ValueError, match="fullUrl/resource identity mismatch"):
        audit(generated, manual, SUSHI_CONFIG)
