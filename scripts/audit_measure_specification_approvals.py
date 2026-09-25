#!/usr/bin/env python3
"""Bind every approved Measure decision to the exact executable specification."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:
    from scripts.approval_evidence import (
        file_sha256,
        resolve_repository_evidence,
        retained_evidence_matches,
    )
except ModuleNotFoundError:  # direct execution
    from approval_evidence import (
        file_sha256,
        resolve_repository_evidence,
        retained_evidence_matches,
    )


APPROVAL_COLUMNS = {
    "approval_id", "measure_id", "indicator_family", "decision_scope",
    "known_issue", "current_status", "required_signer", "acceptance_evidence",
    "decision", "signer_name", "signer_organization_title", "decision_date",
    "evidence_uri_path", "signed_artifact_sha256", "notes",
}
AUDIT_COLUMNS = {
    "measure_id", "indicator_family", "fhir_conformance", "cql_execution",
    "draft_definition_alignment", "terminology_evidence", "raw_source_mapping",
    "independent_recalculation", "golden_cohort", "current_verdict",
    "blocking_issue", "required_approval",
}
CATALOG_COLUMNS = {
    "measure_id", "indicator_family", "measure_kind", "core_indicator",
    "title_zh", "scoring", "improvement_notation", "reporting_unit",
    "threshold_owner", "threshold_2026", "reference_result", "fhir_artifacts",
    "status",
}
CRITERIA_COLUMNS = {
    "measure_id", "indicator_family", "population_type", "criterion_id",
    "variant", "criterion_zh", "fhir_expression", "depends_on_mapping",
    "current_proxy", "proxy_removed_by_fhir", "cql_status", "python_status",
    "review_status", "python_divergence",
}
APPROVAL_CONTEXT_FIELDS = (
    "approval_id", "measure_id", "indicator_family", "decision_scope",
    "known_issue", "required_signer", "acceptance_evidence",
)
COMPONENT_KEYS = {
    "measure_fsh_sha256", "cql_sha256", "generated_measure_sha256",
    "catalog_row_sha256", "population_criteria_sha256",
    "measure_audit_row_sha256", "approval_context_sha256",
}
TRUTH_CASE_KEYS = {
    "case_id", "criterion_id", "expected_result", "boundary_class", "rationale",
}
SHA256 = re.compile(r"[0-9a-fA-F]{64}")


def read_rows(path: Path, columns: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != columns:
            raise ValueError(f"{path}: invalid columns")
        return list(reader)


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure_expressions(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    result: dict[str, list[str]] = {}
    for block in text.split("\nInstance: ")[1:]:
        if "InstanceOf: Measure" not in block:
            continue
        match = re.search(r'\* id = "(bc-q[ir]-\d+)"', block)
        if not match:
            raise ValueError(f"{path}: Measure without a supported id")
        measure_id = match.group(1)
        expressions = re.findall(r'criteria\.expression = "([^"]+)"', block)
        if not expressions or len(expressions) != len(set(expressions)):
            raise ValueError(f"{path}: missing or duplicate expressions for {measure_id}")
        result[measure_id] = sorted(expressions)
    unique = {item for values in result.values() for item in values}
    if len(result) != 20 or sum(map(len, result.values())) != 62 or len(unique) != 46:
        raise ValueError(f"{path}: expected 20 Measures, 62 uses and 46 expressions")
    return result


def generated_measures(path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for resource_path in path.glob("Measure-*.json"):
        resource = json.loads(resource_path.read_text(encoding="utf-8-sig"))
        measure_id = str(resource.get("id", ""))
        if re.fullmatch(r"bc-q[ir]-\d+", measure_id):
            if measure_id in result:
                raise ValueError(f"{path}: duplicate generated Measure {measure_id}")
            result[measure_id] = resource
    if len(result) != 20:
        raise ValueError(f"{path}: expected exactly 20 generated Measures")
    return result


def generated_measure_expressions(resource: dict[str, object]) -> list[str]:
    expressions: list[str] = []
    for group in resource.get("group", []):
        for population in group.get("population", []):
            expression = population.get("criteria", {}).get("expression")
            if expression:
                expressions.append(str(expression))
        for stratifier in group.get("stratifier", []):
            expression = stratifier.get("criteria", {}).get("expression")
            if expression:
                expressions.append(str(expression))
            for component in stratifier.get("component", []):
                expression = component.get("criteria", {}).get("expression")
                if expression:
                    expressions.append(str(expression))
    return sorted(expressions)


def approval_shape_complete(row: dict[str, str]) -> bool:
    if row["current_status"] != "approved" or row["decision"] != "approve":
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
    return SHA256.fullmatch(row["signed_artifact_sha256"]) is not None


def parse_reviewed_at(raw: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid reviewed_at") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: reviewed_at must include timezone")
    return parsed


def validate_truth_table(
    bundle: dict[str, object],
    bundle_path: Path,
    register_path: Path,
    measure_id: str,
    criterion_ids: set[str],
    label: str,
) -> int:
    truth_path_raw = str(bundle.get("truth_table_path", ""))
    truth_hash = str(bundle.get("truth_table_sha256", ""))
    if SHA256.fullmatch(truth_hash) is None:
        raise ValueError(f"{label}: invalid truth-table SHA-256")
    truth_path = resolve_repository_evidence(truth_path_raw, register_path)
    if not truth_path or file_sha256(truth_path).lower() != truth_hash.lower():
        raise ValueError(f"{label}: truth table missing or SHA-256 mismatched")
    if truth_path.resolve() == bundle_path.resolve():
        raise ValueError(f"{label}: truth table must be a distinct artifact")
    truth = json.loads(truth_path.read_text(encoding="utf-8-sig"))
    if (
        not isinstance(truth, dict)
        or set(truth) != {"schema_version", "measure_id", "cases"}
        or truth.get("schema_version") != "1.0"
        or truth.get("measure_id") != measure_id
        or not isinstance(truth.get("cases"), list)
    ):
        raise ValueError(f"{label}: invalid truth-table identity or schema")
    observed: set[tuple[str, bool]] = set()
    case_keys: set[tuple[str, str]] = set()
    for case in truth["cases"]:
        if not isinstance(case, dict) or set(case) != TRUTH_CASE_KEYS:
            raise ValueError(f"{label}: invalid truth-table case schema")
        case_id = str(case["case_id"]).strip()
        criterion_id = str(case["criterion_id"]).strip()
        expected = case["expected_result"]
        if (
            not case_id
            or criterion_id not in criterion_ids
            or type(expected) is not bool
            or not str(case["boundary_class"]).strip()
            or not str(case["rationale"]).strip()
        ):
            raise ValueError(f"{label}: incomplete or unknown truth-table case")
        case_key = (case_id, criterion_id)
        if case_key in case_keys:
            raise ValueError(f"{label}: duplicate case/criterion truth assertion")
        case_keys.add(case_key)
        observed.add((criterion_id, expected))
    expected_coverage = {
        (criterion_id, expected)
        for criterion_id in criterion_ids
        for expected in (False, True)
    }
    if observed != expected_coverage:
        raise ValueError(f"{label}: truth table lacks exact positive/negative criterion coverage")
    return len(truth["cases"])


def validate_bundle(
    row: dict[str, str],
    register_path: Path,
    components: dict[str, str],
    expressions: list[str],
    criterion_ids: set[str],
) -> int:
    measure_id = row["measure_id"]
    label = f"{register_path}: {measure_id}"
    if not approval_shape_complete(row) or not retained_evidence_matches(
        row,
        register_path,
        path_field="evidence_uri_path",
        hash_field="signed_artifact_sha256",
    ):
        raise ValueError(f"{label}: approval bundle is missing or SHA-256 mismatched")
    bundle_path = resolve_repository_evidence(row["evidence_uri_path"], register_path)
    assert bundle_path is not None
    bundle = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
    required_keys = {
        "schema_version", "measure_id", "specification_fingerprint",
        "component_hashes", "reviewed_expression_ids", "reviewed_criterion_ids",
        "known_issue_resolutions", "unresolved_issue_count", "truth_table_path",
        "truth_table_sha256", "reviewer_name", "reviewer_organization_title",
        "reviewed_at",
    }
    if not isinstance(bundle, dict) or set(bundle) != required_keys:
        raise ValueError(f"{label}: invalid approval-bundle schema")
    if bundle["schema_version"] != "1.0" or bundle["measure_id"] != measure_id:
        raise ValueError(f"{label}: approval-bundle identity mismatch")
    component_hashes = bundle["component_hashes"]
    if not isinstance(component_hashes, dict) or set(component_hashes) != COMPONENT_KEYS:
        raise ValueError(f"{label}: invalid component hash set")
    if component_hashes != components:
        raise ValueError(f"{label}: approval bundle is stale against live specification")
    fingerprint = canonical_sha256(components)
    if bundle["specification_fingerprint"] != fingerprint:
        raise ValueError(f"{label}: specification fingerprint mismatch")
    if bundle["reviewed_expression_ids"] != expressions:
        raise ValueError(f"{label}: reviewed expression set mismatch")
    if bundle["reviewed_criterion_ids"] != sorted(criterion_ids):
        raise ValueError(f"{label}: reviewed criterion set mismatch")
    if bundle["unresolved_issue_count"] != 0:
        raise ValueError(f"{label}: unresolved issue count must be zero")
    issues = [item.strip() for item in row["known_issue"].split(";") if item.strip()]
    resolutions = bundle["known_issue_resolutions"]
    resolved_issues = [
        item.get("issue") for item in resolutions if isinstance(item, dict)
    ] if isinstance(resolutions, list) else []
    if (
        len(issues) != len(set(issues))
        or len(resolved_issues) != len(issues)
        or len(resolved_issues) != len(set(resolved_issues))
        or set(resolved_issues) != set(issues)
    ):
        raise ValueError(f"{label}: known-issue resolution coverage mismatch")
    for item in resolutions:
        if (
            not isinstance(item, dict)
            or set(item) != {"issue", "resolution", "evidence"}
            or not str(item["resolution"]).strip()
            or not str(item["evidence"]).strip()
        ):
            raise ValueError(f"{label}: incomplete known-issue resolution")
    reviewed_at = parse_reviewed_at(str(bundle["reviewed_at"]), label)
    if (
        bundle["reviewer_name"] != row["signer_name"]
        or bundle["reviewer_organization_title"] != row["signer_organization_title"]
        or reviewed_at.date().isoformat() != row["decision_date"]
    ):
        raise ValueError(f"{label}: reviewer identity or decision date mismatch")
    return validate_truth_table(
        bundle, bundle_path, register_path, measure_id, criterion_ids, label
    )


def audit(
    approval_path: Path,
    measure_audit_path: Path,
    catalog_path: Path,
    criteria_path: Path,
    measure_fsh_path: Path,
    cql_path: Path,
    generated_resource_dir: Path,
) -> dict[str, object]:
    approvals = read_rows(approval_path, APPROVAL_COLUMNS)
    measure_audits = read_rows(measure_audit_path, AUDIT_COLUMNS)
    catalog = read_rows(catalog_path, CATALOG_COLUMNS)
    criteria = read_rows(criteria_path, CRITERIA_COLUMNS)
    if len(approvals) != 20 or len({row["measure_id"] for row in approvals}) != 20:
        raise ValueError(f"{approval_path}: expected 20 unique Measure approvals")
    if len({row["approval_id"] for row in approvals}) != 20:
        raise ValueError(f"{approval_path}: approval_id must be unique")
    catalogs = {row["measure_id"]: row for row in catalog}
    audits = {row["measure_id"]: row for row in measure_audits}
    measure_ids = {row["measure_id"] for row in approvals}
    if len(catalogs) != 20 or len(audits) != 20 or set(catalogs) != measure_ids or set(audits) != measure_ids:
        raise ValueError("Measure approval, catalog and audit sets differ")
    for row in approvals:
        measure_id = row["measure_id"]
        required = (
            "approval_id", "indicator_family", "decision_scope", "known_issue",
            "current_status", "required_signer", "acceptance_evidence",
        )
        if not all(row[field].strip() for field in required):
            raise ValueError(f"{approval_path}: {measure_id} has incomplete approval context")
        if row["current_status"] not in {
            "pending-human-signoff", "approved", "rejected", "revise",
        }:
            raise ValueError(f"{approval_path}: {measure_id} has invalid current_status")
        if not (
            row["indicator_family"] == catalogs[measure_id]["indicator_family"]
            == audits[measure_id]["indicator_family"]
        ):
            raise ValueError(f"{approval_path}: {measure_id} indicator family mismatch")
        if row["known_issue"] != audits[measure_id]["blocking_issue"]:
            raise ValueError(f"{approval_path}: {measure_id} omits or changes live blocking issues")
        if row["required_signer"] != audits[measure_id]["required_approval"]:
            raise ValueError(f"{approval_path}: {measure_id} required signer is stale")
    criteria_by_measure: dict[str, list[dict[str, str]]] = {
        measure_id: [] for measure_id in measure_ids
    }
    shared_ids = {"bc-qi-00": "quality", "bc-qr-00": "quarterly"}
    shared_by_family: dict[str, list[dict[str, str]]] = {
        "quality": [], "quarterly": [],
    }
    for criterion in criteria:
        if criterion["measure_id"] in shared_ids:
            shared_by_family[shared_ids[criterion["measure_id"]]].append(criterion)
        elif criterion["measure_id"] not in criteria_by_measure:
            raise ValueError(f"{criteria_path}: unknown Measure {criterion['measure_id']}")
        else:
            criteria_by_measure[criterion["measure_id"]].append(criterion)
    if len(criteria) != 68 or len({row["criterion_id"] for row in criteria}) != 68:
        raise ValueError(f"{criteria_path}: expected 68 unique criteria")
    for measure_id in measure_ids:
        family = catalogs[measure_id]["indicator_family"]
        criteria_by_measure[measure_id].extend(shared_by_family[family])
    expressions = measure_expressions(measure_fsh_path)
    generated = generated_measures(generated_resource_dir)
    if set(expressions) != measure_ids or set(generated) != measure_ids:
        raise ValueError("Measure FSH or generated-resource set differs from approvals")
    for measure_id in measure_ids:
        if generated_measure_expressions(generated[measure_id]) != expressions[measure_id]:
            raise ValueError(
                f"{generated_resource_dir}: {measure_id} expression set differs from FSH"
            )
    common_fsh_hash = file_sha256(measure_fsh_path)
    common_cql_hash = file_sha256(cql_path)
    approved = 0
    truth_case_count = 0
    required_truth_assertion_count = sum(
        len(rows) * 2 for rows in criteria_by_measure.values()
    )
    if required_truth_assertion_count != 208:
        raise ValueError(
            f"{criteria_path}: expected 208 per-Measure positive/negative assertions"
        )
    fingerprints: dict[str, str] = {}
    for row in approvals:
        measure_id = row["measure_id"]
        criterion_rows = sorted(
            criteria_by_measure[measure_id], key=lambda item: item["criterion_id"]
        )
        components = {
            "measure_fsh_sha256": common_fsh_hash,
            "cql_sha256": common_cql_hash,
            "generated_measure_sha256": canonical_sha256(generated[measure_id]),
            "catalog_row_sha256": canonical_sha256(catalogs[measure_id]),
            "population_criteria_sha256": canonical_sha256(criterion_rows),
            "measure_audit_row_sha256": canonical_sha256(audits[measure_id]),
            "approval_context_sha256": canonical_sha256(
                {field: row[field] for field in APPROVAL_CONTEXT_FIELDS}
            ),
        }
        fingerprints[measure_id] = canonical_sha256(components)
        if row["current_status"] == "approved" and row["decision"] == "approve":
            truth_case_count += validate_bundle(
                row,
                approval_path,
                components,
                expressions[measure_id],
                {item["criterion_id"] for item in criterion_rows},
            )
            approved += 1
    return {
        "gate_scope": "exact-live-measure-specification-and-truth-table-approval",
        "measure_count": 20,
        "population_criterion_count": 68,
        "measure_expression_use_count": sum(map(len, expressions.values())),
        "approved_measure_specification_count": approved,
        "approved_truth_table_case_count": truth_case_count,
        "required_truth_assertion_count": required_truth_assertion_count,
        "measure_specification_fingerprints": fingerprints,
        "measure_specification_integrity_gate": "pass",
        "measure_specification_approval_gate": (
            "pass" if approved == 20 and truth_case_count >= required_truth_assertion_count
            else "block"
        ),
        "maximum_supported_claim": (
            "approved-live-measure-specifications" if approved == 20
            else "technical-draft-measure-specifications"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval-register", type=Path, required=True)
    parser.add_argument("--measure-audit", type=Path, required=True)
    parser.add_argument("--measure-catalog", type=Path, required=True)
    parser.add_argument("--population-criteria", type=Path, required=True)
    parser.add_argument("--measure-fsh", type=Path, required=True)
    parser.add_argument("--cql", type=Path, required=True)
    parser.add_argument("--generated-resource-dir", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "approval"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(
            args.approval_register,
            args.measure_audit,
            args.measure_catalog,
            args.population_criteria,
            args.measure_fsh,
            args.cql,
            args.generated_resource_dir,
        )
    except (OSError, ValueError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Measure-specification approval audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        f"Measure specification approvals: "
        f"{report['approved_measure_specification_count']}/20; "
        f"truth cases={report['approved_truth_table_case_count']}"
    )
    print(f"Measure specification integrity gate: {report['measure_specification_integrity_gate']}")
    print(f"Measure specification approval gate: {report['measure_specification_approval_gate']}")
    selected = {
        "integrity": "measure_specification_integrity_gate",
        "approval": "measure_specification_approval_gate",
    }[args.target]
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
