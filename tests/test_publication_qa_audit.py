import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_publisher_qa.py"
POLICY = ROOT / "mappings" / "publication" / "publisher-warning-policy.csv"


def write_qa(tmp_path: Path, warnings: list[str], *, errors: int = 0):
    qa_text = tmp_path / "qa.txt"
    qa_html = tmp_path / "qa.html"
    qa_text.write_text(
        f"err = {errors}, warn = {len(warnings)}, info = 2\n"
        + "\n".join(f"WARNING: Example/x: {warning}" for warning in warnings)
        + "\n",
        encoding="utf-8",
    )
    qa_html.write_text(
        f"<!-- broken links = 0, errors = {errors}, "
        f"warn = {len(warnings)}, info = 2-->",
        encoding="utf-8",
    )
    return qa_text, qa_html


def run_audit(tmp_path: Path, warnings: list[str], *, target: str = "integrity"):
    qa_text, qa_html = write_qa(tmp_path, warnings)
    output = tmp_path / "audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--qa-text", str(qa_text),
            "--qa-html", str(qa_html),
            "--policy", str(POLICY),
            "--json-out", str(output),
            "--target", target,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    return completed, report


def test_warning_policy_is_complete_and_blocks_formal_release():
    with POLICY.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 7
    assert sum(int(row["max_count"]) for row in rows) == 52
    assert all(row["formal_disposition"] == "block" for row in rows)
    assert all(row["preview_approval_status"] == "pending" for row in rows)
    assert all(row["owner"] and row["required_evidence"] for row in rows)


def test_targetless_concept_map_warning_fails_as_a_regression(tmp_path):
    warning = "ConceptMap/example: ConceptMap.group[0]: No Target Code System"
    completed, report = run_audit(tmp_path, [warning])
    assert completed.returncode == 1
    assert report["qa_integrity_gate"] == "fail"
    assert report["community_preview_gate"] == "block"
    assert report["formal_release_gate"] == "block"
    assert report["over_limit"] == [
        {"warning_id": "PUB-WARN-002", "observed_count": 1, "max_count": 0}
    ]


def test_resolved_oid_warning_fails_as_a_regression(tmp_path):
    warning = (
        "The resource ValueSet/example should have an OID assigned to cater "
        "for possible use with OID based terminology systems"
    )
    completed, report = run_audit(tmp_path, [warning])
    assert completed.returncode == 1
    assert report["qa_integrity_gate"] == "fail"
    assert report["over_limit"] == [
        {"warning_id": "PUB-WARN-001", "observed_count": 1, "max_count": 0}
    ]


def test_unregistered_oid_root_is_a_classified_governance_blocker(tmp_path):
    warning = (
        "ImplementationGuide: The assigned auto-oid-root value "
        "'2.25.37863882866210842446634463448013114893' is not registered in "
        "https://github.com/FHIR/ig-registry/blob/master/oid-assignments.json "
        "so isn't known to be valid"
    )
    completed, report = run_audit(tmp_path, [warning])
    assert completed.returncode == 0, completed.stderr
    category = next(
        item for item in report["categories"] if item["warning_id"] == "PUB-WARN-007"
    )
    assert category["observed_count"] == 1
    assert category["within_limit"] is True
    assert report["qa_integrity_gate"] == "pass"
    assert report["community_preview_gate"] == "block"


def test_unknown_warning_fails_without_silent_acceptance(tmp_path):
    completed, report = run_audit(tmp_path, ["A completely new Publisher warning"])
    assert completed.returncode == 1
    assert report["qa_integrity_gate"] == "fail"
    assert report["unknown_warnings"]


def test_zero_warning_qa_passes_all_publisher_qa_targets(tmp_path):
    completed, report = run_audit(tmp_path, [], target="formal")
    assert completed.returncode == 0, completed.stderr
    assert report["qa_integrity_gate"] == "pass"
    assert report["community_preview_gate"] == "pass"
    assert report["formal_release_gate"] == "pass"
