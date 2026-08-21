#!/usr/bin/env python3
"""Audit every common-fact mapping target against Publisher profile snapshots."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


CANONICAL_ROOT = (
    "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
    "StructureDefinition/"
)
REGISTER_COLUMNS = (
    "projection_id", "mapping_id", "alternative_index", "common_concept",
    "source_profile_expression", "target_path_expression", "projection_mode",
    "target_profile_id", "target_profile_canonical", "target_element_id",
    "target_element_path", "selected_choice_type", "datatype_child_path",
    "required_unit", "technical_status", "fact_coverage_status", "blocking_issue",
)
EXPECTED_MAPPING_IDS = {f"CM-BC-{number:03d}" for number in range(1, 26)} | {
    f"CM-BC-{number:03d}" for number in range(30, 39)
}
PROFILE_OVERRIDES = {
    ("CM-BC-025", "Procedure"): "breast-cancer-treatment-procedure",
    ("CM-BC-025", "MedicationRequest"): "breast-cancer-medication-request",
    ("CM-BC-035", "Procedure"): "breast-cancer-treatment-procedure",
    ("CM-BC-035", "MedicationRequest"): "breast-cancer-medication-request",
}
KNOWN_FACT_COVERAGE_GAPS = {
    "CM-BC-035": (
        "RadiotherapyCourseSummary is named as a source representation but has "
        "no local profile or target element alternative."
    ),
    "CM-BC-037": (
        "Encounter has no local profile and the EpisodeOfCare alternative has no "
        "target path for last-contact semantics."
    ),
    "CM-BC-038": (
        "EpisodeOfCare.period.start supplies a date but cannot establish that the "
        "episode belongs to the prior-year new-diagnosis cohort; an episode-scoped "
        "new-diagnosis discriminator and linkage rule are absent."
    ),
}
KNOWN_SEMANTIC_PROFILE_GAPS = {
    ("CM-BC-006", "Observation.valueCodeableConcept"): (
        "Pathological regional-node category (pN) is projected into the "
        "BreastCancerStageGroupObservation shell. That Profile is declared for "
        "stage group and does not constrain Observation.code to pN semantics; "
        "path resolution therefore cannot establish semantic conformance."
    ),
    ("CM-BC-007", "Observation.valueCodeableConcept"): (
        "Pathological primary-tumour category (pT) is projected into the "
        "BreastCancerStageGroupObservation shell. That Profile is declared for "
        "stage group and does not constrain Observation.code to pT semantics; "
        "path resolution therefore cannot establish semantic conformance."
    ),
    ("CM-BC-018", "Procedure.code"): (
        "A diagnostic core-needle biopsy is projected into "
        "BreastCancerTreatmentProcedure, whose declared scope is treatment. A "
        "dedicated diagnostic Procedure Profile or an explicitly reviewed broader "
        "Procedure contract is required."
    ),
    ("CM-BC-018", "Procedure.performedDateTime"): (
        "A diagnostic core-needle biopsy is projected into "
        "BreastCancerTreatmentProcedure, whose declared scope is treatment. A "
        "dedicated diagnostic Procedure Profile or an explicitly reviewed broader "
        "Procedure contract is required."
    ),
    ("CM-BC-020", "MedicationRequest.medicationCodeableConcept"): (
        "The measure requires therapy given, but MedicationRequest represents an "
        "order/request and cannot prove medication administration."
    ),
    ("CM-BC-020", "MedicationRequest.authoredOn"): (
        "MedicationRequest.authoredOn is the prescription authoring time, not the "
        "actual therapy start or administration time required by the measure."
    ),
    ("CM-BC-021", "MedicationRequest.medicationCodeableConcept"): (
        "The first-treatment rule requires therapy delivered, but "
        "MedicationRequest represents an order/request and cannot prove medication "
        "administration."
    ),
    ("CM-BC-021", "MedicationRequest.authoredOn"): (
        "MedicationRequest.authoredOn is the prescription authoring time, not the "
        "actual therapy start or administration time required by the measure."
    ),
    ("CM-BC-022", "MedicationRequest.medicationCodeableConcept"): (
        "The measure requires anti-HER2 therapy given, but MedicationRequest "
        "represents an order/request and cannot prove medication administration."
    ),
    ("CM-BC-022", "MedicationRequest.authoredOn"): (
        "MedicationRequest.authoredOn is the prescription authoring time, not the "
        "actual therapy start or administration time required by the measure."
    ),
    ("CM-BC-025", "MedicationRequest.performer"): (
        "MedicationRequest.performer is the intended performer of administration, "
        "not evidence of the organisation that actually performed treatment."
    ),
    ("CM-BC-035", "MedicationRequest.status"): (
        "MedicationRequest.status is the state of an order, not proof that "
        "curative-intent treatment actually started, finished, or stopped."
    ),
}
CHOICE_PATHS = (
    (re.compile(r"^Condition\.onsetDateTime$"), "Condition.onset[x]", "dateTime", False),
    (re.compile(r"^Observation\.valueQuantity$"), "Observation.value[x]", "Quantity", False),
    (re.compile(r"^Observation\.valueCodeableConcept$"), "Observation.value[x]", "CodeableConcept", False),
    (re.compile(r"^Procedure\.performedDateTime$"), "Procedure.performed[x]", "dateTime", False),
    (re.compile(r"^Procedure\.performedPeriod(?:\.(start|end))?$"), "Procedure.performed[x]", "Period", True),
    (re.compile(r"^DiagnosticReport\.effectiveDateTime$"), "DiagnosticReport.effective[x]", "dateTime", False),
    (re.compile(r"^MedicationRequest\.medicationCodeableConcept$"), "MedicationRequest.medication[x]", "CodeableConcept", False),
    (re.compile(r"^Patient\.deceasedDateTime$"), "Patient.deceased[x]", "dateTime", False),
)
DATATYPE_CHILDREN = {"Period": {"start", "end"}}


def read_mapping(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "mapping_id", "common_concept", "source_profile_or_resource",
        "target_path", "review_status",
    }
    if not rows or not required <= set(rows[0]):
        raise ValueError(f"{path}: missing required common mapping columns")
    ids = [row["mapping_id"] for row in rows]
    if len(rows) != 34 or set(ids) != EXPECTED_MAPPING_IDS or len(ids) != len(set(ids)):
        raise ValueError(f"{path}: expected exact 34 unique CM-BC mapping ids")
    if any(not row["target_path"].strip() for row in rows):
        raise ValueError(f"{path}: every mapping row requires target_path")
    return rows


def load_snapshots(directory: Path) -> dict[str, dict[str, object]]:
    if not directory.is_dir():
        raise ValueError(f"{directory}: Publisher snapshot directory does not exist")
    profiles: dict[str, dict[str, object]] = {}
    names: set[str] = set()
    for path in sorted(directory.glob("StructureDefinition-*.json")):
        try:
            resource = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON: {exc}") from exc
        if (
            resource.get("resourceType") != "StructureDefinition"
            or not str(resource.get("url", "")).startswith(CANONICAL_ROOT)
        ):
            continue
        profile_id = str(resource.get("id", ""))
        name = str(resource.get("name", ""))
        elements = resource.get("snapshot", {}).get("element", [])
        if not profile_id or not name or not isinstance(elements, list) or not elements:
            raise ValueError(f"{path}: local Publisher StructureDefinition lacks snapshot")
        if profile_id in profiles or name in names:
            raise ValueError(f"{path}: duplicate local profile id or name")
        profiles[profile_id] = resource
        names.add(name)
    if len(profiles) != 47:
        raise ValueError(f"{directory}: expected exact 47 local Publisher snapshots")
    return profiles


def unit_and_clean_path(expression: str) -> tuple[str, str]:
    match = re.search(r"\{([^{}]+)\}$", expression)
    return (expression, "") if not match else (
        expression[: match.start()], match.group(1)
    )


def element_types(element: dict[str, object]) -> set[str]:
    return {
        str(item.get("code")) for item in element.get("type", [])
        if isinstance(item, dict) and item.get("code")
    }


def preferred_element(
    elements: list[dict[str, object]], path: str
) -> dict[str, object] | None:
    matches = [element for element in elements if element.get("path") == path]
    return next((item for item in matches if item.get("id") == path), matches[0] if matches else None)


def resolve_element(
    profile: dict[str, object], expression: str
) -> tuple[dict[str, object], str, str, str]:
    """Return ElementDefinition, selected choice type, datatype child, and unit."""
    clean, unit = unit_and_clean_path(expression)
    elements = profile["snapshot"]["element"]
    element = preferred_element(elements, clean)
    if element:
        return element, "", "", unit

    slice_match = re.fullmatch(r"(.+)\[([^]]+)\]", clean)
    if slice_match:
        base, slice_name = slice_match.groups()
        matches = [
            item for item in elements
            if item.get("path") == base and item.get("sliceName") == slice_name
        ]
        if not matches:
            raise ValueError(f"slice {slice_name!r} does not exist at {base}")
        return matches[0], "", "", unit

    for pattern, normalized, selected_type, captures_child in CHOICE_PATHS:
        match = pattern.fullmatch(clean)
        if not match:
            continue
        element = preferred_element(elements, normalized)
        if not element:
            raise ValueError(f"choice base {normalized} does not exist")
        if selected_type not in element_types(element):
            raise ValueError(f"{normalized} does not allow selected type {selected_type}")
        child = (match.group(1) or "") if captures_child and match.groups() else ""
        if child and child not in DATATYPE_CHILDREN.get(selected_type, set()):
            raise ValueError(f"{selected_type}.{child} is not an audited datatype child")
        return element, selected_type, child, unit

    parts = clean.split(".")
    for stop in range(len(parts) - 1, 1, -1):
        ancestor_path = ".".join(parts[:stop])
        child = ".".join(parts[stop:])
        element = preferred_element(elements, ancestor_path)
        if not element:
            continue
        valid_types = [
            datatype for datatype in element_types(element)
            if child in DATATYPE_CHILDREN.get(datatype, set())
        ]
        if len(valid_types) == 1:
            return element, valid_types[0], child, unit
    raise ValueError(f"target expression {expression!r} does not resolve in snapshot")


def choose_profile(
    mapping: dict[str, str], expression: str,
    profiles: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    clean, _ = unit_and_clean_path(expression)
    resource_type = clean.split(".", 1)[0]
    override = PROFILE_OVERRIDES.get((mapping["mapping_id"], resource_type))
    if override:
        profile = profiles.get(override)
        if not profile:
            raise ValueError(f"configured target Profile {override} does not exist")
        declared = {
            token.strip() for token in re.split(",|\\|", mapping["source_profile_or_resource"])
        }
        if str(profile["name"]) not in declared and str(profile["type"]) not in declared:
            raise ValueError(
                f"{mapping['mapping_id']}: target Profile {profile['name']} is not "
                "represented by source_profile_or_resource"
            )
        return profile
    by_name = {str(profile["name"]): profile for profile in profiles.values()}
    profile = by_name.get(mapping["source_profile_or_resource"])
    return profile if profile and profile.get("type") == resource_type else None


def derive_rows(
    mappings: list[dict[str, str]], profiles: dict[str, dict[str, object]]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    mapping_ids = {row["mapping_id"] for row in mappings}
    for mapping in mappings:
        alternatives = [part.strip() for part in mapping["target_path"].split("|")]
        for index, expression in enumerate(alternatives, 1):
            row = {column: "" for column in REGISTER_COLUMNS}
            row.update({
                "projection_id": f"{mapping['mapping_id']}-T{index:02d}",
                "mapping_id": mapping["mapping_id"],
                "alternative_index": str(index),
                "common_concept": mapping["common_concept"],
                "source_profile_expression": mapping["source_profile_or_resource"],
                "target_path_expression": expression,
            })
            if mapping["source_profile_or_resource"] == "derived":
                dependencies = set(re.findall(r"CM-BC-\d{3}", expression))
                if len(dependencies) != 5 or not dependencies <= mapping_ids:
                    raise ValueError(
                        f"{mapping['mapping_id']}: derived rule must name five current mapping ids"
                    )
                row.update({
                    "projection_mode": "derived-rule",
                    "technical_status": "declared-derived-rule",
                    "fact_coverage_status": "complete-derived-rule",
                })
                result.append(row)
                continue

            profile = choose_profile(mapping, expression, profiles)
            if profile is None:
                row.update({
                    "projection_mode": "profile-or-related-resource-gap",
                    "technical_status": "blocked-no-exact-profile-element",
                    "fact_coverage_status": "blocked",
                    "blocking_issue": (
                        "No single local Profile and Publisher snapshot element are "
                        "declared for this target alternative."
                    ),
                })
                result.append(row)
                continue
            try:
                element, choice_type, child, unit = resolve_element(profile, expression)
            except ValueError as exc:
                row.update({
                    "projection_mode": "local-profile-element-gap",
                    "target_profile_id": str(profile["id"]),
                    "target_profile_canonical": str(profile["url"]),
                    "technical_status": "blocked-unresolved-profile-element",
                    "fact_coverage_status": "blocked",
                    "blocking_issue": str(exc),
                })
                result.append(row)
                continue
            row.update({
                "projection_mode": "local-profile-element",
                "target_profile_id": str(profile["id"]),
                "target_profile_canonical": str(profile["url"]),
                "target_element_id": str(element["id"]),
                "target_element_path": str(element["path"]),
                "selected_choice_type": choice_type,
                "datatype_child_path": child,
                "required_unit": unit,
                "technical_status": (
                    "resolved-profile-element-unit-policy-pending"
                    if unit else "resolved-profile-element"
                ),
                "fact_coverage_status": "unit-policy-pending" if unit else "complete",
                "blocking_issue": (
                    "Required unit is declared in mapping syntax but still requires "
                    "source-contract and clinical validation."
                    if unit else ""
                ),
            })
            result.append(row)

    row_gap_facts = {
        row["mapping_id"] for row in result
        if row["technical_status"].startswith("blocked-")
    }
    row_gap_messages = {
        mapping_id: list(dict.fromkeys(
            row["blocking_issue"] for row in result
            if row["mapping_id"] == mapping_id
            and row["technical_status"].startswith("blocked-")
            and row["blocking_issue"]
        ))
        for mapping_id in row_gap_facts
    }
    incomplete_facts = row_gap_facts | set(KNOWN_FACT_COVERAGE_GAPS)
    for row in result:
        if row["mapping_id"] not in incomplete_facts:
            continue
        row["fact_coverage_status"] = (
            "blocked" if row["technical_status"].startswith("blocked-") else "partial"
        )
        issues = [row["blocking_issue"]]
        issues.extend(row_gap_messages.get(row["mapping_id"], []))
        issues.append(KNOWN_FACT_COVERAGE_GAPS.get(row["mapping_id"], ""))
        row["blocking_issue"] = "; ".join(dict.fromkeys(filter(None, issues)))

    for row in result:
        semantic_issue = KNOWN_SEMANTIC_PROFILE_GAPS.get((
            row["mapping_id"], row["target_path_expression"]
        ))
        if not semantic_issue:
            continue
        if row["technical_status"].startswith("blocked-"):
            raise ValueError(
                f"{row['mapping_id']}: semantic Profile gap unexpectedly overlaps "
                "an unresolved target path"
            )
        row["technical_status"] = "resolved-profile-element-semantic-profile-gap"
        row["fact_coverage_status"] = "blocked-semantic-profile-gap"
        row["blocking_issue"] = "; ".join(
            dict.fromkeys(filter(None, (row["blocking_issue"], semantic_issue)))
        )
    if len(result) != 55 or len({row["projection_id"] for row in result}) != 55:
        raise ValueError("common mapping must produce exact 55 target alternatives")
    return result


def read_register(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REGISTER_COLUMNS:
            raise ValueError(f"{path}: expected exact columns {list(REGISTER_COLUMNS)}")
        rows = list(reader)
    if len(rows) != 55 or len({row["projection_id"] for row in rows}) != 55:
        raise ValueError(f"{path}: expected exact 55 unique projection rows")
    return rows


def write_register(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def audit(
    mapping_path: Path, register_path: Path, snapshot_directory: Path
) -> dict[str, object]:
    mappings = read_mapping(mapping_path)
    actual = derive_rows(mappings, load_snapshots(snapshot_directory))
    expected = read_register(register_path)
    if actual != expected:
        for index, (actual_row, expected_row) in enumerate(zip(actual, expected), 2):
            if actual_row != expected_row:
                changed = [
                    column for column in REGISTER_COLUMNS
                    if actual_row[column] != expected_row[column]
                ]
                raise ValueError(
                    f"projection register drift at CSV row {index} "
                    f"({actual_row['projection_id']}): changed columns={changed}"
                )
        raise ValueError("projection register row count/order drift")

    blocked_rows = [row for row in actual if row["technical_status"].startswith("blocked-")]
    semantic_gap_rows = [
        row for row in actual
        if row["technical_status"] == "resolved-profile-element-semantic-profile-gap"
    ]
    semantic_gap_facts = sorted({row["mapping_id"] for row in semantic_gap_rows})
    blocked_facts = sorted({
        row["mapping_id"] for row in actual
        if row["fact_coverage_status"] in {
            "blocked", "partial", "blocked-semantic-profile-gap"
        }
    })
    unit_rows = [row for row in actual if row["required_unit"]]
    resolved_rows = [row for row in actual if row["projection_mode"] == "local-profile-element"]
    derived = [row for row in actual if row["projection_mode"] == "derived-rule"]
    if (
        len(resolved_rows) != 49 or len(derived) != 1 or len(blocked_rows) != 5
        or len(unit_rows) != 3
        or len(semantic_gap_rows) != 12
        or semantic_gap_facts != [
            "CM-BC-006", "CM-BC-007", "CM-BC-018", "CM-BC-020",
            "CM-BC-021", "CM-BC-022", "CM-BC-025", "CM-BC-035"
        ]
        or blocked_facts != [
            "CM-BC-006", "CM-BC-007", "CM-BC-018", "CM-BC-020",
            "CM-BC-021", "CM-BC-022", "CM-BC-024", "CM-BC-025",
            "CM-BC-032", "CM-BC-034", "CM-BC-035", "CM-BC-037",
            "CM-BC-038"
        ]
    ):
        raise ValueError("projection classification drift requires explicit review")
    return {
        "gate_scope": "exact-common-fact-profile-and-element-projection",
        "mapping_fact_count": len(mappings),
        "target_alternative_count": len(actual),
        "resolved_local_profile_element_count": len(resolved_rows),
        "declared_derived_rule_count": len(derived),
        "blocked_target_alternative_count": len(blocked_rows),
        "semantic_profile_gap_alternative_count": len(semantic_gap_rows),
        "semantic_profile_gap_fact_count": len(semantic_gap_facts),
        "semantic_profile_gap_fact_ids": semantic_gap_facts,
        "unit_policy_pending_alternative_count": len(unit_rows),
        "blocked_projection_fact_count": len(blocked_facts),
        "blocked_projection_fact_ids": blocked_facts,
        "projection_register_integrity_gate": "pass",
        "projection_readiness_gate": "pass" if not (
            blocked_rows or semantic_gap_rows or unit_rows or blocked_facts
        ) else "block",
        "clinical_projection_correctness_gate": "not-assessed-requires-source-and-clinical-evidence",
        "maximum_supported_claim": "technical-path-inventory-not-clinical-correctness",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--publisher-snapshot-dir", type=Path, required=True)
    parser.add_argument("--write-register", action="store_true")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "readiness"), default="integrity")
    args = parser.parse_args()
    try:
        if args.write_register:
            rows = derive_rows(
                read_mapping(args.mapping), load_snapshots(args.publisher_snapshot_dir)
            )
            write_register(args.register, rows)
            print(f"Wrote mapping projection register: {len(rows)} alternatives")
            return 0
        report = audit(args.mapping, args.register, args.publisher_snapshot_dir)
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Mapping projection audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Mapping projections: {report['mapping_fact_count']} facts; "
        f"{report['target_alternative_count']} alternatives; "
        f"resolved={report['resolved_local_profile_element_count']}; "
        f"derived={report['declared_derived_rule_count']}; "
        f"unresolved={report['blocked_target_alternative_count']}; "
        f"semantic-gaps={report['semantic_profile_gap_alternative_count']}; "
        f"unit-pending={report['unit_policy_pending_alternative_count']}"
    )
    print(f"Projection integrity gate: {report['projection_register_integrity_gate']}")
    print(f"Projection readiness gate: {report['projection_readiness_gate']}")
    selected = {
        "integrity": "projection_register_integrity_gate",
        "readiness": "projection_readiness_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
