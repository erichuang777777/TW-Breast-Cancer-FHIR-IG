from qbc_workbench.fhir import (
    QBC_BUNDLE_PROFILE,
    QBC_FIELD_SYSTEM,
    QBC_OBSERVATION_PROFILE,
    QBC_PATIENT_PROFILE,
    QBC_PROVENANCE_PROFILE,
    build_bundle,
)
from qbc_workbench.models import CaseRecord, Method
from qbc_workbench.rules import ev, put


def test_bundle_declares_unofficial_qbc_profiles_and_resolvable_entries():
    case = CaseRecord(case_id="case with spaces")
    put(case, "ID", "Z000000000", Method.STRUCTURED, ev("synthetic.json", "json"), "test")
    put(case, "BIRTHDAY", "19700101", Method.STRUCTURED, ev("synthetic.json", "json"), "test")
    put(case, "P02", "1", Method.STRUCTURED, ev("synthetic.json", "json"), "test")
    put(case, "D008", "StageⅡA", Method.MANUAL, ev("synthetic.json", "json"), "test")

    bundle = build_bundle(case)

    assert bundle["meta"]["profile"] == [QBC_BUNDLE_PROFILE]
    assert bundle["identifier"]["value"] == "qbc-case-with-spaces"
    assert bundle["timestamp"].endswith("+00:00")
    assert all("fullUrl" in entry for entry in bundle["entry"])
    assert len({entry["fullUrl"] for entry in bundle["entry"]}) == len(bundle["entry"])

    resources = [entry["resource"] for entry in bundle["entry"]]
    patient = next(resource for resource in resources if resource["resourceType"] == "Patient")
    observation = next(resource for resource in resources if resource["resourceType"] == "Observation")
    provenance = next(resource for resource in resources if resource["resourceType"] == "Provenance")

    assert patient["meta"]["profile"] == [QBC_PATIENT_PROFILE]
    assert patient["gender"] == "female"
    assert observation["meta"]["profile"] == [QBC_OBSERVATION_PROFILE]
    assert observation["code"]["coding"][0]["system"] == QBC_FIELD_SYSTEM
    assert provenance["meta"]["profile"] == [QBC_PROVENANCE_PROFILE]
    assert provenance["target"][0]["reference"].endswith("/Observation/obs-case-with-spaces-D008")


def test_bundle_uses_unknown_gender_when_qbc_sex_is_absent():
    case = CaseRecord(case_id="synthetic-case")

    bundle = build_bundle(case)
    patient = bundle["entry"][0]["resource"]

    assert patient["gender"] == "unknown"
