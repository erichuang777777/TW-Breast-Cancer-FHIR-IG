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
    assert "PRIVATE-PATIENT" not in serialized
    by_tag = {row["tag"]: row for row in report["fields"]}
    assert by_tag["LATERALITY"]["value_records"] == 1
    assert by_tag["HOSPID"]["coverage_status"] == "additional-source-required"
    assert (
        by_tag["HOSPID"]["recommended_additional_source"]
        == "organization-and-patient-master"
    )


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
