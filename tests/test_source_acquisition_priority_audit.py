import csv
from pathlib import Path

import pytest

from scripts.audit_source_acquisition_priority import audit, derive


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "source-acquisition-priority.csv"
COMMON = ROOT / "mappings" / "case-management" / "breast-common-to-case-management.csv"
TASK = ROOT / "mappings" / "case-management" / "case-management-task-only-fields.csv"
CRITERIA = ROOT / "mappings" / "case-management" / "case-management-population-criteria.csv"
SOURCES = ROOT / "mappings" / "publication" / "source-traceability-register.csv"


def expected_rows():
    return derive(COMMON, TASK, CRITERIA, SOURCES)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_priority_register_is_complete_exact_and_machine_derived():
    report = audit(REGISTER, expected_rows())
    assert report == {
        "gate_scope": "source-acquisition-priority-integrity",
        "fact_count": 52,
        "priority_counts": {"P0": 42, "P1": 4, "P2": 6},
        "criterion_referenced_fact_count": 45,
        "priority_register_integrity_gate": "pass",
        "priority_is_sequence_not_optionality": True,
    }


def test_a_hand_edited_priority_cannot_downgrade_a_release_critical_fact(tmp_path):
    rows = read_rows(REGISTER)
    target = next(row for row in rows if row["fact_id"] == "CM-BC-024")
    assert target["priority"] == "P0"
    target["priority"] = "P2"
    altered = tmp_path / "priority.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="stale derived fields for CM-BC-024"):
        audit(altered, expected_rows())


def test_all_priorities_remain_required_for_production_publication():
    rows = read_rows(REGISTER)
    assert {row["release_requirement"] for row in rows} == {
        "required-before-production-publication"
    }
    assert {row["priority"] for row in rows} == {"P0", "P1", "P2"}
