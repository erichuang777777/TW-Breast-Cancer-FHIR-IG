import csv
from pathlib import Path

import pytest

from scripts.audit_criterion_implementation_crosscheck import audit, derive


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "criterion-implementation-crosscheck.csv"
CRITERIA = ROOT / "mappings" / "case-management" / "case-management-population-criteria.csv"
SOURCES = ROOT / "mappings" / "publication" / "source-traceability-register.csv"
TASK = ROOT / "mappings" / "case-management" / "case-management-task-only-fields.csv"
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"
FSH = ROOT / "ig" / "input" / "fsh"


def expected_rows():
    return derive(CRITERIA, SOURCES, TASK, CQL, FSH)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_crosscheck_covers_all_68_criteria_without_overstating_publication():
    report = audit(REGISTER, expected_rows())
    assert report == {
        "gate_scope": "criterion-to-implementation-crosscheck-integrity",
        "criterion_count": 68,
        "alignment_counts": {
            "aligned-to-current-draft": 53,
            "candidate-not-approved": 3,
            "conditional-data-contract": 2,
            "definition-contradiction": 1,
            "implemented-variant-unresolved": 3,
            "known-not-enforced": 2,
            "task-layer-only": 4,
        },
        "source_fully_approved_count": 0,
        "production_publication_allowed_count": 0,
        "workflow_profile_gap_count": 0,
        "integrity_gate": "pass",
    }


def test_result_changing_and_conditional_gaps_are_named_at_criterion_level():
    by_id = {row["criterion_id"]: row for row in read_rows(REGISTER)}
    assert by_id["N3-DOSE"]["cql_alignment"] == "known-not-enforced"
    assert ">=4000 cGy" in by_id["N3-DOSE"]["known_difference"]
    assert by_id["D4-COHORT"]["cql_alignment"] == "conditional-data-contract"
    assert by_id["N5-RETURN"]["cql_alignment"] == "candidate-not-approved"
    assert by_id["S17-HISTOLOGY"]["cql_alignment"] == "definition-contradiction"
    assert by_id["X6-AGE-NODE-DEF"]["cql_alignment"] == "implemented-variant-unresolved"
    assert by_id["N1-HT"]["cql_alignment"] == "aligned-to-current-draft"
    assert by_id["D2-SURGERY-FIRST"]["cql_alignment"] == "aligned-to-current-draft"
    assert by_id["N4-ANTIHER2"]["cql_alignment"] == "aligned-to-current-draft"
    assert by_id["X1-STAGING-DEATH"]["cql_alignment"] == "candidate-not-approved"
    assert "curative intent" in by_id["X1-STAGING-DEATH"]["known_difference"]
    assert by_id["X1-NOSTAY-TRANSFER"]["cql_alignment"] == "known-not-enforced"
    assert "new-diagnosis discriminator" in by_id["D4-COHORT"]["known_difference"]


def test_dedicated_case_management_profile_closes_the_structural_task_gap():
    by_id = {row["criterion_id"]: row for row in read_rows(REGISTER)}
    assert by_id["S13-CLOSURE"]["workflow_contract"] == (
        "dedicated-task-profile-present-pending-approval"
    )
    assert by_id["IP-QUARTER"]["workflow_contract"] == "not-applicable"


def test_hand_edit_cannot_turn_a_known_gap_into_alignment(tmp_path):
    rows = read_rows(REGISTER)
    row = next(item for item in rows if item["criterion_id"] == "N3-DOSE")
    row["cql_alignment"] = "aligned-to-current-draft"
    altered = tmp_path / "crosscheck.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="stale fields for N3-DOSE"):
        audit(altered, expected_rows())
