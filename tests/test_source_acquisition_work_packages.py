import csv
from pathlib import Path

import pytest

from scripts.audit_source_acquisition_work_packages import (
    assignment_complete,
    audit,
    derive,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "source-acquisition-work-packages.csv"
PRIORITY = ROOT / "mappings" / "publication" / "source-acquisition-priority.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_work_packages_cover_all_52_facts_in_executable_batches():
    assert audit(REGISTER, derive(PRIORITY)) == {
        "gate_scope": "all-52-source-fact-acquisition-work-packages",
        "fact_count": 52,
        "work_package_count": 8,
        "batch_counts": {
            "B0-result-blockers": 10,
            "B1-cohort-rate": 31,
            "B2-release-provenance": 1,
            "B3-stratifiers": 4,
            "B4-support": 6,
        },
        "work_package_fact_counts": {
            "WP-01-PATIENT-ADMIN": 3,
            "WP-02-REGISTRY-STAGING": 8,
            "WP-03-PATHOLOGY": 8,
            "WP-04-SURGERY-PROCEDURE": 5,
            "WP-05-SYSTEMIC-THERAPY": 3,
            "WP-06-RADIOTHERAPY": 3,
            "WP-07-CASE-MANAGEMENT": 19,
            "WP-08-REPORTING-PROVENANCE": 3,
        },
        "confirmed_owner_assignment_count": 0,
        "unassigned_owner_count": 52,
        "work_package_integrity_gate": "pass",
        "owner_assignment_gate": "block",
    }


def test_blocking_fact_cannot_be_moved_to_a_later_batch(tmp_path):
    rows = read_rows(REGISTER)
    target = next(row for row in rows if row["fact_id"] == "CM-BC-024")
    assert target["acquisition_batch"] == "B0-result-blockers"
    target["acquisition_batch"] = "B4-support"
    altered = tmp_path / "work-packages.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="stale derived fields for CM-BC-024"):
        audit(altered, derive(PRIORITY))


def test_role_assignment_cannot_claim_confirmation_without_signed_evidence(tmp_path):
    rows = read_rows(REGISTER)
    target = rows[0]
    target["assignment_status"] = "confirmed"
    target["confirmed_owner_name"] = "Source owner"
    altered = tmp_path / "work-packages.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="confirmed assignment lacks signed evidence"):
        audit(altered, derive(PRIORITY))


def test_assignment_requires_identity_date_evidence_and_hash():
    row = {
        "assignment_status": "confirmed",
        "confirmed_owner_name": "Source owner",
        "confirmed_owner_organization_title": "Hospital / system owner",
        "assignment_date": "2026-08-21",
        "assignment_evidence_uri_path": "evidence/source-owner.json",
        "signed_assignment_sha256": "",
    }
    assert not assignment_complete(row)
    row["signed_assignment_sha256"] = "a" * 64
    assert assignment_complete(row)
