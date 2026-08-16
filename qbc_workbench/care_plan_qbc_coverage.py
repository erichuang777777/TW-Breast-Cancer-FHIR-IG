from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median
from typing import Any

from .importers import import_case_json
from .models import CaseRecord, ReviewStatus


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
        for tag, candidate in case.candidates.items():
            if tag not in qbc_by_tag:
                continue
            if candidate.status == ReviewStatus.NOT_APPLICABLE:
                not_applicable_records[tag] += 1
            if candidate.value is not None:
                value_records[tag] += 1
                method_records[tag][candidate.method.value] += 1

    rows: list[dict[str, Any]] = []
    source_gap_counts: Counter[str] = Counter()
    for field in qbc_fields:
        tag = field["tag"]
        produced = value_records[tag] > 0
        source_recommendation = None if produced else _recommended_source(tag)
        if source_recommendation:
            source_gap_counts[source_recommendation] += 1
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
                "coverage_status": (
                    "produced-in-january-sample" if produced else "additional-source-required"
                ),
                "recommended_additional_source": source_recommendation,
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
        "parsed_records": len(source_paths) - parse_failures,
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
        "produced_but_not_declared_in_catalog": sorted(produced_tags - declared_tags),
        "declared_but_not_produced_in_january": sorted(declared_tags - produced_tags),
        "source_gap_counts": dict(sorted(source_gap_counts.items())),
        "fields": rows,
    }
