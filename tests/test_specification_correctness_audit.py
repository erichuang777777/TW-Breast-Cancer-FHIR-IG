import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
CATALOG = ROOT / "mappings" / "case-management" / "case-management-measure-catalog.csv"
CRITERIA = ROOT / "mappings" / "case-management" / "case-management-population-criteria.csv"
TERMINOLOGY = ROOT / "ig" / "input" / "fsh" / "case-management-terminology.fsh"
SPEC_AUDIT = ROOT / "SPECIFICATION_CORRECTNESS_AUDIT.md"
APPROVALS = (
    ROOT / "mappings" / "publication" / "case-management-measure-approval-register.csv"
)


def rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_measure_audit_covers_the_exact_measure_catalog():
    catalog_ids = {row["measure_id"] for row in rows(CATALOG)}
    audit_rows = rows(AUDIT)
    assert len(audit_rows) == 20
    assert {row["measure_id"] for row in audit_rows} == catalog_ids


def test_no_measure_is_overstated_as_clinically_release_ready():
    audit_rows = rows(AUDIT)
    assert all(row["fhir_conformance"] == "pass" for row in audit_rows)
    assert all(row["cql_execution"].startswith("pass-synthetic") for row in audit_rows)
    assert all(row["raw_source_mapping"] == "missing" for row in audit_rows)
    assert all(row["independent_recalculation"] == "missing" for row in audit_rows)
    assert all(row["golden_cohort"] == "missing" for row in audit_rows)
    assert all(row["current_verdict"] != "clinically-release-ready" for row in audit_rows)
    assert all(row["blocking_issue"].strip() and row["required_approval"].strip() for row in audit_rows)


def test_known_result_changing_gaps_are_explicit():
    by_id = {row["measure_id"]: row for row in rows(AUDIT)}
    assert by_id["bc-qi-03"]["draft_definition_alignment"] == "known-incomplete"
    assert "unresolved" in by_id["bc-qi-06"]["draft_definition_alignment"]
    assert by_id["bc-qr-04"]["cql_execution"] == "pass-synthetic-conditional"
    assert by_id["bc-qr-05"]["cql_execution"] == "pass-synthetic-candidate"
    assert "10-groups-versus-source-11" in by_id["bc-qr-17"]["draft_definition_alignment"]


def test_every_measure_has_one_traceable_pending_specification_decision():
    audit_rows = rows(AUDIT)
    audit_by_id = {row["measure_id"]: row for row in audit_rows}
    approval_rows = rows(APPROVALS)
    assert len(approval_rows) == 20
    assert {row["measure_id"] for row in approval_rows} == set(audit_by_id)
    assert len({row["approval_id"] for row in approval_rows}) == 20
    assert all(row["current_status"] == "pending-human-signoff" for row in approval_rows)
    assert all(not row["decision"] for row in approval_rows)
    assert all(not row["signed_artifact_sha256"] for row in approval_rows)
    for row in approval_rows:
        source = audit_by_id[row["measure_id"]]
        assert row["indicator_family"] == source["indicator_family"]
        assert row["known_issue"] == source["blocking_issue"]
        assert row["required_signer"] == source["required_approval"]
        assert row["decision_scope"].strip()
        assert row["acceptance_evidence"].strip()


def test_existing_criteria_risks_cannot_be_flattened_to_plain_alignment():
    risky_review = {"blocking-data-gap", "open-question", "proxy-in-use"}
    risky_python = {"not-implemented", "divergent", "not-evaluable", "manual-override"}
    risky_measures = {
        row["measure_id"]
        for row in rows(CRITERIA)
        if row["measure_id"] not in {"bc-qi-00", "bc-qr-00"}
        and (row["review_status"] in risky_review or row["python_status"] in risky_python)
    }
    by_id = {row["measure_id"]: row for row in rows(AUDIT)}
    assert risky_measures == {
        "bc-qi-02", "bc-qi-03", "bc-qi-04", "bc-qi-05", "bc-qi-06", "bc-qr-04", "bc-qr-05"
    }
    assert all(by_id[measure]["draft_definition_alignment"] != "aligned-to-draft" for measure in risky_measures)


def test_the_19_clinical_valuesets_are_still_explicitly_empty():
    text = TERMINOLOGY.read_text(encoding="utf-8")
    clinical_section = text.split("// 個管作業分類：院內行政代碼", 1)[0]
    blocks = clinical_section.split("ValueSet: ")[1:]
    assert len(blocks) == 19
    assert all("* include" not in block for block in blocks)


def test_human_readable_audit_states_the_two_distinct_thresholds():
    text = SPEC_AUDIT.read_text(encoding="utf-8")
    assert "驗證數字正確需要六種" in text
    assert "總共要八種控制" in text
    assert "Measure 規格具名核准完成：0/20" in text
    assert "可供院內臨床／品管正式發布：0/20" in text
