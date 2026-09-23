"""Build a deterministic 100-patient TW breast-cancer FHIR test pack.

The MITRE mCODE STU2/Synthea archives are immutable inputs. Every selected
FHIR resource and element is preserved. Recognized oncology resources receive
an additional TW Breast Cancer IG profile declaration; the original mCODE and
US Core declarations remain intact for subsequent dual-conformance testing.

The output is synthetic software-test data. It is not population representative
and must not be used for clinical decisions.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "outputs" / "synthetic_cohort" / "tw-breast-cancer-synthetic-100-v0.1.zip"
CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition"
DATASET_TIMESTAMP = "2026-09-23T00:00:00Z"
ZIP_TIMESTAMP = (2026, 9, 23, 0, 0, 0)
SOURCES = (
    ("10-year", ROOT / "mcode_2_0_10yrs_breast.zip", 50),
    ("longitudinal", ROOT / "mcode_2_0_longitudinal_breast.zip", 50),
)
EXCLUDED_MEMBER_TOKENS = ("__MACOSX", "hospitalInformation", "practitionerInformation")

LOCAL_PROFILES = {
    "Patient": f"{CANONICAL}/breast-cancer-patient",
    "PrimaryCancerCondition": f"{CANONICAL}/breast-cancer-primary-condition",
    "StageGroup": f"{CANONICAL}/breast-cancer-stage-group-observation",
    "TumorMarker": f"{CANONICAL}/breast-cancer-tumor-marker-observation",
    "TreatmentProcedure": f"{CANONICAL}/breast-cancer-treatment-procedure",
    "MedicationRequest": f"{CANONICAL}/breast-cancer-medication-request",
    "EpisodeOfCare": f"{CANONICAL}/breast-cancer-episode-of-care",
}


def json_members(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name for name in archive.namelist()
        if name.lower().endswith(".json")
        and not any(token in name for token in EXCLUDED_MEMBER_TOKENS)
    )


def stable_selection(names: Iterable[str], count: int, seed: str, cohort: str) -> list[str]:
    ranked = sorted(
        names,
        key=lambda name: hashlib.sha256(f"{seed}\0{cohort}\0{name}".encode("utf-8")).digest(),
    )
    if len(ranked) < count:
        raise ValueError(f"{cohort}: found {len(ranked)} patient files, need {count}")
    return ranked[:count]


def profiles(resource: dict[str, Any]) -> list[str]:
    values = resource.get("meta", {}).get("profile", [])
    return values if isinstance(values, list) else []


def local_role(resource: dict[str, Any]) -> str | None:
    resource_type = resource.get("resourceType")
    profile_text = " ".join(profiles(resource)).lower()
    if resource_type == "Patient":
        return "Patient"
    if resource_type == "Condition" and "primary-cancer-condition" in profile_text:
        return "PrimaryCancerCondition"
    if resource_type == "Observation" and "stage-group" in profile_text:
        return "StageGroup"
    if resource_type == "Observation" and "tumor-marker" in profile_text:
        return "TumorMarker"
    if resource_type == "Procedure" and any(token in profile_text for token in ("cancer-related", "radiotherapy")):
        return "TreatmentProcedure"
    if resource_type == "MedicationRequest" and "cancer-related" in profile_text:
        return "MedicationRequest"
    if resource_type == "EpisodeOfCare":
        return "EpisodeOfCare"
    return None


def add_profile(resource: dict[str, Any], profile: str) -> None:
    declared = resource.setdefault("meta", {}).setdefault("profile", [])
    if profile not in declared:
        declared.append(profile)


def transform_bundle(source: dict[str, Any]) -> tuple[dict[str, Any], Counter[str]]:
    """Return a deep-copied, field-preserving bundle with local profile claims."""
    transformed = deepcopy(source)
    role_counts: Counter[str] = Counter()
    for entry in transformed.get("entry", []):
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            continue
        role = local_role(resource)
        if role:
            add_profile(resource, LOCAL_PROFILES[role])
            role_counts[role] += 1
    return transformed, role_counts


def bundle_patient_id(bundle: dict[str, Any]) -> str:
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return str(resource.get("id", ""))
    return ""


def compact_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def unresolved_urn_references(bundle: dict[str, Any]) -> Counter[str]:
    """Count URN references not resolved by an entry fullUrl, grouped by path."""
    full_urls = {entry.get("fullUrl") for entry in bundle.get("entry", []) if entry.get("fullUrl")}
    unresolved: Counter[str] = Counter()

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "reference" and isinstance(child, str) and child.startswith("urn:uuid:"):
                    if child not in full_urls:
                        unresolved[child_path] += 1
                else:
                    walk(child, child_path)
        elif isinstance(value, list):
            for child in value:
                walk(child, f"{path}[]")

    walk(bundle)
    return unresolved


def zip_write(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def build(output: Path, seed: str) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    resource_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    unresolved_counts: Counter[str] = Counter()
    payloads: list[tuple[str, bytes]] = []
    sequence = 0

    for cohort, source_path, requested in SOURCES:
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source archive: {source_path}")
        with zipfile.ZipFile(source_path) as source_zip:
            selected = stable_selection(json_members(source_zip), requested, seed, cohort)
            for member in selected:
                sequence += 1
                cohort_id = f"twbc-{sequence:04d}"
                source_bytes = source_zip.read(member)
                source_bundle = json.loads(source_bytes)
                if source_bundle.get("resourceType") != "Bundle":
                    raise ValueError(f"{member} is not a FHIR Bundle")
                transformed, roles = transform_bundle(source_bundle)
                transformed_bytes = compact_json(transformed)
                entry_resources = [
                    entry["resource"] for entry in transformed.get("entry", [])
                    if isinstance(entry.get("resource"), dict)
                ]
                counts = Counter(resource.get("resourceType", "Unknown") for resource in entry_resources)
                resource_counts.update(counts)
                role_counts.update(roles)
                unresolved_counts.update(unresolved_urn_references(transformed))
                source_counts[cohort] += 1
                output_name = f"patients/{cohort_id}.json"
                payloads.append((output_name, transformed_bytes))
                rows.append({
                    "cohort_id": cohort_id,
                    "source_cohort": cohort,
                    "source_archive": source_path.name,
                    "source_member": member,
                    "source_patient_id": bundle_patient_id(source_bundle),
                    "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                    "output_file": output_name,
                    "output_sha256": hashlib.sha256(transformed_bytes).hexdigest(),
                    "resource_count": len(entry_resources),
                    "local_profile_count": sum(roles.values()),
                })

    summary = {
        "dataset": "TW Breast Cancer IG Synthetic Test Cohort",
        "version": "0.1",
        "generated_at": DATASET_TIMESTAMP,
        "seed": seed,
        "patient_count": len(rows),
        "source_counts": dict(source_counts),
        "resource_counts": dict(sorted(resource_counts.items())),
        "local_profile_role_counts": dict(sorted(role_counts.items())),
        "unresolved_urn_reference_counts": dict(sorted(unresolved_counts.items())),
        "properties": {
            "synthetic": True,
            "clinical_use": False,
            "population_representative": False,
            "language_translation": "none; original English content retained",
            "source_field_policy": "all FHIR resources and elements preserved",
            "profile_policy": "original profiles retained; recognized resources receive an additional local profile claim",
            "reference_note": "unresolved URNs are retained source Provenance.target lineage references; clinical graph references resolve within each Bundle",
        },
    }

    manifest_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(manifest_buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    readme = """# TW Breast Cancer IG Synthetic Test Cohort v0.1

