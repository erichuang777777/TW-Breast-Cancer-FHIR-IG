from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal

from pydantic import BaseModel, Field


CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG"
PATIENT_PROFILE = f"{CANONICAL}/StructureDefinition/breast-cancer-patient"
CONDITION_PROFILE = f"{CANONICAL}/StructureDefinition/breast-cancer-primary-condition"
CARE_PLAN_PROFILE = f"{CANONICAL}/StructureDefinition/cancer-care-plan-task-care-plan"
QUESTIONNAIRE_RESPONSE_PROFILE = (
    f"{CANONICAL}/StructureDefinition/cancer-care-plan-task-questionnaire-response"
)
CARE_PLAN_BUNDLE_PROFILE = (
    f"{CANONICAL}/StructureDefinition/cancer-care-plan-task-bundle"
)
CARE_PLAN_BUNDLE_ID_SYSTEM = f"{CANONICAL}/sid/cancer-care-plan-bundle-id"
CARE_PLAN_PROVENANCE_PROFILE = (
    f"{CANONICAL}/StructureDefinition/cancer-care-plan-task-provenance"
)


# These controls appear in both task views. Clinical meaning belongs in the
# reusable breast-cancer FHIR layer; this table only supports field inventory
# and cross-task alignment checks. It does not make either task own the other.
CONTROL_QBC_ALIGNMENT_TARGETS: dict[str, tuple[str, ...]] = {
    "ddlReason": ("DIAG_TYPE",),
    "rblLocation": ("LATERALITY",),
    "rblMenopause": ("P05",),
    "rblHospital": ("D002",),
    "rb2HGrade1": ("D004",),
    "ddlClinicTGeneral": ("D005",),
    "ddlClinicNGeneral": ("D006",),
    "ddlClinicMGeneral": ("D007",),
    "txb2EReceptor1": ("D014", "D015"),
    "txb2PReceptor1": ("D016", "D017"),
    "rb2Her1": ("D018",),
    "rb2HerFISH1": ("D019",),
    "rbl2Ki67": ("D020",),
    "txb2Ki67": ("D021",),
    "rblHGrade": ("D031",),
    "ddlPathTGeneral": ("D032",),
    "ddlPathNGeneral": ("D033",),
    "ddlPathMGeneral": ("D034",),
    "txbSize1": ("D047",),
    "txbEReceptor": ("D048", "D049"),
    "txbPReceptor": ("D050", "D051"),
    "rblHer": ("D052",),
    "rblHerFISH": ("D053",),
    "rblKi67": ("D054",),
    "txbKi67": ("D055",),
}

DERIVED_CONTROLS = {
    "cbUnderStagingAuto",
    "txbAutoClinicGeneral",
    "txbAutoPathGeneral",
}


class CarePlanSourceField(BaseModel):
    section: str
    control_name: str
    control_key: str
    label: str | None = None
    input_type: str | None = None
    raw_value: str | None = None
    display_value: str | None = None
    checked: bool | None = None
    source_path: str
    ownership: Literal["shared", "care-plan-only", "derived"]
    qbc_targets: list[str] = Field(default_factory=list)

    def answer(self) -> str | None:
        if self.checked is False:
            return None
        if self.checked is True and self.label:
            return self.label
        return self.display_value or self.raw_value


class CancerCarePlanRecord(BaseModel):
    task_id: str = "cancer-care-plan"
    case_id: str
    source_schema_version: str
    source_sha256: str
    diagnosis_code: str | None = None
    scraped_at: str | None = None
    fields: list[CarePlanSourceField] = Field(default_factory=list)
    treatment_plan_text: str | None = None
    reference_report_texts: dict[str, str] = Field(default_factory=dict)


def _fhir_id(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\-.]", "-", value).strip("-.")
    candidate = cleaned or prefix
    if candidate == value and len(candidate) <= 64:
        return candidate

    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    stem_limit = 64 - len(digest) - 1
    stem = candidate[:stem_limit].rstrip("-.") or prefix[:stem_limit].strip("-.") or "id"
    return f"{stem}-{digest}"


def _control_key(name: str) -> str:
    parts = name.split("$")
    return parts[-2] if parts[-1].isdigit() and len(parts) > 1 else parts[-1]


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text and text != "請選擇" else None


def _ownership(control_key: str) -> Literal["shared", "care-plan-only", "derived"]:
    if control_key in DERIVED_CONTROLS:
        return "derived"
    if control_key in CONTROL_QBC_ALIGNMENT_TARGETS:
        return "shared"
    return "care-plan-only"


