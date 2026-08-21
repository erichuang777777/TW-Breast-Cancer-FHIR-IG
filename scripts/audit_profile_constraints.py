#!/usr/bin/env python3
"""Lock every local StructureDefinition differential element to a review baseline.

Publisher proves that a differential is valid FHIR.  This audit proves a
different property: the exact constraints presented for review have not drifted
since the baseline was prepared.  It deliberately does not claim that those
constraints are clinically correct or approved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


CANONICAL_ROOT = (
    "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/"
    "StructureDefinition/"
)
BASELINE_COLUMNS = (
    "artifact_id",
    "element_id",
    "path",
    "slice_name",
    "facets",
    "cardinality",
    "must_support",
    "binding_strength",
    "binding_value_set",
    "type_constraints_json",
    "fixed_pattern_fields",
    "slicing_json",
    "invariant_keys",
    "constraint_sha256",
)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_structures(resource_dirs: list[Path]) -> dict[str, dict[str, object]]:
    structures: dict[str, dict[str, object]] = {}
    for directory in resource_dirs:
        if not directory.is_dir():
            raise ValueError(f"{directory}: resource directory does not exist")
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
            artifact_id = str(resource.get("id", "")).strip()
            if not artifact_id:
                raise ValueError(f"{path}: local StructureDefinition has no id")
            if artifact_id in structures:
                raise ValueError(f"duplicate local StructureDefinition id {artifact_id}")
            structures[artifact_id] = resource
    if not structures:
        raise ValueError("no local StructureDefinitions found")
    return structures


def constraint_row(
    artifact_id: str, element: dict[str, object]
) -> dict[str, str]:
    element_id = str(element.get("id", "")).strip()
    path = str(element.get("path", "")).strip()
    if not element_id or not path:
        raise ValueError(
            f"{artifact_id}: every differential element must have non-empty id and path"
        )

    binding = element.get("binding")
    binding = binding if isinstance(binding, dict) else {}
    types = element.get("type")
    types = types if isinstance(types, list) else []
    slicing = element.get("slicing")
    slicing = slicing if isinstance(slicing, dict) else {}
    constraints = element.get("constraint")
    constraints = constraints if isinstance(constraints, list) else []
    fixed_pattern_fields = sorted(
        key for key in element if key.startswith(("fixed", "pattern"))
    )

    facets: list[str] = []
    if "min" in element or "max" in element:
        facets.append("cardinality")
    if element.get("mustSupport") is True:
        facets.append("must-support")
    if binding:
        facets.append("binding")
    if types:
        facets.append("type")
    if fixed_pattern_fields:
        facets.append("fixed-or-pattern")
    if slicing:
        facets.append("slicing")
    if constraints:
        facets.append("invariant")
    if not facets:
        facets.append("declaration-or-narrative")

    minimum = "" if "min" not in element else str(element["min"])
    maximum = "" if "max" not in element else str(element["max"])
    cardinality = f"{minimum}..{maximum}" if minimum or maximum else ""
    normalized = compact_json(element)
    return {
        "artifact_id": artifact_id,
        "element_id": element_id,
        "path": path,
        "slice_name": str(element.get("sliceName", "")),
        "facets": ";".join(facets),
        "cardinality": cardinality,
        "must_support": "true" if element.get("mustSupport") is True else "false",
        "binding_strength": str(binding.get("strength", "")),
        "binding_value_set": str(binding.get("valueSet", "")),
        "type_constraints_json": compact_json(types) if types else "",
        "fixed_pattern_fields": ";".join(fixed_pattern_fields),
        "slicing_json": compact_json(slicing) if slicing else "",
        "invariant_keys": ";".join(
            sorted(str(item.get("key", "")) for item in constraints if item.get("key"))
        ),
        "constraint_sha256": sha256_text(normalized),
    }


def live_rows(structures: dict[str, dict[str, object]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for artifact_id, structure in sorted(structures.items()):
        differential = structure.get("differential")
        differential = differential if isinstance(differential, dict) else {}
        elements = differential.get("element")
        if not isinstance(elements, list) or not elements:
            raise ValueError(f"{artifact_id}: differential.element is empty")
        for element in elements:
            if not isinstance(element, dict):
                raise ValueError(f"{artifact_id}: differential element is not an object")
            row = constraint_row(artifact_id, element)
            key = (artifact_id, row["element_id"])
            if key in seen:
                raise ValueError(f"{artifact_id}: duplicate differential id {key[1]}")
            seen.add(key)
            rows.append(row)
    return rows


def read_baseline(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != BASELINE_COLUMNS:
            raise ValueError(f"{path}: expected exact columns {list(BASELINE_COLUMNS)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path}: baseline is empty")
    keys = [(row["artifact_id"], row["element_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{path}: duplicate artifact_id/element_id")
    return rows


def write_baseline(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BASELINE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def manifest_sha256(rows: list[dict[str, str]]) -> str:
    return sha256_text(compact_json(rows))


def audit(baseline_path: Path, resource_dirs: list[Path]) -> dict[str, object]:
    structures = load_structures(resource_dirs)
    actual = live_rows(structures)
    expected = read_baseline(baseline_path)
    actual_by_key = {(r["artifact_id"], r["element_id"]): r for r in actual}
    expected_by_key = {(r["artifact_id"], r["element_id"]): r for r in expected}
    if set(actual_by_key) != set(expected_by_key):
        missing = sorted(set(expected_by_key) - set(actual_by_key))
        extra = sorted(set(actual_by_key) - set(expected_by_key))
        raise ValueError(
            f"profile constraint set drift; missing={missing}; extra={extra}"
        )
    actual_order = [(r["artifact_id"], r["element_id"]) for r in actual]
    expected_order = [(r["artifact_id"], r["element_id"]) for r in expected]
    if actual_order != expected_order:
        first = next(
            index for index, pair in enumerate(zip(actual_order, expected_order))
            if pair[0] != pair[1]
        )
        raise ValueError(
            "profile differential order drift at row "
            f"{first + 2}; actual={actual_order[first]}; "
            f"expected={expected_order[first]}"
        )
    for key in sorted(actual_by_key):
        if actual_by_key[key] != expected_by_key[key]:
            changed = [
                column for column in BASELINE_COLUMNS
                if actual_by_key[key][column] != expected_by_key[key][column]
            ]
            raise ValueError(
                f"profile constraint drift at {key[0]} / {key[1]}; "
                f"changed columns={changed}"
            )

    facet_counts = {
        facet: sum(facet in row["facets"].split(";") for row in actual)
        for facet in (
            "cardinality", "must-support", "binding", "type",
            "fixed-or-pattern", "slicing", "invariant",
            "declaration-or-narrative",
        )
    }
    per_profile = {
        artifact_id: sum(row["artifact_id"] == artifact_id for row in actual)
        for artifact_id in sorted(structures)
    }
    return {
        "gate_scope": "exact-local-profile-differential-constraint-baseline",
        "constraint_baseline_gate": "pass",
        "structure_definition_count": len(structures),
        "differential_element_count": len(actual),
        "facet_counts": facet_counts,
        "per_profile_element_counts": per_profile,
        "constraint_manifest_sha256": manifest_sha256(actual),
        "clinical_correctness_gate": "not-assessed-requires-exact-artifact-approval",
        "maximum_supported_claim": "locked-technical-differential-not-clinically-approved",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--resource-dir", type=Path, action="append", required=True)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        if args.write_baseline:
            rows = live_rows(load_structures(args.resource_dir))
            write_baseline(args.baseline, rows)
            print(
                f"Wrote profile constraint baseline: {len(rows)} elements to "
                f"{args.baseline}"
            )
            return 0
        report = audit(args.baseline, args.resource_dir)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Profile constraint audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        "Profile constraints: "
        f"{report['structure_definition_count']} StructureDefinitions; "
        f"{report['differential_element_count']} differential elements"
    )
    print(f"Constraint baseline gate: {report['constraint_baseline_gate']}")
    print(f"Maximum supported claim: {report['maximum_supported_claim']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
