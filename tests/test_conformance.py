import csv
import re
from pathlib import Path

from qbc_workbench.exporter import export_case
from qbc_workbench.models import CaseRecord, FollowUpEvent, Method, TreatmentEvent
from qbc_workbench.rules import ev, put
from qbc_workbench.spec import field_specs, load_qbc_spec
from qbc_workbench.validation import validate_case
from qbc_workbench.xml_validation import receive_qbc_xml, validate_xml_bytes


POSTOP_VALUES = {
    "D027": "0", "D028": "0", "D029": "1", "D030": "2", "D031": "2",
    "D032": "T2", "D033": "N0", "D034": "M0", "D035": "StageⅡA",
    "D038": "0", "D040": "2", "D041": "0", "D043": "2", "D044": "0",
    "D047": "1.2", "D048": "0", "D050": "0", "D052": "0", "D054": "0",
    "D056": "0", "D057": "0",
}


def base_case(diag="2", sex="0"):
    case = CaseRecord(case_id="synthetic", diagnosis_type=diag, laterality="L")
    values = {
        "HOSPID": "3501200000", "ID": "Z000000000", "BIRTHDAY": "19700101",
        "DIAG_TYPE": diag, "LATERALITY": "L", "P01": "測試個案", "P02": sex,
        "P03": "160.5", "P04": "55.2", "P07": "B123456789", "P08": "1", "P09": "20260101",
    }
    if sex == "1": values["P05"] = "2"
    if diag == "1": values.update(D025="20251201", D026="1", **POSTOP_VALUES)
    if diag == "2": values.update(D001="20251201", D011="1")
    if diag == "3": values.update(
        D058="20251201", D059="1", D060="T2", D061="N0", D062="M0", D063="StageⅡA",
        D064="T2", D065="N0", D066="M0", D067="StageⅡA", D068="1",
        D070="1", D071="1", D072="2", D073="1", D074="1", D075="2",
        D076="1", D077="10", D078="1", D079="10", D080="2", D081="1",
        D082="1", D083="10", D084="0", D085="0",
    )
    for tag, value in values.items():
        put(case, tag, value, Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    if diag == "1":
        case.treatments.append(TreatmentEvent(sequence=1, treatment_type="1", location="1", actual_start="20260102"))
    return case


def errors(case):
    return {issue.rule for issue in validate_case(case) if issue.severity == "error"}


def test_machine_readable_spec_has_all_official_fields_and_source_hash():
    spec = load_qbc_spec()
    assert len(spec["fields"]) == 115
    assert len(spec["source"]["sha256"]) == 64
    assert field_specs()["D042"]["maximum"] == 99
    assert field_specs()["TM05"]["multi_select"] is True
    program_rules = {rule["rule_id"]: rule for rule in spec["program_rules"]}
    assert program_rules["QBC-FAQ-PREOP-HORMONE-3D-DIRECT-SURGERY"]["enforcement"] == "clinical-review"
    assert program_rules["QBC-FAQ-BILATERAL-ID-REWARD"]["enforcement"] == "payer-system-only"


def test_every_word_row_is_preserved_and_conditional_rows_are_traceable():
    spec = load_qbc_spec()
    fields = spec["fields"]
    assert len(fields) == 115
    assert all(field["source_rule"].strip() for field in fields)
    condition_words = ("才需填寫", "才需", "當", "若", "須填", "需填", "必填", "擇一", "不可", "僅")
    conditional = [field for field in fields if any(word in field["source_rule"] for word in condition_words)]
    assert len(conditional) >= 52
    assert not [(field["tag"], field["source_rule"]) for field in conditional if not field["rule_ids"]]

    audit_path = Path("outputs/qbc_conformance/field_rule_audit.csv")
    with audit_path.open(encoding="utf-8-sig", newline="") as handle:
        audit_rows = list(csv.DictReader(handle))
    assert len(audit_rows) == 115
    assert {row["tag"] for row in audit_rows} == {field["tag"] for field in fields}


def test_review_template_only_lists_local_interpretations_not_official_rules():
    """115 欄的規則是健保署公布的法定規格，不需要任何人核准；簽核表只列本專案補上的解讀。"""
    path = Path("outputs/qbc_conformance/clinical_review_template.csv")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert 0 < len(rows) < 20, "簽核表應只列本地解讀，不是逐欄列出 115 個官方規則"
    assert {row["decision"] for row in rows} <= {"pending", "resolved"}
    assert all(row["word_basis"] and row["local_interpretation"] for row in rows)
    assert all(row["reviewer_role"] for row in rows)
    assert all(row["decision_date"] == "" and row["reviewer_name"] == "" for row in rows), \
        "簽核欄位必須留空待具權責人員填寫，不得由程式預填"

    # 已決議者必須留下決議依據，避免日後無法追溯
    assert all(row["notes"] for row in rows if row["decision"] == "resolved")

    # 兩個區段規則的受影響欄位由 rule_ids 反查，須與實作一致
    by_id = {row["item_id"]: row for row in rows}
    assert by_id["QBC-TM02-SURGERY-POSTOP-REQUIRED"]["field_count"] == "19"
    assert by_id["QBC-DIAGTYPE3-RECURRENCE-REQUIRED"]["field_count"] == "20"


def test_word_derived_rules_are_verified_by_test_not_pending_human_review():
    """直接轉錄自 Word 的規則由來源 SHA-256 與自動化測試把關，不應標為待人工審查。"""
    path = Path("outputs/qbc_conformance/rule_coverage.csv")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    statuses = {row["clinical_review_status"] for row in rows}
    assert statuses <= {"verified-by-test", "needs-decision", "decided-by-project"}
    assert "pending" not in statuses

    verified = [row for row in rows if row["clinical_review_status"] == "verified-by-test"]
    assert len(verified) > len(rows) * 0.8, "絕大多數規則直接來自 Word，應由測試驗證而非人工簽核"

    # 需要決議的一定是本專案補的解讀，不會是純格式規則
    for row in rows:
        if row["clinical_review_status"] == "needs-decision":
            assert not row["rule_id"].startswith(("QBC-FORMAT-", "QBC-ENCODING-", "QBC-VALUESET"))


def test_all_six_explanation_sources_have_zero_unmapped_lines():
    import json
    summary = json.loads(Path("outputs/source_audit/coverage_summary.json").read_text(encoding="utf-8"))
    assert summary["source_count"] == 6
    assert summary["mapped_nonempty_lines"] >= 1400
    assert summary["unmapped_lines"] == 0


def test_every_enumerated_word_code_is_in_the_machine_value_set():
    code_pattern = re.compile(r"(?:^|[\n\s])([A-C]?\d{1,2}|X|L|R)[：:]")
    computed_stage_fields = {"D008", "D035", "D063", "D067"}
    for field in load_qbc_spec()["fields"]:
        source_codes = set(code_pattern.findall(field["source_rule"]))
        if source_codes:
            if field["tag"] in computed_stage_fields:
                assert any(rule.endswith("-TNM") for rule in field["rule_ids"])
                continue
            assert source_codes <= set(field["allowed_values"]), field["tag"]


def test_three_diagnosis_paths_can_pass_local_business_validation():
    assert not errors(base_case("1"))
    assert not errors(base_case("2"))
    assert not errors(base_case("3"))


def test_format_values_and_conditional_rules_are_rejected():
    case = base_case("2", "1")
    case.candidates["BIRTHDAY"].value = "20260230"
    case.candidates["P08"].value = "9"
    case.candidates.pop("P05")
    rules = errors(case)
    assert "QBC-FORMAT-DATE" in rules
    assert "QBC-VALUESET" in rules
    assert "QBC-P05-FEMALE" in rules


def test_biomarker_other_and_node_dependencies():
    case = base_case("2")
    for tag, value in [("D014", "1"), ("D009", "12"), ("D008", "StageⅣ"), ("D038", "1"), ("D039", "4"), ("D040", "3")]:
        put(case, tag, value, Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    rules = errors(case)
    assert "QBC-D015-ER" in rules
    assert "QBC-D010-OTHER" in rules
    assert "QBC-D039-LE-D040" in rules


def test_treatment_and_followup_dependencies_and_date_order():
    case = base_case("2")
    case.treatments.append(TreatmentEvent(sequence=1, treatment_type="3", location="1", site_codes=["A5"], actual_start="20260201", actual_end="20260131"))
    case.followups.append(FollowUpEvent(trace_date="20270101", treatment_status="5"))
    rules = errors(case)
    assert "QBC-TM10-DATE-ORDER" in rules
    assert "QBC-TM08-OTHER" in rules
    assert "QBC-T06-DEATH" in rules


def test_neoadjuvant_surgery_requires_response_and_hospid_is_ten_digits():
    case = base_case("2")
    case.candidates["HOSPID"].value = "ABC"
    case.treatments.append(TreatmentEvent(sequence=1, treatment_type="1", location="1", actual_start="20260201"))
    rules = errors(case)
    assert "QBC-HOSPID-FORMAT" in rules
    assert "QBC-D024-NEOADJUVANT-SURGERY" in rules


def test_official_traces_example_from_the_xml_specification_is_accepted():
    """官方 XML 規格的 TRACES 範例必須原封不動通過本地驗證。

    來源：批次上傳格式說明的 TRACES 區段，兩筆追蹤。官方註記為
    「追蹤(每年至多填寫一次，最多5年)」與「追蹤年度(根據收案日滿一年後始可填寫)」。
    第二筆 T03=4（於追蹤中死亡）填 T06 而 T05 留空，對應主表 T06 的
    「※死亡視同結案」，證明結案日期不應被額外要求。
    """
    case = base_case("2")
    case.candidates["P09"].value = "20241025"  # 收案日，第一次追蹤的一年前
    case.followups = [
        FollowUpEvent(trace_date="20251025", treatment_status="2", followup_status="1"),
        FollowUpEvent(trace_date="20261025", treatment_status="2", followup_status="4", death_date="20261026"),
    ]
    assert not [issue for issue in validate_case(case) if issue.severity == "error"]

    # 同一份範例若把死亡日期抽掉，就必須被擋下來
    case.followups[1].death_date = None
    assert "QBC-T06-DEATH" in errors(case)


def test_only_one_followup_per_year():
    case = base_case("2")
    case.followups.extend([
        FollowUpEvent(trace_date="20270101", treatment_status="1", followup_status="1"),
        FollowUpEvent(trace_date="20271231", treatment_status="1", followup_status="1"),
    ])
    assert "QBC-T01-ANNUAL" in errors(case)


def test_recurrence_requires_every_field_from_d058_through_d085():
    case = base_case("3")
    case.candidates.pop("D085")
    recurrence_issues = [issue for issue in validate_case(case) if issue.rule == "QBC-DIAGTYPE3-RECURRENCE-REQUIRED"]
    assert {issue.field for issue in recurrence_issues} == {"D085"}


def test_recurrence_other_location_is_required_only_when_code_13_is_selected():
    case = base_case("3")
    assert "QBC-D069-OTHER" not in errors(case)
    case.candidates["D068"].value = "1,13"
    assert "QBC-D069-OTHER" in errors(case)
    put(case, "D069", "合成其他位置", Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    assert "QBC-D069-OTHER" not in errors(case)


def test_curative_surgery_requires_postoperative_fields_with_specific_conditions():
    case = base_case("1")
    case.candidates.pop("D027")
    assert "QBC-TM02-SURGERY-POSTOP-REQUIRED" in errors(case)
    put(case, "D027", "0", Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    assert "QBC-TM02-SURGERY-POSTOP-REQUIRED" not in errors(case)
    assert "D039" not in case.candidates  # D038=0, so positive count is correctly absent.


def test_neoadjuvant_axillary_examination_requires_exactly_one_path():
    case = base_case("2")
    case.candidates.pop("D011")
    assert "QBC-D011-D012-XOR" in errors(case)
    put(case, "D012", "2", Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    put(case, "D013", "0", Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    assert "QBC-D011-D012-XOR" not in errors(case)


def test_drug_code_group_must_match_treatment_type():
    case = base_case("2")
    case.treatments.append(TreatmentEvent(sequence=1, treatment_type="4", location="1", drug_codes=["B1"], actual_start="20260101", actual_end="20260102"))
    assert "QBC-TM05-TREATMENT-TYPE" in errors(case)


def test_field_specific_values_are_forbidden_outside_their_trigger():
    case = base_case("1")
    case.candidates["D044"].value = "1"
    put(case, "D045", "1", Method.MANUAL, ev("synthetic.json", "test"), "TEST")
    rules = errors(case)
    assert "QBC-D044-NODE-CONSISTENCY" in rules

    case = base_case("2")
    case.treatments.append(TreatmentEvent(
        sequence=1, treatment_type="4", location="1", drug_codes=["A1"],
        site_codes=["A1"], actual_start="20260101", actual_end="20260102",
    ))
    assert "QBC-TM07-RADIOTHERAPY" in errors(case)


def test_followup_conditional_dates_are_forbidden_without_trigger():
    case = base_case("2")
    case.followups.append(FollowUpEvent(
        trace_date="20270101", treatment_status="1", followup_status="1",
        transfer_date="20270102", close_date="20270103", death_date="20270104",
    ))
    rules = errors(case)
    assert {"QBC-T04-TRANSFER", "QBC-T05-CLOSE", "QBC-T06-DEATH"} <= rules


def test_followup_starts_after_one_year_and_is_limited_to_five_years():
    case = base_case("2")
    case.followups.append(FollowUpEvent(trace_date="20261231", treatment_status="1", followup_status="1"))
    assert "QBC-T01-AFTER-ONE-YEAR" in errors(case)
    case.followups = [
        FollowUpEvent(trace_date=f"{year}0101", treatment_status="1", followup_status="1")
        for year in range(2027, 2033)
    ]
    assert "QBC-T01-MAX-FIVE" in errors(case)


def test_death_requires_t06_but_not_t05_because_death_is_closure():
    case = base_case("2")
    case.followups.append(FollowUpEvent(trace_date="20270101", treatment_status="5", death_date="20270102"))
    rules = errors(case)
    assert "QBC-T06-DEATH" not in rules
    assert "QBC-T05-CLOSE" not in rules
    case.followups[0].death_date = "20270230"
    assert "QBC-FORMAT-DATE" in errors(case)


def test_big5_xml_roundtrip_and_mock_receiver(tmp_path: Path):
    case = base_case("1", "1")
    case.followups.append(FollowUpEvent(trace_date="20270101", treatment_status="1", followup_status="1"))
    xml, _ = export_case(case, tmp_path, "QBC_3501200000_11508_001.xml")
    report = receive_qbc_xml(xml.name, xml.read_bytes())
    assert report["status"] == "accepted"
    assert report["errors"] == 0


def test_xml_receiver_rejects_encoding_declaration_and_unknown_element():
    data = b'<?xml version="1.0" encoding="UTF-8"?><QBC><CASE><BAD>1</BAD></CASE></QBC>'
    report = validate_xml_bytes(data, "bad.xml")
    rules = {issue["rule"] for issue in report["issues"]}
    assert report["accepted"] is False
    assert "QBC-XML-DECLARATION" in rules
    assert "QBC-XML-UNKNOWN-ELEMENT" in rules
