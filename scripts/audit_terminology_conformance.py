#!/usr/bin/env python3
"""Audit the complete local terminology set and clinical ValueSet approvals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
EXPECTED_COUNTS = {"CodeSystem": 60, "ValueSet": 90, "ConceptMap": 2}
CLINICAL_VALUESET_IDS = {
    "cm-clinical-stage-group-code",
    "cm-pathological-stage-group-code",
    "cm-pathological-n-category-code",
    "cm-pathological-t-category-code",
    "cm-estrogen-receptor-code",
    "cm-her2-ihc-code",
    "cm-her2-ish-code",
    "cm-breast-surgery-procedure",
    "cm-breast-conserving-surgery-procedure",
    "cm-total-mastectomy-procedure",
    "cm-sentinel-lymph-node-biopsy-procedure",
    "cm-axillary-lymph-node-dissection-procedure",
    "cm-core-needle-biopsy-procedure",
    "cm-radiotherapy-procedure",
    "cm-hormone-therapy-medication",
    "cm-cytotoxic-chemotherapy-medication",
    "cm-anti-her2-medication",
    "cm-progesterone-receptor-code",
    "cm-histology-morphology-code",
}
REQUIRED_APPROVAL_COLUMNS = {
    "approval_id", "valueset_id", "cql_identifier", "cql_usage_status",
    "intended_semantics", "candidate_code_system_family",
    "authoritative_source_version", "content_status", "current_status",
    "required_reviewer", "acceptance_evidence", "decision", "signer_name",
    "signer_organization_title", "decision_date", "evidence_uri_path",
    "signed_artifact_sha256", "notes",
}
REQUIRED_EXPANSION_COLUMNS = {
    "validation_id", "valueset_id", "evidence_bundle_path",
    "evidence_bundle_sha256", "validation_status", "terminology_service",
    "terminology_service_version", "validated_at", "expanded_code_count",
    "resolved_code_count", "unresolved_code_count", "negative_test_count",
    "validator_name", "notes",
}
REQUIRED_RELATIONSHIP_COLUMNS = {
    "relationship_id", "conceptmap_id", "source_system", "source_version",
    "source_code", "target_system", "target_version", "target_code",
    "equivalence", "source_resolution_status", "target_resolution_status",
    "relationship_status", "authoritative_source_version", "required_reviewer",
    "decision", "signer_name", "signer_organization_title", "decision_date",
    "evidence_uri_path", "evidence_sha256", "reviewed_conceptmap_sha256", "notes",
}
SHA256 = re.compile(r"[0-9a-fA-F]{64}")
VALUESET_DECLARATION = re.compile(
    r'^valueset\s+"([^"]+)"\s*:\s*\'([^\']+)\'', re.MULTILINE
)


def strip_cql_comments(source: str) -> str:
    """Remove CQL comments without treating // inside quoted URLs as comments."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(source):
        character = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if quote:
            output.append(character)
            if character == "\\" and following:
                output.append(following)
                index += 2
                continue
            if character == quote:
                quote = None
            index += 1
            continue
        if character in {'"', "'"}:
            quote = character
            output.append(character)
            index += 1
            continue
        if character == "/" and following == "/":
            index += 2
            while index < len(source) and source[index] not in "\r\n":
                index += 1
            continue
        if character == "/" and following == "*":
            index += 2
            while index < len(source) and source[index:index + 2] != "*/":
                if source[index] in "\r\n":
                    output.append(source[index])
                index += 1
            index += 2 if index < len(source) else 0
            continue
        output.append(character)
        index += 1
    return "".join(output)


