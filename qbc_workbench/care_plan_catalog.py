from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .care_plan import CancerCarePlanRecord, parse_cancer_care_plan_json


FHIR_DESTINATIONS: dict[str, tuple[str, str]] = {
    "rblLocation": ("Condition", "Condition.bodySite"),
    "rblMenopause": ("Observation", "Observation.valueCodeableConcept"),
    "rb2HGrade1": ("Observation", "Observation.valueCodeableConcept"),
    "ddlClinicTGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "ddlClinicNGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "ddlClinicMGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "ddlPathTGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "ddlPathNGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "ddlPathMGeneral": ("Observation", "Observation.component.valueCodeableConcept"),
    "txbSize1": ("Observation", "Observation.valueQuantity"),
    "txb2EReceptor1": ("Observation", "Observation.value[x]"),
    "txb2PReceptor1": ("Observation", "Observation.value[x]"),
    "rb2Her1": ("Observation", "Observation.value[x]"),
    "rb2HerFISH1": ("Observation", "Observation.value[x]"),
    "rbl2Ki67": ("Observation", "Observation.value[x]"),
    "txb2Ki67": ("Observation", "Observation.valueQuantity"),
    "txbEReceptor": ("Observation", "Observation.value[x]"),
    "txbPReceptor": ("Observation", "Observation.value[x]"),
    "rblHer": ("Observation", "Observation.value[x]"),
    "rblHerFISH": ("Observation", "Observation.value[x]"),
    "rblKi67": ("Observation", "Observation.value[x]"),
    "txbKi67": ("Observation", "Observation.valueQuantity"),
}


def _destination(control_key: str, ownership: str) -> tuple[str, str]:
    if control_key in FHIR_DESTINATIONS:
        return FHIR_DESTINATIONS[control_key]
    if ownership == "derived":
        return "QuestionnaireResponse / Provenance", "QuestionnaireResponse.item / Provenance.entity"
    return "QuestionnaireResponse", "QuestionnaireResponse.item.answer.value[x]"


def build_field_catalog(record: CancerCarePlanRecord) -> dict[str, Any]:
    """Return a PHI-free inventory; source values and case identifiers are never copied."""
    grouped: dict[str, list[Any]] = defaultdict(list)
    for field in record.fields:
        grouped[field.control_name].append(field)

    fields: list[dict[str, Any]] = []
    for index, control_name in enumerate(sorted(grouped), start=1):
        occurrences = grouped[control_name]
        representative = occurrences[0]
        labels = sorted({field.label for field in occurrences if field.label})
        input_types = sorted({field.input_type for field in occurrences if field.input_type})
        resource, path = _destination(representative.control_key, representative.ownership)
        if representative.ownership == "shared":
            transformation = "Promote reviewed meaning to the breast-cancer common FHIR layer; map independently into each task"
            lossiness = "Task projections may be lossy; retain the reviewed common fact and source Provenance"
            status = "implemented-partial"
        elif representative.ownership == "derived":
            transformation = "Preserve displayed result; record derivation algorithm and version before promotion"
            lossiness = "Derivation lineage pending review"
            status = "pending-algorithm-review"
        else:
            transformation = "Preserve populated source answer without inventing QBC semantics"
            lossiness = "Lossless at source-response level; canonical FHIR promotion pending"
            status = "pending-field-review"

        fields.append(
            {
                "field_id": f"CCP-{index:03d}",
                "section": representative.section,
                "control_name": control_name,
                "control_key": representative.control_key,
                "input_types": input_types,
                "source_labels": labels,
                "ownership": representative.ownership,
                "qbc_targets": representative.qbc_targets,
                "fhir_resource": resource,
                "fhir_path": path,
                "transformation": transformation,
                "lossiness": lossiness,
                "review_status": status,
                "occurrence_count": len(occurrences),
            }
        )

    return {
        "catalog_version": "1.0.0-preview.1",
        "source_contract": "cancer_care_plan.schema.json",
        "source_schema_version": record.source_schema_version,
        "contains_phi": False,
        "privacy_note": "Generated from control metadata only; source values, reports, hashes and case identifiers are excluded.",
        "field_count": len(fields),
        "fields": fields,
    }


def catalog_from_private_json(path: Path) -> dict[str, Any]:
    record = parse_cancer_care_plan_json(path, "CATALOG-NO-CASE-ID")
    return build_field_catalog(record)
