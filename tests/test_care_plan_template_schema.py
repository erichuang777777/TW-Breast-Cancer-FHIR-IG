import json
from pathlib import Path

from jsonschema import Draft202012Validator


def test_synthetic_v2_care_plan_template_contract_is_valid():
    schema = json.loads(
        Path("qbc_workbench/data/cancer_care_plan_template.schema.json").read_text(
            encoding="utf-8"
        )
    )
    payload = {
        "schema_version": "2.0.0-draft",
        "template": {
            "canonical": "https://example.org/fhir/Questionnaire/synthetic-care-plan",
            "version": "0.1.0",
            "status": "draft",
        },
        "instance": {
            "instance_id": "synthetic-instance",
            "authored": "2026-01-01T00:00:00+08:00",
            "source_system": "synthetic-test",
            "subject_identifier": {
                "system": "https://example.org/synthetic-patient",
                "value": "SYNTHETIC",
            },
            "encounter_identifier": None,
            "author_identifier": None,
        },
        "sections": [
            {
                "link_id": "basic",
                "text": "Synthetic basic section",
                "items": [
                    {
                        "link_id": "tumor-laterality",
                        "control_name": "Synthetic$rblLocation",
                        "text": "Synthetic laterality",
                        "type": "choice",
                        "required": True,
                        "repeats": False,
                        "ownership": "shared",
                        "review_status": "reviewed",
                        "answer_options": [
                            {"code": "L", "display": "Synthetic left"},
                            {"code": "R", "display": "Synthetic right"},
                        ],
                        "answers": [
                            {
                                "value": "L",
                                "display": "Synthetic left",
                                "data_absent_reason": None,
                            }
                        ],
                        "enable_when": [],
                        "fhir_mappings": [
                            {
                                "target_layer": "breast-cancer-common",
                                "resource_type": "Condition",
                                "profile": None,
                                "path": "Condition.bodySite",
                                "transform": "reviewed-code-map",
                                "mapping_status": "reviewed",
                            }
                        ],
                    }
                ],
            }
        ],
    }

    Draft202012Validator(schema).validate(payload)