def parse_cancer_care_plan_json(path: Path, case_id: str) -> CancerCarePlanRecord:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("sections"), dict):
        raise ValueError("care-plan JSON must contain a sections object")
    basic = data["sections"].get("basic")
    if not isinstance(basic, dict) or not isinstance(basic.get("fields"), list):
        raise ValueError("care-plan JSON must contain sections.basic.fields")

    fields: list[CarePlanSourceField] = []
    for section_name, section in data["sections"].items():
        if not isinstance(section, dict):
            continue
        for index, field in enumerate(section.get("fields", [])):
            if not isinstance(field, dict) or not isinstance(field.get("name"), str):
                continue
            control_name = field["name"]
            control_key = _control_key(control_name)
            fields.append(
                CarePlanSourceField(
                    section=section_name,
                    control_name=control_name,
                    control_key=control_key,
                    label=_string(field.get("label")),
                    input_type=_string(field.get("type")),
                    raw_value=_string(field.get("value")),
                    display_value=_string(field.get("selected_text")),
                    checked=field.get("checked") if isinstance(field.get("checked"), bool) else None,
                    source_path=f"sections.{section_name}.fields[{index}]",
                    ownership=_ownership(control_key),
                    qbc_targets=list(CONTROL_QBC_ALIGNMENT_TARGETS.get(control_key, ())),
                )
            )

    treatment_section = data["sections"].get("treatment_plan", {})
    treatment_text = _string(treatment_section.get("text")) if isinstance(treatment_section, dict) else None
    report_section = data["sections"].get("reference_reports", {})
    report_texts: dict[str, str] = {}
    if isinstance(report_section, dict):
        if text := _string(report_section.get("text")):
            report_texts["combined"] = text
        for field in fields:
            if field.section == "reference_reports" and (answer := field.answer()):
                report_texts[field.control_key] = answer

    return CancerCarePlanRecord(
        case_id=case_id,
        source_schema_version=_string(data.get("schema_version")) or "unknown",
        source_sha256=hashlib.sha256(raw).hexdigest(),
        diagnosis_code=_string(data.get("diagnosis_code")),
        scraped_at=_string(data.get("scraped_at")),
        fields=fields,
        treatment_plan_text=treatment_text,
        reference_report_texts=report_texts,
    )


def _timestamp(value: str | None) -> str:
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()


def _entry(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "fullUrl": f"{CANONICAL}/{resource['resourceType']}/{resource['id']}",
        "resource": resource,
    }


def build_cancer_care_plan_bundle(record: CancerCarePlanRecord) -> dict[str, Any]:
    created = _timestamp(record.scraped_at)
    case_id = _fhir_id(record.case_id, "care-plan-case")
    patient_id = _fhir_id(f"patient-{case_id}", "care-plan-patient")
    condition_id = _fhir_id(f"condition-{case_id}", "care-plan-condition")
    response_id = _fhir_id(f"response-{case_id}", "care-plan-response")
    care_plan_id = _fhir_id(f"care-plan-{case_id}", "care-plan")
    provenance_id = _fhir_id(f"provenance-{case_id}", "care-plan-provenance")
    bundle_id = _fhir_id(f"cancer-care-plan-{case_id}", "cancer-care-plan")
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {"profile": [PATIENT_PROFILE]},
    }
    patient_entry = _entry(patient)
    condition = {
        "resourceType": "Condition",
        "id": condition_id,
        "meta": {"profile": [CONDITION_PROFILE]},
        "clinicalStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
        },
        "verificationStatus": {
            "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
        },
        "code": {"text": record.diagnosis_code or "Breast cancer diagnosis from care-plan source"},
        "subject": {"reference": patient_entry["fullUrl"]},
    }
    condition_entry = _entry(condition)

    answered_fields = [field for field in record.fields if field.answer()]
    if not answered_fields:
        raise ValueError("care-plan JSON must contain at least one populated source field")
    response_items = [
        {
            "linkId": _fhir_id(f"{field.section}-{index}-{field.control_key}", "item"),
            "text": field.label or field.control_key,
            "answer": [{"valueString": field.answer()}],
        }
        for index, field in enumerate(answered_fields, start=1)
    ]
    answered_report_keys = {
        field.control_key for field in answered_fields if field.section == "reference_reports"
    }
    for report_key, report_text in record.reference_report_texts.items():
        if report_key in answered_report_keys:
            continue
        response_items.append(
            {
                "linkId": _fhir_id(f"reference-reports-{report_key}", "reference-report"),
                "text": "Combined reference reports" if report_key == "combined" else report_key,
                "answer": [{"valueString": report_text}],
            }
        )

    response = {
        "resourceType": "QuestionnaireResponse",
        "id": response_id,
        "meta": {"profile": [QUESTIONNAIRE_RESPONSE_PROFILE]},
        "status": "completed",
        "subject": {"reference": patient_entry["fullUrl"]},
        "authored": created,
        "item": response_items,
    }
    response_entry = _entry(response)
    care_plan: dict[str, Any] = {
        "resourceType": "CarePlan",
        "id": care_plan_id,
        "meta": {"profile": [CARE_PLAN_PROFILE]},
        "status": "active",
        "intent": "plan",
        "category": [{"text": "Cancer care plan task"}],
        "subject": {"reference": patient_entry["fullUrl"]},
        "addresses": [{"reference": condition_entry["fullUrl"]}],
        "created": created,
        "author": {"display": "Cancer care plan source system"},
        "supportingInfo": [{"reference": response_entry["fullUrl"]}],
    }
    if record.treatment_plan_text:
        care_plan["activity"] = [
            {
                "detail": {
                    "status": "scheduled",
                    "description": record.treatment_plan_text,
                }
            }
        ]
    care_plan_entry = _entry(care_plan)
    provenance = {
        "resourceType": "Provenance",
        "id": provenance_id,
        "meta": {"profile": [CARE_PLAN_PROVENANCE_PROFILE]},
        "target": [
            {"reference": care_plan_entry["fullUrl"]},
            {"reference": response_entry["fullUrl"]},
        ],
        "recorded": created,
        "agent": [{"who": {"display": "Cancer care plan JSON importer"}}],
        "entity": [
            {
                "role": "source",
                "what": {"display": f"source-sha256:{record.source_sha256}"},
            }
        ],
    }

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"profile": [CARE_PLAN_BUNDLE_PROFILE]},
        "identifier": {
            "system": CARE_PLAN_BUNDLE_ID_SYSTEM,
            "value": bundle_id,
        },
        "type": "collection",
        "timestamp": created,
        "entry": [
            patient_entry,
            condition_entry,
            response_entry,
            care_plan_entry,
            _entry(provenance),
        ],
    }
