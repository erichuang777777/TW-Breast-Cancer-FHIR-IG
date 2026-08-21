import csv
import hashlib
from pathlib import Path

import pytest

from scripts.audit_criterion_resolution_decisions import audit, decision_complete


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "mappings" / "publication" / "criterion-resolution-decision-register.csv"
CROSSCHECK = ROOT / "mappings" / "publication" / "criterion-implementation-crosscheck.csv"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sign(
    row: dict[str, str], *, rule: str = "approved-rule", evidence_path: Path | None = None
) -> None:
    evidence_uri = "evidence/criterion-resolution.json"
    evidence_hash = "a" * 64
    if evidence_path is not None:
        evidence_path.write_text('{"decision":"approve"}\n', encoding="utf-8")
        evidence_uri = evidence_path.name
        evidence_hash = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    row.update({
        "current_status": "approved",
        "decision": "approve",
        "approved_rule_or_contract": rule,
        "signer_name": "Authorized owner",
        "signer_organization_title": "Hospital / committee chair",
        "decision_date": "2026-08-21",
        "evidence_uri_path": evidence_uri,
        "signed_artifact_sha256": evidence_hash,
    })


def test_register_covers_every_current_non_aligned_criterion_without_overclaim():
    assert audit(REGISTER, CROSSCHECK) == {
        "gate_scope": "all-current-non-aligned-criterion-resolution-decisions",
        "decision_count": 15,
        "decision_group_count": 10,
        "issue_class_counts": {
            "candidate-not-approved": 3,
            "conditional-data-contract": 2,
            "definition-contradiction": 1,
            "implemented-variant-unresolved": 3,
            "known-not-enforced": 2,
            "task-layer-only": 4,
        },
        "approved_decision_count": 0,
        "pending_decision_count": 15,
        "current_non_aligned_decision_count": 15,
        "production_allowed_decision_count": 0,
        "decision_register_integrity_gate": "pass",
        "criterion_resolution_gate": "block",
    }


def test_signoff_requires_rule_identity_date_evidence_and_hash():
    row = {
        "current_status": "approved",
        "decision": "approve",
        "approved_rule_or_contract": "written AND rule",
        "signer_name": "Committee chair",
        "signer_organization_title": "Hospital / cancer committee",
        "decision_date": "2026-08-21",
        "evidence_uri_path": "evidence/qi06.json",
        "signed_artifact_sha256": "",
    }
    assert not decision_complete(row)
    row["signed_artifact_sha256"] = "b" * 64
    assert decision_complete(row)


def test_stale_issue_statement_is_rejected(tmp_path):
    rows = read_rows(REGISTER)
    rows[0]["known_difference"] = "old issue text"
    altered = tmp_path / "decisions.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="baseline issue changed"):
        audit(altered, CROSSCHECK)


def test_pending_row_cannot_contain_unsigned_decision_data(tmp_path):
    rows = read_rows(REGISTER)
    rows[0]["approved_rule_or_contract"] = "quietly selected rule"
    altered = tmp_path / "decisions.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="pending row contains unsigned decision data"):
        audit(altered, CROSSCHECK)


def test_qi06_variant_rows_cannot_carry_contradictory_approvals(tmp_path):
    rows = read_rows(REGISTER)
    variants = [row for row in rows if row["decision_group"] == "QI-06-AGE-NODE-VARIANT"]
    for row in variants:
        sign(row, rule="written AND rule")
    variants[-1]["approved_rule_or_contract"] = "historical separate OR rule"
    altered = tmp_path / "decisions.csv"
    write_rows(altered, rows)
    with pytest.raises(ValueError, match="QI-06 variant rows disagree"):
        audit(altered, CROSSCHECK)


def test_all_signatures_cannot_bypass_live_technical_alignment(tmp_path):
    rows = read_rows(REGISTER)
    evidence = tmp_path / "criterion-resolution.json"
    for row in rows:
        sign(row, evidence_path=evidence)
    # The three QI-06 rows are one decision package and therefore share fields.
    for row in rows:
        if row["decision_group"] == "QI-06-AGE-NODE-VARIANT":
            row["approved_rule_or_contract"] = "written AND rule"
    altered = tmp_path / "decisions.csv"
    write_rows(altered, rows)
    report = audit(altered, CROSSCHECK)
    assert report["approved_decision_count"] == 15
    assert report["current_non_aligned_decision_count"] == 15
    assert report["production_allowed_decision_count"] == 0
    assert report["criterion_resolution_gate"] == "block"


def test_gate_has_a_strict_path_to_pass_after_live_resolution(tmp_path):
    decision_rows = read_rows(REGISTER)
    tracked = {row["criterion_id"] for row in decision_rows}
    evidence = tmp_path / "criterion-resolution.json"
    for row in decision_rows:
        sign(row, evidence_path=evidence)
        if row["decision_group"] == "QI-06-AGE-NODE-VARIANT":
            row["approved_rule_or_contract"] = "written AND rule"
    signed = tmp_path / "signed-decisions.csv"
    write_rows(signed, decision_rows)

    crosscheck_rows = read_rows(CROSSCHECK)
    for row in crosscheck_rows:
        if row["criterion_id"] in tracked:
            row["cql_alignment"] = "aligned-to-current-draft"
            row["publication_disposition"] = "production-publication-allowed"
    resolved_crosscheck = tmp_path / "resolved-crosscheck.csv"
    write_rows(resolved_crosscheck, crosscheck_rows)

    report = audit(signed, resolved_crosscheck)
    assert report["approved_decision_count"] == 15
    assert report["current_non_aligned_decision_count"] == 0
    assert report["production_allowed_decision_count"] == 15
    assert report["criterion_resolution_gate"] == "pass"
