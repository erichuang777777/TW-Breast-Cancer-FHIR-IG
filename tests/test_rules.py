import pytest

from qbc_workbench.models import CaseRecord
from qbc_workbench.rules import derive_stage,ev,extract_pathology,more_severe,put,severity_rank,stage_group
from qbc_workbench.models import Method
from qbc_workbench.validation import validate_case

def test_stage_rules():
    c=CaseRecord(case_id="x")
    for tag,value in [("D005","T2"),("D006","N0"),("D007","M0")]: put(c,tag,value,Method.STRUCTURED,ev("x","test"),"test")
    derive_stage(c,"D005","D006","D007","D008")
    assert c.candidates["D008"].value=="StageⅡA"

def test_pathology_node_parser_requires_review():
    c=CaseRecord(case_id="x")
    extract_pathology(c,"Lymph node, axillary, left, core biopsy, invasive carcinoma of no special type. involved/total: 7/13", "p.txt")
    assert c.candidates["D012"].value=="2"
    assert c.candidates["D013"].value=="1"
    assert c.candidates["D012"].status.value=="pending_review"
    assert c.candidates["D042"].value=="7" and c.candidates["D043"].value=="13"


# --- 專案決議 2026-08-13：較嚴重的定義為 Stage Ⅲ>Ⅱ>Ⅰ，同期別以腫瘤大小排序 ---

@pytest.mark.parametrize("stage,expected", [
    ("Stage 0", 0), ("StageⅠA", 1), ("StageⅠB", 1), ("StageⅡA", 2),
    ("StageⅡB", 2), ("StageⅢA", 3), ("StageⅢC", 3), ("StageⅣ", 4),
    ("StageX", None), ("", None), (None, None),
])
def test_stage_group_collapses_subgroups(stage, expected):
    assert stage_group(stage) == expected


def test_higher_stage_group_wins_regardless_of_tumour_size():
    # 期別優先於腫瘤大小：ⅢA 的 1.0cm 仍比 ⅡB 的 9.0cm 嚴重
    assert more_severe([("a", "StageⅢA", "1.0"), ("b", "StageⅡB", "9.0")]) == "a"


def test_same_stage_group_is_ordered_by_tumour_size():
    # 同期別（皆為 Ⅲ 群組，含不同次分期）改以腫瘤大小排序
    assert more_severe([("a", "StageⅢA", "2.0"), ("b", "StageⅢC", "5.5")]) == "b"


def test_unknown_stage_forces_manual_decision():
    assert more_severe([("a", "StageX", "5.0"), ("b", "StageⅡA", "1.0")]) is None


def test_identical_severity_forces_manual_decision():
    assert more_severe([("a", "StageⅡA", "3.0"), ("b", "StageⅡB", "3.0")]) is None


def test_missing_tumour_size_ranks_below_a_measured_one():
    assert severity_rank("StageⅡA", None) < severity_rank("StageⅡA", "0.5")


# --- 專案決議 2026-08-13：惡性葉狀瘤／肉瘤不適用一般乳癌 TNM 自動分期 ---

def _staged_case(**kwargs):
    case = CaseRecord(case_id="x", **kwargs)
    for tag, value in [("D032", "T2"), ("D033", "N0"), ("D034", "M0"), ("D035", "StageⅢB")]:
        put(case, tag, value, Method.MANUAL, ev("x", "test"), "test")
    return case


def _rules(case):
    return {issue.rule: issue.severity for issue in validate_case(case)}


def test_tnm_mismatch_is_an_error_for_ordinary_breast_cancer():
    assert _rules(_staged_case()).get("QBC-D035-TNM-CONSISTENCY") == "error"


def test_tnm_mismatch_is_only_a_warning_for_a_flagged_sarcoma():
    found = _rules(_staged_case(non_epithelial_tumor=True))
    assert found.get("QBC-D035-TNM-SARCOMA-EXCEPTION") == "warning"
    assert "QBC-D035-TNM-CONSISTENCY" not in found


def test_histology_other_also_triggers_the_sarcoma_exception():
    case = _staged_case()
    put(case, "D030", "8", Method.MANUAL, ev("x", "test"), "test")
    found = _rules(case)
    assert found.get("QBC-D035-TNM-SARCOMA-EXCEPTION") == "warning"
    assert "QBC-D035-TNM-CONSISTENCY" not in found


# --- 專案決議 2026-08-13：雙側必須各自建檔與上傳，須提醒使用者 ---

def test_bilateral_case_warns_that_the_counterpart_must_be_uploaded_separately():
    case = CaseRecord(case_id="L-001", laterality="L", bilateral_counterpart_case_id="R-001")
    issues = [i for i in validate_case(case) if i.rule == "QBC-FAQ-BILATERAL-TWO-RECORDS"]
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert "R-001" in issues[0].message


def test_bilateral_case_without_laterality_is_an_error():
    case = CaseRecord(case_id="L-001", bilateral_counterpart_case_id="R-001")
    assert _rules(case).get("QBC-BILATERAL-COUNTERPART") == "error"


def test_bilateral_counterpart_cannot_be_the_case_itself():
    case = CaseRecord(case_id="L-001", laterality="L", bilateral_counterpart_case_id="L-001")
    assert _rules(case).get("QBC-BILATERAL-COUNTERPART") == "error"

