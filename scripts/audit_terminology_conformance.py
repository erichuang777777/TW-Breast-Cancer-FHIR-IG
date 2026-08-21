#!/usr/bin/env python3
"""Audit the complete local terminology set and clinical ValueSet approvals."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
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
            resources[key] = resource
    return resources


def audit(
    approval_path: Path,
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

    code_system_urls = {
        str(resource.get("url"))
        for (resource_type, _), resource in resources.items()
        if resource_type == "CodeSystem"
    }
    empty_valuesets: set[str] = set()
    external_systems: set[str] = set()
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

    with approval_path.open(encoding="utf-8-sig", newline="") as handle:
        approvals = list(csv.DictReader(handle))
    actual_columns = set(approvals[0]) if approvals else set()
    if actual_columns != REQUIRED_APPROVAL_COLUMNS:
        raise ValueError(f"{approval_path}: invalid columns")
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
        "clinical_terminology_gate": (
            "pass" if not empty_valuesets and approved == len(approvals) else "block"
        ),
        "external_code_systems": sorted(external_systems),
        "maximum_supported_claim": "technical-draft-terminology-inventory",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval-register", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, action="append", required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "clinical"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(args.approval_register, args.cql, args.resource_dir)
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
        f"{report['clinical_value_set_approval_count']}"
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
