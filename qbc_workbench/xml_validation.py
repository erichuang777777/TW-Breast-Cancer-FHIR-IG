from __future__ import annotations

import hashlib
import re
from xml.etree.ElementTree import ParseError, fromstring

from .exporter import ROOT_TAGS, SEC01, SEC02, validate_filename
from .models import CaseRecord, FollowUpEvent, Method, TreatmentEvent
from .rules import ev, put
from .spec import field_specs
from .validation import ValidationIssue, validate_case


TOP_ORDER = {tag: index for index, tag in enumerate([*ROOT_TAGS, "SEC01", "SEC02", "TREATMENTS", "TRACES"])}


def _xml_issue(field: str, rule: str, message: str, severity: str = "error", location: str = "xml") -> ValidationIssue:
    return ValidationIssue(severity, field, rule, message, location)


def _ordered(issues: list[ValidationIssue], tags: list[str], rank: dict[str, int], location: str) -> None:
    known = [tag for tag in tags if tag in rank]
    if known != sorted(known, key=rank.get):
        issues.append(_xml_issue(location, "QBC-XML-ELEMENT-ORDER", "elements are not in the official QBC order"))


def _unique_children(issues: list[ValidationIssue], element, allowed: set[str], location: str) -> None:
    seen = set()
    for child in element:
        if child.tag not in allowed:
            issues.append(_xml_issue(child.tag, "QBC-XML-UNKNOWN-ELEMENT", f"unknown element under {location}"))
        if child.tag in seen:
            issues.append(_xml_issue(child.tag, "QBC-XML-DUPLICATE-ELEMENT", f"duplicate element under {location}"))
        seen.add(child.tag)


def parse_qbc_xml(data: bytes, filename: str | None = None) -> tuple[CaseRecord | None, list[ValidationIssue]]:
    issues: list[ValidationIssue] = []
    if not re.match(br'^<\?xml\s+version=["\']1\.0["\']\s+encoding=["\']Big5["\']\?>', data, re.I):
        issues.append(_xml_issue("XML", "QBC-XML-DECLARATION", "XML declaration must specify version 1.0 and Big5 encoding"))
    try:
        text = data.decode("big5")
    except UnicodeDecodeError as exc:
        return None, [*issues, _xml_issue("XML", "QBC-XML-BIG5", f"invalid Big5 byte sequence at byte {exc.start}")]
    try:
        root = fromstring(text)
    except ParseError as exc:
        return None, [*issues, _xml_issue("XML", "QBC-XML-WELLFORMED", str(exc))]
    if root.tag != "QBC":
        return None, [*issues, _xml_issue(root.tag, "QBC-XML-ROOT", "root element must be QBC")]
    cases = [child for child in root if child.tag == "CASE"]
    unknown_root = [child.tag for child in root if child.tag != "CASE"]
    for tag in unknown_root:
        issues.append(_xml_issue(tag, "QBC-XML-UNKNOWN-ELEMENT", "QBC may contain CASE elements only"))
    if len(cases) != 1:
        return None, [*issues, _xml_issue("CASE", "QBC-XML-CASE-COUNT", "this per-case workbench requires exactly one CASE element")]

    case_node = cases[0]
    top_tags = [child.tag for child in case_node]
    _unique_children(issues, case_node, set(TOP_ORDER), "CASE")
    _ordered(issues, top_tags, TOP_ORDER, "CASE")
    case = CaseRecord(case_id="xml-import")
    evidence = ev(filename or "memory.xml", "qbc_xml")

    for tag in ROOT_TAGS:
        node = case_node.find(tag)
        if node is not None and node.text not in (None, ""):
            put(case, tag, node.text, Method.STRUCTURED, evidence, "XML_IMPORT")
    for section_name, tags in [("SEC01", SEC01), ("SEC02", SEC02)]:
        section = case_node.find(section_name)
        if section is None:
            issues.append(_xml_issue(section_name, "QBC-XML-SECTION", f"{section_name} element is required"))
            continue
        rank = {tag: index for index, tag in enumerate(tags)}
        _unique_children(issues, section, set(tags), section_name)
        _ordered(issues, [child.tag for child in section], rank, section_name)
        for child in section:
            if child.tag in rank and child.text not in (None, ""):
                put(case, child.tag, child.text, Method.STRUCTURED, evidence, "XML_IMPORT")

    treatments_node = case_node.find("TREATMENTS")
    if treatments_node is not None:
        for index, node in enumerate(treatments_node):
            if node.tag != "TREATMENT":
                issues.append(_xml_issue(node.tag, "QBC-XML-UNKNOWN-ELEMENT", "TREATMENTS may contain TREATMENT elements only"))
                continue
            allowed = [f"TM{i:02d}" for i in range(1, 11)]
            _unique_children(issues, node, set(allowed), f"TREATMENT[{index}]")
            _ordered(issues, [child.tag for child in node], {tag: i for i, tag in enumerate(allowed)}, f"TREATMENT[{index}]")
            vals = {child.tag: child.text for child in node if child.text not in (None, "")}
            sequence = int(vals["TM01"]) if vals.get("TM01", "").isdigit() else 0
            case.treatments.append(TreatmentEvent(
                sequence=sequence, treatment_type=vals.get("TM02", ""), location=vals.get("TM03"),
                surgery_code=vals.get("TM04"), drug_codes=(vals.get("TM05") or "").split(",") if vals.get("TM05") else [],
                other_drug=vals.get("TM06"), site_codes=(vals.get("TM07") or "").split(",") if vals.get("TM07") else [],
                other_site=vals.get("TM08"), actual_start=vals.get("TM09"), actual_end=vals.get("TM10"),
            ))

    traces_node = case_node.find("TRACES")
    if traces_node is not None:
        for index, node in enumerate(traces_node):
            if node.tag != "TRACE":
                issues.append(_xml_issue(node.tag, "QBC-XML-UNKNOWN-ELEMENT", "TRACES may contain TRACE elements only"))
                continue
            allowed = [f"T{i:02d}" for i in range(1, 7)]
            _unique_children(issues, node, set(allowed), f"TRACE[{index}]")
            _ordered(issues, [child.tag for child in node], {tag: i for i, tag in enumerate(allowed)}, f"TRACE[{index}]")
            vals = {child.tag: child.text for child in node if child.text not in (None, "")}
            case.followups.append(FollowUpEvent(
                trace_date=vals.get("T01", ""), treatment_status=vals.get("T02"), followup_status=vals.get("T03"),
                transfer_date=vals.get("T04"), close_date=vals.get("T05"), death_date=vals.get("T06"),
            ))

    case.diagnosis_type = next((case.candidates[tag].value for tag in ["DIAG_TYPE"] if tag in case.candidates), None)
    case.laterality = next((case.candidates[tag].value for tag in ["LATERALITY"] if tag in case.candidates), None)
    if filename:
        if not validate_filename(filename):
            issues.append(_xml_issue("filename", "QBC-FILENAME", "must match QBC_<10-digit HOSPID>_<YYYMM>_<NNN>.xml"))
        else:
            expected_hospid = filename.split("_")[1]
            actual_hospid = case.candidates.get("HOSPID")
            if actual_hospid and actual_hospid.value != expected_hospid:
                issues.append(_xml_issue("HOSPID", "QBC-FILENAME-HOSPID", "does not match the HOSPID in the filename"))
    return case, issues