This archive contains 100 fully synthetic FHIR R4 patient Bundles selected
deterministically from the MITRE mCODE STU2 breast-cancer Synthea datasets:
50 ten-year histories and 50 longitudinal histories.

Source archives:
- Ten years: https://mitre.box.com/shared/static/c6ca6y2jfumrhw4nu20kztktxdlhhzo8.zip
- Longitudinal: https://mitre.box.com/shared/static/59n7mcm8si0qk3p36ud0vmrcdv7pr0s7.zip

All original FHIR resources and elements are retained. Recognized oncology
resources also declare the corresponding TW Breast Cancer IG draft profile;
original mCODE and US Core profile declarations remain available for testing.
The clinical text remains in English.

The dataset is intended only for FHIR server, SMART on FHIR, CQL, mapping and
conformance testing. It is not representative of Taiwan's population and must
not be used for clinical decisions, official submission or model validation.

Files:
- patients/twbc-0001.json through patients/twbc-0100.json
- manifest.csv: deterministic source and output lineage with SHA-256 hashes
- summary.json: cohort and resource coverage
"""

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as target:
        zip_write(target, "README.md", readme.encode("utf-8"))
        zip_write(target, "manifest.csv", manifest_buffer.getvalue().encode("utf-8"))
        zip_write(target, "summary.json", compact_json(summary))
        for name, data in payloads:
            zip_write(target, name, data)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", default="tw-breast-ca-ig-v0.1")
    args = parser.parse_args()
    summary = build(args.output.resolve(), args.seed)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
