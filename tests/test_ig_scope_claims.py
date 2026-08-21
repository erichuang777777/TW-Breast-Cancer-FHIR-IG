import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "mappings" / "publication" / "ig-scope-claim-register.csv"
DECISIONS = ROOT / "mappings" / "publication" / "publication-scope-decision-register.csv"
CONFIG = ROOT / "ig" / "sushi-config.yaml"
COMMON_FSH = ROOT / "ig" / "input" / "fsh" / "breast-common-profiles.fsh"
ALL_FSH = ROOT / "ig" / "input" / "fsh"
CARE_PLAN = ROOT / "qbc_workbench" / "data" / "cancer_care_plan_field_catalog.json"
CARE_PLAN_SOURCE_AUDIT = ROOT / "ig" / "input" / "pagecontent" / "care-plan-source-audit.md"
QBC_AUDIT = ROOT / "outputs" / "qbc_conformance" / "field_rule_audit.csv"
APPROVALS = ROOT / "outputs" / "qbc_ig_mapping" / "qbc_mapping_approval_register.csv"
TWPAS_COMMON = ROOT / "mappings" / "twpas" / "breast-common-to-twpas-1.2.5.csv"
TWPAS_TASK = ROOT / "mappings" / "twpas" / "twpas-task-only-fields-1.2.5.csv"
MEASURES = ROOT / "mappings" / "publication" / "case-management-measure-audit.csv"
TCR_QUESTIONNAIRE = ROOT / "ig" / "input" / "resources" / "Questionnaire-tcr-breast-longform.json"
README = ROOT / "README.md"
TASK_INDEX = ROOT / "ig" / "input" / "pagecontent" / "task-index.md"
TASK_TCR = ROOT / "ig" / "input" / "pagecontent" / "task-tcr.md"


def csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_claim_register_has_one_explicit_row_for_every_implemented_or_planned_scope():
    rows = csv_rows(CLAIMS)
    by_id = {row["claim_id"]: row for row in rows}
    assert {row["claim_id"] for row in rows} == {
        "IG-CORE", "IG-TWCORE", "IG-MCODE", "IG-ICHOM",
        "TASK-CAREPLAN", "TASK-QBC", "TASK-TWPAS", "TASK-CASE-MGMT",
        "TASK-TCR", "TASK-FUTURE",
    }
    assert len(rows) == 10
    assert all(row["allowed_claim"].strip() for row in rows)
    assert all(row["prohibited_claim"].strip() for row in rows)
    assert all(row["blocking_evidence"].strip() for row in rows)
    assert not any(row["evidence_status"] == "formal-release-ready" for row in rows)
    assert by_id["IG-TWCORE"]["relationship"] == "partial direct profile conformance"
    assert by_id["IG-MCODE"]["relationship"] == "semantic reference only"
    assert by_id["IG-ICHOM"]["relationship"] == "semantic reference only"
    assert by_id["TASK-QBC"]["evidence_status"] == "technical-pass-human-review-pending"
    assert by_id["TASK-TWPAS"]["evidence_status"] == "mapping-design-only"
    assert by_id["TASK-CASE-MGMT"]["evidence_status"] == "technical-pass-data-validation-blocked"
    assert by_id["TASK-TCR"]["evidence_status"] == "partial-codebook-draft"


def test_scope_decision_register_is_exactly_traceable_and_unsigned():
    claims = {row["claim_id"]: row for row in csv_rows(CLAIMS)}
    decisions = csv_rows(DECISIONS)
    assert len(decisions) == 10
    assert {row["claim_id"] for row in decisions} == set(claims)
    assert len({row["decision_id"] for row in decisions}) == 10
    expected_roles = {
        "IG-CORE": "normative", "IG-TWCORE": "informative",
        "IG-MCODE": "informative", "IG-ICHOM": "informative",
        "TASK-CAREPLAN": "informative", "TASK-QBC": "normative",
        "TASK-TWPAS": "informative", "TASK-CASE-MGMT": "normative",
        "TASK-TCR": "informative", "TASK-FUTURE": "excluded",
    }
    for row in decisions:
        claim = claims[row["claim_id"]]
        assert row["proposed_role"] == expected_roles[row["claim_id"]]
        assert row["scope"] == claim["scope"]
        assert row["claim_evidence_status"] == claim["evidence_status"]
        assert row["allowed_claim"] == claim["allowed_claim"]
        assert row["prohibited_claim"] == claim["prohibited_claim"]
        assert row["blocking_evidence"] == claim["blocking_evidence"]
        assert row["current_status"] == "pending-human-signoff"
        assert not row["decision"]
        assert not row["signer_name"]


