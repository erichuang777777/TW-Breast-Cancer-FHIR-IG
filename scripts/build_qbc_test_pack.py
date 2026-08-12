from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qbc_workbench.exporter import export_case
from qbc_workbench.models import CaseRecord, FollowUpEvent, Method, TreatmentEvent
from qbc_workbench.rules import ev, put
from qbc_workbench.validation import validate_case
from qbc_workbench.xml_validation import receive_qbc_xml


OUT = ROOT / "outputs" / "qbc_test_pack"

POSTOP_VALUES = {
    "D027": "0", "D028": "0", "D029": "1", "D030": "2", "D031": "2",
    "D032": "T2", "D033": "N0", "D034": "M0", "D035": "StageⅡA",
    "D038": "0", "D040": "2", "D041": "0", "D043": "2", "D044": "0",
    "D047": "1.2", "D048": "0", "D050": "0", "D052": "0", "D054": "0",
    "D056": "0", "D057": "0",
}


def synthetic_case(diag: str, serial: int) -> CaseRecord:
    case = CaseRecord(case_id=f"SYNTHETIC-DIAG-{diag}", diagnosis_type=diag, laterality="L")
    values = {
        "HOSPID": "3501200000", "ID": f"Z00000000{serial}", "BIRTHDAY": "19700101",
        "DIAG_TYPE": diag, "LATERALITY": "L", "P01": f"合成個案{serial}", "P02": "0",
        "P03": "170.0", "P04": "65.0", "P07": "B123456789", "P08": "3" if diag == "3" else "1", "P09": "20260101",
    }
    if diag == "1": values.update(D025="20251201", D026="1", **POSTOP_VALUES)
    if diag == "2": values.update(D001="20251201", D011="1")
    if diag == "3": values.update(
        D058="20251201", D059="1", D060="T2", D061="N0", D062="M0", D063="StageⅡA",
        D064="T2", D065="N0", D066="M0", D067="StageⅡA", D068="1",
        D070="1", D071="1", D072="2", D073="1", D074="1", D075="2",
        D076="1", D077="10", D078="1", D079="10", D080="2", D081="1",
        D082="1", D083="10", D084="0", D085="0",
    )
    for tag, value in values.items():
        put(case, tag, value, Method.MANUAL, ev("synthetic-source.json", "synthetic"), "SYNTHETIC")
    if diag == "1":
        case.treatments.append(TreatmentEvent(sequence=1, treatment_type="1", location="1", actual_start="20260102"))
    elif diag == "2":
        case.treatments.append(TreatmentEvent(sequence=1, treatment_type="2", location="1", actual_start="20260102", actual_end="20260301"))
    else:
        case.treatments.append(TreatmentEvent(sequence=1, treatment_type="3", location="1", site_codes=["A1"], actual_start="20260102", actual_end="20260201"))
    case.followups.append(FollowUpEvent(trace_date="20270101", treatment_status="1", followup_status="1"))
    return case


def issue_report(case: CaseRecord) -> dict:
    issues = validate_case(case)
    return {"accepted": not any(item.severity == "error" for item in issues), "issues": [item.as_dict() for item in issues]}


def build() -> Path:
    golden = OUT / "golden"
    negative = OUT / "negative"
    golden.mkdir(parents=True, exist_ok=True)
    negative.mkdir(parents=True, exist_ok=True)
    manifest = {"notice": "All cases are fully synthetic.", "golden": [], "negative": []}
    for serial, diag in enumerate(["1", "2", "3"], 1):
        case = synthetic_case(diag, serial)
        filename = f"QBC_3501200000_11508_00{serial}.xml"
        xml, audit = export_case(case, golden, filename)
        receipt = receive_qbc_xml(filename, xml.read_bytes())
        manifest["golden"].append({"diagnosis_type": diag, "xml": str(xml.relative_to(OUT)).replace("\\", "/"), "audit": str(audit.relative_to(OUT)).replace("\\", "/"), "sha256": hashlib.sha256(xml.read_bytes()).hexdigest(), "mock_status": receipt["status"]})

    cases = []
    invalid_date = synthetic_case("2", 4); invalid_date.candidates["BIRTHDAY"].value = "20260230"; cases.append(("invalid_date", invalid_date))
    missing_other = synthetic_case("2", 5); put(missing_other, "D008", "StageⅣ", Method.MANUAL, ev("synthetic", "synthetic"), "SYNTHETIC"); put(missing_other, "D009", "12", Method.MANUAL, ev("synthetic", "synthetic"), "SYNTHETIC"); cases.append(("missing_other_description", missing_other))
    bad_treatment = synthetic_case("2", 6); bad_treatment.treatments[0].actual_end = "20260101"; cases.append(("treatment_end_before_start", bad_treatment))
    for name, case in cases:
        path = negative / f"{name}.report.json"
        report = issue_report(case)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["negative"].append({"name": name, "report": str(path.relative_to(OUT)).replace("\\", "/"), "accepted": report["accepted"]})
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


if __name__ == "__main__":
    print(build())
