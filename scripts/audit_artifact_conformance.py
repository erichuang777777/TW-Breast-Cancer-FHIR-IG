#!/usr/bin/env python3
"""Audit every local StructureDefinition against its declared release evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path


REQUIRED_COLUMNS = {
    "artifact_id", "artifact_name", "artifact_kind", "scope_claim_id",
    "expected_type", "expected_kind", "expected_base_definition",
    "evidence_mode", "example_resource_id", "technical_status",
    "clinical_review_status", "required_reviewer", "review_requirement",
    "decision", "signer_name", "signer_organization_title", "decision_date",
    "evidence_uri_path", "signed_artifact_sha256", "notes",
}
EVIDENCE_MODES = {"direct-profile", "derived-profile", "extension-use"}
SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    actual = set(rows[0]) if rows else set()
    if not rows or actual != REQUIRED_COLUMNS:
        raise ValueError(f"{path}: expected exact columns {sorted(REQUIRED_COLUMNS)}")
    return rows


def approval_complete(row: dict[str, str]) -> bool:
    if row["clinical_review_status"] != "approved" or row["decision"] != "approve":
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


def load_resources(paths: list[Path]) -> list[dict[str, object]]:
    resources: list[dict[str, object]] = []
    for directory in paths:
        if not directory.is_dir():
            raise ValueError(f"{directory}: resource directory does not exist")
        for path in directory.glob("*.json"):
            try:
                resource = json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: invalid JSON: {exc}") from exc
            if isinstance(resource, dict) and resource.get("resourceType"):
                resources.append(resource)
    return resources


def contains_extension(value: object, canonical: str) -> bool:
    if isinstance(value, dict):
        if value.get("url") == canonical:
            return True
        return any(contains_extension(child, canonical) for child in value.values())
    if isinstance(value, list):
        return any(contains_extension(child, canonical) for child in value)
    return False


def audit(
    register_path: Path,
    scope_claims_path: Path,
    resource_dirs: list[Path],
) -> dict[str, object]:
    rows = read_csv(register_path)
    if len(rows) != 46 or len({row["artifact_id"] for row in rows}) != 46:
        raise ValueError(f"{register_path}: expected exactly 46 unique artifacts")
    if len({row["artifact_name"] for row in rows}) != 46:
        raise ValueError(f"{register_path}: artifact_name must be unique")
    if sum(row["artifact_kind"] == "profile" for row in rows) != 33:
        raise ValueError(f"{register_path}: expected exactly 33 profiles")
    if sum(row["artifact_kind"] == "extension" for row in rows) != 13:
        raise ValueError(f"{register_path}: expected exactly 13 extensions")

    with scope_claims_path.open(encoding="utf-8-sig", newline="") as handle:
        scope_rows = list(csv.DictReader(handle))
    scope_ids = {row["claim_id"] for row in scope_rows}
    if not scope_ids or any(row["scope_claim_id"] not in scope_ids for row in rows):
        raise ValueError(f"{register_path}: unknown scope_claim_id")

    resources = load_resources(resource_dirs)
    structures = {
        str(resource["id"]): resource
        for resource in resources
        if resource.get("resourceType") == "StructureDefinition"
        and str(resource.get("url", "")).startswith(
            "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
        )
    }
    if set(structures) != {row["artifact_id"] for row in rows}:
        missing = sorted({row["artifact_id"] for row in rows} - set(structures))
        extra = sorted(set(structures) - {row["artifact_id"] for row in rows})
        raise ValueError(
            f"generated StructureDefinition set mismatch; missing={missing}; extra={extra}"
        )

    examples: dict[str, list[dict[str, object]]] = {}
    for resource in resources:
        if resource.get("resourceType") not in {
            "StructureDefinition", "CodeSystem", "ValueSet", "ConceptMap",
            "NamingSystem", "CapabilityStatement", "ImplementationGuide",
            "Library", "Measure",
        } and resource.get("id"):
            examples.setdefault(str(resource["id"]), []).append(resource)

    canonical_root = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/"

    def derives_from(profile_url: str, target_url: str) -> bool:
        seen: set[str] = set()
        current = profile_url
        while current.startswith(canonical_root) and current not in seen:
            seen.add(current)
            artifact = structures.get(current.removeprefix(canonical_root))
            if not artifact:
                return False
            base = str(artifact.get("baseDefinition", ""))
            if base == target_url:
                return True
            current = base
        return False

    for row in rows:
        for field in (
            "artifact_id", "artifact_name", "artifact_kind", "scope_claim_id",
            "expected_type", "expected_kind", "expected_base_definition",
            "evidence_mode", "example_resource_id", "technical_status",
            "clinical_review_status", "required_reviewer", "review_requirement",
        ):
            if not row[field].strip():
                raise ValueError(f"{register_path}: {row['artifact_id']} has empty {field}")
        if row["artifact_kind"] not in {"profile", "extension"}:
            raise ValueError(f"{register_path}: {row['artifact_id']} invalid artifact_kind")
        if row["evidence_mode"] not in EVIDENCE_MODES:
            raise ValueError(f"{register_path}: {row['artifact_id']} invalid evidence_mode")
        if row["technical_status"] != "pass-publisher-synthetic-example":
            raise ValueError(f"{register_path}: {row['artifact_id']} invalid technical_status")

        artifact = structures[row["artifact_id"]]
        expected = {
            "name": row["artifact_name"],
            "type": row["expected_type"],
            "kind": row["expected_kind"],
            "baseDefinition": row["expected_base_definition"],
            "derivation": "constraint",
            "status": "draft",
            "experimental": True,
        }
        for field, value in expected.items():
            if artifact.get(field) != value:
                raise ValueError(
                    f"{row['artifact_id']}: generated {field}={artifact.get(field)!r}, "
                    f"expected {value!r}"
                )

        candidates = examples.get(row["example_resource_id"], [])
        if not candidates:
            raise ValueError(
                f"{row['artifact_id']}: missing example {row['example_resource_id']}"
            )
        canonical = canonical_root + row["artifact_id"]
        if row["evidence_mode"] == "extension-use":
            evidenced = any(contains_extension(example, canonical) for example in candidates)
        else:
            profile_urls = [
                str(url)
                for example in candidates
                if example.get("resourceType") == row["expected_type"]
                for url in example.get("meta", {}).get("profile", [])
            ]
            evidenced = canonical in profile_urls if row["evidence_mode"] == "direct-profile" else any(
                derives_from(url, canonical) for url in profile_urls
            )
        if not evidenced:
            raise ValueError(
                f"{row['artifact_id']}: example {row['example_resource_id']} does not prove "
                f"{row['evidence_mode']}"
            )

    return {
        "gate_scope": "artifact-structure-and-example-only",
        "artifact_integrity_gate": "pass",
        "artifact_count": len(rows),
        "profile_count": sum(row["artifact_kind"] == "profile" for row in rows),
        "extension_count": sum(row["artifact_kind"] == "extension" for row in rows),
        "approved_artifact_count": sum(approval_complete(row) for row in rows),
        "clinical_artifact_approval_gate": (
            "pass" if all(approval_complete(row) for row in rows) else "block"
        ),
        "maximum_supported_claim": "technical-structure-with-synthetic-examples",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--scope-claims", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, action="append", required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "clinical"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(args.register, args.scope_claims, args.resource_dir)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Artifact-conformance audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Artifact conformance: {report['artifact_count']} total "
        f"({report['profile_count']} profiles, {report['extension_count']} extensions); "
        f"approved={report['approved_artifact_count']}"
    )
    print(f"Artifact integrity gate: {report['artifact_integrity_gate']}")
    print(f"Clinical artifact approval gate: {report['clinical_artifact_approval_gate']}")
    selected = {
        "integrity": "artifact_integrity_gate",
        "clinical": "clinical_artifact_approval_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