def _roundtrip_issues(original: CaseRecord, parsed: CaseRecord) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for tag in [*ROOT_TAGS, *SEC01, *SEC02]:
        expected = original.candidates.get(tag)
        expected_value = expected.value if expected and expected.value not in (None, "") and expected.status.value != "not_applicable" else None
        actual = parsed.candidates.get(tag)
        actual_value = actual.value if actual else None
        if expected_value != actual_value:
            issues.append(_xml_issue(tag, "QBC-XML-ROUNDTRIP", f"round-trip mismatch: expected {expected_value!r}, got {actual_value!r}"))
    if [item.model_dump(exclude={"evidence"}) for item in original.treatments] != [item.model_dump(exclude={"evidence"}) for item in parsed.treatments]:
        issues.append(_xml_issue("TREATMENTS", "QBC-XML-ROUNDTRIP", "treatment data changed during XML round-trip"))
    if [item.model_dump(exclude={"evidence"}) for item in original.followups] != [item.model_dump(exclude={"evidence"}) for item in parsed.followups]:
        issues.append(_xml_issue("TRACES", "QBC-XML-ROUNDTRIP", "follow-up data changed during XML round-trip"))
    return issues


def validate_xml_bytes(data: bytes, filename: str | None = None, expected_case: CaseRecord | None = None) -> dict:
    case, issues = parse_qbc_xml(data, filename)
    if case is not None:
        issues.extend(validate_case(case))
        if expected_case is not None:
            issues.extend(_roundtrip_issues(expected_case, case))
    unique = sorted(set(issues), key=lambda item: (item.severity, item.location, item.field, item.rule, item.message))
    return {
        "accepted": not any(item.severity == "error" for item in unique),
        "sha256": hashlib.sha256(data).hexdigest(),
        "errors": sum(item.severity == "error" for item in unique),
        "warnings": sum(item.severity == "warning" for item in unique),
        "issues": [item.as_dict() for item in unique],
    }


def validate_xml_file(path) -> dict:
    return validate_xml_bytes(path.read_bytes(), path.name)


def receive_qbc_xml(filename: str, data: bytes) -> dict:
    report = validate_xml_bytes(data, filename)
    return {
        "status": "accepted" if report["accepted"] else "rejected",
        "receipt_id": report["sha256"][:16],
        **report,
    }
