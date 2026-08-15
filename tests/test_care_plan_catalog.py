import json
from pathlib import Path

from qbc_workbench.care_plan import CancerCarePlanRecord, CarePlanSourceField
from qbc_workbench.care_plan_catalog import build_field_catalog


def test_catalog_excludes_source_values_case_id_and_hash():
    record = CancerCarePlanRecord(
        case_id="PRIVATE-CASE-ID",
        source_schema_version="1.0",
        source_sha256="PRIVATE-SOURCE-HASH",
        fields=[
            CarePlanSourceField(
                section="basic",
                control_name="Form$rblLocation",
                control_key="rblLocation",
                label="Synthetic left",
                input_type="radio",
                raw_value="PRIVATE-SOURCE-VALUE",
                source_path="sections.basic.fields[0]",
                ownership="shared",
                qbc_targets=["LATERALITY"],
            )
        ],
    )

    catalog = build_field_catalog(record)
    serialized = str(catalog)

    assert catalog["contains_phi"] is False
    assert catalog["field_count"] == 1
    assert catalog["fields"][0]["fhir_path"] == "Condition.bodySite"
    assert "PRIVATE-CASE-ID" not in serialized
    assert "PRIVATE-SOURCE-HASH" not in serialized
    assert "PRIVATE-SOURCE-VALUE" not in serialized


def test_published_catalog_is_complete_and_contains_no_value_fields():
    path = Path("qbc_workbench/data/cancer_care_plan_field_catalog.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    prohibited = {"case_id", "source_sha256", "raw_value", "display_value", "answer", "chart"}

    assert catalog["field_count"] == 223
    assert len(catalog["fields"]) == 223
    assert catalog["contains_phi"] is False
    assert all(not prohibited.intersection(field) for field in catalog["fields"])
