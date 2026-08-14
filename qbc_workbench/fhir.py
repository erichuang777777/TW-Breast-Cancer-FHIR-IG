from datetime import datetime, timezone
import os
import re

from .models import CaseRecord


QBC_CANONICAL = os.getenv("QBC_FHIR_CANONICAL", "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG").rstrip("/")
QBC_FIELD_SYSTEM = f"{QBC_CANONICAL}/CodeSystem/qbc-field"
QBC_PATIENT_ID_SYSTEM = f"{QBC_CANONICAL}/sid/qbc-patient-id"
QBC_BUNDLE_ID_SYSTEM = f"{QBC_CANONICAL}/sid/qbc-bundle-id"
QBC_PATIENT_PROFILE = f"{QBC_CANONICAL}/StructureDefinition/qbc-patient"
QBC_OBSERVATION_PROFILE = f"{QBC_CANONICAL}/StructureDefinition/qbc-raw-data-item-observation"
QBC_PROVENANCE_PROFILE = f"{QBC_CANONICAL}/StructureDefinition/qbc-provenance"
QBC_BUNDLE_PROFILE = f"{QBC_CANONICAL}/StructureDefinition/qbc-submission-bundle"

QBC_GENDER = {
    "0": "male",
    "1": "female",
    "2": "other",
    "3": "unknown",
}


def _fhir_id(value: str, prefix: str = "qbc") -> str:
    """Return a stable FHIR id containing only the characters allowed by R4."""
    cleaned = re.sub(r"[^A-Za-z0-9\-.]", "-", value).strip("-.")
    return (cleaned or prefix)[:64]


def _entry(resource: dict) -> dict:
    resource_type = resource["resourceType"]
    resource_id = resource["id"]
    return {
        "fullUrl": f"{QBC_CANONICAL}/{resource_type}/{resource_id}",
        "resource": resource,
    }


def build_bundle(case: CaseRecord):
    """Build the lossless, unofficial QBC IG collection Bundle."""
    created = datetime.now(timezone.utc).isoformat()
    patient_id = _fhir_id(case.case_id, "patient")
    patient = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {"profile": [QBC_PATIENT_PROFILE]},
        "identifier": [],
    }
    entries = [_entry(patient)]

    if (candidate := case.candidates.get("ID")) and candidate.value:
        patient["identifier"].append(
            {"system": QBC_PATIENT_ID_SYSTEM, "value": candidate.value}
        )
    if (candidate := case.candidates.get("BIRTHDAY")) and candidate.value and len(candidate.value) == 8:
        patient["birthDate"] = (
            f"{candidate.value[:4]}-{candidate.value[4:6]}-{candidate.value[6:]}"
        )
    gender_candidate = case.candidates.get("P02")
    patient["gender"] = QBC_GENDER.get(
        gender_candidate.value if gender_candidate else "", "unknown"
    )

    patient_reference = entries[0]["fullUrl"]
    for tag, candidate in sorted(case.candidates.items()):
        if not (tag.startswith("D") and candidate.value):
            continue

        observation_id = _fhir_id(f"obs-{patient_id}-{tag}", "observation")
        observation = {
            "resourceType": "Observation",
            "id": observation_id,
            "meta": {"profile": [QBC_OBSERVATION_PROFILE]},
            "status": "final",
            "code": {
                "coding": [{"system": QBC_FIELD_SYSTEM, "code": tag}],
                "text": candidate.display or tag,
            },
            "subject": {"reference": patient_reference},
            "valueString": candidate.value,
        }
        observation_entry = _entry(observation)
        entries.append(observation_entry)

        if candidate.evidence:
            provenance_id = _fhir_id(f"prov-{patient_id}-{tag}", "provenance")
            provenance = {
                "resourceType": "Provenance",
                "id": provenance_id,
                "meta": {"profile": [QBC_PROVENANCE_PROFILE]},
                "target": [{"reference": observation_entry["fullUrl"]}],
                "recorded": candidate.reviewed_at or created,
                "agent": [
                    {
                        "type": {"text": candidate.method.value},
                        "who": {"display": candidate.reviewed_by or "qbc-workbench"},
                    }
                ],
                "entity": [
                    {"role": "source", "what": {"display": evidence.source_file}}
                    for evidence in candidate.evidence
                ],
            }
            entries.append(_entry(provenance))

    bundle_id = _fhir_id(f"qbc-{case.case_id}", "qbc-bundle")
    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {"profile": [QBC_BUNDLE_PROFILE]},
        "identifier": {"system": QBC_BUNDLE_ID_SYSTEM, "value": bundle_id},
        "type": "collection",
        "timestamp": created,
        "entry": entries,
    }
