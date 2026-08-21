#!/usr/bin/env python3
"""Audit human decisions for every non-aligned population criterion.

The register is intentionally tied to the live implementation crosscheck.  A
signature against an older issue statement must not silently approve a changed
rule, and a signature alone must not turn an unresolved technical gap into an
aligned implementation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

try:
    from scripts.approval_evidence import retained_evidence_matches
except ModuleNotFoundError:  # direct execution
    from approval_evidence import retained_evidence_matches


COLUMNS = [
    "decision_id",
    "criterion_id",
    "measure_id",
    "issue_class",
    "known_difference",
    "decision_group",
    "decision_scope",
    "decision_question",
    "required_outcome",
    "required_signer",
    "acceptance_evidence",
    "current_status",
    "decision",
    "approved_rule_or_contract",
    "signer_name",
    "signer_organization_title",
    "decision_date",
    "evidence_uri_path",
    "signed_artifact_sha256",
    "notes",
]

SHA256 = re.compile(r"[0-9a-fA-F]{64}")
ISSUE_FINGERPRINTS = {
    "IP-CLASS": "72e2c056538726b15852ffbba7f659ab288a0920d642bb423e53e8fa2f125e55",
    "X1-TEAM": "03ee520f10020ff933b9df14cbf971f6ae153506488e9ebf88c212eccf34f89d",
    "N1-HT": "57b8839557515dc5517e827386ee10c0b2ff6dfeb3afaedb1dc4d2c31021d7d8",
    "D2-SURGERY-FIRST": "3da2e733ce3b370c228e408216c18e40d8ff31d557709cc68c08d1e5b5a9fcda",
    "N3-DOSE": "1197225b390961f7e72b59a28d2a821087f9c6657d4a5aff978291b48024fb74",
    "N4-ANTIHER2": "c86f104bd385bc1f7e340c2d4da338d44c99433d0fd7a04f84bcec80234e1395",
    "X5-TEAM": "230c33d46615306c5e5c67f4a93d01615013e09cca39545bb9e5d3e75cae24f0",
    "N5-ADH-RULE": "14d51c84fb7a2bd043eef2fa933b219fd0965dc4da69409e049f696420cfff6a",
    "X6-AGE-NODE-DEF": "9be47a70491f9f75e60a301b3446b1b25f3d7d858fc3463b4125074c86eedcf2",
    "X6-AGE-PRACTICE": "f70e156dc07f0a7a079b96b6b744498ba3c8b315a0da5b60a3b3c2dec4b3fb81",
    "X6-NODE-PRACTICE": "29dad5773f13f83b78bdd3e27b5a657def5698fd1f6f1067647c5b691f9ec3bd",
    "X1-STAGING-DEATH": "cc76b871e46043624d2e7e0833813cb0a460cc488af1dc87089a564a3cd3746a",
    "X1-NOSTAY-TRANSFER": "0398236e6d5804608d1b4f0301754955a55f905c93e6cd6cbc16f700fc1f3d4d",
    "X3-STAGING": "440968d7b333d2b7e3f4bbd0720875c1d36727d2c649f3c6efa84a254456f77f",
    "D4-COHORT": "5821e6d6c82486e12932fda608aae884c76a62baf31b3632b6c4d65be7c2a70b",
    "N4-LOST": "e1f2193f7285af4b5781167f531adf82d9c80d6dffe4e569c12309eb0b00c59a",
    "N5-RETURN": "856b04c9c4d8e288ff888865320d64d92f601b70d7513b46f45676191bb710e4",
    "S17-HISTOLOGY": "1ad61de74b1741d0befba1ef72958cf7aa408d7639dc10664c94a8bda17da2b8",
}
PENDING_STATUSES = {
    "pending-human-decision",
    "pending-implementation",
    "pending-data-contract",
    "pending-definition-reconciliation",
}
EXPECTED_DECISION_COUNT = 18


DECISION_CONTEXT = {
    "IP-CLASS": {
        "group": "QI-COHORT-ASSEMBLY",
        "scope": "Group assembly before Measure evaluation",
        "question": "What executable rule creates the class 1/2 breast-cancer evaluation Group, including null and duplicate handling?",
        "outcome": "Implement the approved Group-assembly rule and prove that every included and excluded case has a reproducible reason.",
        "signer": "cohort owner; cancer-registry owner; FHIR/CQL owner",
        "evidence": "versioned cohort specification; executable assembly implementation; boundary truth table; case-level cohort reconciliation; signed artifact hash",
        "status": "pending-implementation",
    },
    "X1-TEAM": {
        "group": "QI-MDT-OVERRIDE",
        "scope": "multidisciplinary exclusion for QI-01",
        "question": "Which governed case-level decision excludes a patient after multidisciplinary review, and where is its reason and approver recorded?",
        "outcome": "Approve one explicit override contract and reconcile every QI-01 exclusion against the unadjusted CQL result.",
        "signer": "QI-01 clinical owner; multidisciplinary-team chair; data-governance owner",
        "evidence": "versioned override schema; Task or MeasureReport representation; positive negative and null truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "N1-HT": {
        "group": "QI-01-MEDICATION-EVENT",
        "scope": "actual hormone-therapy evidence for QI-01 numerator",
        "question": "Which event and source prove that hormone therapy was actually administered rather than merely ordered?",
        "outcome": "Replace MedicationRequest-existence inference with an approved delivery-event contract and reconcile every numerator case.",
        "signer": "QI-01 clinical owner; oncology pharmacy owner; FHIR/CQL owner",
        "evidence": "FHIR R4 resource decision; administration or approved dispense source contract; event-time rule; ordered-not-given and actually-given truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "D2-SURGERY-FIRST": {
        "group": "QI-02-FIRST-TREATMENT-EVENT",
        "scope": "actual systemic-treatment start for QI-02 ordering rule",
        "question": "Which actual administration event and timestamp determine whether surgery preceded systemic therapy?",
        "outcome": "Replace MedicationRequest.authoredOn with approved treatment-event time and reconcile before same-day and after-surgery cases.",
        "signer": "QI-02 clinical owner; oncology pharmacy owner; FHIR/CQL owner",
        "evidence": "FHIR R4 resource decision; administration source path; time and timezone contract; before same-day and after truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "N3-DOSE": {
        "group": "QI-03-RT-DOSE",
        "scope": "delivered radiotherapy dose threshold for QI-03 numerator",
        "question": "Which authoritative delivered-dose fact, target-volume semantics and unit conversion prove total dose is at least 4000 cGy?",
        "outcome": "Map an approved raw delivered-dose source, normalize UCUM units, enforce >=4000 cGy in CQL, and prove boundary cases below at and above the threshold.",
        "signer": "radiation-oncology owner; source-system owner; FHIR/CQL owner",
        "evidence": "source schema and lineage; FHIR profile/path; unit-conversion rule; 3999 4000 4001 cGy truth cases; independent case-level recalculation; signed artifact hash",
        "status": "pending-implementation",
    },
    "N4-ANTIHER2": {
        "group": "QI-04-ANTIHER2-EVENT",
        "scope": "actual anti-HER2 treatment evidence for QI-04 numerator",
        "question": "Which event and source prove that anti-HER2 therapy was actually administered rather than merely ordered?",
        "outcome": "Replace MedicationRequest-existence inference with an approved delivery-event contract and reconcile every numerator case.",
        "signer": "QI-04 clinical owner; oncology pharmacy owner; FHIR/CQL owner",
        "evidence": "FHIR R4 resource decision; administration or approved dispense source contract; event-time rule; ordered-not-given and actually-given truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "X5-TEAM": {
        "group": "QI-MDT-OVERRIDE",
        "scope": "multidisciplinary exclusion for QI-05",
        "question": "Which governed case-level decision excludes a patient after multidisciplinary review, and where is its reason and approver recorded?",
        "outcome": "Approve one explicit override contract and reconcile every QI-05 exclusion against the unadjusted CQL result.",
        "signer": "QI-05 clinical owner; multidisciplinary-team chair; data-governance owner",
        "evidence": "versioned override schema; Task or MeasureReport representation; positive negative and null truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "N5-ADH-RULE": {
        "group": "QI-05-ADH-ADD-BACK",
        "scope": "ADH committee numerator add-back for QI-05",
        "question": "What original result, reason, decision, approver and time are required to add a case back to the numerator?",
        "outcome": "Implement and approve a non-destructive add-back contract that preserves the original result and produces an auditable adjusted result.",
        "signer": "QI-05 clinical owner; pathology owner; data-governance owner",
        "evidence": "versioned add-back schema; before and after result representation; approval trail; positive negative revoked and missing-evidence truth cases; case-level reconciliation; signed artifact hash",
        "status": "pending-implementation",
    },
    "X6-AGE-NODE-DEF": {
        "group": "QI-06-AGE-NODE-VARIANT",
        "scope": "authoritative age and node exclusion semantics for QI-06",
        "question": "Is the production exclusion the written combined age-and-node rule or the historical separate age or node rule?",
        "outcome": "Approve exactly one variant, lock the production parameter, retire the competing production interpretation, and reconcile all changed denominator cases.",
        "signer": "cancer-committee chair; QI-06 clinical owner; quality owner",
        "evidence": "signed interpretation of the normative wording; locked parameter value; boundary truth table; historical-versus-approved case-level diff; signed artifact hash",
        "status": "pending-human-decision",
    },
    "X6-AGE-PRACTICE": {
        "group": "QI-06-AGE-NODE-VARIANT",
        "scope": "historical age-only exclusion variant for QI-06",
        "question": "Is the historical age-only exclusion retained as part of the approved production interpretation?",
        "outcome": "Use the same single signed variant decision and reconciliation as X6-AGE-NODE-DEF; no independent contradictory approval is allowed.",
        "signer": "cancer-committee chair; QI-06 clinical owner; quality owner",
        "evidence": "same signed decision package as QI-06-AGE-NODE-VARIANT; age boundary cases; case-level diff; signed artifact hash",
        "status": "pending-human-decision",
    },
    "X6-NODE-PRACTICE": {
        "group": "QI-06-AGE-NODE-VARIANT",
        "scope": "historical node-only exclusion variant for QI-06",
        "question": "Is the historical node-only exclusion retained as part of the approved production interpretation?",
        "outcome": "Use the same single signed variant decision and reconciliation as X6-AGE-NODE-DEF; no independent contradictory approval is allowed.",
        "signer": "cancer-committee chair; QI-06 clinical owner; quality owner",
        "evidence": "same signed decision package as QI-06-AGE-NODE-VARIANT; node boundary cases; case-level diff; signed artifact hash",
        "status": "pending-human-decision",
    },
    "X1-STAGING-DEATH": {
        "group": "QR-TREATMENT-BEFORE-DEATH",
        "scope": "actual curative treatment before death for QR-01",
        "question": "Which actual treatment event proves that curative treatment occurred before death, without treating an order as delivery?",
        "outcome": "Implement approved actual-treatment evidence and reconcile every death-before-treatment exclusion.",
        "signer": "QR-01 case-management owner; oncology treatment owner; FHIR/CQL owner",
        "evidence": "FHIR R4 resource decision; treatment-event source contract; order-only and administered-before-death truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "X1-NOSTAY-TRANSFER": {
        "group": "QR-01-TRANSFER-WITHOUT-TREATMENT",
        "scope": "transfer-during-staging numerator exclusion for QR-01",
        "question": "Must the transfer exclusion also prove that no local treatment occurred, as the declared rule currently states?",
        "outcome": "Implement the no-local-treatment predicate or approve revised wording and reconcile every transferred case.",
        "signer": "QR-01 case-management owner; quality-program owner; FHIR/CQL owner",
        "evidence": "approved criterion wording; treatment-event contract; transfer with and without local treatment truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "X3-STAGING": {
        "group": "QR-TREATMENT-BEFORE-DEATH",
        "scope": "actual curative treatment before staging death for QR-03",
        "question": "Which actual treatment event proves that curative treatment occurred before death, without treating an order as delivery?",
        "outcome": "Use the same approved actual-treatment evidence as QR-01 and reconcile all inherited QR-03 staging-death cases.",
        "signer": "QR-03 case-management owner; oncology treatment owner; FHIR/CQL owner",
        "evidence": "same signed treatment-before-death decision package; QR-03 inherited truth cases; case-level diff; signed artifact hash",
        "status": "pending-implementation",
    },
    "D4-COHORT": {
        "group": "QR-04-LONGITUDINAL-COHORT",
        "scope": "complete prior-year plus current QR-04 cohort",
        "question": "Which extract window, episode-scoped new-diagnosis discriminator and completeness assertion prove that all required prior-year and current cases were loaded?",
        "outcome": "Approve an executable longitudinal cohort contract with deterministic new-diagnosis inclusion, episode linkage, deduplication, late-arrival and completeness rules.",
        "signer": "QR-04 case-management owner; source-system owner; data-governance owner",
        "evidence": "versioned extract contract; source query and snapshot hash; completeness proof; late-arrival and duplicate truth cases; denominator reconciliation; signed artifact hash",
        "status": "pending-data-contract",
    },
    "N4-LOST": {
        "group": "QR-04-LONGITUDINAL-COHORT",
        "scope": "one-year loss-to-follow-up adjudication for QR-04",
        "question": "Which contact events count, what is the one-year anchor, and how is manual loss-to-follow-up adjudication recorded?",
        "outcome": "Approve longitudinal contact and adjudication semantics, then reconcile every numerator member inside the complete QR-04 cohort.",
        "signer": "QR-04 case-management owner; source-system owner; clinical validation owner",
        "evidence": "approved contact-event dictionary; anchor and interval rule; adjudication trail; one-year boundary and missing-contact truth cases; numerator reconciliation; signed artifact hash",
        "status": "pending-data-contract",
    },
    "N5-RETURN": {
        "group": "QR-05-RETURN-RULE",
        "scope": "return after treatment interruption for QR-05",
        "question": "What event starts an interruption, what subsequent event constitutes return, and how are same-day null and multiple episodes handled?",
        "outcome": "Approve event semantics and source lineage, then compare the candidate CQL with a case-manager-authored truth set and resolve every difference.",
        "signer": "QR-05 case-management owner; clinical owner; source-system owner",
        "evidence": "event dictionary and source path; interval rule; same-day null and multiple-episode truth cases; independent case-manager truth set; case-level diff; signed artifact hash",
        "status": "pending-human-decision",
    },
    "S17-HISTOLOGY": {
        "group": "QR-17-HISTOLOGY-GROUPS",
        "scope": "authoritative histology group count and terminology for QR-17",
        "question": "What are the exact approved histology groups: the ten implemented groups or an identified eleven-group set?",
        "outcome": "Resolve the source contradiction, publish the exact versioned group list and code membership, and reconcile every historical free-text normalization.",
        "signer": "pathology owner; cancer-registry owner; terminology reviewer",
        "evidence": "signed group definition; versioned ValueSet membership; mapping of all 27 historical spellings; unmapped and ambiguous-case policy; case-level reconciliation; signed artifact hash",
        "status": "pending-definition-reconciliation",
    },
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: empty CSV")
    return rows


def decision_complete(row: dict[str, str]) -> bool:
    if row["current_status"] != "approved" or row["decision"] != "approve":
        return False
    required = (
        "approved_rule_or_contract",
        "signer_name",
        "signer_organization_title",
        "decision_date",
        "evidence_uri_path",
        "signed_artifact_sha256",
    )
    if not all(row[field].strip() for field in required):
        return False
    try:
        date.fromisoformat(row["decision_date"])
    except ValueError:
        return False
    return SHA256.fullmatch(row["signed_artifact_sha256"].strip()) is not None


def decision_evidence_complete(row: dict[str, str], register_path: Path) -> bool:
    return decision_complete(row) and retained_evidence_matches(
        row,
        register_path,
        path_field="evidence_uri_path",
        hash_field="signed_artifact_sha256",
    )


def audit(register_path: Path, crosscheck_path: Path) -> dict[str, object]:
    decisions = read_rows(register_path)
    if list(decisions[0]) != COLUMNS:
        raise ValueError(f"{register_path}: columns must exactly match the locked schema")
    crosscheck = read_rows(crosscheck_path)
    crosscheck_by_id = {row["criterion_id"]: row for row in crosscheck}
    if len(crosscheck) != 68 or len(crosscheck_by_id) != 68:
        raise ValueError(f"{crosscheck_path}: expected exactly 68 unique criteria")
    missing_tracked = set(DECISION_CONTEXT) - set(crosscheck_by_id)
    new_untracked_gaps = {
        criterion_id
        for criterion_id, row in crosscheck_by_id.items()
        if row["cql_alignment"] != "aligned-to-current-draft"
        and criterion_id not in DECISION_CONTEXT
    }
    if missing_tracked or new_untracked_gaps:
        raise ValueError(
            f"{crosscheck_path}: decision coverage changed; "
            f"missing={sorted(missing_tracked)}, untracked_gaps={sorted(new_untracked_gaps)}"
        )
    if (
        len(decisions) != EXPECTED_DECISION_COUNT
        or {row["criterion_id"] for row in decisions} != set(DECISION_CONTEXT)
        or len({row["decision_id"] for row in decisions}) != EXPECTED_DECISION_COUNT
    ):
        raise ValueError(
            f"{register_path}: expected exactly one unique decision row for each "
            f"of {EXPECTED_DECISION_COUNT} non-aligned criteria"
        )

    for row in decisions:
        criterion_id = row["criterion_id"]
        issue = crosscheck_by_id[criterion_id]
        context = DECISION_CONTEXT[criterion_id]
        issue_fingerprint = hashlib.sha256(
            "\0".join(
                (criterion_id, row["issue_class"], row["known_difference"])
            ).encode("utf-8")
        ).hexdigest()
        if issue_fingerprint != ISSUE_FINGERPRINTS[criterion_id]:
            raise ValueError(f"{register_path}: {criterion_id} baseline issue changed")
        if issue["cql_alignment"] != "aligned-to-current-draft" and (
            row["issue_class"] != issue["cql_alignment"]
            or row["known_difference"] != issue["known_difference"]
        ):
            raise ValueError(f"{register_path}: {criterion_id} differs from live unresolved issue")
        expected = {
            "decision_id": f"CR-{criterion_id}",
            "measure_id": issue["measure_id"],
            "decision_group": context["group"],
            "decision_scope": context["scope"],
            "decision_question": context["question"],
            "required_outcome": context["outcome"],
            "required_signer": context["signer"],
            "acceptance_evidence": context["evidence"],
        }
        for field, value in expected.items():
            if row[field] != value:
                raise ValueError(f"{register_path}: {criterion_id} has stale {field}")
        if row["current_status"] not in PENDING_STATUSES | {"approved", "rejected", "revise"}:
            raise ValueError(f"{register_path}: {criterion_id} has invalid current_status")
        if row["current_status"] in PENDING_STATUSES:
            if row["current_status"] != context["status"]:
                raise ValueError(f"{register_path}: {criterion_id} has stale pending status")
            if any(
                row[field].strip()
                for field in (
                    "decision", "approved_rule_or_contract", "signer_name",
                    "signer_organization_title", "decision_date",
                    "evidence_uri_path", "signed_artifact_sha256",
                )
            ):
                raise ValueError(f"{register_path}: {criterion_id} pending row contains unsigned decision data")
        elif row["decision"] not in {"approve", "reject", "revise"}:
            raise ValueError(f"{register_path}: {criterion_id} has invalid decision")

    # These rows represent one inseparable interpretation and must never carry
    # contradictory approvals or point to different signed evidence.
    variant_rows = [
        row for row in decisions
        if row["decision_group"] == "QI-06-AGE-NODE-VARIANT"
    ]
    if any(decision_complete(row) for row in variant_rows):
        fields = (
            "current_status", "decision", "approved_rule_or_contract",
            "signer_name", "signer_organization_title", "decision_date",
            "evidence_uri_path", "signed_artifact_sha256",
        )
        for field in fields:
            if len({row[field] for row in variant_rows}) != 1:
                raise ValueError(f"{register_path}: QI-06 variant rows disagree on {field}")

    for row in decisions:
        if (
            row["current_status"] == "approved"
            and row["decision"] == "approve"
            and not decision_evidence_complete(row, register_path)
        ):
            raise ValueError(
                f"{register_path}: {row['criterion_id']} approved evidence is missing or SHA-256 mismatched"
            )

    approved = sum(decision_evidence_complete(row, register_path) for row in decisions)
    current_non_aligned = sum(
        crosscheck_by_id[criterion_id]["cql_alignment"]
        != "aligned-to-current-draft"
        for criterion_id in DECISION_CONTEXT
    )
    production_allowed = sum(
        crosscheck_by_id[criterion_id]["publication_disposition"]
        == "production-publication-allowed"
        for criterion_id in DECISION_CONTEXT
    )
    return {
        "gate_scope": "all-current-non-aligned-criterion-resolution-decisions",
        "decision_count": EXPECTED_DECISION_COUNT,
        "decision_group_count": len({row["decision_group"] for row in decisions}),
        "issue_class_counts": {
            key: sum(row["issue_class"] == key for row in decisions)
            for key in sorted({row["issue_class"] for row in decisions})
        },
        "approved_decision_count": approved,
        "pending_decision_count": EXPECTED_DECISION_COUNT - approved,
        "current_non_aligned_decision_count": current_non_aligned,
        "production_allowed_decision_count": production_allowed,
        "decision_register_integrity_gate": "pass",
        "criterion_resolution_gate": (
            "pass"
            if approved == EXPECTED_DECISION_COUNT
            and current_non_aligned == 0
            and production_allowed == EXPECTED_DECISION_COUNT
            else "block"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--register", type=Path, required=True)
    parser.add_argument("--crosscheck", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--target", choices=("integrity", "approval"), default="integrity")
    args = parser.parse_args()
    try:
        report = audit(args.register, args.crosscheck)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Criterion-resolution decision audit failed: {exc}", file=sys.stderr)
        return 2
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Criterion resolution decisions: {report['approved_decision_count']}/"
        f"{EXPECTED_DECISION_COUNT} approved; "
        f"integrity={report['decision_register_integrity_gate']}; "
        f"release={report['criterion_resolution_gate']}"
    )
    selected = "decision_register_integrity_gate" if args.target == "integrity" else "criterion_resolution_gate"
    return 0 if report[selected] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
