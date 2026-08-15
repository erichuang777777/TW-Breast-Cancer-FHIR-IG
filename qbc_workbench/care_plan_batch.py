from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any
import json
import re
import unicodedata

from .care_plan import parse_cancer_care_plan_json


EXPECTED_RESOURCE_TYPES = {
    "Patient",
    "Condition",
    "QuestionnaireResponse",
    "CarePlan",
    "Provenance",
}
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/+-]{1,}|[\u3400-\u9fff]{2,}")


def _distribution(values: list[int]) -> dict[str, int | float]:
    if not values:
        return {"min": 0, "median": 0, "max": 0}
    return {"min": min(values), "median": median(values), "max": max(values)}


def _strings(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for nested in value.values():
            result.extend(_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            result.extend(_strings(nested))
    elif isinstance(value, (str, int, float, bool)):
        result.append(str(value))
    return result


def _tokens(value: Any) -> set[str]:
    text = unicodedata.normalize("NFKC", "\n".join(_strings(value))).lower()
    return {token for token in TOKEN_PATTERN.findall(text) if len(token) >= 2}


def _ratio(source: set[str], target: set[str]) -> float:
    return len(source & target) / len(source) if source else 1.0


def _bundle_issues(bundle: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if bundle.get("resourceType") != "Bundle" or bundle.get("type") != "collection":
        issues.append("not-collection-bundle")
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        return issues + ["missing-entry-array"]

    full_urls = [entry.get("fullUrl") for entry in entries if isinstance(entry, dict)]
    if len(full_urls) != len(set(full_urls)):
        issues.append("duplicate-full-url")
    resources = [entry.get("resource") for entry in entries if isinstance(entry, dict)]
    resources = [resource for resource in resources if isinstance(resource, dict)]
    resource_types = {resource.get("resourceType") for resource in resources}
    if resource_types != EXPECTED_RESOURCE_TYPES:
        issues.append("unexpected-resource-type-set")
    if any(not resource.get("id") or len(resource["id"]) > 64 for resource in resources):
        issues.append("invalid-resource-id")
    if not bundle.get("id") or len(bundle["id"]) > 64:
        issues.append("invalid-bundle-id")

    known_urls = set(full_urls)
    references: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            reference = value.get("reference")
            if isinstance(reference, str):
                references.append(reference)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(resources)
    if any(reference.startswith("http") and reference not in known_urls for reference in references):
        issues.append("unresolved-internal-reference")
    return sorted(set(issues))


def analyze_care_plan_batch(
    source_dir: Path,
    bundle_dir: Path,
    catalog_path: Path,
) -> dict[str, Any]:
    """Return aggregate-only batch evidence without case identifiers or source values."""
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_by_name = {field["control_name"]: field for field in catalog["fields"]}
    source_paths = sorted(source_dir.glob("*.case.json"))
    schema_versions: Counter[str] = Counter()
    field_counts: list[int] = []
    answer_counts: list[int] = []
    field_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "present_records": 0,
            "populated_records": 0,
            "unchecked_with_source_value_records": 0,
            "sections": set(),
            "control_keys": set(),
            "input_types": set(),
            "ownership": set(),
            "qbc_targets": set(),
        }
    )
    parse_failures = 0
    bundle_missing = 0
    bundle_invalid = 0
    bundle_issue_counts: Counter[str] = Counter()
    mapping_mismatches = 0
    treatment_plan_text_records = 0
    reference_report_text_records = 0
    table_token_coverage: dict[str, list[float]] = defaultdict(list)
    table_token_coverage_in_fields_or_text: dict[str, list[float]] = defaultdict(list)
    section_text_token_coverage: dict[str, list[float]] = defaultdict(list)
    table_tokens_not_in_bundle: dict[str, list[int]] = defaultdict(list)

    for source_path in source_paths:
        try:
            record = parse_cancer_care_plan_json(source_path, source_path.stem.removesuffix(".case"))
        except (ValueError, json.JSONDecodeError):
            parse_failures += 1
            continue
        raw_data = json.loads(source_path.read_text(encoding="utf-8-sig"))

        schema_versions[record.source_schema_version] += 1
        field_counts.append(len(record.fields))
        answered_fields = [field for field in record.fields if field.answer()]
        answer_counts.append(len(answered_fields))
        treatment_plan_text_records += int(bool(record.treatment_plan_text))
        reference_report_text_records += int(bool(record.reference_report_texts))

        seen_controls: set[str] = set()
        populated_controls: set[str] = set()
        unchecked_value_controls: set[str] = set()
        for field in record.fields:
            stats = field_stats[field.control_name]
            stats["sections"].add(field.section)
            stats["control_keys"].add(field.control_key)
            if field.input_type:
                stats["input_types"].add(field.input_type)
            stats["ownership"].add(field.ownership)
            stats["qbc_targets"].update(field.qbc_targets)
            seen_controls.add(field.control_name)
            if field.answer():
                populated_controls.add(field.control_name)
            if field.checked is False and (field.raw_value or field.display_value):
                unchecked_value_controls.add(field.control_name)
        for control_name in seen_controls:
            field_stats[control_name]["present_records"] += 1
        for control_name in populated_controls:
            field_stats[control_name]["populated_records"] += 1
        for control_name in unchecked_value_controls:
            field_stats[control_name]["unchecked_with_source_value_records"] += 1

        bundle_path = bundle_dir / f"{source_path.stem.removesuffix('.case')}.care-plan.fhir.json"
        if not bundle_path.exists():
            bundle_missing += 1
            continue
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            bundle_invalid += 1
            bundle_issue_counts["invalid-json"] += 1
            continue
        bundle_tokens = _tokens(bundle)
        raw_sections = raw_data.get("sections", {})
        if isinstance(raw_sections, dict):
            for section_name, section in raw_sections.items():
                if not isinstance(section, dict):
                    continue
                section_table_tokens = _tokens(section.get("tables", []))
                section_text_tokens = _tokens(section.get("text"))
                fields_or_text_tokens = _tokens(section.get("fields", [])) | section_text_tokens
                table_token_coverage[section_name].append(
                    _ratio(section_table_tokens, bundle_tokens)
                )
                table_token_coverage_in_fields_or_text[section_name].append(
                    _ratio(section_table_tokens, fields_or_text_tokens)
                )
                section_text_token_coverage[section_name].append(
                    _ratio(section_text_tokens, bundle_tokens)
                )
                table_tokens_not_in_bundle[section_name].append(
                    len(section_table_tokens - bundle_tokens)
                )
        issues = _bundle_issues(bundle)
        if issues:
            bundle_invalid += 1
            bundle_issue_counts.update(issues)

        response = next(
            (
                entry["resource"]
                for entry in bundle.get("entry", [])
                if entry.get("resource", {}).get("resourceType") == "QuestionnaireResponse"
            ),
            None,
        )
        answered_report_keys = {
            field.control_key for field in answered_fields if field.section == "reference_reports"
        }
        extra_report_count = sum(
            report_key not in answered_report_keys for report_key in record.reference_report_texts
        )
        expected_items = len(answered_fields) + extra_report_count
        if not response or len(response.get("item", [])) != expected_items:
            mapping_mismatches += 1

    field_rows: list[dict[str, Any]] = []
    for control_name, stats in sorted(field_stats.items()):
        catalog_field = catalog_by_name.get(control_name, {})
        field_rows.append(
            {
                "field_id": catalog_field.get("field_id"),
                "section": sorted(stats["sections"]),
                "control_key": sorted(stats["control_keys"]),
                "input_types": sorted(stats["input_types"]),
                "ownership": sorted(stats["ownership"]),
                "qbc_targets": sorted(stats["qbc_targets"]),
                "fhir_resource": catalog_field.get("fhir_resource"),
                "fhir_path": catalog_field.get("fhir_path"),
                "review_status": catalog_field.get("review_status", "not-in-catalog"),
                "present_records": stats["present_records"],
                "populated_records": stats["populated_records"],
                "unchecked_with_source_value_records": stats[
                    "unchecked_with_source_value_records"
                ],
            }
        )

    observed_names = set(field_stats)
    catalog_names = set(catalog_by_name)
    return {
        "analysis_kind": "aggregate-technical-structure-only",
        "contains_case_identifiers": False,
        "contains_source_values": False,
        "source_files": len(source_paths),
        "parsed_records": len(source_paths) - parse_failures,
        "parse_failures": parse_failures,
        "schema_versions": dict(sorted(schema_versions.items())),
        "source_field_count_per_record": _distribution(field_counts),
        "populated_field_count_per_record": _distribution(answer_counts),
        "observed_unique_controls": len(observed_names),
        "catalog_controls": len(catalog_names),
        "observed_not_in_catalog_count": len(observed_names - catalog_names),
        "catalog_not_observed_count": len(catalog_names - observed_names),
        "catalog_not_observed_field_ids": sorted(
            catalog_by_name[name]["field_id"] for name in catalog_names - observed_names
        ),
        "treatment_plan_text_records": treatment_plan_text_records,
        "reference_report_text_records": reference_report_text_records,
        "bundle_files": len(list(bundle_dir.glob("*.care-plan.fhir.json"))),
        "bundle_missing": bundle_missing,
        "bundle_invalid": bundle_invalid,
        "bundle_issue_counts": dict(sorted(bundle_issue_counts.items())),
        "mapping_item_count_mismatches": mapping_mismatches,
        "json_channel_to_fhir_coverage": {
            "table_token_coverage_by_section": {
                section: _distribution(values)
                for section, values in sorted(table_token_coverage.items())
            },
            "table_token_coverage_in_fields_or_text_by_section": {
                section: _distribution(values)
                for section, values in sorted(
                    table_token_coverage_in_fields_or_text.items()
                )
            },
            "section_text_token_coverage_by_section": {
                section: _distribution(values)
                for section, values in sorted(section_text_token_coverage.items())
            },
            "table_tokens_not_in_bundle_by_section": {
                section: _distribution(values)
                for section, values in sorted(table_tokens_not_in_bundle.items())
            },
        },
        "fields": field_rows,
    }
