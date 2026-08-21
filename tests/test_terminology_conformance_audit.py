import csv
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
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"


def rows():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
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
        resource_id = f"cs-{index:03d}"
        resource = {
            "resourceType": "CodeSystem",
            "id": resource_id,
            "url": f"{CANONICAL}CodeSystem/{resource_id}",
            "status": "draft",
            "experimental": True,
            "content": "complete",
            "concept": [{"code": f"code-{index:03d}"}],
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

    for index in range(2):
        resource_id = f"cm-{index:03d}"
        resource = {
            "resourceType": "ConceptMap",
            "id": resource_id,
            "url": f"{CANONICAL}ConceptMap/{resource_id}",
            "status": "draft",
            "experimental": True,
            "group": [{
                "source": "http://example.org/source",
                "target": "http://example.org/target",
                "element": [{
                    "code": "source-code",
                    "target": [{"code": "target-code", "equivalence": "equivalent"}],
                }],
            }],
        }
        (resource_dir / f"ConceptMap-{resource_id}.json").write_text(
            json.dumps(resource), encoding="utf-8"
        )
    return resource_dir


def test_current_register_covers_complete_inventory_and_keeps_clinical_gate_open(tmp_path):
    report = audit(REGISTER, CQL, [synthetic_resources(tmp_path)])
    assert report["terminology_integrity_gate"] == "pass"
    assert report["terminology_artifact_count"] == 152
    assert report["code_system_count"] == 60
    assert report["value_set_count"] == 90
    assert report["concept_map_count"] == 2
    assert report["empty_clinical_value_set_count"] == 19
    assert report["clinical_value_set_approval_count"] == 19
    assert report["approved_clinical_value_set_count"] == 0
    assert report["clinical_terminology_gate"] == "block"


def test_deleting_an_approval_cannot_make_the_gate_pass(tmp_path):
    altered = tmp_path / "register.csv"
    write_register(altered, rows()[:-1])
    with pytest.raises(ValueError, match="each of 19 clinical ValueSets"):
        audit(altered, CQL, [synthetic_resources(tmp_path)])


def test_empty_nonclinical_valueset_is_rejected(tmp_path):
    resource_dir = synthetic_resources(tmp_path)
    path = resource_dir / "ValueSet-vs-000.json"
    resource = json.loads(path.read_text(encoding="utf-8"))
    resource.pop("compose")
    path.write_text(json.dumps(resource), encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected empty ValueSets"):
        audit(REGISTER, CQL, [resource_dir])


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
        audit(altered, CQL, [synthetic_resources(tmp_path)])


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
