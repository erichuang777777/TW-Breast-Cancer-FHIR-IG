#!/usr/bin/env python3
"""Audit the exact FHIR resource inventory and generated IG manifest graph."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from datetime import date
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
    "MedicationAdministration": 1,
    "MedicationRequest": 1,
    "NamingSystem": 2,
    "Observation": 12,
    "Patient": 2,
    "Procedure": 2,
    "Provenance": 2,
    "Questionnaire": 1,
    "QuestionnaireResponse": 3,
    "Specimen": 1,
    "StructureDefinition": 48,
    "Task": 2,
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
EXPECTED_CAPABILITY_PROFILES = {
    "Patient": ("breast-cancer-patient",),
    "Condition": ("breast-cancer-primary-condition",),
    "Observation": (
        "breast-cancer-source-observation",
        "breast-cancer-stage-group-observation",
        "breast-cancer-tumor-marker-observation",
    ),
    "Procedure": ("breast-cancer-treatment-procedure",),
    "MedicationAdministration": ("breast-cancer-medication-administration",),
    "MedicationRequest": ("breast-cancer-medication-request",),
    "EpisodeOfCare": ("breast-cancer-episode-of-care",),
    "DiagnosticReport": (
        "breast-cancer-pathology-report",
        "breast-cancer-laboratory-report",
        "breast-cancer-ultrasound-report",
    ),
    "Specimen": ("breast-cancer-pathology-specimen",),
    "CarePlan": ("cancer-care-plan-task-care-plan",),
    "QuestionnaireResponse": ("cancer-care-plan-task-questionnaire-response",),
    "Task": (
        "breast-cancer-case-management-task",
        "tcr-registry-abstraction-task",
    ),
    "Bundle": (
        "breast-cancer-common-facts-bundle",
        "cancer-care-plan-task-bundle",
        "qbc-submission-bundle",
    ),
}
CAPABILITY_DOCUMENTATION = (
    "A conforming implementation supports only the resources required by its "
    "declared task modules; this community capability statement is not an "
    "authorization to claim every task."
)
REGISTER_COLUMNS = {
    "resource_type", "resource_id", "publication_role", "authoring_source",
}
VERSION_POLICY_COLUMNS = {
    "policy_id", "scope_rule", "artifact_count", "current_version_state",
    "required_owner", "required_evidence", "current_status", "decision",
    "signer_name", "signer_organization_title", "decision_date",
    "evidence_uri_path", "signed_artifact_sha256", "notes",
}
VERSION_POLICY_IDS = {
    "CV-PACKAGE-EXPLICIT",
    "CV-CQL-LIBRARY",
    "CV-PACKAGE-CONTEXT",
    "CV-TCR-MANUAL",
}
VERSION_POLICY_DEFINITIONS = {
    "CV-PACKAGE-EXPLICIT": {
        "scope_rule": (
            "generated canonical resources explicitly carrying package version except "
            "CQL Library"
        ),
        "artifact_count": "24",
        "required_owner": "IG publication owner",
        "required_evidence": (
            "immutable release manifest; package version; exact covered canonical list "
            "and hashes"
        ),
    },
    "CV-CQL-LIBRARY": {
        "scope_rule": "CQL Library and source library declaration",
        "artifact_count": "1",
        "required_owner": "CQL and publication owners",
        "required_evidence": (
            "CQL lifecycle decision; Library/CQL version equality; immutable ELM and "
            "source hashes"
        ),
    },
    "CV-PACKAGE-CONTEXT": {
        "scope_rule": "generated canonical resources with no resource-level business version",
            "artifact_count": "98",
        "required_owner": "IG publication owner",
        "required_evidence": (
            "decision to add explicit resource versions or approve package-context-only "
            "versioning; exact covered canonical list and release hash"
        ),
    },
    "CV-TCR-MANUAL": {
        "scope_rule": "all manually authored TCR canonical resources",
        "artifact_count": "101",
        "required_owner": "TCR source and publication owners",
        "required_evidence": (
            "authoritative TCR form/manual/code-table edition; decision whether local "
            "artifact or source version is asserted; exact covered canonical list and hashes"
        ),
    },
}
SHA256 = re.compile(r"[0-9a-fA-F]{64}")
LIBRARY_DECLARATION = re.compile(
    r"^library\s+([A-Za-z][A-Za-z0-9_]*)\s+version\s+'([^']+)'", re.MULTILINE
)


def version_policy_approval_complete(row: dict[str, str]) -> bool:
    if (
        row["current_status"] != "approved"
        or row["decision"] != "approve"
        or row["current_version_state"] not in {
            "explicit-package-version",
            "cql-library-version",
            "approved-package-context-only",
            "authoritative-business-version",
        }
    ):
        return False
    required = (
        "signer_name", "signer_organization_title", "decision_date",
        "evidence_uri_path", "signed_artifact_sha256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["decision_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_artifact_sha256"].strip()) is not None


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
    version_policy_path: Path,
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
    if len(rows) != 264 or len(set(register_keys)) != 264:
        raise ValueError(f"{register_path}: expected exactly 264 unique resources")

    with version_policy_path.open(encoding="utf-8-sig", newline="") as handle:
        version_policies = list(csv.DictReader(handle))
    version_columns = set(version_policies[0]) if version_policies else set()
    if version_columns != VERSION_POLICY_COLUMNS:
        raise ValueError(f"{version_policy_path}: invalid columns")
    if (
        len(version_policies) != 4
        or {row["policy_id"] for row in version_policies} != VERSION_POLICY_IDS
    ):
        raise ValueError(f"{version_policy_path}: expected exact four version policies")
    policy_by_id = {row["policy_id"]: row for row in version_policies}
    for row in version_policies:
        for field in (
            "policy_id", "scope_rule", "artifact_count", "current_version_state",
            "required_owner", "required_evidence", "current_status",
        ):
            if not row[field].strip():
                raise ValueError(f"{version_policy_path}: {row['policy_id']} empty {field}")
        if row["current_status"] not in {"pending-human-signoff", "approved"}:
            raise ValueError(f"{version_policy_path}: invalid current_status")
        if row["decision"] not in {"", "approve", "reject", "revise"}:
            raise ValueError(f"{version_policy_path}: invalid decision")
        definition = VERSION_POLICY_DEFINITIONS[row["policy_id"]]
        for field, expected in definition.items():
            if row[field] != expected:
                raise ValueError(
                    f"{version_policy_path}: {row['policy_id']} {field} does not match "
                    "the locked policy"
                )

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
    if canonical_count != 224:
        raise ValueError(f"canonical resource count {canonical_count}, expected 224")

    ig_key = ("ImplementationGuide", "io.github.erichuang777777.breast-cancer")
    ig = resources[ig_key][0]
    if ig.get("version") != PACKAGE_VERSION or ig.get("fhirVersion") != ["4.0.1"]:
        raise ValueError(f"{ig_key}: package or FHIR version mismatch")
    manifest_entries = ig.get("definition", {}).get("resource", [])
    manifest_refs = [entry.get("reference", {}).get("reference") for entry in manifest_entries]
    expected_refs = {f"{kind}/{resource_id}" for kind, resource_id in actual_keys - {ig_key}}
    if len(manifest_refs) != 263 or len(set(manifest_refs)) != 263:
        raise ValueError("ImplementationGuide manifest must have 263 unique resource references")
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
    if (definitions, examples) != (226, 38):
        raise ValueError(
            f"publication roles definitions={definitions}, examples={examples}; expected 226/38"
        )

    capability = resources[
        ("CapabilityStatement", "BreastCancerCommunityCapabilityStatement")
    ][0]
    if (
        capability.get("version") != PACKAGE_VERSION
        or capability.get("fhirVersion") != "4.0.1"
        or capability.get("kind") != "requirements"
        or capability.get("status") != "draft"
        or capability.get("experimental") is not True
        or set(capability.get("format", [])) != {"json", "xml"}
    ):
        raise ValueError("CapabilityStatement lifecycle, version, format, or kind mismatch")
    rest_entries = capability.get("rest", [])
    if len(rest_entries) != 1:
        raise ValueError("CapabilityStatement must have exactly one REST requirements block")
    rest = rest_entries[0]
    if (
        set(rest) != {"mode", "documentation", "resource"}
        or rest.get("mode") != "server"
        or rest.get("documentation") != CAPABILITY_DOCUMENTATION
    ):
        raise ValueError("CapabilityStatement REST claim boundary mismatch")
    expected_capability_pairs = {
        (resource_type, f"{CANONICAL}StructureDefinition/{profile_id}")
        for resource_type, profile_ids in EXPECTED_CAPABILITY_PROFILES.items()
        for profile_id in profile_ids
    }
    observed_capability_pairs: list[tuple[str, str]] = []
    resources_supported = rest.get("resource", [])
    if (
        len(resources_supported) != len(EXPECTED_CAPABILITY_PROFILES)
        or len({item.get("type") for item in resources_supported})
        != len(resources_supported)
    ):
        raise ValueError("CapabilityStatement resource type set is incomplete or duplicated")
    for supported in resources_supported:
        if set(supported) != {"type", "supportedProfile"}:
            raise ValueError("CapabilityStatement resource claim has unexpected fields")
        resource_type = supported.get("type")
        profile_urls = supported.get("supportedProfile", [])
        if not profile_urls or len(profile_urls) != len(set(profile_urls)):
            raise ValueError("CapabilityStatement supportedProfile set is empty or duplicated")
        for profile_url in profile_urls:
            observed_capability_pairs.append((resource_type, profile_url))
            profile_key = canonical_urls.get(profile_url)
            if not profile_key or profile_key[0] != "StructureDefinition":
                raise ValueError(f"CapabilityStatement unresolved supportedProfile {profile_url}")
            profile = resources[profile_key][0]
            if profile.get("type") != resource_type:
                raise ValueError(
                    f"CapabilityStatement type mismatch for supportedProfile {profile_url}"
                )
    if set(observed_capability_pairs) != expected_capability_pairs:
        raise ValueError("CapabilityStatement supportedProfile set differs from locked policy")

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

    explicit_package = []
    cql_libraries = []
    package_context = []
    manual_canonicals = []
    unexpected_versions = []
    for key, (resource, source) in resources.items():
        if key[0] not in CANONICAL_TYPES:
            continue
        version = resource.get("version")
        if source == "manual-json":
            manual_canonicals.append((key, version))
        elif key == library_key:
            cql_libraries.append((key, version))
        elif version == PACKAGE_VERSION:
            explicit_package.append((key, version))
        elif not version:
            package_context.append((key, version))
        else:
            unexpected_versions.append((key, version))
    if unexpected_versions:
        raise ValueError(f"unexpected generated canonical versions: {unexpected_versions}")

    group_counts = {
        "CV-PACKAGE-EXPLICIT": len(explicit_package),
        "CV-CQL-LIBRARY": len(cql_libraries),
        "CV-PACKAGE-CONTEXT": len(package_context),
        "CV-TCR-MANUAL": len(manual_canonicals),
    }
    if group_counts != {
        "CV-PACKAGE-EXPLICIT": 24,
        "CV-CQL-LIBRARY": 1,
        "CV-PACKAGE-CONTEXT": 98,
        "CV-TCR-MANUAL": 101,
    }:
        raise ValueError(f"canonical version policy group counts changed: {group_counts}")
    for policy_id, count in group_counts.items():
        try:
            registered_count = int(policy_by_id[policy_id]["artifact_count"])
        except ValueError as exc:
            raise ValueError(f"{version_policy_path}: invalid artifact_count") from exc
        if registered_count != count:
            raise ValueError(
                f"{version_policy_path}: {policy_id} artifact_count must be {count}"
            )

    context_policy = policy_by_id["CV-PACKAGE-CONTEXT"]
    context_approved = version_policy_approval_complete(context_policy)
    expected_context_state = (
        "approved-package-context-only"
        if context_approved
        else "package-context-policy-pending"
    )
    manual_versions = {str(version) if version is not None else "" for _, version in manual_canonicals}
    manual_policy = policy_by_id["CV-TCR-MANUAL"]
    manual_approved = version_policy_approval_complete(manual_policy)
    if not manual_versions or "" in manual_versions:
        expected_manual_state = "missing-business-version"
    elif "4.0.1" in manual_versions:
        expected_manual_state = "fhir-version-collision"
    elif len(manual_versions) != 1:
        expected_manual_state = "mixed-business-versions"
    else:
        expected_manual_state = (
            "authoritative-business-version"
            if manual_approved
            else "authoritative-business-version-candidate"
        )
    expected_states = {
        "CV-PACKAGE-EXPLICIT": "explicit-package-version",
        "CV-CQL-LIBRARY": "cql-library-version",
        "CV-PACKAGE-CONTEXT": expected_context_state,
        "CV-TCR-MANUAL": expected_manual_state,
    }
    for policy_id, expected_state in expected_states.items():
        if policy_by_id[policy_id]["current_version_state"] != expected_state:
            raise ValueError(
                f"{version_policy_path}: {policy_id} current_version_state must be "
                f"{expected_state}"
            )
    approved_version_policies = sum(
        version_policy_approval_complete(row) for row in version_policies
    )
    version_gate = (
        "pass" if approved_version_policies == 4
        and expected_context_state == "approved-package-context-only"
        and expected_manual_state == "authoritative-business-version"
        else "block"
    )

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
        "capability_resource_type_count": len(resources_supported),
        "capability_supported_profile_count": len(observed_capability_pairs),
        "canonical_version_policy_count": len(version_policies),
        "approved_canonical_version_policy_count": approved_version_policies,
        "canonical_version_policy_group_counts": group_counts,
        "canonical_version_policy_states": expected_states,
        "manual_canonical_versions": sorted(manual_versions),
        "business_version_provenance_gate": version_gate,
        "maximum_supported_claim": "complete-technical-inventory-not-semantic-approval",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--version-policy-register", type=Path, required=True)
    parser.add_argument("--generated-resource-dir", type=Path, required=True)
    parser.add_argument("--manual-resource-dir", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("inventory", "business-version"), default="inventory")
    args = parser.parse_args()
    try:
        report = audit(
            args.register,
            args.version_policy_register,
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
