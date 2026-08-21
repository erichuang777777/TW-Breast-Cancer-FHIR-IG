#!/usr/bin/env python3
"""Audit the exact FHIR resource inventory and generated IG manifest graph."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
PACKAGE_VERSION = "1.0.0-preview.1"
EXPECTED_COUNTS = {
    "Bundle": 3,
    "CapabilityStatement": 1,
    "CarePlan": 1,
    "CodeSystem": 60,
    "ConceptMap": 2,
    "Condition": 1,
    "DiagnosticReport": 3,
    "Encounter": 1,
    "EpisodeOfCare": 2,
    "ImplementationGuide": 1,
    "Library": 1,
    "Measure": 20,
    "MeasureReport": 1,
    "MedicationRequest": 1,
    "NamingSystem": 2,
    "Observation": 12,
    "Patient": 2,
    "Procedure": 2,
    "Provenance": 2,
    "Questionnaire": 1,
    "QuestionnaireResponse": 3,
    "Specimen": 1,
    "StructureDefinition": 46,
    "Task": 1,
    "ValueSet": 90,
}
DEFINITION_TYPES = {
    "CapabilityStatement",
    "CodeSystem",
    "ConceptMap",
    "ImplementationGuide",
    "Library",
    "Measure",
    "NamingSystem",
    "Questionnaire",
    "StructureDefinition",
    "ValueSet",
}
CANONICAL_TYPES = DEFINITION_TYPES - {"NamingSystem"}
MEASURE_IDS = {
    *(f"bc-qi-{number:02d}" for number in range(1, 7)),
    *(f"bc-qr-{number:02d}" for number in range(1, 6)),
    *(f"bc-qr-{number:02d}" for number in range(10, 19)),
}
REGISTER_COLUMNS = {
    "resource_type", "resource_id", "publication_role", "authoring_source",
}
LIBRARY_DECLARATION = re.compile(
    r"^library\s+([A-Za-z][A-Za-z0-9_]*)\s+version\s+'([^']+)'", re.MULTILINE
)


def load_resources(
    generated_dir: Path,
    manual_dir: Path,
) -> dict[tuple[str, str], tuple[dict[str, object], str]]:
    resources: dict[tuple[str, str], tuple[dict[str, object], str]] = {}
    for directory, source in (
        (generated_dir, "generated-fsh"),
        (manual_dir, "manual-json"),
    ):
        if not directory.is_dir():
            raise ValueError(f"{directory}: resource directory does not exist")
        for path in directory.glob("*.json"):
            resource = json.loads(path.read_text(encoding="utf-8-sig"))
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")
            if not resource_type or not resource_id:
                continue
            key = (str(resource_type), str(resource_id))
            if key in resources:
                raise ValueError(f"duplicate FHIR resource {key}")
            resources[key] = (resource, source)
    return resources


def audit(
    register_path: Path,
    generated_dir: Path,
    manual_dir: Path,
    cql_path: Path,
) -> dict[str, object]:
    with register_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = set(rows[0]) if rows else set()
    if columns != REGISTER_COLUMNS:
        raise ValueError(f"{register_path}: invalid columns")
    register_keys = [(row["resource_type"], row["resource_id"]) for row in rows]
    if len(rows) != 260 or len(set(register_keys)) != 260:
        raise ValueError(f"{register_path}: expected exactly 260 unique resources")

    resources = load_resources(generated_dir, manual_dir)
    actual_keys = set(resources)
    expected_keys = set(register_keys)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        raise ValueError(
            f"resource inventory mismatch; missing={missing}; unexpected={unexpected}"
        )
    counts = Counter(resource_type for resource_type, _ in actual_keys)
    if dict(sorted(counts.items())) != EXPECTED_COUNTS:
        raise ValueError(f"resource type counts {dict(counts)}, expected {EXPECTED_COUNTS}")

    for row in rows:
        key = (row["resource_type"], row["resource_id"])
        _, actual_source = resources[key]
        expected_role = (
            "publication-definition"
            if row["resource_type"] in DEFINITION_TYPES
            else "synthetic-example"
        )
        if row["publication_role"] != expected_role:
            raise ValueError(f"{key}: publication_role must be {expected_role}")
        if row["authoring_source"] != actual_source:
            raise ValueError(f"{key}: authoring_source must be {actual_source}")

    canonical_count = 0
    canonical_urls: dict[str, tuple[str, str]] = {}
    for key, (resource, _) in resources.items():
        resource_type, resource_id = key
        if resource_type not in CANONICAL_TYPES:
            continue
        canonical_count += 1
        expected_url = f"{CANONICAL}{resource_type}/{resource_id}"
        if resource.get("url") != expected_url:
            raise ValueError(f"{key}: canonical URL must be {expected_url}")
        if expected_url in canonical_urls:
            raise ValueError(f"duplicate canonical URL {expected_url}")
        canonical_urls[expected_url] = key
        if resource.get("status") != "draft" or resource.get("experimental") is not True:
            raise ValueError(f"{key}: must remain draft and experimental")
    if canonical_count != 222:
        raise ValueError(f"canonical resource count {canonical_count}, expected 222")

    ig_key = ("ImplementationGuide", "io.github.erichuang777777.breast-cancer")
    ig = resources[ig_key][0]
    if ig.get("version") != PACKAGE_VERSION or ig.get("fhirVersion") != ["4.0.1"]:
        raise ValueError(f"{ig_key}: package or FHIR version mismatch")
    manifest_entries = ig.get("definition", {}).get("resource", [])
    manifest_refs = [entry.get("reference", {}).get("reference") for entry in manifest_entries]
    expected_refs = {f"{kind}/{resource_id}" for kind, resource_id in actual_keys - {ig_key}}
    if len(manifest_refs) != 259 or len(set(manifest_refs)) != 259:
        raise ValueError("ImplementationGuide manifest must have 259 unique resource references")
    if set(manifest_refs) != expected_refs:
        raise ValueError("ImplementationGuide manifest does not match the exact resource inventory")

    examples = 0
    definitions = 1  # The ImplementationGuide does not reference itself.
    for entry in manifest_entries:
        reference = entry["reference"]["reference"]
        resource_type, resource_id = reference.split("/", 1)
        is_example = resource_type not in DEFINITION_TYPES
        if is_example:
            examples += 1
            example_boolean = entry.get("exampleBoolean") is True
            example_canonical = entry.get("exampleCanonical")
            if example_boolean == bool(example_canonical):
                raise ValueError(
                    f"{reference}: example must use exactly one valid example marker"
                )
            if example_canonical and example_canonical not in canonical_urls:
                raise ValueError(f"{reference}: unresolved exampleCanonical")
        else:
            definitions += 1
            if entry.get("exampleBoolean") is not False or entry.get("exampleCanonical"):
                raise ValueError(f"{reference}: definition is incorrectly marked as example")
    if (definitions, examples) != (224, 36):
        raise ValueError(
            f"publication roles definitions={definitions}, examples={examples}; expected 224/36"
        )

    capability = resources[
        ("CapabilityStatement", "BreastCancerCommunityCapabilityStatement")
    ][0]
    if (
        capability.get("version") != PACKAGE_VERSION
        or capability.get("fhirVersion") != "4.0.1"
        or capability.get("kind") != "requirements"
    ):
        raise ValueError("CapabilityStatement version, FHIR version, or kind mismatch")
    for rest in capability.get("rest", []):
        for supported in rest.get("resource", []):
            for profile_url in supported.get("supportedProfile", []):
                profile_key = canonical_urls.get(profile_url)
                if not profile_key or profile_key[0] != "StructureDefinition":
                    raise ValueError(f"CapabilityStatement unresolved supportedProfile {profile_url}")
                profile = resources[profile_key][0]
                if profile.get("type") != supported.get("type"):
                    raise ValueError(
                        f"CapabilityStatement type mismatch for supportedProfile {profile_url}"
                    )

    library_key = ("Library", "BreastCancerCaseManagement")
    library = resources[library_key][0]
    cql = cql_path.read_text(encoding="utf-8")
    declaration = LIBRARY_DECLARATION.search(cql)
    if not declaration:
        raise ValueError(f"{cql_path}: missing CQL library declaration")
    if (library.get("name"), library.get("version")) != declaration.groups():
        raise ValueError(f"{library_key}: name/version does not match CQL declaration")
    if library.get("content") != [{"id": "ig-loader-BreastCancerCaseManagement.cql"}]:
        raise ValueError(f"{library_key}: CQL attachment loader id mismatch")
    library_url = str(library["url"])

    measures = {
        resource_id: resource
        for (resource_type, resource_id), (resource, _) in resources.items()
        if resource_type == "Measure"
    }
    if set(measures) != MEASURE_IDS:
        raise ValueError("Measure inventory does not match the exact 20 required IDs")
    for measure_id, measure in measures.items():
        if measure.get("version") != PACKAGE_VERSION:
            raise ValueError(f"Measure/{measure_id}: version mismatch")
        if measure.get("library") != [library_url]:
            raise ValueError(f"Measure/{measure_id}: must reference the local CQL Library")

    naming_uris: set[str] = set()
    for key, (resource, _) in resources.items():
        if key[0] != "NamingSystem":
            continue
        identifiers = resource.get("uniqueId", [])
        if (
            resource.get("status") != "draft"
            or resource.get("kind") != "identifier"
            or len(identifiers) != 1
            or identifiers[0].get("type") != "uri"
            or identifiers[0].get("preferred") is not True
            or not str(identifiers[0].get("value", "")).startswith(f"{CANONICAL}sid/")
        ):
            raise ValueError(f"{key}: invalid NamingSystem metadata or preferred URI")
        naming_uris.add(str(identifiers[0]["value"]))
    if len(naming_uris) != 2:
        raise ValueError("NamingSystem preferred URIs must be unique")

    questionnaire = resources[("Questionnaire", "tcr-breast-longform")][0]
    ambiguous_versions = []
    if (
        not questionnaire.get("version")
        or questionnaire.get("version") == capability.get("fhirVersion")
    ):
        ambiguous_versions.append("Questionnaire/tcr-breast-longform")

    return {
        "gate_scope": "exact-complete-fhir-resource-inventory-and-ig-manifest",
        "resource_inventory_gate": "pass",
        "resource_count": len(resources),
        "publication_definition_count": definitions,
        "synthetic_example_count": examples,
        "canonical_resource_count": canonical_count,
        "manual_json_resource_count": sum(
            source == "manual-json" for _, source in resources.values()
        ),
        "generated_fsh_resource_count": sum(
            source == "generated-fsh" for _, source in resources.values()
        ),
        "measure_count": len(measures),
        "ambiguous_business_version_artifacts": ambiguous_versions,
        "business_version_provenance_gate": "block" if ambiguous_versions else "pass",
        "maximum_supported_claim": "complete-technical-inventory-not-semantic-approval",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--generated-resource-dir", type=Path, required=True)
    parser.add_argument("--manual-resource-dir", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("inventory", "business-version"), default="inventory")
    args = parser.parse_args()
    try:
        report = audit(
            args.register,
            args.generated_resource_dir,
            args.manual_resource_dir,
            args.cql,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"FHIR resource inventory audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"FHIR inventory: {report['resource_count']} resources; "
        f"definitions={report['publication_definition_count']}; "
        f"examples={report['synthetic_example_count']}; "
        f"canonical={report['canonical_resource_count']}"
    )
    print(
        f"Authoring sources: generated={report['generated_fsh_resource_count']}; "
        f"manual JSON={report['manual_json_resource_count']}"
    )
    print(f"Resource inventory gate: {report['resource_inventory_gate']}")
    print(f"Business-version provenance gate: {report['business_version_provenance_gate']}")
    selected = {
        "inventory": "resource_inventory_gate",
        "business-version": "business_version_provenance_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
