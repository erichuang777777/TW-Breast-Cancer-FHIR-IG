import json
from pathlib import Path

from qbc_workbench.care_plan import (
    CARE_PLAN_BUNDLE_PROFILE,
    CARE_PLAN_PROFILE,
    CARE_PLAN_PROVENANCE_PROFILE,
    QUESTIONNAIRE_RESPONSE_PROFILE,
    build_cancer_care_plan_bundle,
    parse_cancer_care_plan_json,
)
from qbc_workbench.task_alignment import build_parallel_task_alignment_outputs


def synthetic_source() -> dict:
    prefix = "EligibleCase$pnlCancerPlan$ucPlnSheetEdit$ctl01$ucPlnSheetGeneral$pnlGeneralCancerPlan"
    return {
        "schema_version": "1.0.0",
        "scraped_at": "2026-01-15T08:00:00+08:00",
        "diagnosis_code": "SYNTHETIC-BREAST-CANCER",
        "sections": {
            "basic": {
                "fields": [
                    {
                        "name": f"{prefix}$ucGeneralCancerPlan$ucDiagnosisBC_Custom$rblLocation",
                        "type": "radio",
                        "label": "左側",
                        "checked": True,
                    },
                    {
                        "name": f"{prefix}$ucGeneralCancerPlan$ucBasicInfo_Custom$ddlReason",
                        "type": "select",
                        "selected_text": "初診斷或初次治療",
                    },
                    {
                        "name": f"{prefix}$ucGeneralCancerPlan$ucHistoryBC_Custom$cblFamilyHistory$0",
                        "type": "checkbox",
                        "label": "母親或姐妹得過乳癌",
                        "checked": True,
                    },
                    {
                        "name": f"{prefix}$ucGeneralCancerPlan$ucBasicInfo_Custom$ddlECOG",
                        "type": "select",
                        "selected_text": "1",
                    },
                ]
            },
            "reference_reports": {"fields": [], "text": "SYNTHETIC REPORT"},
            "treatment_plan": {"fields": [], "text": "SYNTHETIC TREATMENT PLAN"},
        },
    }


def write_source(tmp_path: Path) -> Path:
    path = tmp_path / "synthetic.case.json"
    path.write_text(json.dumps(synthetic_source(), ensure_ascii=False), encoding="utf-8")
    return path


def test_parser_classifies_shared_and_care_plan_only_fields(tmp_path):
    record = parse_cancer_care_plan_json(write_source(tmp_path), "SYNTHETIC-CASE")
    fields = {field.control_key: field for field in record.fields}

    assert fields["rblLocation"].ownership == "shared"
    assert fields["rblLocation"].qbc_targets == ["LATERALITY"]
    assert fields["cblFamilyHistory"].ownership == "care-plan-only"
    assert fields["cblFamilyHistory"].qbc_targets == []
    assert fields["ddlECOG"].ownership == "care-plan-only"
    assert record.treatment_plan_text == "SYNTHETIC TREATMENT PLAN"


def test_care_plan_bundle_preserves_extra_fields(tmp_path):
    record = parse_cancer_care_plan_json(write_source(tmp_path), "SYNTHETIC-CASE")
    bundle = build_cancer_care_plan_bundle(record)

    assert bundle["meta"]["profile"] == [CARE_PLAN_BUNDLE_PROFILE]
    resources = [entry["resource"] for entry in bundle["entry"]]
    care_plan = next(resource for resource in resources if resource["resourceType"] == "CarePlan")
    response = next(resource for resource in resources if resource["resourceType"] == "QuestionnaireResponse")
    assert care_plan["meta"]["profile"] == [CARE_PLAN_PROFILE]
    assert response["meta"]["profile"] == [QUESTIONNAIRE_RESPONSE_PROFILE]
    provenance = next(resource for resource in resources if resource["resourceType"] == "Provenance")
    assert provenance["meta"]["profile"] == [CARE_PLAN_PROVENANCE_PROFILE]
    answers = {item["text"]: item["answer"][0]["valueString"] for item in response["item"]}
    assert answers["母親或姐妹得過乳癌"] == "母親或姐妹得過乳癌"
    assert answers["ddlECOG"] == "1"
    assert care_plan["activity"][0]["detail"]["description"] == "SYNTHETIC TREATMENT PLAN"


def test_same_source_can_compare_parallel_task_outputs(tmp_path):
    outputs = build_parallel_task_alignment_outputs(write_source(tmp_path), "SYNTHETIC-CASE")
    response = next(
        entry["resource"]
        for entry in outputs.care_plan_check_bundle["entry"]
        if entry["resource"]["resourceType"] == "QuestionnaireResponse"
    )
    qbc_resources = [entry["resource"] for entry in outputs.qbc_check_bundle["entry"]]
    qbc_codes = {
        resource["code"]["coding"][0]["code"]
        for resource in qbc_resources
        if resource["resourceType"] == "Observation"
    }

    assert any(item["text"] == "母親或姐妹得過乳癌" for item in response["item"])
    assert outputs.relationship == "parallel-task-alignment-check"
    assert "母親或姐妹得過乳癌" not in json.dumps(outputs.qbc_check_bundle, ensure_ascii=False)
    assert outputs.qbc_check_bundle["resourceType"] == "Bundle"
    assert "D008" not in qbc_codes  # no TNM inputs were provided; the projection must not invent them


def test_bundle_rejects_a_source_without_populated_fields(tmp_path):
    source = synthetic_source()
    source["sections"]["basic"]["fields"] = []
    path = tmp_path / "empty.case.json"
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    record = parse_cancer_care_plan_json(path, "SYNTHETIC-CASE")
    try:
        build_cancer_care_plan_bundle(record)
    except ValueError as error:
        assert "at least one populated source field" in str(error)
    else:
        raise AssertionError("an empty QuestionnaireResponse must be rejected")


def test_all_generated_fhir_ids_fit_the_r4_length_limit(tmp_path):
    record = parse_cancer_care_plan_json(write_source(tmp_path), "X" * 100)
    bundle = build_cancer_care_plan_bundle(record)

    assert len(bundle["id"]) <= 64
    assert all(len(entry["resource"]["id"]) <= 64 for entry in bundle["entry"])


def test_care_plan_module_has_no_qbc_task_generator_dependency():
    source = Path("qbc_workbench/care_plan.py").read_text(encoding="utf-8")

    assert "from .fhir import" not in source
    assert "from .importers import" not in source
