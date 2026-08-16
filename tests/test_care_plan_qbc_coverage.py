import json
from pathlib import Path

from qbc_workbench.care_plan_qbc_coverage import analyze_care_plan_qbc_coverage
from qbc_workbench.importers import import_case_json
from qbc_workbench.models import CaseRecord


def test_qbc_coverage_report_is_aggregate_and_classifies_gaps(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source = {
        "schema_version": 1,
        "sections": {
            "basic": {
                "fields": [
                    {
                        "name": "Synthetic$rblLocation",
                        "type": "radio",
                        "label": "左側",
                        "value": "L",
                        "checked": True,
                    }
                ]
            },
            "reference_reports": {"fields": [], "text": ""},
            "treatment_plan": {"fields": [], "text": ""},
        },
    }
    private_name = "PRIVATE-PATIENT.case.json"
    (source_dir / private_name).write_text(json.dumps(source), encoding="utf-8")

    report = analyze_care_plan_qbc_coverage(
        source_dir,
        Path("qbc_workbench/data/qbc_fields.json"),
        Path("qbc_workbench/data/cancer_care_plan_field_catalog.json"),
    )
    serialized = json.dumps(report, ensure_ascii=False)

    assert report["source_files"] == 1
    assert report["parsed_records"] == 1
    assert report["qbc_field_count"] == 115
    assert report["contains_case_identifiers"] is False
    assert report["contains_source_values"] is False
    assert report["diagnosis_type_counts"]["pending_review"] == 1
    assert "PRIVATE-PATIENT" not in serialized
    by_tag = {row["tag"]: row for row in report["fields"]}
    assert by_tag["LATERALITY"]["value_records"] == 1
    assert by_tag["HOSPID"]["coverage_status"] == "unresolved-source-review"
    assert (
        by_tag["HOSPID"]["candidate_additional_source"]
        == "organization-and-patient-master"
    )
    assert by_tag["D025"]["coverage_status"] == "unresolved-source-review"
    assert by_tag["TM02"]["coverage_status"] == "json-source-candidate-unmapped"
    assert by_tag["T01"]["coverage_status"] == "no-follow-up-event-in-source"


def test_fish_source_options_map_only_actual_results(tmp_path: Path):
    fields = [
        {
            "name": "Synthetic$rb2Her1",
            "type": "select",
            "selected_text": "2+",
        },
        {
            "name": "Synthetic$rblHer",
            "type": "select",
            "selected_text": "2+",
        },
    ]
    for key, selected_value in (("rb2HerFISH1", "1"), ("rblHerFISH", "2")):
        for value in ("0", "1", "2"):
            fields.append(
                {
                    "name": f"Synthetic${key}",
                    "type": "radio",
                    "value": value,
                    "checked": value == selected_value,
                }
            )
    source = {
        "schema_version": 1,
        "sections": {
            "basic": {"fields": fields},
            "reference_reports": {"fields": [], "text": ""},
            "treatment_plan": {"fields": [], "text": ""},
        },
    }
    path = tmp_path / "synthetic.case.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.candidates["D019"].value == "1"
    assert case.candidates["D053"].value == "0"


def test_json_tables_and_unmapped_breast_controls_supply_qbc_candidates(tmp_path: Path):
    source = {
        "schema_version": 1,
        "sections": {
            "basic": {
                "tables": [
                    {
                        "index": 0,
                        "rows": [
                            ["姓名：", "合成病人"],
                            ["生日：", "2000/01/02"],
                            ["性別：", "F"],
                        ],
                    }
                ],
                "fields": [
                    {
                        "name": "Synthetic$ddlReason",
                        "type": "select",
                        "selected_text": "初診斷或初次治療",
                    },
                    {
                        "name": "Synthetic$cblHisType$0",
                        "type": "checkbox",
                        "label": "Invasive ductal carcinoma",
                        "checked": True,
                    },
                    {
                        "name": "Synthetic$rblMargin",
                        "type": "radio",
                        "label": "Negative",
                        "checked": True,
                    },
                    {
                        "name": "Synthetic$cblMetastasis$0",
                        "type": "checkbox",
                        "label": "Lung",
                        "checked": True,
                    },
                    *[
                        {
                            "name": f"Synthetic${key}",
                            "type": "select",
                            "selected_text": value,
                        }
                        for key, value in (
                            ("ddlClinicTGeneral", "4"),
                            ("ddlClinicNGeneral", "0"),
                            ("ddlClinicMGeneral", "1"),
                            ("ddlPathTGeneral", "4"),
                            ("ddlPathNGeneral", "0"),
                            ("ddlPathMGeneral", "1"),
                        )
                    ],
                ],
            },
            "reference_reports": {"fields": [], "text": ""},
            "treatment_plan": {
                "fields": [],
                "text": (
                    "計畫日期 2026/01/01 [抗癌治療]\n"
                    "計畫日期 2026/02/01 [手術]"
                ),
            },
        },
    }
    path = tmp_path / "synthetic.case.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.candidates["P01"].value == "合成病人"
    assert case.candidates["BIRTHDAY"].value == "20000102"
    assert case.candidates["P02"].value == "1"
    assert case.candidates["D003"].value == "2"
    assert case.candidates["D028"].value == "0"
    assert case.candidates["D009"].value == "5"
    assert case.candidates["D036"].value == "5"


def _write_diagnosis_type_source(
    tmp_path: Path, treatment_text: str, clinical_m: str = "0"
) -> Path:
    source = {
        "schema_version": 1,
        "sections": {
            "basic": {
                "fields": [
                    {
                        "name": "Synthetic$ddlReason",
                        "type": "select",
                        "selected_text": "初診斷或初次治療",
                    },
                    {
                        "name": "Synthetic$ddlClinicMGeneral",
                        "type": "select",
                        "selected_text": clinical_m,
                    },
                ]
            },
            "reference_reports": {"fields": [], "text": ""},
            "treatment_plan": {"fields": [], "text": treatment_text},
        },
    }
    path = tmp_path / "diagnosis-type.case.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    return path


def test_diagnosis_type_uses_treatment_order_instead_of_intake_reason(tmp_path: Path):
    path = _write_diagnosis_type_source(
        tmp_path,
        "計畫日期 2026/01/01 [手術]\n計畫日期 2026/02/01 [抗癌治療]",
    )
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.diagnosis_type == "1"
    assert case.candidates["DIAG_TYPE"].rule_id == "CARE_PLAN_SURGERY_FIRST"
    assert [fact.category for fact in case.care_plan_treatment_facts] == [
        "surgery",
        "systemic",
    ]
    assert case.care_plan_treatment_facts[0].plan_date == "20260101"


def test_diagnosis_type_is_two_when_systemic_treatment_precedes_surgery(tmp_path: Path):
    path = _write_diagnosis_type_source(
        tmp_path,
        "計畫日期 2026/01/01 [抗癌治療]\n計畫日期 2026/02/01 [手術]",
    )
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.diagnosis_type == "2"
    assert case.candidates["DIAG_TYPE"].rule_id == "CARE_PLAN_SYSTEMIC_BEFORE_SURGERY"


def test_diagnosis_type_is_three_for_systemic_only_m1(tmp_path: Path):
    path = _write_diagnosis_type_source(
        tmp_path, "計畫日期 2026/01/01 [抗癌治療]", clinical_m="1"
    )
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.diagnosis_type == "3"
    assert case.candidates["DIAG_TYPE"].rule_id == "CARE_PLAN_SYSTEMIC_ONLY_M1"


def test_diagnosis_type_remains_pending_when_rules_are_insufficient(tmp_path: Path):
    path = _write_diagnosis_type_source(
        tmp_path, "計畫日期 2026/01/01 [抗癌治療]", clinical_m="0"
    )
    case = CaseRecord(case_id="synthetic")

    import_case_json(path, case)

    assert case.diagnosis_type is None
    assert "DIAG_TYPE" not in case.candidates
