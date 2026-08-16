from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any

from .importers import import_case_json
from .models import CaseRecord, ReviewStatus


JSON_SOURCE_CANDIDATES: dict[str, dict[str, str]] = {
    "D010": {"channel": "basic.fields", "source": "cblMetastasis + txbMetastasisDesc"},
    "D027": {"channel": "treatment_plan.text", "source": "care-plan breast surgery fact"},
    "D029": {"channel": "treatment_plan.text", "source": "care-plan axillary surgery fact"},
    "D030": {"channel": "basic.fields", "source": "cblHisType"},
    "D037": {"channel": "basic.fields", "source": "cblMetastasis + txbMetastasisDesc"},
    "TM01": {"channel": "treatment_plan.text", "source": "ordered care-plan treatment facts"},
    "TM02": {"channel": "treatment_plan.text", "source": "care-plan treatment category"},
    "TM05": {"channel": "treatment_plan.text", "source": "care-plan regimen or drug fact"},
    "TM06": {"channel": "treatment_plan.text", "source": "care-plan other drug text"},
    "TM07": {"channel": "treatment_plan.text", "source": "care-plan radiation site fact"},
    "TM08": {"channel": "treatment_plan.text", "source": "care-plan other site text"},
}


def _recommended_source(tag: str) -> str:
    if tag in {"HOSPID", "ID", "BIRTHDAY"}:
        return "organization-and-patient-master"
    if tag.startswith("P") or tag in {"DIAG_TYPE", "LATERALITY"}:
        return "eligibility-intake-or-patient-administration"
    if tag in {"D001", "D002", "D025", "D026", "D058", "D059"}:
        return "diagnosis-or-cancer-registry"
    clinical_staging = {
        "D003", "D005", "D006", "D007", "D008", "D009", "D010",
        "D011", "D012", "D013", "D036", "D037",
        *(f"D{number:03d}" for number in range(60, 66)),
    }
    if tag in clinical_staging:
        return "imaging-clinical-exam-or-staging"
    if tag in {"D027", "D029"}:
        return "operative-record"
    if tag.startswith("D"):
        return "pathology-laboratory-or-molecular-report"
    if tag.startswith("TM"):
        return "executed-treatment-record"
    if tag.startswith("T"):
        return "follow-up-or-outcome-record"
    return "manual-source-review"


def analyze_care_plan_qbc_coverage(
    source_dir: Path,
    qbc_fields_path: Path,
    catalog_path: Path,
) -> dict[str, Any]:
    """Measure aggregate Care Plan JSON support for QBC without exposing case values."""
    qbc_contract = json.loads(qbc_fields_path.read_text(encoding="utf-8"))
    qbc_fields = qbc_contract["fields"]
    qbc_by_tag = {field["tag"]: field for field in qbc_fields}
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    declared_controls: dict[str, set[str]] = defaultdict(set)
    for field in catalog["fields"]:
        for target in field.get("qbc_targets", []):
            declared_controls[target].add(field["control_key"])

    source_paths = sorted(source_dir.glob("*.case.json"))
    value_records: Counter[str] = Counter()
    not_applicable_records: Counter[str] = Counter()
    method_records: dict[str, Counter[str]] = defaultdict(Counter)
    value_field_counts: list[int] = []
    diagnosis_types: Counter[str] = Counter()
    diagnosis_assessments: Counter[str] = Counter()
    parse_failures = 0

    for index, source_path in enumerate(source_paths, start=1):
        case = CaseRecord(case_id=f"aggregate-case-{index:04d}")
        try:
            import_case_json(source_path, case)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            parse_failures += 1
            continue
        value_field_counts.append(
            sum(
                candidate.value is not None
                for tag, candidate in case.candidates.items()
                if tag in qbc_by_tag
            )
        )
        if case.diagnosis_type:
            diagnosis_types[case.diagnosis_type] += 1
        diagnosis_assessments[case.diagnosis_type_assessment] += 1
        for tag, candidate in case.candidates.items():
            if tag not in qbc_by_tag:
                continue
            if candidate.status == ReviewStatus.NOT_APPLICABLE:
                not_applicable_records[tag] += 1
            if candidate.value is not None:
                value_records[tag] += 1
                method_records[tag][candidate.method.value] += 1

    parsed_records = len(source_paths) - parse_failures
    rows: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    unresolved_source_review_counts: Counter[str] = Counter()
    for field in qbc_fields:
        tag = field["tag"]
        produced = value_records[tag] > 0
        all_not_applicable = (
            parsed_records > 0 and not_applicable_records[tag] == parsed_records
        ) or (
            tag == "TM04"
            and parsed_records > 0
            and sum(diagnosis_types.values()) == parsed_records
            and diagnosis_types.get("3", 0) == 0
        )
        if produced:
            coverage_status = "adapter-produced-in-january-sample"
        elif all_not_applicable:
            coverage_status = "not-applicable-in-january-sample"
        elif tag in JSON_SOURCE_CANDIDATES:
            coverage_status = "json-source-candidate-unmapped"
        elif tag.startswith("T") and not tag.startswith("TM"):
            coverage_status = "no-follow-up-event-in-source"
        else:
            coverage_status = "unresolved-source-review"
        status_counts[coverage_status] += 1
        source_recommendation = None
        if coverage_status == "unresolved-source-review":
            source_recommendation = _recommended_source(tag)
            unresolved_source_review_counts[source_recommendation] += 1
        rows.append(
            {
                "tag": tag,
                "label": field["label"],
                "section": field["section"],
                "always_required": field["always_required"],
                "required_when": field["required_when"],
                "declared_care_plan_controls": sorted(declared_controls.get(tag, set())),
                "value_records": value_records[tag],
                "not_applicable_records": not_applicable_records[tag],
                "production_methods": dict(sorted(method_records[tag].items())),
                "coverage_status": coverage_status,
                "json_source_candidate": JSON_SOURCE_CANDIDATES.get(tag),
                "candidate_additional_source": source_recommendation,
            }
        )

    produced_tags = {tag for tag, count in value_records.items() if count > 0}
    declared_tags = set(declared_controls)
    return {
        "analysis_kind": "aggregate-care-plan-json-to-qbc-coverage",
        "relationship": "parallel-task-reconciliation-only",
        "contains_case_identifiers": False,
        "contains_source_values": False,
        "source_files": len(source_paths),
        "parsed_records": parsed_records,
        "parse_failures": parse_failures,
        "qbc_field_count": len(qbc_fields),
        "declared_care_plan_mapping_field_count": len(declared_tags),
        "produced_in_january_field_count": len(produced_tags),
        "not_produced_in_january_field_count": len(qbc_fields) - len(produced_tags),
        "value_field_count_per_record": {
            "min": min(value_field_counts, default=0),
            "median": median(value_field_counts) if value_field_counts else 0,
            "max": max(value_field_counts, default=0),
        },
        "diagnosis_type_counts": {
            "1": diagnosis_types.get("1", 0),
            "2": diagnosis_types.get("2", 0),
            "3": diagnosis_types.get("3", 0),
            "pending_review": diagnosis_assessments.get("pending_review", 0),
            "source_incomplete": diagnosis_assessments.get("source_incomplete", 0),
        },
        "produced_but_not_declared_in_catalog": sorted(produced_tags - declared_tags),
        "declared_but_not_produced_in_january": sorted(declared_tags - produced_tags),
        "coverage_status_counts": dict(sorted(status_counts.items())),
        "unresolved_source_review_counts": dict(
            sorted(unresolved_source_review_counts.items())
        ),
        "fields": rows,
    }
