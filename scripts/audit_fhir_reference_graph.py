#!/usr/bin/env python3
"""Audit every local URL link, FHIR Reference, and external canonical edge."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.audit_fhir_resource_inventory import CANONICAL, load_resources
except ModuleNotFoundError:  # Direct execution sets sys.path to scripts/.
    from audit_fhir_resource_inventory import CANONICAL, load_resources


CANONICAL_FIELDS = {
    "answerValueSet": "ValueSet",
    "baseDefinition": "StructureDefinition",
    "derivedFrom": None,
    "exampleCanonical": "StructureDefinition",
    "instantiatesCanonical": None,
    "library": "Library",
    "measure": "Measure",
    "profile": "StructureDefinition",
    "questionnaire": "Questionnaire",
    "sourceUri": "ValueSet",
    "supportedProfile": "StructureDefinition",
    "targetProfile": "StructureDefinition",
    "targetUri": "ValueSet",
    "valueSet": "ValueSet",
}
EXPECTED_LOCAL_LINK_COUNTS = {
    "bundle-fullUrl": 19,
    "canonical-field": 219,
    "code-system-use": 138,
    "conceptmap-code-system-use": 2,
    "extension-use-url": 240,
    "fixed-extension-url": 13,
    "naming-system-use": 2,
}
EXPECTED_EXTERNAL_CANONICALS = {
    "http://hl7.org/fhir/StructureDefinition/Bundle",
    "http://hl7.org/fhir/StructureDefinition/CarePlan",
    "http://hl7.org/fhir/StructureDefinition/Condition",
    "http://hl7.org/fhir/StructureDefinition/DiagnosticReport",
    "http://hl7.org/fhir/StructureDefinition/EpisodeOfCare",
    "http://hl7.org/fhir/StructureDefinition/Extension",
    "http://hl7.org/fhir/StructureDefinition/MeasureReport",
    "http://hl7.org/fhir/StructureDefinition/MedicationRequest",
    "http://hl7.org/fhir/StructureDefinition/Observation",
    "http://hl7.org/fhir/StructureDefinition/Patient",
    "http://hl7.org/fhir/StructureDefinition/Procedure",
    "http://hl7.org/fhir/StructureDefinition/Provenance",
    "http://hl7.org/fhir/StructureDefinition/QuestionnaireResponse",
    "http://hl7.org/fhir/StructureDefinition/Specimen",
    "http://hl7.org/fhir/StructureDefinition/Task",
    "http://hl7.org/fhir/ValueSet/administrative-gender",
    "https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition/Bundle-twcore",
    "https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition/Patient-twcore",
}


@dataclass(frozen=True)
class GraphExpectations:
    resource_count: int
    local_link_counts: dict[str, int]
    unique_local_target_count: int
    external_canonical_occurrence_count: int
    external_canonicals: frozenset[str]
    external_authority_counts: dict[str, int]
    versioned_canonical_reference_count: int
    fhir_reference_count: int
    manifest_reference_count: int


PRODUCTION_EXPECTATIONS = GraphExpectations(
    resource_count=260,
    local_link_counts=EXPECTED_LOCAL_LINK_COUNTS,
    unique_local_target_count=190,
    external_canonical_occurrence_count=35,
    external_canonicals=frozenset(EXPECTED_EXTERNAL_CANONICALS),
    external_authority_counts={
        "fhir-r4-core-4.0.1": 33,
        "tw-core-1.0.0": 2,
    },
    versioned_canonical_reference_count=0,
    fhir_reference_count=326,
    manifest_reference_count=259,
)


def walk_strings(value: object, path: tuple[str, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, path + (str(index),))
    elif isinstance(value, str):
        yield path, value


def named_path(path: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(part for part in path if not part.isdigit())


def split_canonical(value: str) -> tuple[str, str | None]:
    canonical, separator, version = value.partition("|")
    return canonical, version if separator else None


def audit(
    generated_dir: Path,
    manual_dir: Path,
    sushi_config_path: Path,
    *,
    expectations: GraphExpectations = PRODUCTION_EXPECTATIONS,
) -> dict[str, object]:
    resources = load_resources(generated_dir, manual_dir)
    if len(resources) != expectations.resource_count:
        raise ValueError(
            f"reference graph requires exactly {expectations.resource_count} resources"
        )

    config_text = sushi_config_path.read_text(encoding="utf-8")
    fhir_version = re.search(r"^fhirVersion:\s*['\"]?([^\s'\"]+)", config_text, re.M)
    tw_core_version = re.search(
        r"^\s{2}tw\.gov\.mohw\.twcore:\s*['\"]?([^\s'\"]+)",
        config_text,
        re.M,
    )
    if not fhir_version or fhir_version.group(1) != "4.0.1":
        raise ValueError(f"{sushi_config_path}: fhirVersion must be 4.0.1")
    if not tw_core_version or tw_core_version.group(1) != "1.0.0":
        raise ValueError(f"{sushi_config_path}: TW Core dependency must be pinned to 1.0.0")

    canonical_targets: dict[str, tuple[str, str]] = {}
    for key, (resource, _) in resources.items():
        url = resource.get("url")
        if isinstance(url, str):
            if url in canonical_targets:
                raise ValueError(f"duplicate resource URL {url}")
            canonical_targets[url] = key

    naming_targets: dict[str, tuple[str, str]] = {}
    for key, (resource, _) in resources.items():
        if key[0] != "NamingSystem":
            continue
        for identifier in resource.get("uniqueId", []):
            value = identifier.get("value")
            if isinstance(value, str):
                if value in naming_targets:
                    raise ValueError(f"duplicate NamingSystem URI {value}")
                naming_targets[value] = key

    local_counts: Counter[str] = Counter()
    local_targets: set[str] = set()
    external_canonicals: list[str] = []
    versioned_canonicals = 0
    reference_count = 0
    manifest_reference_count = 0

    def require_local_target(
        source_key: tuple[str, str],
        path: tuple[str, ...],
        raw_value: str,
        expected_type: str | None,
    ) -> str:
        nonlocal versioned_canonicals
        target_url, version = split_canonical(raw_value)
        if version is not None:
            versioned_canonicals += 1
        target_key = canonical_targets.get(target_url)
        if target_key is None:
            raise ValueError(
                f"{source_key} {'.'.join(path)}: unresolved local URL {target_url}"
            )
        if expected_type and target_key[0] != expected_type:
            raise ValueError(
                f"{source_key} {'.'.join(path)}: expected {expected_type}, "
                f"resolved {target_key[0]}"
            )
        if version is not None:
            target_version = resources[target_key][0].get("version")
            if version != target_version:
                raise ValueError(
                    f"{source_key} {'.'.join(path)}: version {version} does not "
                    f"match target version {target_version}"
                )
        local_targets.add(target_url)
        return target_url

    for source_key, (resource, _) in resources.items():
        for path, value in walk_strings(resource):
            named = named_path(path)
            field = named[-1] if named else ""

            if field == "reference":
                reference_count += 1
                if named == ("definition", "resource", "reference", "reference"):
                    manifest_reference_count += 1
                if value.startswith("#"):
                    contained_ids = {
                        str(item.get("id"))
                        for item in resource.get("contained", [])
                        if item.get("id")
                    }
                    if value[1:] not in contained_ids:
                        raise ValueError(
                            f"{source_key} {'.'.join(path)}: unresolved contained reference {value}"
                        )
                elif value.startswith("http://") or value.startswith("https://"):
                    if value.startswith(CANONICAL):
                        relative = value.removeprefix(CANONICAL)
                        parts = relative.split("/", 1)
                        if len(parts) != 2 or tuple(parts) not in resources:
                            raise ValueError(
                                f"{source_key} {'.'.join(path)}: unresolved absolute reference {value}"
                            )
                    else:
                        raise ValueError(
                            f"{source_key} {'.'.join(path)}: ungoverned external Reference {value}"
                        )
                else:
                    parts = value.split("/", 1)
                    if len(parts) != 2 or tuple(parts) not in resources:
                        raise ValueError(
                            f"{source_key} {'.'.join(path)}: unresolved FHIR reference {value}"
                        )

            if field in CANONICAL_FIELDS:
                canonical_url, _ = split_canonical(value)
                if canonical_url.startswith(CANONICAL):
                    local_counts["canonical-field"] += 1
                    require_local_target(
                        source_key, path, value, CANONICAL_FIELDS[field]
                    )
                else:
                    expected_type = CANONICAL_FIELDS[field]
                    if expected_type and f"/{expected_type}/" not in canonical_url:
                        raise ValueError(
                            f"{source_key} {'.'.join(path)}: external canonical does "
                            f"not identify a {expected_type}"
                        )
                    if split_canonical(value)[1] is not None:
                        versioned_canonicals += 1
                    external_canonicals.append(canonical_url)
                continue

            if not value.startswith(CANONICAL):
                continue
            if named == ("url",):
                continue
            if named[-2:] == ("uniqueId", "value"):
                continue
            if field == "fullUrl":
                local_counts["bundle-fullUrl"] += 1
                continue
            if field == "fixedUri":
                local_counts["fixed-extension-url"] += 1
                target_url = require_local_target(
                    source_key, path, value, "StructureDefinition"
                )
                target_key = canonical_targets[target_url]
                if resources[target_key][0].get("type") != "Extension":
                    raise ValueError(f"{source_key} {'.'.join(path)}: target is not Extension")
                continue
            if field == "url" and "extension" in named:
                local_counts["extension-use-url"] += 1
                target_url = require_local_target(
                    source_key, path, value, "StructureDefinition"
                )
                target_key = canonical_targets[target_url]
                if resources[target_key][0].get("type") != "Extension":
                    raise ValueError(f"{source_key} {'.'.join(path)}: target is not Extension")
                continue
            if field == "system" and named[-2:] == ("identifier", "system"):
                local_counts["naming-system-use"] += 1
                if value not in naming_targets:
                    raise ValueError(
                        f"{source_key} {'.'.join(path)}: unresolved NamingSystem URI {value}"
                    )
                local_targets.add(value)
                continue
            if field == "system":
                local_counts["code-system-use"] += 1
                require_local_target(source_key, path, value, "CodeSystem")
                continue
            if field in {"source", "target"} and "group" in named:
                local_counts["conceptmap-code-system-use"] += 1
                require_local_target(source_key, path, value, "CodeSystem")
                continue
            raise ValueError(
                f"{source_key} {'.'.join(path)}: unclassified local URL link {value}"
            )

        if source_key[0] == "Bundle":
            for index, entry in enumerate(resource.get("entry", [])):
                full_url = entry.get("fullUrl")
                embedded = entry.get("resource", {})
                embedded_key = (embedded.get("resourceType"), embedded.get("id"))
                expected_full_url = f"{CANONICAL}{embedded_key[0]}/{embedded_key[1]}"
                if full_url != expected_full_url or embedded_key not in resources:
                    raise ValueError(
                        f"{source_key} entry[{index}]: fullUrl/resource identity mismatch"
                    )
                local_targets.add(full_url)

    if dict(sorted(local_counts.items())) != expectations.local_link_counts:
        raise ValueError(
            f"local URL link counts changed: {dict(sorted(local_counts.items()))}"
        )
    external_set = set(external_canonicals)
    if (
        len(external_canonicals) != expectations.external_canonical_occurrence_count
        or external_set != expectations.external_canonicals
    ):
        raise ValueError(
            "external canonical graph changed; update authority and dependency review"
        )
    external_authority_counts = {
        "fhir-r4-core-4.0.1": sum(
            value.startswith("http://hl7.org/fhir/") for value in external_canonicals
        ),
        "tw-core-1.0.0": sum(
            value.startswith("https://twcore.mohw.gov.tw/")
            for value in external_canonicals
        ),
    }
    if external_authority_counts != expectations.external_authority_counts:
        raise ValueError(f"external canonical authority counts changed")
    if versioned_canonicals != expectations.versioned_canonical_reference_count:
        raise ValueError(
            "versioned canonical reference policy changed; explicit review is required"
        )
    if (
        reference_count != expectations.fhir_reference_count
        or manifest_reference_count != expectations.manifest_reference_count
    ):
        raise ValueError(
            f"FHIR reference counts changed: total={reference_count}, "
            f"manifest={manifest_reference_count}"
        )
    if len(local_targets) != expectations.unique_local_target_count:
        raise ValueError(f"unique local URL target count changed: {len(local_targets)}")

    return {
        "gate_scope": "complete-local-fhir-reference-and-canonical-graph",
        "reference_graph_integrity_gate": "pass",
        "resource_count": len(resources),
        "local_url_link_occurrence_count": sum(local_counts.values()),
        "local_url_link_counts": dict(sorted(local_counts.items())),
        "unique_local_url_target_count": len(local_targets),
        "canonical_reference_occurrence_count": (
            local_counts["canonical-field"] + len(external_canonicals)
        ),
        "local_canonical_reference_occurrence_count": local_counts["canonical-field"],
        "external_canonical_reference_occurrence_count": len(external_canonicals),
        "unique_external_canonical_count": len(external_set),
        "external_canonical_authority_counts": external_authority_counts,
        "versioned_canonical_reference_occurrence_count": versioned_canonicals,
        "fhir_reference_occurrence_count": reference_count,
        "manifest_reference_occurrence_count": manifest_reference_count,
        "non_manifest_reference_occurrence_count": (
            reference_count - manifest_reference_count
        ),
        "total_audited_reference_edge_count": (
            sum(local_counts.values()) + reference_count + len(external_canonicals)
        ),
        "maximum_supported_claim": "complete-technical-reference-graph-not-semantic-approval",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-resource-dir", type=Path, required=True)
    parser.add_argument("--manual-resource-dir", type=Path, required=True)
    parser.add_argument("--sushi-config", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = audit(
            args.generated_resource_dir,
            args.manual_resource_dir,
            args.sushi_config,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FHIR reference graph audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        f"FHIR reference graph: {report['total_audited_reference_edge_count']} edges; "
        f"local URL={report['local_url_link_occurrence_count']}; "
        f"FHIR Reference={report['fhir_reference_occurrence_count']}; "
        f"external canonical={report['external_canonical_reference_occurrence_count']}"
    )
    print(f"Reference graph integrity gate: {report['reference_graph_integrity_gate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