def test_external_alignment_claims_match_actual_dependencies_and_profile_parents():
    config = CONFIG.read_text(encoding="utf-8")
    dependencies = config.split("dependencies:", 1)[1].split("resources:", 1)[0]
    all_fsh = "\n".join(path.read_text(encoding="utf-8") for path in ALL_FSH.glob("*.fsh"))
    assert "tw.gov.mohw.twcore: 1.0.0" in dependencies
    assert "mcode" not in dependencies.lower()
    assert "ichom" not in dependencies.lower()
    assert "tw.gov.mohw.nhi.pas" not in dependencies
    assert all_fsh.count("Parent: $TWCorePatient") == 1
    assert all_fsh.count("Parent: $TWCoreBundle") == 1
    assert "Profile: BreastCancerPatient\nParent: $TWCorePatient" in COMMON_FSH.read_text(encoding="utf-8")


def test_care_plan_claim_reports_the_actual_review_backlog():
    catalog = json.loads(CARE_PLAN.read_text(encoding="utf-8"))
    statuses = {}
    for field in catalog["fields"]:
        statuses[field["review_status"]] = statuses.get(field["review_status"], 0) + 1
    assert catalog["field_count"] == len(catalog["fields"]) == 223
    assert statuses == {
        "pending-field-review": 195,
        "pending-algorithm-review": 3,
        "implemented-partial": 25,
    }
    source_audit = CARE_PLAN_SOURCE_AUDIT.read_text(encoding="utf-8")
    assert "| 觀察到的唯一 control | 314 |" in source_audit
    assert "| 新增待盤點 control | 91 |" in source_audit


def test_qbc_claim_separates_technical_implementation_from_human_acceptance():
    fields = csv_rows(QBC_AUDIT)
    approvals = csv_rows(APPROVALS)
    assert len(fields) == 115
    assert all(row["technical_status"] == "implemented" for row in fields)
    assert all(row["clinical_review_status"] == "pending" for row in fields)
    assert len(approvals) == 14
    assert not any(row["Status"] == "approved" for row in approvals)


def test_twpas_claim_is_mapping_design_not_an_unimplemented_adapter_claim():
    assert len(csv_rows(TWPAS_COMMON)) == 12
    assert len(csv_rows(TWPAS_TASK)) == 15
    all_fsh = "\n".join(path.read_text(encoding="utf-8") for path in ALL_FSH.glob("*.fsh"))
    assert "Profile: PatientTWPAS" not in all_fsh
    assert "Profile: BundleTWPAS" not in all_fsh


def test_case_management_claim_cannot_exceed_its_measure_evidence():
    measures = csv_rows(MEASURES)
    assert len(measures) == 20
    assert all(row["fhir_conformance"] == "pass" for row in measures)
    assert all(row["cql_execution"].startswith("pass-synthetic") for row in measures)
    assert all(row["raw_source_mapping"] == "missing" for row in measures)
    assert all(row["independent_recalculation"] == "missing" for row in measures)
    assert all(row["golden_cohort"] == "missing" for row in measures)


def test_tcr_claim_distinguishes_verified_pending_and_non_coded_fields():
    questionnaire = json.loads(TCR_QUESTIONNAIRE.read_text(encoding="utf-8"))
    leaves = [item for group in questionnaire["item"] for item in group["item"]]
    verified = [item for item in leaves if item.get("answerValueSet")]
    pending = [
        item for item in leaves
        if any(ext["url"].endswith("tcr-codetable-pending") for ext in item.get("extension", []))
    ]
    non_coded = [item for item in leaves if item not in verified and item not in pending]
    assert len(leaves) == 99
    assert (len(verified), len(pending), len(non_coded)) == (48, 32, 19)


def test_human_facing_scope_language_does_not_overstate_task_completion():
    readme = README.read_text(encoding="utf-8")
    task_index = TASK_INDEX.read_text(encoding="utf-8")
    task_tcr = TASK_TCR.read_text(encoding="utf-8")
    assert "第一個完成欄位契約技術驗證" in readme
    assert "clinical review 與 VPN acceptance pending" in task_index
    assert "尚無正式 adapter output" in task_index
    assert "48 欄已有已驗證碼表" in task_tcr
    assert "32 欄" in task_tcr and "19 欄" in task_tcr
