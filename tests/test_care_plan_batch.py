import json
from pathlib import Path

from qbc_workbench.care_plan import build_cancer_care_plan_bundle, parse_cancer_care_plan_json
from qbc_workbench.care_plan_batch import analyze_care_plan_batch


def test_batch_report_contains_only_aggregate_evidence(tmp_path: Path):
    source_dir = tmp_path / "source"
    bundle_dir = tmp_path / "bundles"
    source_dir.mkdir()
    bundle_dir.mkdir()
    source = {
        "schema_version": "synthetic-1",
        "sections": {
            "basic": {
                "fields": [
                    {
                        "name": "Synthetic$ddlReason",
                        "type": "select",
                        "selected_text": "SYNTHETIC ANSWER",
                    },
                    {
                        "name": "Synthetic$unchecked$0",
                        "type": "checkbox",
                        "value": "SENSITIVE-SYNTHETIC-VALUE",
                        "checked": False,
                    },
                ]
            },
            "reference_reports": {"fields": [], "text": "SYNTHETIC REPORT"},
            "treatment_plan": {"fields": [], "text": "SYNTHETIC PLAN"},
        },
    }
    source_path = source_dir / "PRIVATE-CASE.case.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    record = parse_cancer_care_plan_json(source_path, "PRIVATE-CASE")
    bundle = build_cancer_care_plan_bundle(record)
    (bundle_dir / "PRIVATE-CASE.care-plan.fhir.json").write_text(
        json.dumps(bundle), encoding="utf-8"
    )

    report = analyze_care_plan_batch(
        source_dir,
        bundle_dir,
        Path("qbc_workbench/data/cancer_care_plan_field_catalog.json"),
    )
    serialized = json.dumps(report, ensure_ascii=False)

    assert report["source_files"] == 1
    assert report["bundle_invalid"] == 0
    assert report["mapping_item_count_mismatches"] == 0
    assert report["contains_case_identifiers"] is False
    assert report["contains_source_values"] is False
    assert "PRIVATE-CASE" not in serialized
    assert "SENSITIVE-SYNTHETIC-VALUE" not in serialized