def approval_complete(row: dict[str, str]) -> bool:
    if (
        row["content_status"] != "approved"
        or row["current_status"] != "approved"
        or row["decision"] != "approve"
    ):
        return False
    required = (
        "signer_name", "signer_organization_title", "decision_date",
        "evidence_uri_path", "signed_artifact_sha256",
        "authoritative_source_version",
    )
    if not all(row[field].strip() for field in required):
        return False
    if row["authoritative_source_version"] == "pending-owner-confirmation":
        return False
    try:
        date.fromisoformat(row["decision_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_artifact_sha256"].strip()) is not None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_register(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != required_columns:
            raise ValueError(f"{path}: invalid columns")
        return list(reader)


def resolve_evidence_path(raw_path: str, repository_root: Path, label: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label}: evidence path must be repository-relative")
    resolved = (repository_root / candidate).resolve()
    try:
        resolved.relative_to(repository_root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label}: evidence path escapes repository") from exc
    if not resolved.is_file():
        raise ValueError(f"{label}: evidence file does not exist: {raw_path}")
    return resolved


def repository_root_for_register(register_path: Path) -> Path:
    parent = register_path.resolve().parent
    if parent.name == "publication" and parent.parent.name == "mappings":
        return parent.parents[1]
    return parent


def concept_codes(concepts: list[dict[str, object]]) -> set[str]:
    codes: set[str] = set()
    for concept in concepts:
        code = str(concept.get("code", "")).strip()
        if not code:
            raise ValueError("CodeSystem concept has no code")
        if code in codes:
            raise ValueError(f"CodeSystem has duplicate code {code}")
        codes.add(code)
        nested = concept_codes(list(concept.get("concept", [])))
        overlap = codes & nested
        if overlap:
            raise ValueError(f"CodeSystem has duplicate nested code {sorted(overlap)[0]}")
        codes.update(nested)
    return codes


def load_resources(directories: list[Path]) -> dict[tuple[str, str], dict[str, object]]:
    resources: dict[tuple[str, str], dict[str, object]] = {}
    for directory in directories:
        if not directory.is_dir():
            raise ValueError(f"{directory}: resource directory does not exist")
        for path in directory.glob("*.json"):
            resource = json.loads(path.read_text(encoding="utf-8-sig"))
            resource_type = resource.get("resourceType")
            resource_id = resource.get("id")
            if resource_type not in EXPECTED_COUNTS or not resource_id:
                continue
            key = (str(resource_type), str(resource_id))
            if key in resources:
                raise ValueError(f"duplicate terminology artifact {key}")
            resource["_audit_source_path"] = str(path.resolve())
            resources[key] = resource
    return resources


def parse_nonnegative_integer(raw: str, label: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label}: must be an integer") from exc
    if value < 0:
        raise ValueError(f"{label}: must be non-negative")
    return value


def parse_timestamp(raw: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timestamp must include a timezone")
    return parsed


def audit_expansion_evidence(
    register_path: Path,
    approvals: list[dict[str, str]],
    resources: dict[tuple[str, str], dict[str, object]],
    code_systems_by_url: dict[str, dict[str, object]],
    code_system_code_sets: dict[str, set[str]],
    repository_root: Path,
) -> tuple[int, int]:
    rows = read_register(register_path, REQUIRED_EXPANSION_COLUMNS)
    if (
        len(rows) != len(CLINICAL_VALUESET_IDS)
        or len({row["validation_id"] for row in rows}) != len(rows)
        or {row["valueset_id"] for row in rows} != CLINICAL_VALUESET_IDS
    ):
        raise ValueError(
            f"{register_path}: expected one unique validation for each of 19 clinical ValueSets"
        )
    approvals_by_valueset = {row["valueset_id"]: row for row in approvals}
    validated_count = 0
    validated_code_count = 0
    for row in rows:
        valueset_id = row["valueset_id"]
        label = f"{register_path}: {valueset_id}"
        if row["validation_status"] not in {"pending-validation", "validated"}:
            raise ValueError(f"{label}: invalid validation_status")
        if row["validation_status"] != "validated":
            continue
        approval = approvals_by_valueset[valueset_id]
        if not approval_complete(approval):
            raise ValueError(f"{label}: cannot be validated before clinical approval is complete")
        required = (
            "evidence_bundle_path", "evidence_bundle_sha256", "terminology_service",
            "terminology_service_version", "validated_at", "expanded_code_count",
            "resolved_code_count", "unresolved_code_count", "negative_test_count",
            "validator_name",
        )
        if not all(row[field].strip() for field in required):
            raise ValueError(f"{label}: validated row has incomplete evidence metadata")
        if not SHA256.fullmatch(row["evidence_bundle_sha256"]):
            raise ValueError(f"{label}: invalid evidence bundle SHA-256")
        bundle_path = resolve_evidence_path(
            row["evidence_bundle_path"], repository_root, label
        )
        actual_hash = sha256_file(bundle_path)
        if actual_hash.lower() != row["evidence_bundle_sha256"].lower():
            raise ValueError(f"{label}: evidence bundle SHA-256 mismatch")
        if approval["evidence_uri_path"] != row["evidence_bundle_path"]:
            raise ValueError(f"{label}: approval does not identify the validated bundle")
        if approval["signed_artifact_sha256"].lower() != actual_hash.lower():
            raise ValueError(f"{label}: approval hash does not match the validated bundle")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
        valueset = resources[("ValueSet", valueset_id)]
        valueset_version = str(valueset.get("version", "")).strip()
        if not valueset_version:
            raise ValueError(f"{label}: published ValueSet has no business version")
        if (
            bundle.get("schema_version") != "1.0"
            or bundle.get("valueset_url") != valueset.get("url")
            or bundle.get("valueset_version") != valueset_version
            or not str(bundle.get("expansion_identifier", "")).strip()
            or not isinstance(bundle.get("expansion_parameters"), list)
        ):
            raise ValueError(f"{label}: bundle identity or expansion metadata mismatch")
        parse_timestamp(str(bundle.get("expansion_timestamp", "")), label)
        parse_timestamp(row["validated_at"], label)
        service = bundle.get("terminology_service")
        if not isinstance(service, dict) or (
            service.get("url") != row["terminology_service"]
            or service.get("version") != row["terminology_service_version"]
            or not str(service.get("software", "")).strip()
        ):
            raise ValueError(f"{label}: terminology service identity mismatch")
        codes = bundle.get("codes")
        negatives = bundle.get("negative_tests")
        if not isinstance(codes, list) or not codes:
            raise ValueError(f"{label}: expansion code list is empty")
        if not isinstance(negatives, list) or not negatives:
            raise ValueError(f"{label}: negative validation controls are empty")
        expanded: set[tuple[str, str, str]] = set()
        for item in codes:
            if not isinstance(item, dict):
                raise ValueError(f"{label}: invalid expansion code entry")
            key = tuple(str(item.get(field, "")).strip() for field in ("system", "version", "code"))
            if not all(key) or not str(item.get("display", "")).strip():
                raise ValueError(f"{label}: code lacks system/version/code/display")
            if item.get("validation_result") is not True:
                raise ValueError(f"{label}: expansion contains an unresolved code")
            if key in expanded:
                raise ValueError(f"{label}: duplicate expansion tuple {key}")
            expanded.add(key)
        negative_system_versions: set[tuple[str, str]] = set()
        for item in negatives:
            if not isinstance(item, dict):
                raise ValueError(f"{label}: invalid negative validation entry")
            system = str(item.get("system", "")).strip()
            version = str(item.get("version", "")).strip()
            code = str(item.get("code", "")).strip()
            if not system or not version or not code or item.get("validation_result") is not False:
                raise ValueError(f"{label}: negative control must record a rejected code")
            if (system, version, code) in expanded:
                raise ValueError(f"{label}: negative control is also in the expansion")
            negative_system_versions.add((system, version))
        expanded_system_versions = {(system, version) for system, version, _ in expanded}
        if negative_system_versions != expanded_system_versions:
            raise ValueError(f"{label}: needs one rejected-code control per system/version")

        expected_local_or_explicit: set[tuple[str, str, str]] = set()
        for include in valueset.get("compose", {}).get("include", []):
            system = str(include.get("system", "")).strip()
            local_system = code_systems_by_url.get(system)
            version = str(include.get("version", "")).strip()
            if local_system:
                local_version = str(local_system.get("version", "")).strip()
                if not local_version:
                    raise ValueError(f"{label}: local CodeSystem {system} has no business version")
                if version and version != local_version:
                    raise ValueError(f"{label}: local CodeSystem version mismatch")
                version = local_version
            if not version:
                raise ValueError(f"{label}: include {system} is not version-pinned")
            concepts = include.get("concept", [])
            if concepts:
                expected_local_or_explicit.update(
                    (system, version, str(concept.get("code", "")).strip())
                    for concept in concepts
                )
            elif local_system and not include.get("filter"):
                expected_local_or_explicit.update(
                    (system, version, code) for code in code_system_code_sets[system]
                )
        missing = expected_local_or_explicit - expanded
        if missing:
            raise ValueError(f"{label}: expansion omits composed code {sorted(missing)[0]}")
        expanded_count = parse_nonnegative_integer(row["expanded_code_count"], label)
        resolved_count = parse_nonnegative_integer(row["resolved_code_count"], label)
        unresolved_count = parse_nonnegative_integer(row["unresolved_code_count"], label)
        negative_count = parse_nonnegative_integer(row["negative_test_count"], label)
        if (
            expanded_count != len(expanded)
            or resolved_count != len(expanded)
            or unresolved_count != 0
            or negative_count != len(negatives)
        ):
            raise ValueError(f"{label}: declared validation counts do not match the bundle")
        validated_count += 1
        validated_code_count += len(expanded)
    return validated_count, validated_code_count


def audit_conceptmap_relationships(
    register_path: Path,
    resources: dict[tuple[str, str], dict[str, object]],
    code_systems_by_url: dict[str, dict[str, object]],
    code_system_code_sets: dict[str, set[str]],
    repository_root: Path,
) -> tuple[int, int]:
    rows = read_register(register_path, REQUIRED_RELATIONSHIP_COLUMNS)
    actual: dict[tuple[str, str, str, str, str, str], tuple[dict[str, object], dict[str, object]]] = {}
    for (resource_type, resource_id), resource in resources.items():
        if resource_type != "ConceptMap":
            continue
        for group in resource.get("group", []):
            for element in group.get("element", []):
                for target in element.get("target", []):
                    key = (
                        resource_id, str(group.get("source", "")), str(element.get("code", "")),
                        str(group.get("target", "")), str(target.get("code", "")),
                        str(target.get("equivalence", "")),
                    )
                    if key in actual:
                        raise ValueError(f"ConceptMap/{resource_id}: duplicate relationship {key}")
                    actual[key] = (resource, group)
    registered: dict[tuple[str, str, str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in (
            "conceptmap_id", "source_system", "source_code", "target_system",
            "target_code", "equivalence",
        ))
        if key in registered:
            raise ValueError(f"{register_path}: duplicate relationship tuple {key}")
        registered[key] = row
    if set(registered) != set(actual) or len({row["relationship_id"] for row in rows}) != len(rows):
        missing = sorted(set(actual) - set(registered))
        extra = sorted(set(registered) - set(actual))
        raise ValueError(
            f"{register_path}: relationship coverage mismatch; missing={missing}; extra={extra}"
        )
    approved_count = 0
    for key, row in registered.items():
        label = f"{register_path}: {row['relationship_id']}"
        if row["relationship_status"] not in {"pending-review", "approved"}:
            raise ValueError(f"{label}: invalid relationship_status")
        if row["relationship_status"] != "approved":
            continue
        required = (
            "source_version", "target_version", "authoritative_source_version",
            "required_reviewer", "decision", "signer_name", "signer_organization_title",
            "decision_date", "evidence_uri_path", "evidence_sha256",
            "reviewed_conceptmap_sha256",
        )
        if not all(row[field].strip() for field in required):
            raise ValueError(f"{label}: approved relationship has incomplete evidence")
        if (
            row["decision"] != "approve"
            or row["source_resolution_status"] != "resolved"
            or row["target_resolution_status"] != "resolved"
            or "pending" in row["authoritative_source_version"].lower()
        ):
            raise ValueError(f"{label}: approved relationship is unresolved")
        try:
            date.fromisoformat(row["decision_date"])
        except ValueError as exc:
            raise ValueError(f"{label}: invalid decision date") from exc
        if not SHA256.fullmatch(row["evidence_sha256"]) or not SHA256.fullmatch(row["reviewed_conceptmap_sha256"]):
            raise ValueError(f"{label}: invalid evidence SHA-256")
        evidence_path = resolve_evidence_path(row["evidence_uri_path"], repository_root, label)
        if sha256_file(evidence_path).lower() != row["evidence_sha256"].lower():
            raise ValueError(f"{label}: review evidence SHA-256 mismatch")
        resource, group = actual[key]
        conceptmap_path = Path(str(resource["_audit_source_path"]))
        if sha256_file(conceptmap_path).lower() != row["reviewed_conceptmap_sha256"].lower():
            raise ValueError(f"{label}: reviewed ConceptMap SHA-256 is stale")
        if group.get("sourceVersion") != row["source_version"] or group.get("targetVersion") != row["target_version"]:
            raise ValueError(f"{label}: ConceptMap group is not pinned to the reviewed versions")
        source_system, source_code = row["source_system"], row["source_code"]
        if source_system in code_systems_by_url:
            source_resource = code_systems_by_url[source_system]
            if source_resource.get("version") != row["source_version"]:
                raise ValueError(f"{label}: source CodeSystem version mismatch")
            if source_code not in code_system_code_sets[source_system]:
                raise ValueError(f"{label}: unresolved local source code")
        target_system, target_code = row["target_system"], row["target_code"]
        if target_system in code_systems_by_url:
            target_resource = code_systems_by_url[target_system]
            if target_resource.get("version") != row["target_version"]:
                raise ValueError(f"{label}: target CodeSystem version mismatch")
            if target_code not in code_system_code_sets[target_system]:
                raise ValueError(f"{label}: unresolved local target code")
        approved_count += 1
    return approved_count, len(rows)


def audit(
    approval_path: Path,
    expansion_register_path: Path,
    relationship_register_path: Path,
    cql_path: Path,
    resource_dirs: list[Path],
) -> dict[str, object]:
    resources = load_resources(resource_dirs)
    counts = {
        resource_type: sum(key[0] == resource_type for key in resources)
        for resource_type in EXPECTED_COUNTS
    }
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"terminology artifact counts {counts}, expected {EXPECTED_COUNTS}")

    code_systems_by_url = {
        str(resource.get("url")): resource
        for (resource_type, _), resource in resources.items()
        if resource_type == "CodeSystem"
    }
    code_system_urls = set(code_systems_by_url)
    code_system_code_sets: dict[str, set[str]] = {}
    duplicate_code_system_code_count = 0
    for url, resource in code_systems_by_url.items():
        try:
            code_system_code_sets[url] = concept_codes(list(resource.get("concept", [])))
        except ValueError as exc:
            duplicate_code_system_code_count += 1
            raise ValueError(f"CodeSystem/{resource.get('id')}: {exc}") from exc
    empty_valuesets: set[str] = set()
    external_systems: set[str] = set()
    local_valueset_code_reference_count = 0
    for (resource_type, resource_id), resource in resources.items():
        expected_url = f"{CANONICAL}{resource_type}/{resource_id}"
        if resource.get("url") != expected_url:
            raise ValueError(f"{resource_type}/{resource_id}: noncanonical url")
        if resource.get("status") != "draft" or resource.get("experimental") is not True:
            raise ValueError(f"{resource_type}/{resource_id}: must remain draft and experimental")
        if resource_type == "CodeSystem":
            if resource.get("content") != "complete" or not resource.get("concept"):
                raise ValueError(f"CodeSystem/{resource_id}: incomplete or empty content")
        elif resource_type == "ValueSet":
            includes = resource.get("compose", {}).get("include", [])
            if not includes:
                empty_valuesets.add(resource_id)
            for include in includes:
                system = include.get("system")
                if not system:
                    raise ValueError(f"ValueSet/{resource_id}: include has no system")
                if system.startswith(CANONICAL) and system not in code_system_urls:
                    raise ValueError(
                        f"ValueSet/{resource_id}: missing local CodeSystem {system}"
                    )
                if not system.startswith(CANONICAL):
                    external_systems.add(str(system))
                for concept in include.get("concept", []):
                    code = str(concept.get("code", "")).strip()
                    if not code:
                        raise ValueError(f"ValueSet/{resource_id}: concept has no code")
                    if system in code_system_code_sets:
                        local_valueset_code_reference_count += 1
                        if code not in code_system_code_sets[str(system)]:
                            raise ValueError(
                                f"ValueSet/{resource_id}: unresolved local code {system}|{code}"
                            )
        else:
            groups = resource.get("group", [])
            if not groups or any(not group.get("element") for group in groups):
                raise ValueError(f"ConceptMap/{resource_id}: missing mapped elements")
            for group in groups:
                if not group.get("source") or not group.get("target"):
                    raise ValueError(f"ConceptMap/{resource_id}: missing source or target")
                for element in group["element"]:
                    if not element.get("target") or any(
                        not target.get("code") or not target.get("equivalence")
                        for target in element["target"]
                    ):
                        raise ValueError(f"ConceptMap/{resource_id}: incomplete target")

    approvals = read_register(approval_path, REQUIRED_APPROVAL_COLUMNS)
    if (
        len(approvals) != 19
        or len({row["approval_id"] for row in approvals}) != 19
        or {row["valueset_id"] for row in approvals} != CLINICAL_VALUESET_IDS
    ):
        raise ValueError(
            f"{approval_path}: expected one unique approval for each of 19 clinical ValueSets"
        )
    if not empty_valuesets <= CLINICAL_VALUESET_IDS:
        raise ValueError(f"unexpected empty ValueSets: {sorted(empty_valuesets - CLINICAL_VALUESET_IDS)}")

    cql = cql_path.read_text(encoding="utf-8")
    executable_cql = strip_cql_comments(cql)
    declarations = dict(VALUESET_DECLARATION.findall(executable_cql))
    cql_without_valueset_declarations = VALUESET_DECLARATION.sub("", executable_cql)
    for row in approvals:
        for field in (
            "approval_id", "valueset_id", "cql_usage_status", "intended_semantics",
            "candidate_code_system_family", "authoritative_source_version",
            "content_status", "current_status", "required_reviewer",
            "acceptance_evidence",
        ):
            if not row[field].strip():
                raise ValueError(f"{approval_path}: {row['valueset_id']} has empty {field}")
        expected_content = (
            "empty-blocking" if row["valueset_id"] in empty_valuesets
            else "approved" if approval_complete(row)
            else "content-present-review-pending"
        )
        if row["content_status"] != expected_content:
            raise ValueError(
                f"{approval_path}: {row['valueset_id']} content_status must be {expected_content}"
            )
        if row["cql_usage_status"] == "referenced":
            identifier = row["cql_identifier"]
            expected_url = f"{CANONICAL}ValueSet/{row['valueset_id']}"
            if declarations.get(identifier) != expected_url:
                raise ValueError(f"{approval_path}: {row['valueset_id']} stale CQL declaration")
            if f'"{identifier}"' not in cql_without_valueset_declarations:
                raise ValueError(f"{approval_path}: {row['valueset_id']} is declared but unused")
        elif row["cql_usage_status"] == "defined-not-referenced":
            if row["cql_identifier"] or row["valueset_id"] in executable_cql:
                raise ValueError(f"{approval_path}: {row['valueset_id']} usage status is stale")
        else:
            raise ValueError(f"{approval_path}: invalid cql_usage_status")

    approved = sum(approval_complete(row) for row in approvals)
    validated_expansions, validated_expansion_codes = audit_expansion_evidence(
        expansion_register_path,
        approvals,
        resources,
        code_systems_by_url,
        code_system_code_sets,
        repository_root_for_register(expansion_register_path),
    )
    approved_relationships, relationship_count = audit_conceptmap_relationships(
        relationship_register_path,
        resources,
        code_systems_by_url,
        code_system_code_sets,
        repository_root_for_register(relationship_register_path),
    )
    versionless_clinical_valuesets = sum(
        not str(resources[("ValueSet", resource_id)].get("version", "")).strip()
        for resource_id in CLINICAL_VALUESET_IDS
    )
    return {
        "gate_scope": "complete-local-terminology-technical-and-clinical",
        "terminology_integrity_gate": "pass",
        "terminology_artifact_count": len(resources),
        "code_system_count": counts["CodeSystem"],
        "value_set_count": counts["ValueSet"],
        "concept_map_count": counts["ConceptMap"],
        "empty_clinical_value_set_count": len(empty_valuesets),
        "clinical_value_set_approval_count": len(approvals),
        "approved_clinical_value_set_count": approved,
        "validated_clinical_value_set_expansion_count": validated_expansions,
        "validated_clinical_expansion_code_count": validated_expansion_codes,
        "versionless_clinical_value_set_count": versionless_clinical_valuesets,
        "concept_map_relationship_count": relationship_count,
        "approved_concept_map_relationship_count": approved_relationships,
        "local_value_set_code_reference_count": local_valueset_code_reference_count,
        "duplicate_code_system_code_count": duplicate_code_system_code_count,
        "clinical_terminology_gate": (
            "pass" if (
                not empty_valuesets
                and approved == len(approvals)
                and validated_expansions == len(approvals)
                and versionless_clinical_valuesets == 0
                and approved_relationships == relationship_count
            ) else "block"
        ),
        "external_code_systems": sorted(external_systems),
        "maximum_supported_claim": "technical-draft-terminology-inventory",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval-register", type=Path, required=True)
    parser.add_argument("--expansion-register", type=Path, required=True)
    parser.add_argument("--relationship-register", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, action="append", required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "clinical"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(
            args.approval_register,
            args.expansion_register,
            args.relationship_register,
            args.cql,
            args.resource_dir,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Terminology audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Terminology: {report['terminology_artifact_count']} artifacts "
        f"({report['code_system_count']} CodeSystems, "
        f"{report['value_set_count']} ValueSets, "
        f"{report['concept_map_count']} ConceptMaps)"
    )
    print(
        f"Clinical ValueSets: empty={report['empty_clinical_value_set_count']}; "
        f"approved={report['approved_clinical_value_set_count']}/"
        f"{report['clinical_value_set_approval_count']}; "
        f"validated expansions={report['validated_clinical_value_set_expansion_count']}/"
        f"{report['clinical_value_set_approval_count']}"
    )
    print(
        f"ConceptMap relationships: approved="
        f"{report['approved_concept_map_relationship_count']}/"
        f"{report['concept_map_relationship_count']}"
    )
    print(f"Terminology integrity gate: {report['terminology_integrity_gate']}")
    print(f"Clinical terminology gate: {report['clinical_terminology_gate']}")
    selected = {
        "integrity": "terminology_integrity_gate",
        "clinical": "clinical_terminology_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
